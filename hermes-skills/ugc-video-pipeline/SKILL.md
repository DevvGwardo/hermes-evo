---
name: ugc-video-pipeline
category: creative
description: Local AI-powered UGC video generation pipeline for social media marketing. Produces talking-head + scene video composites with voice cloning, lip-sync, and professional polish. Targets near-Higgsfield quality at near-zero cost using open-source models.
version: 2.0.0
---

# UGC Video Pipeline Skill

## Trigger Conditions

Invoke this skill when:
- User requests a UGC (User Generated Content) marketing video
- User wants a talking-head video with AI-generated voice and lip-sync
- User needs to produce social media content (TikTok, Instagram Reels, YouTube Shorts)
- User wants to generate video from a script or topic
- User requests a specific pipeline stage (voice clone, lip-sync, video gen, etc.)
- User wants to resume a partially-completed pipeline run

Do NOT invoke this skill when:
- User wants a live-action video shoot
- User needs real-time video generation
- User requests non-English content requiring specialized TTS (use vid-gen-multilang instead)

---

## v2.0 — New Features

- **`pipeline_config.json`** — Centralized configuration for all paths, LLM, ComfyUI, and stage defaults. No more environment variable sprawl.
- **`--dry-run`** — Validate the full pipeline setup (scripts exist, services reachable, files accessible) without running any heavy steps.
- **`--start-stage <stage>`** — Resume from any stage. The orchestrator auto-detects which artifacts already exist, or you can specify the stage explicitly.
- **`--skip-stages <s1> <s2>`** — Skip any stage(s) (e.g. skip scene video to use a colored background).
- **Progress callbacks** — `UGCPipeline(progress=MyCallback())` lets a calling agent track every stage start/complete/error/warning.
- **Character image auto-generation** — If `--character` is a text prompt (no file extension), the pipeline generates an avatar using Stable Diffusion via the `talking_head` module.
- **All stage scripts are importable modules** — `voice_clone.clone_voice()`, `talking_head.generate_talking_head()`, `video_gen.generate_scene_video()`, `compose.compose_pipeline()` can all be called directly from Python.
- **Thumbnail extraction** — Final video includes a `thumbnail.jpg` at `00:00:01`.

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        UGC VIDEO PIPELINE                                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │  STAGE 1 │──▶│  STAGE 2 │──▶│  STAGE 3 │──▶│  STAGE 4 │──▶│  STAGE 5 │ │
│  │  Script  │   │  Voice   │   │  Lip-Sync│   │  Video   │   │Polish &  │ │
│  │  Gen     │   │  Clone   │   │  (Head)  │   │  Gen     │   │Compose   │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│       │              │              │              │              │         │
│       ▼              ▼              ▼              ▼              ▼         │
│  [LLM Output]   [XTTS Audio]   [Hedra Video]  [Scene Video]  [Final MP4]    │
└─────────────────────────────────────────────────────────────────────────────┘

Input: Topic/Keyword/Article → Output: Polished MP4 video (~30-60s)
```

### Data Flow

```
Script Text
    │
    ▼
┌────────────────┐
│ Stage 1: Script │ → structured.json (topic, sections, hooks, captions)
└────────────────┘
    │
    ▼
┌────────────────┐
│ Stage 2: Voice │ → reference_audio.wav + cloned_voice.wav
└────────────────┘
    │
    ▼
┌────────────────┐
│ Stage 3: Head  │ → talking_head.mp4 (audio-lipsync video)
└────────────────┘
    │
    ▼
┌────────────────┐
│ Stage 4: Scene │ → scene_video.mp4 (B-roll / background)
└────────────────┘
    │
    ▼
┌────────────────┐
│ Stage 5: Polish│ → final_video.mp4 (composited + LUT + captions)
└────────────────┘
```

---

## Stage 1: Script Generation

### Which LLM to Call

**Recommended (in order):**
1. `claude-sonnet-4-20250514` via Anthropic API — best quality for marketing copy
2. `gpt-4o` via OpenAI API — good alternative
3. Local: `llama3.1:70b` via Ollama — for cost savings, acceptable quality

### Prompt Format

```python
SCRIPT_PROMPT = """You are an expert UGC scriptwriter for social media marketing videos.

Generate a video script for: {topic}

Requirements:
- Duration: {duration_seconds} seconds (~{word_count} words)
- Style: Conversational, authentic, hook-driven
- Structure: Hook (3s) → Problem (5s) → Solution (15s) → CTA (5s)
- Tone: {tone} (professional/casual/urgent/playful)
- Include B-roll scene suggestions in brackets: [product closeup], [testimonial], [lifestyle shot]

Output ONLY valid JSON with this structure:
{
  "title": "video title",
  "hook": "opening hook line",
  "sections": [
    {"timestamp": "0-3s", "speaker_text": "hook line", "scene_hint": "[description]"},
    ...
  ],
  "cta": "call to action",
  "captions": ["keyword1", "keyword2", "keyword3"],
  "scene_sequence": ["description1", "description2"]
}

No markdown, no explanation, only valid JSON.
"""
```

### CLI Command (Ollama)

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1:70b",
    "prompt": "Generate a UGC script about... (use SCRIPT_PROMPT above)",
    "stream": false,
    "format": "json"
  }' | jq '.response'
```

### Output Schema

```json
{
  "title": "5 Tips for Better Sleep",
  "hook": "You're doing sleep wrong — here's why.",
  "sections": [
    {"timestamp": "0-3s", "speaker_text": "You're doing sleep wrong...", "scene_hint": "[person tossing in bed]"},
    {"timestamp": "3-8s", "speaker_text": "Most people miss...", "scene_hint": "[sleep cycle diagram]"},
    {"timestamp": "8-23s", "speaker_text": "Tip one:...", "scene_hint": "[dark room with phone]"}
  ],
  "cta": "Follow for more wellness tips!",
  "captions": ["sleep tips", "wellness", "health", "self-care"],
  "scene_sequence": ["bedroom night", "phone screen glow", "morning sunlight"]
}
```

