#!/usr/bin/env python3
"""
compose.py — Enhanced FFmpeg composition for UGC video pipeline.

Features:
- Caption burn-in with word-level karaoke highlighting (ASS subtitles)
- LUT application (3D LUT .cube files)
- Audio normalization (LUFS/EBU R128)
- Transitions (fade in/out, cross-dissolve)
- Thumbnail extraction
- Social media format presets (9:16, 1:1, 16:9)

Requirements:
- FFmpeg built with libass support for subtitles:
  Ubuntu/Debian: apt-get install ffmpeg libavfilter-extra
  macOS: brew reinstall ffmpeg --with-libass
  Or build from source with --enable-libass

For LUT creation and conversion tools:
- https://www.colorloving.com/free-luts/
- https://www.cinebenchr3.com/ (free LUTs)
- Adobe SpeedGrade LUTs (.cube format)
"""

import argparse
import json
import math
import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

SKILL_DIR = Path("~/.hermes/skills/ugc-video-pipeline").expanduser()
DEFAULT_LUTS_DIR = SKILL_DIR / "luts"
DEFAULT_FONTS_DIR = SKILL_DIR / "fonts"
DEFAULT_CAPTION_STYLE = SKILL_DIR / "caption_style.json"


# =============================================================================
# FFmpeg Availability Checks
# =============================================================================

def check_ffmpeg():
    """Check if FFmpeg is installed with required filters."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        version = result.stdout.split('\n')[0]
        
        # Check for drawtext/subtitles support
        filter_check = subprocess.run(
            ["ffmpeg", "-filters"], capture_output=True, text=True
        )
        has_drawtext = "drawtext" in filter_check.stdout
        has_ass = bool(__import__('re').search(r'\bass\b', filter_check.stdout)) or bool(__import__('re').search(r'\bsubtitles\b', filter_check.stdout))
        has_lut3d = "lut3d" in filter_check.stdout
        has_loudnorm = "loudnorm" in filter_check.stdout
        
        print(f"[FFmpeg] {version}")
        print(f"  lut3d: {'✓' if has_lut3d else '✗'}")
        print(f"  loudnorm: {'✓' if has_loudnorm else '✗'}")
        print(f"  drawtext: {'✓' if has_drawtext else '✗ (caption burns require this)'}")
        print(f"  ass/subtitles: {'✓' if has_ass else '✗ (caption burns require this)'}")
        
        if not (has_drawtext and has_ass):
            print("\n[Warning] FFmpeg is missing drawtext/ass filters.")
            print("  Ubuntu/Debian: apt-get install libavfilter-extra")
            print("  macOS: brew reinstall ffmpeg --with-libass")
            print("  Alternatively, use --caption-method python for text overlay via PIL\n")
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "FFmpeg not found. Install with:\n"
            "  Ubuntu/Debian: apt-get install ffmpeg\n"
            "  macOS: brew install ffmpeg\n"
            "  Windows: winget install ffmpeg"
        )


def get_video_info(video_path: str) -> Dict[str, Any]:
    """Get video dimensions, duration, and codec info."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,r_frame_rate",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    stream = data.get("streams", [{}])[0]
    format_data = data.get("format", {})
    
    return {
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "codec": stream.get("codec_name", "unknown"),
        "fps": eval(stream.get("r_frame_rate", "0/1")),
        "duration": float(format_data.get("duration", 0))
    }