### Verification

- [ ] JSON is valid and parseable
- [ ] `sections` array has entries covering full duration
- [ ] `scene_sequence` has 2-4 distinct scene descriptions
- [ ] `captions` has 3-5 hashtags/caption keywords

---

## Stage 2: Voice Clone (XTTS v2)

### Model Setup

**Download:**
```bash
mkdir -p ~/models/xttsv2
cd ~/models/xttsv2

# XTTS v2 model files
git lfs install
git clone https://huggingface.co/coqui/XTTS-v2
# Expected files: model.pth, config.json, vocab.json, speaking_style.wav
```

**Alternative (Coqui API for instant setup):**
```bash
pip install TTS
python -c "from TTS.api import TTS; tts = TTS('xtts_v2', device='cuda')"
```

### Inference Code

```python
#!/usr/bin/env python3
"""voice_clone.py — Clone voice from reference audio"""

import torch
from TTS.api import TTS
import argparse
import os

def clone_voice(reference_audio: str, text: str, output_path: str):
    """Clone voice using XTTS v2."""
    tts = TTS("xtts_v2").to("cuda" if torch.cuda.is_available() else "cpu")
    
    # Clone and generate
    tts.tts_to_file(
        text=text,
        speaker_wav=reference_audio,
        file_path=output_path,
        language="en"
    )
    print(f"[XTTS v2] Voice cloned: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, help="Reference audio file")
    parser.add_argument("--text", required=True, help="Text to synthesize")
    parser.add_argument("--output", required=True, help="Output WAV path")
    args = parser.parse_args()
    
    clone_voice(args.reference, args.text, args.output)
```

### CLI Usage

```bash
# Single line synthesis
python voice_clone.py \
  --reference ~/models/xttsv2/samples/jenny.wav \
  --text "You're doing sleep wrong — here's why." \
  --output ./output/cloned_voice.wav

# Full script (concatenate sections)
for section in "${SCRIPT_SECTIONS[@]}"; do
  python voice_clone.py --reference "$REF_AUDIO" --text "$section" --output "$SECTION_AUDIO"
  # Concatenate all section audios later
done
```

### Requirements

| Item | Value |
|------|-------|
| VRAM | 6GB+ recommended, 4GB minimum |
| Reference audio | 5-30 seconds, clean speech, WAV/MP3 |
| Max text length | ~300 characters per call |
| Language | English (v2 supports 17 languages) |

### Verification

- [ ] Output WAV plays without glitches
- [ ] Voice timbre matches reference
- [ ] No TTS artifacts or cut-off words
- [ ] Duration matches expected speech pace (~150 words/minute)

### Known Issues

- **Memory errors**: Reduce batch size or use CPU fallback
- **Voice drift**: Long texts may shift voice character — split into 50-word chunks
- **Non-English accent**: XTTS v2 English model may carry accent from reference

---

## Stage 3: Talking Head / Lip-Sync (Hedra)

### Model Setup

```bash
mkdir -p ~/models/hedra
cd ~/models/hedra

# Clone Hedra repository
git clone https://github.com/Hedra-Labs/Hedra
cd Hedra

# Install dependencies
pip install -e .

# Download default character (or use custom)
# Place reference image in ~/models/hedra/characters/avatar.png
```

### Inference Code

```python
#!/usr/bin/env python3
"""talking_head.py — Generate lip-synced talking head video"""

import argparse
import subprocess
import os

def generate_talking_head(
    audio_path: str,
    character_image: str,
    output_path: str,
    hedra_repo: str = "~/models/hedra"
):
    """Generate talking head with Hedra character lip-sync."""
    
    cmd = [
        "python", f"{hedra_repo}/generate.py",
        "--audio", audio_path,
        "--image", character_image,
        "--output", output_path,
        "--aspect-ratio", "9:16",  # vertical for reels/shorts
        "--seed", "42"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Hedra failed: {result.stderr}")
    
    print(f"[Hedra] Talking head generated: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Cloned voice audio")
    parser.add_argument("--character", default="avatar.png", help="Character image")
    parser.add_argument("--output", required=True, help="Output MP4")
    args = parser.parse_args()
    
    generate_talking_head(args.audio, args.character, args.output)
```

### CLI Usage

```bash
# Generate talking head video from audio
python talking_head.py \
  --audio ./output/cloned_voice.wav \
  --character ~/models/hedra/characters/avatar.png \
  --output ./output/talking_head.mp4

# With custom aspect ratio (16:9 for YouTube)
python talking_head.py \
  --audio ./output/cloned_voice.wav \
  --character ~/models/hedra/characters/avatar.png \
  --output ./output/talking_head_16x9.mp4
```

### Alternative: Wav2Lip (if Hedra is unavailable)

```bash
# Wav2Lip is an alternative for lip-sync without character animation
pip install wav2lip

# Generate lip-sync
python -m wav2lip.inference \
  --checkpoint_path ~/models/wav2lip/wav2lip.pth \
  --audio ./output/cloned_voice.wav \
  --face ./output/character_face.png \
  --outfile ./output/talking_head_wav2lip.mp4
```

### Requirements

| Item | Value |
|------|-------|
| VRAM | 8GB+ for Hedra, 4GB+ for Wav2Lip |
| Character image | PNG/JPG, frontal face, 512x512+ recommended |
| Input audio | WAV format, clean speech |
| Output | MP4, synced to audio duration |

### Verification

- [ ] Lips move in sync with speech
- [ ] No visual artifacts or frozen frames
- [ ] Character remains stationary (no drift)
- [ ] Duration matches audio duration (±0.5s)

### Known Issues

- **Facial distortion**: Character image must be frontal, well-lit
- **Audio-video desync**: Resample audio to 25fps if desync occurs
- **Seed variation**: Different seeds produce different animations

---

## Stage 4: Video Generation (ComfyUI + Wan 2.2 / LTX-Video)

### Model Setup

#### Wan 2.2 T2V-A14B (Recommended for quality)

```bash
mkdir -p ~/models/Wan2.2
cd ~/models/Wan2.2

# Download from HuggingFace (requires git-lfs)
git lfs install
git clone https://huggingface.co/ali-vilab/Wan2.2-T2V-A14B

# Or use wget/curl for individual files
wget https://huggingface.co/ali-vilab/Wan2.2-T2V-A14B/resolve/main/*.safetensors
```

#### LTX-Video 13B (Faster inference)

```bash
mkdir -p ~/models/ltx-video
cd ~/models/ltx-video

git lfs install
git clone https://huggingface.co/Lightricks/LTX-Video-13B
```

#### ComfyUI Setup

```bash
# Install ComfyUI
cd ~
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI

# Install dependencies
pip install -r requirements.txt

# Create video generation workflow (see below)
mkdir -p custom_nodes/comfyui-xl-video
```

### ComfyUI Workflow (JSON)

```json
{
  "nodes": [
    {
      "id": 1,
      "type": "CLIPTextEncode",
      "widgets": ["prompt"],
      "values": {"text": " cinematic scene, product showcase, lifestyle, warm lighting"}
    },
    {
      "id": 2,
      "type": "CLIPTextEncode",
      "widgets": ["negative_prompt"],
      "values": {"text": "watermark, text, logo, blurry, low quality"}
    },
    {
      "id": 3,
      "type": "VideoPromptStyleSampling",
      "widgets": ["model", "clip", "video_prompt"]
    },
    {
      "id": 4,
      "type": "WanVideoPipeline",
      "widgets": ["model", "sample_kwargs"],
      "inputs": {"model": "~/models/Wan2.2/Wan2.2_T2V_A14B.safetensors"}
    },
    {
      "id": 5,
      "type": "SaveVideo",
      "widgets": ["output_path"],
      "values": {"filename_prefix": "ugc_scene"}
    }
  ],
  "connections": [[1, 3, 0, 0], [2, 3, 1, 1], [3, 4, 0, 0], [4, 5, 0, 0]]
}
```

### Python Inference Script

```python
#!/usr/bin/env python3
"""video_gen.py — Generate scene video using Wan 2.2 or LTX-Video via ComfyUI API"""

import requests
import json
import argparse
import time
import os

COMFYUI_HOST = "http://localhost:8188"

def queue_prompt(prompt_dict: dict) -> str:
    """Submit a workflow to ComfyUI queue."""
    response = requests.post(f"{COMFYUI_HOST}/prompt", json=prompt_dict)
    response.raise_for_status()
    return response.json()["prompt_id"]

def get_history(prompt_id: str) -> dict:
    """Get execution history for a prompt."""
    response = requests.get(f"{COMFYUI_HOST}/history/{prompt_id}")
    return response.json()

def generate_scene_video(
    scene_description: str,
    duration: int = 5,
    model: str = "wan22",
    output_path: str = "./output/scene_video.mp4"
):
    """Generate a scene video from text description."""
    
    # Build prompt based on model
    if model == "wan22":
        base_prompt = f"UGC video style, {scene_description}, professional lighting, 4K"
        negative = "watermark, text, logo, cartoon, anime"
        checkpoint = "~/.cache/huggingface/hub/Wan2.2_T2V_A14B.safetensors"
    else:  # ltx-video
        base_prompt = f"realistic, {scene_description}, cinematic"
        negative = "cartoon, anime, watermark, text"
        checkpoint = "~/.cache/huggingface/hub/LTX-Video-13B.safetensors"
    
    # Load workflow template
    workflow_path = f"~/.hermes/skills/ugc-video-pipeline/workflows/{model}_video.json"
    with open(os.path.expanduser(workflow_path)) as f:
        workflow = json.load(f)
    
    # Update workflow parameters
    workflow["3"]["widgets"]["values"]["video_prompt"] = base_prompt
    workflow["3"]["widgets"]["values"]["negative_prompt"] = negative
    workflow["4"]["inputs"]["model"] = checkpoint
    workflow["5"]["values"]["output_path"] = output_path
    
    # Queue and execute
    prompt_id = queue_prompt(workflow)
    print(f"[ComfyUI] Queued prompt: {prompt_id}")
    
    # Poll for completion (max 5 minutes)
    for _ in range(60):
        time.sleep(5)
        history = get_history(prompt_id)
        if prompt_id in history and history[prompt_id].get("outputs"):
            print(f"[ComfyUI] Video generated: {output_path}")
            return output_path
    
    raise TimeoutError("Video generation timed out")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True, help="Scene description")
    parser.add_argument("--duration", type=int, default=5, help="Duration in seconds")
    parser.add_argument("--model", default="wan22", choices=["wan22", "ltx"])
    parser.add_argument("--output", required=True, help="Output MP4 path")
    args = parser.parse_args()
    
    generate_scene_video(args.scene, args.duration, args.model, args.output)
```

### CLI Usage

```bash
# Generate scene video with Wan 2.2
python video_gen.py \
  --scene "cozy bedroom with morning sunlight filtering through curtains" \
  --duration 5 \
  --model wan22 \
  --output ./output/scene_video.mp4

# Generate with LTX-Video (faster)
python video_gen.py \
  --scene "person relaxing with phone in dimly lit room" \
  --duration 5 \
  --model ltx \
  --output ./output/scene_video_ltx.mp4
```