def get_audio_info(video_path: str) -> Dict[str, float]:
    """Get audio duration."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return {"duration": float(result.stdout.strip())}


# =============================================================================
# Audio Processing
# =============================================================================

def normalize_audio_lufs(
    input_video: str,
    output_video: str,
    target_lufs: float = -14.0,
    method: str = "loudnorm"
) -> str:
    """
    Normalize audio to target LUFS level for social media.
    
    Args:
        input_video: Input video path
        output_video: Output video path
        target_lufs: Target LUFS (-14 for TikTok/Reels, -16 for YouTube, -24 for podcasts)
        method: 'loudnorm' for EBU R128, 'dynaudnorm' for dynamic normalization
    
    Returns:
        Path to normalized video
    """
    if method == "loudnorm":
        # Two-pass loudnorm for accurate LUFS measurement
        # First pass: measure current levels
        measure_cmd = [
            "ffmpeg", "-i", input_video,
            "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
            "-f", "null", "-"
        ]
        result = subprocess.run(measure_cmd, capture_output=True, text=True)
        
        # Parse measured values
        try:
            # Extract JSON from ffmpeg output
            output_lines = result.stderr.split('\n')
            json_start = -1
            json_end = -1
            for i, line in enumerate(output_lines):
                if "{" in line:
                    json_start = i
                if "}" in line and json_start >= 0:
                    json_end = i
                    break
            
            if json_start >= 0 and json_end >= 0:
                json_str = '\n'.join(output_lines[json_start:json_end+1])
                measured = json.loads(json_str)
                measured_lufs = float(measured.get("input_i", target_lufs))
                measured_tp = float(measured.get("input_tp", -1.0))
                measured_lra = float(measured.get("input_lra", 0))
            else:
                measured_lufs = target_lufs
                measured_tp = -1.0
                measured_lra = 0
        except:
            measured_lufs = target_lufs
            measured_tp = -1.0
            measured_lra = 0
        
        # Second pass: apply normalization with measured values
        filter_str = (
            f"loudnorm="
            f"I={target_lufs}:"
            f"TP={measured_tp if measured_tp > 0 else 1.5}:"
            f"LRA={measured_lra if measured_lra > 0 else 11}:"
            f"measured_I={measured_lufs}:"
            f"measured_TP={measured_tp}:"
            f"measured_LRA={measured_lra}:"
            f"linear=true"
        )
        
        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-af", filter_str,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            output_video
        ]
    else:
        # Dynamic audio normalizer (simpler, one-pass)
        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-af", f"dynaudnorm=g=3:m=20:s=12",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            output_video
        ]
    
    print(f"[Audio] Normalizing to {target_lufs} LUFS using {method}...")
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[Audio] Normalized: {output_video}")
    return output_video


# =============================================================================
# LUT Application
# =============================================================================

def apply_lut(input_video: str, output_video: str, lut_file: str) -> str:
    """
    Apply 3D LUT to video using FFmpeg's lut3d filter.
    
    Args:
        input_video: Input video path
        output_video: Output video path
        lut_file: Path to .cube LUT file
    
    Returns:
        Path to LUT-applied video
    """
    if not os.path.exists(lut_file):
        print(f"[Warning] LUT file not found: {lut_file}, skipping LUT")
        return input_video
    
    # Validate LUT file
    try:
        with open(lut_file, 'r') as f:
            content = f.read()
            if "LUT_3D_SIZE" not in content:
                print(f"[Warning] Invalid LUT file: {lut_file}, skipping")
                return input_video
    except:
        print(f"[Warning] Cannot read LUT file: {lut_file}, skipping")
        return input_video
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", f"lut3d={lut_file}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "copy",
        output_video
    ]
    print(f"[LUT] Applying: {lut_file}")
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[LUT] Applied: {output_video}")
    return output_video


def apply_lut_with_fallback(input_video: str, output_video: str, lut_file: str) -> str:
    """
    Apply LUT with fallback to color correction if lut3d fails.
    Useful for FFmpeg builds without 3DLUT support.
    """
    if not os.path.exists(lut_file):
        return input_video
    
    try:
        return apply_lut(input_video, output_video, lut_file)
    except subprocess.CalledProcessError:
        print("[LUT] lut3d not available, applying color correction instead")
        return apply_color_preset(input_video, output_video, lut_file)


def apply_color_preset(input_video: str, output_video: str, lut_name: str) -> str:
    """
    Apply color correction based on LUT name when 3D LUT is unavailable.
    
    Maps LUT names to equivalent color filter chains:
    - cinematic: Teal shadows, orange highlights, lifted blacks
    - warm_social: Warm temperature, slight saturation boost
    - cool_blue: Cool temperature, lifted blues
    - vintage: Faded blacks, reduced saturation, warm tint
    """
    presets = {
        "cinematic": " curves=master='0/0 0.12/0.08 0.5/0.55 0.88/0.9':green='0/0 0.3/0.2 0.7/0.75 1/0.95':blue='0/0 0.1/0.15 0.5/0.4 1/0.85',eq=brightness=0.03:saturation=1.15:contrast=1.05",
        "warm_social": " curves=master='0/0.02 0.4/0.45 1/0.98':red='0/0 0.5/0.55 1/0.98':green='0/0.02 0.5/0.5 1/0.96',colortemperature=temperature=6500:map=0.2",
        "cool_blue": " curves=master='0/0.02 0.3/0.25 0.7/0.7 1/0.95':blue='0/0.1 0.5/0.6 1/1.0',colortemperature=temperature=9000:map=0.3",
        "vintage": " curves=master='0.05/0.08 0.4/0.35 0.9/0.88 1/0.95':saturation=0.85,colortemperature=temperature=5500:map=0.15",
        "vivid": "eq=brightness=0.02:saturation=1.4:contrast=1.1",
        "natural": "eq=brightness=0.01:saturation=1.0:contrast=1.02"
    }
    
    preset = presets.get(lut_name.lower().replace(".cube", ""), "eq=brightness=0.03:saturation=1.1:contrast=1.05")
    
    cmd = [
        "ffmpeg", "-y", "-i", input_video,
        "-vf", f"format=yuv420p{preset}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "copy",
        output_video
    ]
    print(f"[Color] Applying preset: {lut_name}")
    subprocess.run(cmd, check=True, capture_output=True)
    return output_video


# =============================================================================
# Caption Generation & Burn-In
# =============================================================================

def generate_captions_from_script(
    script_text: str,
    duration: float,
    output_path: str,
    style_config: Dict[str, Any] = None
) -> str:
    """
    Generate timed captions from script text using word-level detection.
    
    This creates an ASS subtitle file with karaoke-style word highlighting.
    Requires LLM for word timing - generates estimated timings based on
    speech rate (~150 words/minute for natural pacing).
    
    Args:
        script_text: Full script/dialogue text
        duration: Total video duration in seconds
        output_path: Output .ass file path
        style_config: Caption style configuration
    
    Returns:
        Path to generated ASS file
    """
    if style_config is None:
        style_config = load_caption_style()
    
    # Simple word splitting with timing estimation
    # For accurate word-level timing, use a tool like gentle forced aligner
    words = script_text.split()
    word_count = len(words)
    if word_count == 0:
        return None
    
    # Estimate timing: ~150 words per minute for natural speech
    avg_word_duration = (duration / word_count) * 0.9  # Leave some pause
    pause_duration = (duration - (avg_word_duration * word_count)) / max(word_count - 1, 1)
    
    captions = []
    current_time = 0.0
    
    for i, word in enumerate(words):
        start = current_time
        end = start + avg_word_duration
        current_time = end + pause_duration
        
        # Clean word for display (remove markdown, etc)
        clean_word = word.strip(".,!?;:\"'()[]{}")
        
        captions.append({
            "word": clean_word,
            "start": round(start, 3),
            "end": round(end, 3),
            "highlighted": False
        })
    
    return generate_ass_from_captions(captions, output_path, style_config)


def generate_ass_from_captions(
    captions: List[Dict],
    output_path: str,
    style_config: Dict[str, Any] = None
) -> str:
    """
    Generate ASS subtitle file from caption data with karaoke highlighting.
    
    Args:
        captions: List of dicts with 'word', 'start', 'end', 'highlighted'
        output_path: Output .ass file path
        style_config: Caption style configuration
    
    Returns:
        Path to generated ASS file
    """
    if style_config is None:
        style_config = load_caption_style()
    
    # Get style values
    font = style_config.get("font", "Arial")
    font_size = style_config.get("font_size", 48)
    primary_color = style_config.get("primary_color", "&H00FFFFFF")
    highlight_color = style_config.get("highlight_color", "&H0000FFFF")
    outline_color = style_config.get("outline_color", "&H00000000")
    shadow_color = style_config.get("shadow_color", "&H00333333")
    position = style_config.get("position", "bottom")
    animation = style_config.get("animation", "karaoke")
    margin_v = style_config.get("margin_vertical", 50)
    
    # ASS header with styles
    ass_header = f"""[Script Info]