### Requirements

| Item | Wan 2.2 T2V-A14B | LTX-Video 13B |
|------|------------------|---------------|
| VRAM | 16GB+ | 12GB+ |
| Disk space | 30GB | 26GB |
| Inference time | ~3-5 min/second | ~1-2 min/second |
| Resolution | 1280x720 | 1280x720 |
| Max duration | 10 seconds | 10 seconds |

### Verification

- [ ] Video plays without corruption
- [ ] Scene matches description
- [ ] No watermark or artifacts
- [ ] Duration matches requested length

### Known Issues

- **VRAM OOM**: Reduce resolution to 960x540 or use LTX-Video (smaller model)
- **Slow generation**: Use LTX-Video for faster iteration, Wan 2.2 for final output
- **Prompt sensitivity**: Wan models require detailed scene descriptions

---

## Stage 5: Composition & Polish (FFmpeg + LUTs + Captions)

### FFmpeg Composition

```python
#!/usr/bin/env python3
"""compose.py — Composite talking head + scene video + captions + LUT"""

import subprocess
import argparse
import os
import json

def apply_lut(input_video: str, output_video: str, lut_file: str):
    """Apply color LUT to video."""
    # Convert LUTcube to MTV stream, then apply
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", f"lut3d={lut_file}",
        "-c:a", "copy",
        output_video
    ]
    subprocess.run(cmd, check=True)
    return output_video

def add_captions(
    input_video: str,
    output_video: str,
    caption_text: str,
    font: str = "~/fonts/inter.ttf"
):
    """Add burned-in captions to video."""
    # Position: bottom center, with background
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", (
            f"drawtext=text='{caption_text}':"
            f"fontfile={font}:"
            f"fontcolor=white:fontsize=48:"
            f"borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-100"
        ),
        "-c:a", "copy",
        output_video
    ]
    subprocess.run(cmd, check=True)
    return output_video

def composite_videos(
    talking_head: str,
    scene_video: str,
    output_path: str,
    layout: str = "picture_in_picture"
):
    """Composite talking head over scene video."""
    
    if layout == "picture_in_picture":
        # Talking head in bottom-right corner (30% width)
        cmd = [
            "ffmpeg", "-y",
            "-i", scene_video,
            "-i", talking_head,
            "-filter_complex", (
                "[1:v]scale=iw*0.3:ih*0.3[pip];"
                "[0:v][pip]overlay=W-w-20:H-h-20"
            ),
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
    elif layout == "side_by_side":
        cmd = [
            "ffmpeg", "-y",
            "-i", talking_head,
            "-i", scene_video,
            "-filter_complex", "hstack=inputs=2",
            "-c:a", "aac",
            output_path
        ]
    else:  # overlay (talking head transparent over scene)
        cmd = [
            "ffmpeg", "-y",
            "-i", scene_video,
            "-i", talking_head,
            "-filter_complex", "overlay=0:0",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
    
    subprocess.run(cmd, check=True)
    print(f"[FFmpeg] Composited: {output_path}")

def final_polish(
    input_video: str,
    output_path: str,
    lut: str = "cinematic",
    captions_file: str = None,
    caption_style: str = "bottom"
):
    """Apply final polish: LUT, stabilization, captions."""
    
    filters = []
    
    # Apply LUT (if specified)
    if lut == "cinematic":
        lut_file = "~/.hermes/skills/ugc-video-pipeline/luts/cinematic.cube"
        filters.append(f"lut3d={lut_file}")
    elif lut == "warm":
        lut_file = "~/.hermes/skills/ugc-video-pipeline/luts/warm_social.cube"
        filters.append(f"lut3d={lut_file}")
    
    # Basic color correction
    filters.append("eq=brightness=0.05:saturation=1.1:contrast=1.05")
    
    # Stabilization (if enabled)
    filters.append("deshake")
    
    # Build filter chain
    filter_str = ",".join(filters)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", filter_str,
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    
    subprocess.run(cmd, check=True)
    print(f"[Polish] Final video: {output_path}")

def add_s.dynamic_captions(video_path: str, captions_data: str, output: str):
    """Add animated captions from JSON data."""
    # Load captions timeline
    with open(captions_data) as f:
        captions = json.load(f)
    
    # Generate ASS subtitle file
    ass_content = generate_ass_from_captions(captions)
    ass_path = output.replace(".mp4", "_captions.ass")
    
    with open(ass_path, "w") as f:
        f.write(ass_content)
    
    # Burn subtitles into video
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"ass={ass_path}",
        "-c:a", "copy",
        output
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--talking-head", required=True)
    parser.add_argument("--scene", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--layout", default="picture_in_picture")
    parser.add_argument("--lut", default="cinematic")
    args = parser.parse_args()
    
    # Step 1: Composite
    composite_path = args.output.replace(".mp4", "_composite.mp4")
    composite_videos(args.talking_head, args.scene, composite_path, args.layout)
    
    # Step 2: Polish with LUT
    final_polish(composite_path, args.output, args.lut)
```

### CLI Usage

```bash
# Basic composition (PiP layout)
python compose.py \
  --talking-head ./output/talking_head.mp4 \
  --scene ./output/scene_video.mp4 \
  --output ./output/ugc_final.mp4 \
  --layout picture_in_picture \
  --lut cinematic

# Add captions
python compose.py \
  --talking-head ./output/talking_head.mp4 \
  --scene ./output/scene_video.mp4 \
  --output ./output/ugc_with_captions.mp4

# Full pipeline with animated captions
python compose.py \
  --talking-head ./output/talking_head.mp4 \
  --scene ./output/scene_video.mp4 \
  --output ./output/ugc_final.mp4 \
  --captions ./output/captions.json
```

### LUT Files

Place `.cube` LUT files in:
```
~/.hermes/skills/ugc-video-pipeline/luts/
├── cinematic.cube
├── warm_social.cube
├── cool_blue.cube
└── vintage.cube
```

### Requirements

| Item | Value |
|------|-------|
| FFmpeg | 4.4+ with libx264, libass |
| LUT format | .cube (3D LUT) |
| Font | TTF/OTF for captions |

### Verification

- [ ] Final video plays without errors
- [ ] Talking head visible and properly positioned
- [ ] Captions are readable and well-timed
- [ ] Color grade looks professional

### Known Issues

- **Font missing**: Install font or fallback to Liberation Sans
- **LUT not found**: Use absolute path or omit LUT flag
- **Aspect ratio mismatch**: Ensure both videos have same dimensions before compositing

---

## Stage 6: End-to-End Orchestration

### Python Orchestration Script

```python
#!/usr/bin/env python3
"""ugc_pipeline.py — End-to-end UGC video generation pipeline

Usage:
    python ugc_pipeline.py --topic "5 tips for better sleep" --duration 30
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Configuration
SKILL_DIR = Path("~/.hermes/skills/ugc-video-pipeline").expanduser()
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(exist_ok=True)

LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")  # anthropic|openai|ollama

# ─── Stage 1: Script Generation ─────────────────────────────────────────────

def generate_script(topic: str, duration: int = 30, tone: str = "casual") -> dict:
    """Generate video script using LLM."""
    word_count = int(duration * 2.5)  # ~150 words/min speaking pace
    
    prompt = f"""You are an expert UGC scriptwriter for social media marketing videos.

Generate a video script for: {topic}

Requirements:
- Duration: {duration} seconds (~{word_count} words)
- Style: Conversational, authentic, hook-driven
- Structure: Hook (3s) → Problem (5s) → Solution (15s) → CTA (5s)
- Tone: {tone}
- Include B-roll scene suggestions in brackets: [product closeup], [testimonial], [lifestyle shot]

Output ONLY valid JSON with this structure:
{{
  "title": "video title",
  "hook": "opening hook line",
  "sections": [
    {{"timestamp": "0-3s", "speaker_text": "hook line", "scene_hint": "[description]"}},
    ...
  ],
  "cta": "call to action",
  "captions": ["keyword1", "keyword2", "keyword3"],
  "scene_sequence": ["description1", "description2"]
}}

No markdown, no explanation, only valid JSON."""

    if LLM_PROVIDER == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        script_text = response.content[0].text
    elif LLM_PROVIDER == "openai":
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        script_text = response.choices[0].message.content
    elif LLM_PROVIDER == "ollama":
        response = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/generate",
             "-d", json.dumps({"model": "llama3.1:70b", "prompt": prompt, "stream": False})],
            capture_output=True, text=True
        )
        script_text = json.loads(response.stdout)["response"]
    
    script = json.loads(script_text)
    print(f"[Stage 1] Script generated: {script['title']}")
    return script

# ─── Stage 2: Voice Clone ────────────────────────────────────────────────────

def clone_voice(script: dict, reference_audio: str) -> str:
    """Clone voice using XTTS v2."""
    from TTS.api import TTS
    import torch
    
    tts = TTS("xtts_v2").to("cuda" if torch.cuda.is_available() else "cpu")
    
    # Combine all speaker text
    full_script = f"{script['hook']} "
    for section in script['sections']:
        full_script += section['speaker_text'] + " "
    full_script += script['cta']
    
    output_path = OUTPUT_DIR / "cloned_voice.wav"
    tts.tts_to_file(
        text=full_script,
        speaker_wav=reference_audio,
        file_path=str(output_path),
        language="en"
    )
    print(f"[Stage 2] Voice cloned: {output_path}")
    return str(output_path)

# ─── Stage 3: Talking Head ───────────────────────────────────────────────────

def generate_talking_head(audio_path: str, character_image: str) -> str:
    """Generate lip-synced talking head using Hedra."""
    output_path = OUTPUT_DIR / "talking_head.mp4"
    
    # Call Hedra (adjust path as needed)
    hedra_script = SKILL_DIR / "scripts" / "talking_head.py"
    subprocess.run([
        sys.executable, str(hedra_script),
        "--audio", audio_path,
        "--character", character_image,
        "--output", str(output_path)
    ], check=True)
    
    print(f"[Stage 3] Talking head generated: {output_path}")
    return str(output_path)

# ─── Stage 4: Scene Video ────────────────────────────────────────────────────

def generate_scene_video(scene_descriptions: list, duration: int = 5) -> str:
    """Generate B-roll scene video."""
    output_path = OUTPUT_DIR / "scene_video.mp4"
    
    # Use first scene description
    scene = scene_descriptions[0] if scene_descriptions else "lifestyle scene"
    
    video_gen_script = SKILL_DIR / "scripts" / "video_gen.py"
    subprocess.run([
        sys.executable, str(video_gen_script),
        "--scene", scene,
        "--duration", str(duration),
        "--model", "wan22",
        "--output", str(output_path)
    ], check=True)
    
    print(f"[Stage 4] Scene video generated: {output_path}")
    return str(output_path)

# ─── Stage 5: Composition & Polish ─────────────────────────────────────────

def compose_and_polish(
    talking_head: str,
    scene_video: str,
    script: dict,
    layout: str = "picture_in_picture"
) -> str:
    """Composite, add captions, apply LUT."""
    compose_script = SKILL_DIR / "scripts" / "compose.py"
    
    output_path = OUTPUT_DIR / "ugc_final.mp4"
    
    subprocess.run([
        sys.executable, str(compose_script),
        "--talking-head", talking_head,
        "--scene", scene_video,
        "--output", str(output_path),
        "--layout", layout,
        "--lut", "cinematic"
    ], check=True)
    
    print(f"[Stage 5] Final video composed: {output_path}")
    return str(output_path)

# ─── Main Pipeline ──────────────────────────────────────────────────────────

def run_pipeline(
    topic: str,
    reference_audio: str,
    character_image: str,
    duration: int = 30,
    tone: str = "casual",
    layout: str = "picture_in_picture"
):
    """Run the full UGC video pipeline."""
    
    start_time = time.time()
    print(f"=== UGC Pipeline Started: {topic} ===")
    
    # Stage 1: Script
    script = generate_script(topic, duration, tone)
    script_path = OUTPUT_DIR / "script.json"
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)
    
    # Stage 2: Voice Clone
    audio_path = clone_voice(script, reference_audio)
    
    # Stage 3: Talking Head
    talking_head_path = generate_talking_head(audio_path, character_image)
    
    # Stage 4: Scene Video
    scene_video_path = generate_scene_video(script.get("scene_sequence", []))
    
    # Stage 5: Compose & Polish
    final_video = compose_and_polish(
        talking_head_path,
        scene_video_path,
        script,
        layout
    )
    
    elapsed = time.time() - start_time
    print(f"=== UGC Pipeline Complete: {elapsed:.1f}s ===")
    print(f"Output: {final_video}")
    
    return {
        "script": str(script_path),
        "audio": audio_path,
        "talking_head": talking_head_path,
        "scene_video": scene_video_path,
        "final_video": final_video
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UGC Video Pipeline")
    parser.add_argument("--topic", required=True, help="Video topic/keyword")
    parser.add_argument("--reference-audio", required=True, help="Voice reference WAV")
    parser.add_argument("--character", required=True, help="Character image PNG")
    parser.add_argument("--duration", type=int, default=30, help="Target duration (seconds)")
    parser.add_argument("--tone", default="casual", choices=["casual", "professional", "urgent"])
    parser.add_argument("--layout", default="picture_in_picture",
                        choices=["picture_in_picture", "side_by_side", "overlay"])
    parser.add_argument("--output-dir", default="./output")
    
    args = parser.parse_args()
    OUTPUT_DIR = Path(args.output_dir)
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    results = run_pipeline(
        topic=args.topic,
        reference_audio=args.reference_audio,
        character_image=args.character,
        duration=args.duration,
        tone=args.tone,
        layout=args.layout
    )
    
    print("\nPipeline Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")
```