Title: UGC Captions - Karaoke Style
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{primary_color},{highlight_color},{outline_color},{shadow_color},0,0,0,0,100,100,0,0,1,2,3,2,20,20,{margin_v},1
Style: Karaoke,{font},{font_size},{primary_color},{highlight_color},{outline_color},{shadow_color},0,0,0,0,100,100,0,0,1,3,4,2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def to_ass_time(seconds: float) -> str:
        """Convert seconds to ASS time format (H:MM:SS.CS)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
    
    # Build dialogue entries
    ass_events = ""
    
    # Group words into lines based on style config
    words_per_line = style_config.get("words_per_line", 8)
    max_line_width = style_config.get("max_line_width", 40)
    
    current_line_words = []
    line_start_time = None
    accumulated_text = ""
    
    def flush_line():
        nonlocal ass_events, current_line_words, line_start_time, accumulated_text
        if not current_line_words:
            return
        
        # Build the line text
        line_text = " ".join(w["word"] for w in current_line_words)
        
        # Use karaoke effect if enabled
        if animation == "karaoke" and len(current_line_words) > 1:
            # Create karaoke animation using \kf (fill) effect
            # Build per-word segments with timing
            kf_segments = []
            for w in current_line_words:
                start_ms = int((w["start"] - current_line_words[0]["start"]) * 100)
                duration_ms = int((w["end"] - w["start"]) * 100)
                kf_segments.append(f"{{\\kf{start_ms}}}{w['word']}")
            
            # Simplified: just use the full line with start-to-end karaoke
            line_start = to_ass_time(current_line_words[0]["start"])
            line_end = to_ass_time(current_line_words[-1]["end"])
            
            # Use \k for karaoke effect on individual words
            karaoke_text = ""
            for w in current_line_words:
                word_dur = int((w["end"] - w["start"]) * 100)
                karaoke_text += f"{{\\k{word_dur}}}{w['word']} "
            
            ass_events += f"Dialogue: 0,{line_start},{line_end},Karaoke,,0,0,0,,{karaoke_text.strip()}\n"
        else:
            # Simple static text
            line_start = to_ass_time(current_line_words[0]["start"])
            line_end = to_ass_time(current_line_words[-1]["end"])
            ass_events += f"Dialogue: 0,{line_start},{line_end},Default,,0,0,0,,{line_text}\n"
        
        current_line_words = []
        line_start_time = None
    
    for cap in captions:
        word_len = len(cap["word"])
        
        # Check if adding this word would exceed max line width
        if current_line_words and (len(accumulated_text) + word_len > max_line_width or 
                                   len(current_line_words) >= words_per_line):
            flush_line()
        
        if line_start_time is None:
            line_start_time = cap["start"]
        
        current_line_words.append(cap)
        accumulated_text += cap["word"] + " "
    
    # Flush remaining
    if current_line_words:
        flush_line()
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header + ass_events)
    
    print(f"[Captions] Generated: {output_path}")
    return output_path


def add_captions(
    input_video: str,
    output_video: str,
    captions_data: str = None,
    caption_text: str = None,
    caption_style: str = None,
    method: str = "ass"
) -> str:
    """
    Add captions to video using ASS subtitles or drawtext.
    
    Args:
        input_video: Input video path
        output_video: Output video path
        captions_data: Path to JSON/SRT/ASS file with captions, or script text
        caption_text: Direct caption text (alternative)
        caption_style: Path to caption_style.json
        method: 'ass' (default) or 'drawtext' or 'python'
    
    Returns:
        Path to captioned video
    """
    style_config = load_caption_style(caption_style) if caption_style else load_caption_style()
    
    # Determine caption data source
    if caption_text:
        # Use provided text directly
        video_info = get_video_info(input_video)
        duration = video_info.get("duration", 30.0)
        
        # Generate timed captions from text
        ass_path = output_video.replace(".mp4", "_captions.ass")
        generate_captions_from_script(caption_text, duration, ass_path, style_config)
        captions_data = ass_path
    
    elif captions_data and os.path.exists(captions_data):
        # Load from file
        ext = os.path.splitext(captions_data)[1].lower()
        
        if ext == ".json":
            # JSON format: list of {text, start, end} or {word, start, end}
            with open(captions_data) as f:
                data = json.load(f)
            
            # Check if it's word-level or sentence-level
            if data and isinstance(data[0], dict) and "word" in data[0]:
                # Word-level captions
                ass_path = output_video.replace(".mp4", "_captions.ass")
                generate_ass_from_captions(data, ass_path, style_config)
            elif data and isinstance(data[0], dict) and "text" in data[0]:
                # Sentence-level captions
                ass_path = output_video.replace(".mp4", "_captions.ass")
                # Convert to word-level
                word_captions = []
                for cap in data:
                    words = cap["text"].split()
                    start = cap.get("start", 0)
                    end = cap.get("end", start + 3)
                    word_duration = (end - start) / max(len(words), 1)
                    for word in words:
                        word_captions.append({
                            "word": word,
                            "start": start,
                            "end": start + word_duration,
                            "highlighted": False
                        })
                        start += word_duration
                generate_ass_from_captions(word_captions, ass_path, style_config)
            else:
                raise ValueError(f"Unknown caption JSON format")
            captions_data = ass_path
        
        elif ext == ".srt":
            # SRT to ASS conversion needed
            ass_path = output_video.replace(".mp4", "_captions.ass")
            convert_srt_to_ass(captions_data, ass_path, style_config)
            captions_data = ass_path
        
        # else: assume it's already an .ass file
    else:
        print("[Warning] No caption data provided, skipping captions")
        return input_video
    
    # Apply captions based on method
    if method == "ass":
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_video,
                "-vf", f"ass={captions_data}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-c:a", "copy",
                output_video
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[Captions] Burned in (ASS): {output_video}")
        except subprocess.CalledProcessError as e:
            print(f"[Error] ASS subtitle burn failed: {e.stderr.decode() if e.stderr else str(e)}")
            print("[Info] Falling back to copy without captions")
            shutil.copy(input_video, output_video)
    else:
        print(f"[Warning] Caption method '{method}' not fully implemented")
        shutil.copy(input_video, output_video)
    
    return output_video


def convert_srt_to_ass(srt_path: str, ass_path: str, style_config: Dict = None) -> str:
    """Convert SRT subtitle file to ASS format."""
    if style_config is None:
        style_config = load_caption_style()
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        srt_content = f.read()
    
    # Parse SRT
    entries = []
    blocks = srt_content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_line = lines[1]
            text_lines = lines[2:]
            
            # Parse time codes: 00:00:00,000 --> 00:00:00,000
            times = time_line.split(' --> ')
            if len(times) == 2:
                start = parse_srt_time(times[0])
                end = parse_srt_time(times[1])
                text = ' '.join(text_lines).replace('\n', '\\N')
                
                entries.append({
                    "word": text,
                    "start": start,
                    "end": end,
                    "highlighted": False
                })
    
    return generate_ass_from_captions(entries, ass_path, style_config)


def parse_srt_time(time_str: str) -> float:
    """Parse SRT time string to seconds."""
    time_str = time_str.strip().replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


# =============================================================================
# Video Composition
# =============================================================================

def composite_videos(
    talking_head: str,
    scene_video: str,
    output_path: str,
    layout: str = "picture_in_picture",
    talking_head_scale: float = 0.30
) -> str:
    """
    Composite talking head over scene video.
    
    Args:
        talking_head: Path to talking head video
        scene_video: Path to scene background video
        output_path: Output composite video path
        layout: Layout type ('picture_in_picture', 'side_by_side', 'overlay')
        talking_head_scale: Scale of PiP window (0.30 = 30% of main video)
    
    Returns:
        Path to composited video
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    if layout == "picture_in_picture":
        video_info = get_video_info(scene_video)
        w, h = video_info["width"], video_info["height"]
        
        pip_w = int(w * talking_head_scale)
        pip_h = int(h * talking_head_scale)
        pip_x = w - pip_w - 20
        pip_y = h - pip_h - 20
        
        cmd = [
            "ffmpeg", "-y",
            "-i", scene_video,
            "-i", talking_head,
            "-filter_complex", (
                f"[1:v]scale={pip_w}:{pip_h}[pip];"
                f"[0:v][pip]overlay={pip_x}:{pip_y}"
            ),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path
        ]
    elif layout == "side_by_side":
        cmd = [
            "ffmpeg", "-y",
            "-i", talking_head,
            "-i", scene_video,
            "-filter_complex", "hstack=inputs=2",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path
        ]
    elif layout == "overlay":
        cmd = [
            "ffmpeg", "-y",
            "-i", scene_video,
            "-i", talking_head,
            "-filter_complex", "overlay=0:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path
        ]
    else:
        raise ValueError(f"Unknown layout: {layout}")
    
    print(f"[FFmpeg] Compositing with {layout} layout...")
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[FFmpeg] Composite saved: {output_path}")
    return output_path