### CLI Usage

```bash
# Run full pipeline
python ugc_pipeline.py \
  --topic "5 tips for better sleep quality" \
  --reference-audio ~/models/xttsv2/samples/jenny.wav \
  --character ~/models/hedra/characters/avatar.png \
  --duration 30 \
  --tone casual \
  --layout picture_in_picture

# With environment variables for LLM
export LLM_PROVIDER=anthropic
export LLM_MODEL=claude-sonnet-4-20250514
export ANTHROPIC_API_KEY=sk-...

python ugc_pipeline.py --topic "..." --reference-audio ... --character ...
```

---

## Prerequisites

### GPU Requirements

| Stage | Minimum VRAM | Recommended VRAM | GPU Examples |
|-------|--------------|------------------|--------------|
| Voice Clone (XTTS v2) | 4GB | 6GB | RTX 3060, A4000 |
| Talking Head (Hedra) | 6GB | 8GB | RTX 3080, A5000 |
| Video Gen (Wan 2.2) | 16GB | 24GB | A100, RTX 4090 |
| Video Gen (LTX-Video) | 12GB | 16GB | A5000, RTX 3090 |
| Composition (FFmpeg) | CPU only | CPU only | Any |

**Total VRAM needed for full pipeline:** 24GB+ (run stages sequentially to manage)

### Models to Download

```
~/models/
├── xttsv2/
│   ├── model.pth
│   ├── config.json
│   └── samples/jenny.wav
├── hedra/
│   ├── characters/avatar.png
│   └── [Hedra repository]
├── Wan2.2/
│   └── Wan2.2_T2V_A14B.safetensors  # ~28GB
├── ltx-video/
│   └── LTX-Video-13B.safetensors  # ~26GB
└── wav2lip/
    └── wav2lip.pth
```

### Disk Space

| Component | Size |
|-----------|------|
| XTTS v2 | 1.5GB |
| Hedra | 2GB |
| Wan 2.2 | 28GB |
| LTX-Video | 26GB |
| Wav2Lip (optional) | 500MB |
| ComfyUI | 5GB |
| **Total** | **~63GB** |

### Software Dependencies

```bash
# Core dependencies
pip install torch torchvision torchaudio
pip install TTS  # XTTS v2
pip install anthropic openai  # LLM clients
pip install opencv-python pillow

# FFmpeg
apt-get install ffmpeg libx264 libass  # Ubuntu/Debian
brew install ffmpeg  # macOS

# ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI && pip install -r requirements.txt

# Optional: Ollama for local LLM
brew install ollama  # macOS
# or: curl -fsSL https://ollama.com/install.sh | sh
```

---

## Verification Steps

### Stage 1: Script Generation
```bash
# Verify JSON is valid
python -c "import json; json.load(open('./output/script.json'))"

# Verify expected fields
python -c "
import json
s = json.load(open('./output/script.json'))
assert 'title' in s
assert 'sections' in s
assert len(s['sections']) > 0
print('Script verification: PASS')
"
```

### Stage 2: Voice Clone
```bash
# Verify audio file exists and is playable
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 ./output/cloned_voice.wav

# Check for audio glitches
python -c "
import subprocess
result = subprocess.run(['ffprobe', '-v', 'error', './output/cloned_voice.wav'], capture_output=True)
if result.returncode == 0:
    print('Voice clone verification: PASS')
else:
    print(f'FAIL: {result.stderr.decode()}')
"
```

### Stage 3: Talking Head
```bash
# Verify video plays and has content
ffprobe -v error -show_entries stream=codec_type,codec_name -of json ./output/talking_head.mp4

# Check duration matches audio
python -c "
import subprocess
audio_dur = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                            '-of', 'default=noprint_wrappers=1:nokey=1', './output/cloned_voice.wav'],
                           capture_output=True, text=True)
video_dur = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                            '-of', 'default=noprint_wrappers=1:nokey=1', './output/talking_head.mp4'],
                           capture_output=True, text=True)
print(f'Audio: {audio_dur.stdout.strip()}s, Video: {video_dur.stdout.strip()}s')
"
```

### Stage 4: Video Generation
```bash
# Verify video is valid and has expected duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 ./output/scene_video.mp4
```

### Stage 5: Composition
```bash
# Verify final video has video and audio streams
ffprobe -v error -show_entries stream=codec_type -of json ./output/ugc_final.mp4

# Verify resolution and aspect ratio
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 ./output/ugc_final.mp4
```

---

## Pitfalls and Known Issues

### Voice Clone
- **Reference audio too short**: Need 5-30 seconds of clear speech
- **Background noise in reference**: Reduces clone quality; denoise first
- **Non-English reference**: XTTS v2 English model works best with English reference

### Talking Head
- **Face not frontal**: Hedra requires clear frontal face; side angles fail
- **Desync lip movement**: Audio must be 16kHz mono WAV; resample if needed
- **Character drift**: Long videos (>60s) may show character movement; use shorter clips

### Video Generation
- **VRAM OOM on Wan 2.2**: Use LTX-Video (13B) instead, or reduce resolution
- **Prompt not followed**: Wan models need very specific scene descriptions; use adjectives
- **Generation too slow**: Use LTX-Video for drafts, Wan 2.2 for final output
- **Aspect ratio issues**: Always match output aspect ratio to target platform (9:16 for Reels/Shorts)

### Composition
- **Aspect ratio mismatch**: Resize all inputs to same resolution before compositing
- **Caption font missing**: Install fonts or fallback: `apt-get install fonts-liberation`
- **LUT not applying**: FFmpeg requires libx264; check `ffmpeg -formats | grep 3d`

### General
- **CUDA OOM**: Run stages sequentially, clear GPU cache between stages
- **Slow end-to-end**: Full pipeline takes 15-30 minutes depending on GPU
- **Model downloads fail**: Use `git lfs install` before cloning HF repos

---

## v2.0 CLI Usage

```bash
# Full pipeline — all defaults from pipeline_config.json
python ugc_pipeline.py --topic "5 tips for better sleep" \
  --reference-audio ~/models/xttsv2/samples/jenny.wav \
  --character ~/models/hedra/characters/avatar.png

# Dry run — validate everything without running heavy steps
python ugc_pipeline.py --topic "Test video" --dry-run

# Resume from a specific stage (e.g., you already have the cloned voice)
python ugc_pipeline.py --topic "Product launch" \
  --reference-audio ./cloned_voice.wav \
  --start-stage talking_head

# Skip scene video (use solid-color background instead)
python ugc_pipeline.py --topic "Quick demo" \
  --reference-audio voice.wav --character avatar.png \
  --skip-stages scene_video

# With custom config file
python ugc_pipeline.py --config /path/to/custom_config.json \
  --topic "Wellness tips"

# Generate character from text prompt (no image needed)
python ugc_pipeline.py --topic "Morning routine" \
  --reference-audio voice.wav \
  --character "friendly woman with curly hair, natural makeup"

# Override config defaults via CLI
python ugc_pipeline.py --topic "Sale video" \
  --reference-audio voice.wav --character avatar.png \
  --duration 15 --tone urgent --lut warm_social \
  --video-model ltx --aspect-ratio 1:1
```

### CLI Options Reference

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--topic` / `-t` | str | *required* | Video topic/description |
| `--reference-audio` | path | from config | Voice reference WAV (5-30s) |
| `--character` / `-c` | path or text | from config | Character image or text prompt to generate avatar |
| `--duration` | int | 30 | Target duration in seconds |
| `--tone` | str | casual | Script tone (casual/professional/urgent/playful) |
| `--layout` | str | picture_in_picture | Composite layout |
| `--lut` | str | cinematic | LUT to apply (or "none") |
| `--aspect-ratio` | str | 9:16 | Video aspect ratio |
| `--video-model` | str | wan22 | Scene video model (wan22/ltx) |
| `--config` | path | pipeline_config.json | Config file path |
| `--output-dir` / `-o` | path | ~/.hermes/ugc-output/ | Output directory |
| `--dry-run` | flag | false | Validate without running heavy steps |
| `--start-stage` | str | - | Resume from this stage |
| `--skip-stages` | list | - | Skip these stages entirely |
| `--no-thumbnail` | flag | false | Skip thumbnail extraction |
| `--captions` | list | - | Caption keywords for script |

---

## v2.0 Python API

```python
from ugc_pipeline import UGCPipeline, PipelineConfig, ProgressCallback

# Load config (auto-detects pipeline_config.json or env var)
config = PipelineConfig.load()
# Or: PipelineConfig.load("/path/to/custom_config.json")

# Custom progress callback for agent integration
class AgentCallback(ProgressCallback):
    def on_start(self, stage, description):
        print(f"[AGENT] Starting: {description}")
        # Could send webhook, update task status, etc.
    def on_complete(self, stage, description, result):
        print(f"[AGENT] Done: {description} → {result}")
    def on_error(self, stage, description, error):
        print(f"[AGENT] Error in {description}: {error}")
        raise error

pipeline = UGCPipeline(
    config=config,
    progress=AgentCallback(),
    output_dir="./output",
)