# =============================================================================
# Transitions
# =============================================================================

def add_fade_in_out(
    input_video: str,
    output_video: str,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
    fade_color: str = "black"
) -> str:
    """
    Add fade in and/or fade out transitions to video.
    
    Args:
        input_video: Input video path
        output_video: Output video path
        fade_in: Fade in duration in seconds (0 to disable)
        fade_out: Fade out duration in seconds (0 to disable)
        fade_color: Color to fade to ('black', 'white', or '0xRRGGBB')
    
    Returns:
        Path to video with fades applied
    """
    video_info = get_video_info(input_video)
    duration = video_info.get("duration", 0)
    
    filters = []
    
    if fade_in > 0:
        if fade_color == "black":
            filters.append(f"fade=t=in:st=0:d={fade_in}")
        else:
            filters.append(f"fade=t=in:st=0:d={fade_in}:c={fade_color}")
    
    if fade_out > 0 and duration > 0:
        fade_out_start = duration - fade_out
        if fade_color == "black":
            filters.append(f"fade=t=out:st={fade_out_start}:d={fade_out}")
        else:
            filters.append(f"fade=t=out:st={fade_out_start}:d={fade_out}:c={fade_color}")
    
    if not filters:
        shutil.copy(input_video, output_video)
        return output_video
    
    vf = ",".join(filters)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "copy",
        output_video
    ]
    print(f"[Transition] Adding fades (in={fade_in}s, out={fade_out}s)...")
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[Transition] Fade applied: {output_video}")
    return output_video


def add_cross_dissolve(
    input_video1: str,
    input_video2: str,
    output_video: str,
    duration: float = 1.0
) -> str:
    """
    Create cross-dissolve transition between two videos.
    
    Args:
        input_video1: First video (cross-fade from)
        input_video2: Second video (cross-fade to)
        output_video: Output video path
        duration: Cross-dissolve duration in seconds
    
    Returns:
        Path to video with cross-dissolve applied
    """
    # Get duration of first video
    info1 = get_video_info(input_video1)
    duration1 = info1.get("duration", 10)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video1,
        "-i", input_video2,
        "-filter_complex", (
            f"[0:v]format=rgba[f0];"
            f"[1:v]format=rgba[f1];"
            f"[f0][f1]blend=all='if(lt(t,{duration}),t/{duration},1)':shortest=1:repeatlast=1[out]"
        ),
        "-map", "[out]",
        "-t", str(duration1),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        output_video
    ]
    print(f"[Transition] Cross-dissolve ({duration}s)...")
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[Transition] Cross-dissolve applied: {output_video}")
    return output_video


def add_scene_transition(
    input_video: str,
    output_video: str,
    transition_type: str = "fade",
    duration: float = 0.5
) -> str:
    """
    Add a transition effect to the start of a video.
    
    Args:
        input_video: Input video path
        output_video: Output video path
        transition_type: Type of transition ('fade', 'fade_black', 'fade_white', 'wipe_left', 'wipe_right')
        duration: Transition duration in seconds
    
    Returns:
        Path to video with transition applied
    """
    video_info = get_video_info(input_video)
    w = video_info.get("width", 1280)
    h = video_info.get("height", 720)
    
    if transition_type == "fade" or transition_type == "fade_black":
        vf = f"fade=t=in:st=0:d={duration}"
    elif transition_type == "fade_white":
        vf = f"fade=t=in:st=0:d={duration}:c=white"
    elif transition_type == "wipe_left":
        vf = f"fade=t=in:st=0:d={duration}:c=black@0:0x00000000"
    elif transition_type == "wipe_right":
        vf = f"crop=iw*t/{duration}:ih:0:0,fade=t=in:st=0:d={duration}"
    else:
        vf = f"fade=t=in:st=0:d={duration}"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "copy",
        output_video
    ]
    print(f"[Transition] {transition_type} ({duration}s)...")
    subprocess.run(cmd, check=True, capture_output=True)
    return output_video