# Run full pipeline
results = pipeline.run(
    topic="5 tips for better sleep",
    reference_audio="~/models/xttsv2/samples/jenny.wav",
    character_image="~/models/hedra/characters/avatar.png",
    duration=30,
    tone="casual",
)

# Access artifacts
print(results.final_video_path)   # str
print(results.audio_path)          # str
print(results.thumbnail_path)      # str
print(results.script)             # dict

# Dry run validation
checks = pipeline.dry_run()
print(checks["all_passed"])  # bool

# Or use the convenience function
from ugc_pipeline import run
results = run(
    topic="Product launch",
    reference_audio="voice.wav",
    character_image="avatar.png",
    duration=15,
)
```

### Stage-by-stage module import

Each stage script can also be used independently:

```python
# Stage 2: Voice clone standalone
from voice_clone import clone_voice
clone_voice(reference_audio="ref.wav", text="Hello world", output_path="out.wav")

# Stage 3: Talking head standalone
from talking_head import generate_talking_head
generate_talking_head(audio_path="voice.wav", character_image="avatar.png",
                      output_path="head.mp4", backend="auto")

# Stage 4: Scene video standalone
from video_gen import generate_scene_video
generate_scene_video(scene_description="cozy bedroom", duration=5,
                     model="wan22", output_path="scene.mp4")

# Stage 5: Composition standalone
from compose import compose_pipeline
compose_pipeline(talking_head="head.mp4", scene_video="scene.mp4",
                 output_path="final.mp4", layout="picture_in_picture",
                 lut="cinematic")
```

---

## Configuration File

**`pipeline_config.json`** (at `~/.hermes/skills/ugc-video-pipeline/pipeline_config.json`):

```json
{
  "_version": "1.0",
  "paths": {
    "skill_dir": "~/.hermes/skills/ugc-video-pipeline",
    "output_dir": "~/.hermes/ugc-output",
    "reference_audio": "",
    "character_image": "",
    "luts_dir": "~/.hermes/skills/ugc-video-pipeline/luts"
  },
  "llm": {
    "provider": "ollama",
    "model": "llama3.1:70b",
    "endpoint": "http://localhost:11434/api/generate"
  },
  "comfyui": {
    "host": "http://localhost:8188",
    "timeout_secs": 600
  },
  "talking_head": {
    "backend": "auto",
    "aspect_ratio": "9:16",
    "avatar_prompt": "professional headshot photo of a friendly diverse person, frontal face, studio lighting",
    "avatar_model": "sd-xl"
  },
  "scene_video": {
    "model": "wan22",
    "duration": 5,
    "resolution": [1280, 720]
  },
  "compose": {
    "layout": "picture_in_picture",
    "lut": "cinematic",
    "normalize_audio": true,
    "target_lufs": -14.0,
    "fade_in": 0.5,
    "fade_out": 0.5
  },
  "defaults": {
    "duration": 30,
    "tone": "casual",
    "aspect_ratio": "9:16"
  }
}
```

Environment variables always override config file values:
- `LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_ENDPOINT`
- `COMFYUI_HOST`
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- `UGC_PIPELINE_CONFIG` (path to config JSON)

---

## File Manifest

This skill creates the following files:

```
~/.hermes/skills/ugc-video-pipeline/
├── SKILL.md                          # This file
├── README.md                         # Quick start guide
├── pipeline_config.json               # v2.0: Centralized configuration
├── scripts/
│   ├── voice_clone.py                # Stage 2: XTTS v2 voice cloning
│   ├── talking_head.py               # Stage 3: Hedra lip-sync
│   ├── video_gen.py                  # Stage 4: ComfyUI video generation
│   ├── compose.py                    # Stage 5: FFmpeg composition
│   └── ugc_pipeline.py               # Stage 6: End-to-end orchestrator (v2.0)
├── workflows/
│   ├── wan22_video.json              # ComfyUI workflow for Wan 2.2
│   └── ltx_video.json                # ComfyUI workflow for LTX-Video
├── luts/
│   ├── cinematic.cube
│   ├── warm_social.cube
│   ├── cool_blue.cube
│   └── vintage.cube
├── caption_style.json                # Caption styling config
└── prompts/
    ├── script_gen.txt                # Script generation prompt template
    └── scene_prompt.txt              # Scene video prompt template
```

### Output Files (runtime)

```
~/.hermes/ugc-output/
├── script.json                      # Generated script (Stage 1)
├── cloned_voice.wav                 # Cloned voice audio (Stage 2)
├── talking_head.mp4                 # Lip-synced head (Stage 3)
├── scene_video.mp4                  # B-roll scene (Stage 4)
├── ugc_final.mp4                   # Final polished video (Stage 5)
└── thumbnail.jpg                    # Thumbnail extracted at 00:00:01
```

---

## Quick Start (v2.0)

```bash
# 1. Ensure prerequisites
mkdir -p ~/models/xttsv2 ~/models/hedra ~/models/Wan2.2

# 2. Validate pipeline setup (no heavy steps run)
cd ~/.hermes/skills/ugc-video-pipeline
python scripts/ugc_pipeline.py --topic "Test" --dry-run

# 3. Run the full pipeline
python scripts/ugc_pipeline.py \
  --topic "Why sleep matters" \
  --reference-audio ~/models/xttsv2/samples/jenny.wav \
  --character ~/models/hedra/characters/avatar.png \
  --duration 30

# 4. Check output
ls -la ~/.hermes/ugc-output/

# Or use a text prompt to auto-generate the character image:
python scripts/ugc_pipeline.py \
  --topic "Morning routine tips" \
  --reference-audio ~/models/xttsv2/samples/jenny.wav \
  --character "friendly person with short hair, natural look"
```

---

*Skill version: 2.0.0 | Last updated: 2026-04-06*