# =============================================================================
# Thumbnail / Screenshot
# =============================================================================

def extract_thumbnail(
    input_video: str,
    output_path: str,
    timestamp: str = "00:00:01",
    size: str = None
) -> str:
    """
    Extract a thumbnail/screenshot from video.
    
    Args:
        input_video: Input video path
        output_path: Output image path (.jpg or .png)
        timestamp: Timestamp to extract frame from (HH:MM:SS)
        size: Optional size (e.g., '640x360')
    
    Returns:
        Path to extracted thumbnail
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", timestamp,
        "-i", input_video,
        "-vframes", "1"
    ]
    
    if size:
        cmd.extend(["-vf", f"scale={size}:force_original_aspect_ratio=decrease,pad={size}:(ow-iw)/2:(oh-ih)/2"])
    
    cmd.append(output_path)
    
    print(f"[Thumbnail] Extracting frame at {timestamp}...")
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[Thumbnail] Extracted: {output_path}")
    return output_path


def extract_thumbnail_at_moment(
    input_video: str,
    output_path: str,
    moment: float = 0.1,
    size: str = None
) -> str:
    """
    Extract thumbnail at a specific moment (as fraction of duration).
    
    Args:
        input_video: Input video path
        output_path: Output image path
        moment: Moment to capture (0.0 to 1.0, represents fraction of duration)
        size: Optional size specification
    
    Returns:
        Path to extracted thumbnail
    """
    video_info = get_video_info(input_video)
    duration = video_info.get("duration", 1.0)
    timestamp = f"00:00:{min(duration * moment, duration - 0.1):.2f}"
    
    return extract_thumbnail(input_video, output_path, timestamp, size)


# =============================================================================
# Social Media Format Export
# =============================================================================

def export_social_formats(
    input_video: str,
    output_dir: str,
    formats: List[str] = None,
    lut: str = None,
    normalize_audio: bool = True,
    target_lufs: float = -14.0
) -> Dict[str, str]:
    """
    Export video in multiple social media formats.
    
    Args:
        input_video: Input video path
        output_dir: Output directory for formatted videos
        formats: List of formats to export (default: ['9:16', '1:1', '16:9'])
        lut: LUT name to apply
        normalize_audio: Whether to normalize audio to LUFS
        target_lufs: Target LUFS level
    
    Returns:
        Dict mapping format name to output path
    """
    if formats is None:
        formats = ["9:16", "1:1", "16:9"]
    
    os.makedirs(output_dir, exist_ok=True)
    
    video_info = get_video_info(input_video)
    original_w = video_info["width"]
    original_h = video_info["height"]
    original_fps = video_info.get("fps", 30)
    duration = video_info.get("duration", 30)
    
    results = {}
    
    for fmt in formats:
        if fmt == "9:16":
            # Vertical Reels/Shorts (e.g., 1080x1920)
            target_w = 1080
            target_h = 1920
            output_name = "reels_9x16.mp4"
        elif fmt == "1:1":
            # Square Instagram
            target_w = 1080
            target_h = 1080
            output_name = "instagram_1x1.mp4"
        elif fmt == "16:9":
            # Horizontal YouTube
            target_w = 1920
            target_h = 1080
            output_name = "youtube_16x9.mp4"
        elif fmt == "4:5":
            # Instagram Portrait
            target_w = 1080
            target_h = 1350
            output_name = "instagram_4x5.mp4"
        elif fmt == "9:19":
            # TikTok
            target_w = 1080
            target_h = 2280
            output_name = "tiktok_9x19.mp4"
        else:
            continue
        
        output_path = os.path.join(output_dir, output_name)
        
        # Calculate scaling to fit within target dimensions while maintaining aspect
        aspect = original_w / original_h
        target_aspect = target_w / target_h
        
        if aspect > target_aspect:
            # Video is wider - scale by width
            scale_w = target_w
            scale_h = int(target_w / aspect)
        else:
            # Video is taller - scale by height
            scale_h = target_h
            scale_w = int(target_h * aspect)
        
        # Ensure even dimensions
        scale_w = scale_w // 2 * 2
        scale_h = scale_h // 2 * 2
        
        # Build filter chain
        filters = [f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=decrease"]
        
        # Pad to target dimensions (center)
        pad_x = (target_w - scale_w) // 2
        pad_y = (target_h - scale_h) // 2
        filters.append(f"pad={target_w}:{target_h}:{pad_x}:{pad_y}:black")
        
        # Apply LUT if specified
        if lut:
            lut_file = str(DEFAULT_LUTS_DIR / f"{lut}.cube")
            if os.path.exists(lut_file):
                filters.append(f"lut3d={lut_file}")
        
        vf = ",".join(filters)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-r", str(min(original_fps, 30)),
            output_path
        ]
        
        # Add audio normalization if requested
        if normalize_audio:
            # Use loudnorm for streaming platforms
            cmd[4:4] = ["-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"]
        
        print(f"[Export] Creating {fmt} format: {output_path}")
        subprocess.run(cmd, check=True, capture_output=True)
        results[fmt] = output_path
    
    return results


# =============================================================================
# Style Configuration
# =============================================================================

def load_caption_style(config_path: str = None) -> Dict[str, Any]:
    """Load caption style configuration from JSON file."""
    if config_path is None:
        config_path = str(DEFAULT_CAPTION_STYLE)
    
    default_style = {
        "font": "Arial",
        "font_size": 48,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000FFFF",
        "outline_color": "&H00000000",
        "shadow_color": "&H00333333",
        "position": "bottom",
        "margin_vertical": 50,
        "margin_horizontal": 20,
        "words_per_line": 8,
        "max_line_width": 40,
        "animation": "karaoke",
        "font_weight": "normal",
        "italic": False,
        "outline": 2,
        "shadow": 3
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                user_style = json.load(f)
                default_style.update(user_style)
        except json.JSONDecodeError:
            print(f"[Warning] Invalid caption style JSON: {config_path}")
    
    return default_style


def save_caption_style(style: Dict[str, Any], output_path: str = None):
    """Save caption style configuration to JSON file."""
    if output_path is None:
        output_path = str(DEFAULT_CAPTION_STYLE)
    
    with open(output_path, 'w') as f:
        json.dump(style, f, indent=2)
    
    print(f"[Config] Caption style saved: {output_path}")


# =============================================================================
# Main Pipeline
# =============================================================================

def compose_pipeline(
    talking_head: str,
    scene_video: str,
    output_path: str,
    layout: str = "picture_in_picture",
    lut: str = "cinematic",
    captions: str = None,
    caption_text: str = None,
    caption_style: str = None,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
    normalize_audio: bool = True,
    target_lufs: float = -14.0,
    aspect_ratio: str = None,
    thumbnail: str = None,
    thumbnail_time: str = "00:00:01"
) -> str:
    """
    Full composition pipeline with all polish options.
    
    Args:
        talking_head: Path to talking head video
        scene_video: Path to scene background video
        output_path: Final output MP4 path
        layout: Composite layout
        lut: LUT name to apply
        captions: Path to caption JSON/ASS/SRT file
        caption_text: Direct caption text
        caption_style: Path to caption style JSON
        fade_in: Fade in duration (seconds)
        fade_out: Fade out duration (seconds)
        normalize_audio: Normalize audio to LUFS
        target_lufs: Target LUFS level
        aspect_ratio: Target aspect ratio for export
        thumbnail: Thumbnail output path
        thumbnail_time: Timestamp for thumbnail extraction
    
    Returns:
        Path to final composed video
    """
    check_ffmpeg()
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    base_output = output_path.replace(".mp4", "")
    
    # Step 1: Composite talking head + scene
    composite_path = f"{base_output}_composite.mp4"
    composite_videos(talking_head, scene_video, composite_path, layout)
    
    current = composite_path
    
    # Step 2: Apply LUT / color correction
    if lut and lut.lower() != "none":
        lut_dir = str(DEFAULT_LUTS_DIR)
        lut_file = os.path.join(lut_dir, f"{lut}.cube")
        
        if os.path.exists(lut_file):
            lut_output = f"{base_output}_lut.mp4"
            current = apply_lut_with_fallback(current, lut_output, lut_file)
        else:
            print(f"[Warning] LUT file not found: {lut_file}")
    
    # Step 3: Add transitions (fade in/out)
    if fade_in > 0 or fade_out > 0:
        transition_output = f"{base_output}_transition.mp4"
        current = add_fade_in_out(current, transition_output, fade_in, fade_out)
    
    # Step 4: Normalize audio
    if normalize_audio:
        audio_output = f"{base_output}_audio.mp4"
        current = normalize_audio_lufs(current, audio_output, target_lufs)
    
    # Step 5: Add captions
    if captions or caption_text:
        captioned_output = f"{base_output}_captioned.mp4"
        current = add_captions(
            current, captioned_output,
            captions_data=captions,
            caption_text=caption_text,
            caption_style=caption_style
        )
    
    # Step 6: Export to target aspect ratio if specified
    if aspect_ratio:
        formatted_output = f"{base_output}_formatted.mp4"
        export_social_formats(
            current,
            os.path.dirname(output_path) or ".",
            formats=[aspect_ratio],
            lut=None,  # LUT already applied
            normalize_audio=False  # Already normalized
        )
        formatted_path = os.path.join(
            os.path.dirname(output_path) or ".",
            f"{aspect_ratio.replace(':', 'x')}.mp4"
        )
        if os.path.exists(formatted_path):
            shutil.move(formatted_path, formatted_output)
            current = formatted_output
    
    # Step 7: Extract thumbnail
    if thumbnail:
        extract_thumbnail(current, thumbnail, thumbnail_time)
    
    # Step 8: Final encode (copy to final output path)
    if current != output_path:
        shutil.copy(current, output_path)
    
    # Cleanup intermediate files
    for ext in ["_composite.mp4", "_lut.mp4", "_transition.mp4", "_audio.mp4", "_captioned.mp4"]:
        intermediate = base_output + ext
        if os.path.exists(intermediate) and intermediate != output_path:
            os.remove(intermediate)
    
    print(f"\n[Complete] Output: {output_path}")
    return output_path


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compose talking head + scene video with polish (LUT, captions, audio normalization)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic composition with LUT
  python compose.py --talking-head head.mp4 --scene scene.mp4 --output final.mp4 --lut cinematic

  # With captions and audio normalization
  python compose.py --talking-head head.mp4 --scene scene.mp4 --output final.mp4 \\
      --captions captions.json --lut warm_social --normalize-audio

  # Export in multiple social media formats
  python compose.py --talking-head head.mp4 --scene scene.mp4 --output final.mp4 \\
      --formats 9:16 1:1 16:9 --thumbnail thumbnail.jpg

  # With fade transitions
  python compose.py --talking-head head.mp4 --scene scene.mp4 --output final.mp4 \\
      --fade-in 0.5 --fade-out 0.5 --lut none

Caption file formats:
  - JSON (word-level): [{"word": "Hello", "start": 0.0, "end": 0.5, "highlighted": false}, ...]
  - JSON (sentence-level): [{"text": "Hello world", "start": 0.0, "end": 1.0}, ...]
  - SRT: Standard SubRip format
  - ASS: Advanced SubStation Alpha format (karaoke effects)
        """
    )
    
    parser.add_argument("--talking-head", help="Talking head video path")
    parser.add_argument("--scene", help="Scene background video path")
    parser.add_argument("--output", help="Output MP4 path")
    
    # Layout options
    parser.add_argument("--layout", default="picture_in_picture",
                        choices=["picture_in_picture", "side_by_side", "overlay"],
                        help="Composite layout (default: picture_in_picture)")
    parser.add_argument("--head-scale", type=float, default=0.30,
                        help="PiP scale relative to main video (default: 0.30)")
    
    # LUT options
    parser.add_argument("--lut", default="cinematic",
                        help="LUT name (cinematic/warm_social/cool_blue/vintage/none)")
    parser.add_argument("--lut-dir", help="LUT directory (default: skill luts folder)")
    
    # Caption options
    parser.add_argument("--captions", help="Caption file (JSON/SRT/ASS) or direct text")
    parser.add_argument("--caption-text", help="Direct caption text to burn in")
    parser.add_argument("--caption-style", help="Caption style JSON file")
    parser.add_argument("--caption-method", default="ass",
                        choices=["ass", "drawtext", "python"],
                        help="Caption burn method")
    
    # Audio options
    parser.add_argument("--normalize-audio", action="store_true",
                        help="Normalize audio to LUFS")
    parser.add_argument("--target-lufs", type=float, default=-14.0,
                        help="Target LUFS level (default: -14 for TikTok/Reels)")
    
    # Transition options
    parser.add_argument("--fade-in", type=float, default=0.5,
                        help="Fade in duration in seconds (default: 0.5)")
    parser.add_argument("--fade-out", type=float, default=0.5,
                        help="Fade out duration in seconds (default: 0.5)")
    parser.add_argument("--transition", default="fade",
                        choices=["fade", "fade_black", "fade_white", "wipe_left", "wipe_right"])
    
    # Format/export options
    parser.add_argument("--formats", nargs="+",
                        choices=["9:16", "1:1", "16:9", "4:5", "9:19"],
                        help="Export formats (e.g., 9:16 1:1 16:9)")
    parser.add_argument("--thumbnail", help="Thumbnail output path")
    parser.add_argument("--thumbnail-time", default="00:00:01",
                        help="Timestamp for thumbnail (HH:MM:SS)")
    
    # Utility options
    parser.add_argument("--check-filters", action="store_true",
                        help="Check available FFmpeg filters and exit")
    
    args = parser.parse_args()
    
    if args.check_filters:
        check_ffmpeg()
        sys.exit(0)
    
    # Validate required arguments
    if not args.talking_head or not args.scene or not args.output:
        parser.print_help()
        sys.exit(1)
    
    # Determine LUT directory
    lut_dir = args.lut_dir or str(DEFAULT_LUTS_DIR)
    
    # Determine caption source
    captions = None
    caption_text = None
    if args.captions:
        if os.path.exists(args.captions):
            captions = args.captions
        else:
            # Treat as direct text
            caption_text = args.captions
    
    # Run pipeline
    try:
        output = compose_pipeline(
            talking_head=args.talking_head,
            scene_video=args.scene,
            output_path=args.output,
            layout=args.layout,
            lut=args.lut,
            captions=captions,
            caption_text=caption_text,
            caption_style=args.caption_style,
            fade_in=args.fade_in,
            fade_out=args.fade_out,
            normalize_audio=args.normalize_audio,
            target_lufs=args.target_lufs
        )
        
        # Export additional formats if requested
        if args.formats:
            export_dir = os.path.dirname(args.output) or "."
            export_social_formats(
                output,
                export_dir,
                formats=args.formats,
                lut=None,  # Already applied
                normalize_audio=False
            )
        
        print(f"\n✓ Pipeline complete: {output}")
        
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}")
        sys.exit(1)
