#!/usr/bin/env python3
"""ugc_pipeline.py — End-to-end UGC video generation pipeline

Orchestrates all pipeline stages:
  Stage 1: Script Generation  (LLM)
  Stage 2: Voice Clone         (XTTS v2)
  Stage 3: Talking Head        (Hedra / SadTalker / Wav2Lip)
  Stage 4: Scene Video         (Wan2.2 / LTX-Video via ComfyUI)
  Stage 5: Composition & Polish (FFmpeg + LUT + Captions + Thumbnail)

Can be used as a Python module or CLI script.

Usage (CLI):
    python ugc_pipeline.py --topic "5 tips for better sleep"
    python ugc_pipeline.py --config pipeline_config.json --topic "Product launch"
    python ugc_pipeline.py --stage voice_clone --skip-stages script_gen
    python ugc_pipeline.py --dry-run --topic "Test video"

Usage (module):
    from ugc_pipeline import UGCPipeline, PipelineConfig

    config = PipelineConfig.load("pipeline_config.json")
    pipeline = UGCPipeline(config)
    results = pipeline.run(
        topic="5 tips for better sleep",
        reference_audio="~/models/xttsv2/samples/jenny.wav",
        character_image="~/models/hedra/characters/avatar.png"
    )
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Callable, Any

# ─── Version & Metadata ───────────────────────────────────────────────────────

__version__ = "2.0.0"

# ─── Default paths ───────────────────────────────────────────────────────────

SKILL_DIR = Path("~/.hermes/skills/ugc-video-pipeline").expanduser()
DEFAULT_CONFIG = SKILL_DIR / "pipeline_config.json"
DEFAULT_OUTPUT_DIR = Path("~/.hermes/ugc-output").expanduser()

# ─── Pipeline Stage Names ────────────────────────────────────────────────────

STAGES = [
    "script_gen",
    "voice_clone",
    "talking_head",
    "scene_video",
    "compose",
]

STAGE_DESCRIPTIONS = {
    "script_gen":   "Script Generation (LLM)",
    "voice_clone":  "Voice Clone (XTTS v2)",
    "talking_head": "Talking Head (Hedra/Wav2Lip)",
    "scene_video":  "Scene Video (ComfyUI)",
    "compose":      "Composition & Polish (FFmpeg)",
}


# ══════════════════════════════════════════════════════════════════════════════
# Progress Callback
# ══════════════════════════════════════════════════════════════════════════════

class ProgressCallback:
    """Callback interface for pipeline progress. Override any method."""

    def on_start(self, stage: str, description: str) -> None:
        print(f"\n[Pipeline] Starting: {description}")

    def on_complete(self, stage: str, description: str, result: Any) -> None:
        print(f"[Pipeline] Complete: {description}")

    def on_error(self, stage: str, description: str, error: Exception) -> None:
        print(f"[Pipeline] Error in {description}: {error}")

    def on_skip(self, stage: str, reason: str) -> None:
        print(f"[Pipeline] Skipping {stage}: {reason}")

    def on_warning(self, stage: str, message: str) -> None:
        print(f"[Pipeline] Warning [{stage}]: {message}")

    def on_progress(self, stage: str, message: str) -> None:
        print(f"[{stage.upper()}] {message}")


class SilentProgressCallback(ProgressCallback):
    """Silence all output — useful for programmatic use."""
    def on_start(self, *a, **k) -> None: pass
    def on_complete(self, *a, **k) -> None: pass
    def on_error(self, *a, **k) -> None: pass
    def on_skip(self, *a, **k) -> None: pass
    def on_warning(self, *a, **k) -> None: pass
    def on_progress(self, *a, **k) -> None: pass


# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PipelineConfig:
    """Configuration for the UGC pipeline. Load from JSON + env overrides."""

    # Paths
    skill_dir: Path = field(default_factory=lambda: SKILL_DIR)
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)
    models_dir: Path = field(default_factory=lambda: Path("~/models").expanduser())
    comfyui_dir: Path = field(default_factory=lambda: Path("~/models/ComfyUI").expanduser())
    reference_audio: str = ""
    character_image: str = ""
    luts_dir: Path = field(default_factory=lambda: SKILL_DIR / "luts")
    workflows_dir: Path = field(default_factory=lambda: SKILL_DIR / "workflows")
    caption_style: Path = field(default_factory=lambda: SKILL_DIR / "caption_style.json")

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:70b"
    llm_endpoint: str = "http://localhost:11434/api/generate"
    llm_api_key_env: str = ""
    llm_timeout_secs: int = 120

    # ComfyUI
    comfyui_host: str = "http://localhost:8188"
    comfyui_timeout_secs: int = 600

    # Stage defaults
    voice_clone_enabled: bool = True
    voice_clone_language: str = "en"

    talking_head_backend: str = "auto"
    talking_head_aspect_ratio: str = "9:16"
    avatar_prompt: str = "professional headshot photo of a friendly diverse person, frontal face, studio lighting"
    avatar_model: str = "sd-xl"

    scene_video_model: str = "wan22"
    scene_video_duration: int = 5
    scene_video_resolution: tuple = (1280, 720)
    scene_video_seed: int = 42

    compose_layout: str = "picture_in_picture"
    compose_lut: str = "cinematic"
    normalize_audio: bool = True
    target_lufs: float = -14.0
    fade_in: float = 0.5
    fade_out: float = 0.5
    add_captions: bool = True

    # Defaults
    default_duration: int = 30
    default_tone: str = "casual"
    default_aspect_ratio: str = "9:16"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "PipelineConfig":
        """Load config from JSON file, with env-var overrides."""
        if path is None:
            path = os.environ.get("UGC_PIPELINE_CONFIG", str(DEFAULT_CONFIG))

        path = Path(path).expanduser()
        if path.exists():
            with open(path) as f:
                data = json.load(f)
        else:
            data = {}

        # Flatten nested structure back to dataclass fields
        flat = {}
        flat["skill_dir"] = Path(data.get("paths", {}).get("skill_dir", str(SKILL_DIR))).expanduser()
        flat["output_dir"] = Path(data.get("paths", {}).get("output_dir", str(DEFAULT_OUTPUT_DIR))).expanduser()
        flat["models_dir"] = Path(data.get("paths", {}).get("models_dir", "~/models")).expanduser()
        flat["comfyui_dir"] = Path(data.get("paths", {}).get("comfyui_dir", "~/models/ComfyUI")).expanduser()
        flat["reference_audio"] = data.get("paths", {}).get("reference_audio", "")
        flat["character_image"] = data.get("paths", {}).get("character_image", "")
        flat["luts_dir"] = Path(data.get("paths", {}).get("luts_dir", str(SKILL_DIR / "luts"))).expanduser()
        flat["workflows_dir"] = Path(data.get("paths", {}).get("workflows_dir", str(SKILL_DIR / "workflows"))).expanduser()
        flat["caption_style"] = Path(data.get("paths", {}).get("caption_style", str(SKILL_DIR / "caption_style.json"))).expanduser()

        llm = data.get("llm", {})
        flat["llm_provider"] = os.environ.get("LLM_PROVIDER", llm.get("provider", "ollama"))
        flat["llm_model"] = os.environ.get("LLM_MODEL", llm.get("model", "llama3.1:70b"))
        flat["llm_endpoint"] = os.environ.get("OLLAMA_ENDPOINT", llm.get("endpoint", "http://localhost:11434/api/generate"))
        flat["llm_api_key_env"] = llm.get("api_key_env", "")
        flat["llm_timeout_secs"] = llm.get("timeout_secs", 120)

        comfyui = data.get("comfyui", {})
        flat["comfyui_host"] = os.environ.get("COMFYUI_HOST", comfyui.get("host", "http://localhost:8188"))
        flat["comfyui_timeout_secs"] = comfyui.get("timeout_secs", 600)

        vc = data.get("voice_clone", {})
        flat["voice_clone_enabled"] = vc.get("enabled", True)
        flat["voice_clone_language"] = vc.get("language", "en")

        th = data.get("talking_head", {})
        flat["talking_head_backend"] = th.get("backend", "auto")
        flat["talking_head_aspect_ratio"] = th.get("aspect_ratio", "9:16")
        flat["avatar_prompt"] = th.get("avatar_prompt", "professional headshot photo of a friendly diverse person, frontal face, studio lighting")
        flat["avatar_model"] = th.get("avatar_model", "sd-xl")

        sv = data.get("scene_video", {})
        flat["scene_video_model"] = sv.get("model", "wan22")
        flat["scene_video_duration"] = sv.get("duration", 5)
        res = sv.get("resolution", [1280, 720])
        flat["scene_video_resolution"] = tuple(res) if isinstance(res, list) else res
        flat["scene_video_seed"] = sv.get("seed", 42)

        cp = data.get("compose", {})
        flat["compose_layout"] = cp.get("layout", "picture_in_picture")
        flat["compose_lut"] = cp.get("lut", "cinematic")
        flat["normalize_audio"] = cp.get("normalize_audio", True)
        flat["target_lufs"] = cp.get("target_lufs", -14.0)
        flat["fade_in"] = cp.get("fade_in", 0.5)
        flat["fade_out"] = cp.get("fade_out", 0.5)
        flat["add_captions"] = cp.get("caption_text", True)

        d = data.get("defaults", {})
        flat["default_duration"] = d.get("duration", 30)
        flat["default_tone"] = d.get("tone", "casual")
        flat["default_aspect_ratio"] = d.get("aspect_ratio", "9:16")

        return cls(**flat)

    def to_json(self, path: Path) -> None:
        """Save current config to a JSON file."""
        # Build nested structure
        data = {
            "_version": "1.0",
            "paths": {
                "skill_dir": str(self.skill_dir),
                "output_dir": str(self.output_dir),
                "models_dir": str(self.models_dir),
                "comfyui_dir": str(self.comfyui_dir),
                "reference_audio": self.reference_audio,
                "character_image": self.character_image,
                "luts_dir": str(self.luts_dir),
                "workflows_dir": str(self.workflows_dir),
                "caption_style": str(self.caption_style),
            },
            "llm": {
                "provider": self.llm_provider,
                "model": self.llm_model,
                "endpoint": self.llm_endpoint,
                "api_key_env": self.llm_api_key_env,
                "timeout_secs": self.llm_timeout_secs,
            },
            "comfyui": {
                "host": self.comfyui_host,
                "timeout_secs": self.comfyui_timeout_secs,
            },
            "voice_clone": {
                "enabled": self.voice_clone_enabled,
                "language": self.voice_clone_language,
            },
            "talking_head": {
                "backend": self.talking_head_backend,
                "aspect_ratio": self.talking_head_aspect_ratio,
                "avatar_prompt": self.avatar_prompt,
                "avatar_model": self.avatar_model,
            },
            "scene_video": {
                "model": self.scene_video_model,
                "duration": self.scene_video_duration,
                "resolution": list(self.scene_video_resolution),
                "seed": self.scene_video_seed,
            },
            "compose": {
                "layout": self.compose_layout,
                "lut": self.compose_lut,
                "normalize_audio": self.normalize_audio,
                "target_lufs": self.target_lufs,
                "fade_in": self.fade_in,
                "fade_out": self.fade_out,
                "caption_text": self.add_captions,
            },
            "defaults": {
                "duration": self.default_duration,
                "tone": self.default_tone,
                "aspect_ratio": self.default_aspect_ratio,
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1: Script Generation
# ══════════════════════════════════════════════════════════════════════════════

def generate_script(
    topic: str,
    config: PipelineConfig,
    duration: int = 30,
    tone: str = "casual",
    caption_keywords: list | None = None,
    output_path: Path | None = None,
    progress: ProgressCallback | None = None,
) -> dict:
    """Generate a UGC video script using an LLM.

    Args:
        topic: Video topic/keyword
        config: Pipeline configuration
        duration: Target duration in seconds
        tone: Script tone (casual, professional, urgent)
        caption_keywords: Optional keywords to incorporate
        output_path: Optional path to save script JSON
        progress: Progress callback

    Returns:
        Script dict with title, hook, sections, cta, captions, scene_sequence
    """
    cb = progress or ProgressCallback()
    cb.on_start("script_gen", STAGE_DESCRIPTIONS["script_gen"])

    word_count = int(duration * 2.5)

    caption_context = ""
    if caption_keywords:
        caption_context = f"\nIncorporate these keywords/captions: {', '.join(caption_keywords)}"

    prompt = f"""You are an expert UGC scriptwriter for social media marketing videos.

Generate a video script for: {topic}
{caption_context}

Requirements:
- Duration: {duration} seconds (~{word_count} words)
- Style: Conversational, authentic, hook-driven
- Structure: Hook (3s) → Problem (5s) → Solution ({duration - 13}s) → CTA (5s)
- Tone: {tone}
- Include B-roll scene suggestions in brackets: [product closeup], [testimonial], [lifestyle shot]
- The script should feel natural and spoken aloud

Output ONLY valid JSON with this structure:
{{
  "title": "video title",
  "hook": "opening hook line (2-3 seconds)",
  "sections": [
    {{"timestamp": "0-3s", "speaker_text": "hook line", "scene_hint": "[description]"}},
    {{"timestamp": "3-8s", "speaker_text": "problem statement", "scene_hint": "[description]"}},
    {{"timestamp": "8-{duration-5}s", "speaker_text": "main content/solution", "scene_hint": "[description]"}}
  ],
  "cta": "call to action",
  "captions": ["keyword1", "keyword2", "keyword3"],
  "scene_sequence": ["description1", "description2"]
}}

No markdown, no explanation, only valid JSON."""

    try:
        if config.llm_provider == "ollama":
            script_text = _llm_call_ollama(prompt, config)
        elif config.llm_provider == "anthropic":
            script_text = _llm_call_anthropic(prompt, config)
        elif config.llm_provider == "openai":
            script_text = _llm_call_openai(prompt, config)
        else:
            raise ValueError(f"Unknown LLM provider: {config.llm_provider}")

        script = json.loads(script_text)

    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nResponse: {script_text[:500] if 'script_text' in dir() else 'N/A'}")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(script, f, indent=2)
        cb.on_progress("script_gen", f"Saved script: {output_path}")

    cb.on_complete("script_gen", STAGE_DESCRIPTIONS["script_gen"], script)
    return script


def _llm_call_ollama(prompt: str, config: PipelineConfig) -> str:
    """Call local Ollama LLM."""
    payload = {
        "model": config.llm_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "timeout": config.llm_timeout_secs,
    }
    cmd = ["curl", "-s", config.llm_endpoint, "-d", json.dumps(payload)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=config.llm_timeout_secs + 30)
    return json.loads(result.stdout)["response"]


def _llm_call_anthropic(prompt: str, config: PipelineConfig) -> str:
    """Call Anthropic Claude API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if config.llm_api_key_env:
        api_key = os.environ.get(config.llm_api_key_env, api_key)

    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    response = client.messages.create(
        model=config.llm_model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        timeout=config.llm_timeout_secs,
    )
    return response.content[0].text


def _llm_call_openai(prompt: str, config: PipelineConfig) -> str:
    """Call OpenAI API."""
    try:
        import openai
    except ImportError:
        raise ImportError("pip install openai")

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if config.llm_api_key_env:
        api_key = os.environ.get(config.llm_api_key_env, api_key)

    client = openai.OpenAI(api_key=api_key) if api_key else openai.OpenAI()
    response = client.chat.completions.create(
        model=config.llm_model,
        messages=[{"role": "user", "content": prompt}],
        timeout=config.llm_timeout_secs,
    )
    return response.choices[0].message.content


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2: Voice Clone
# ══════════════════════════════════════════════════════════════════════════════

def clone_voice(
    script: dict,
    reference_audio: str,
    output_path: str | Path,
    config: PipelineConfig,
    progress: ProgressCallback | None = None,
) -> str:
    """Clone voice using XTTS v2.

    Args:
        script: Script dict containing hook, sections, cta
        reference_audio: Path to reference WAV (5-30s, clean speech)
        output_path: Output WAV path
        config: Pipeline configuration
        progress: Progress callback

    Returns:
        Path to cloned voice WAV file
    """
    cb = progress or ProgressCallback()
    cb.on_start("voice_clone", STAGE_DESCRIPTIONS["voice_clone"])

    # Build full script text
    parts = [script.get("hook", "")]
    for section in script.get("sections", []):
        parts.append(section.get("speaker_text", ""))
    parts.append(script.get("cta", ""))
    full_text = " ".join(p for p in parts if p)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Option A: import voice_clone as module ───────────────────────────────
    voice_clone_script = config.skill_dir / "scripts" / "voice_clone.py"
    if voice_clone_script.exists():
        try:
            # Dynamically import the module
            import importlib.util
            spec = importlib.util.spec_from_file_location("voice_clone_module", voice_clone_script)
            vc_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(vc_mod)

            cb.on_progress("voice_clone", f"Using voice_clone module with XTTS v2")
            vc_mod.clone_voice(
                reference_audio=reference_audio,
                text=full_text,
                output_path=str(output_path),
                language=config.voice_clone_language,
            )
            cb.on_complete("voice_clone", STAGE_DESCRIPTIONS["voice_clone"], str(output_path))
            return str(output_path)
        except Exception as e:
            cb.on_warning("voice_clone", f"Module import failed ({e}), falling back to direct import")

    # ── Option B: direct TTS import ─────────────────────────────────────────
    try:
        import torch
        from TTS.api import TTS
    except ImportError:
        raise ImportError("pip install TTS")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    cb.on_progress("voice_clone", f"Loading XTTS v2 on {device}")
    tts = TTS("xtts_v2").to(device)

    cb.on_progress("voice_clone", f"Synthesizing {len(full_text)} chars of speech")
    tts.tts_to_file(
        text=full_text,
        speaker_wav=reference_audio,
        file_path=str(output_path),
        language=config.voice_clone_language,
    )

    if not output_path.exists():
        raise RuntimeError("Voice cloning failed — no output file created")

    size_kb = output_path.stat().st_size / 1024
    cb.on_progress("voice_clone", f"Cloned voice saved: {output_path} ({size_kb:.0f} KB)")
    cb.on_complete("voice_clone", STAGE_DESCRIPTIONS["voice_clone"], str(output_path))
    return str(output_path)


# ══════════════════════════════════════════════════════════════════════════════
# Stage 3: Talking Head
# ══════════════════════════════════════════════════════════════════════════════

def generate_talking_head(
    audio_path: str,
    character_image: str,
    output_path: str | Path,
    config: PipelineConfig,
    progress: ProgressCallback | None = None,
) -> str:
    """Generate lip-synced talking head video.

    Args:
        audio_path: Path to cloned voice WAV
        character_image: Path to character image, or a text prompt to generate one
        output_path: Output MP4 path
        config: Pipeline configuration
        progress: Progress callback

    Returns:
        Path to talking head MP4 file
    """
    cb = progress or ProgressCallback()
    cb.on_start("talking_head", STAGE_DESCRIPTIONS["talking_head"])

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Resolve character image (generate if needed) ─────────────────────────
    char_path = _resolve_character_image(character_image, config, cb)
    cb.on_progress("talking_head", f"Using character image: {char_path}")

    # ── Try importing talking_head as module ────────────────────────────────
    talking_head_script = config.skill_dir / "scripts" / "talking_head.py"
    if talking_head_script.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("talking_head_module", talking_head_script)
            th_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(th_mod)

            cb.on_progress("talking_head", "Calling talking_head module")
            th_mod.generate_talking_head(
                audio_path=str(audio_path),
                character_image=char_path,
                output_path=str(output_path),
                backend=config.talking_head_backend,
                aspect_ratio=config.talking_head_aspect_ratio,
                use_wav2lip_fallback=True,
            )
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                cb.on_progress("talking_head", f"Talking head saved: {output_path} ({size_mb:.1f} MB)")
                cb.on_complete("talking_head", STAGE_DESCRIPTIONS["talking_head"], str(output_path))
                return str(output_path)
        except Exception as e:
            cb.on_warning("talking_head", f"Module call failed ({e}), trying direct generation")

    raise RuntimeError(
        "talking_head.py module call failed and direct import is not available. "
        "Ensure talking_head.py is installed correctly."
    )


def _resolve_character_image(
    character_image: str,
    config: PipelineConfig,
    cb: ProgressCallback,
) -> str:
    """Resolve character_image: generate from prompt or validate file exists."""
    if not character_image:
        # Generate default avatar
        return _generate_avatar(config.avatar_prompt, config, cb)

    if Path(character_image).exists():
        return character_image

    # Treat as text prompt — generate avatar
    cb.on_progress("talking_head", f"Character image not found, generating from prompt: '{character_image[:50]}...'")
    return _generate_avatar(character_image, config, cb)


def _generate_avatar(
    prompt: str,
    config: PipelineConfig,
    cb: ProgressCallback,
) -> str:
    """Generate avatar using talking_head's generate_avatar (imported as module)."""
    talking_head_script = config.skill_dir / "scripts" / "talking_head.py"
    if not talking_head_script.exists():
        raise FileNotFoundError(f"talking_head.py not found at {talking_head_script}")

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("talking_head_module", talking_head_script)
        th_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(th_mod)

        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        os.unlink(tmp_path)  # generate_avatar creates the file

        result = th_mod.generate_avatar(
            prompt=prompt,
            output_path=tmp_path,
            model=config.avatar_model,
        )
        cb.on_progress("talking_head", f"Avatar generated: {result}")
        return result
    except Exception as e:
        raise RuntimeError(f"Avatar generation failed: {e}. Provide a character image path to bypass.")


# ══════════════════════════════════════════════════════════════════════════════
# Stage 4: Scene Video
# ══════════════════════════════════════════════════════════════════════════════

def generate_scene_video(
    scene_descriptions: list,
    output_path: str | Path,
    config: PipelineConfig,
    progress: ProgressCallback | None = None,
) -> str:
    """Generate background scene video via ComfyUI (Wan2.2 / LTX-Video).

    Args:
        scene_descriptions: List of scene description strings
        output_path: Output MP4 path
        config: Pipeline configuration
        progress: Progress callback

    Returns:
        Path to scene video MP4 file
    """
    cb = progress or ProgressCallback()
    cb.on_start("scene_video", STAGE_DESCRIPTIONS["scene_video"])

    scene = scene_descriptions[0] if scene_descriptions else "lifestyle scene, professional lighting"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try importing video_gen as module
    video_gen_script = config.skill_dir / "scripts" / "video_gen.py"
    if video_gen_script.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("video_gen_module", video_gen_script)
            vg_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(vg_mod)

            cb.on_progress("scene_video", f"Generating scene: {scene[:60]}...")
            result = vg_mod.generate_scene_video(
                scene_description=scene,
                duration=config.scene_video_duration,
                model=config.scene_video_model,
                output_path=str(output_path),
                resolution=config.scene_video_resolution,
                seed=config.scene_video_seed,
            )
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                cb.on_progress("scene_video", f"Scene video saved: {output_path} ({size_mb:.1f} MB)")
                cb.on_complete("scene_video", STAGE_DESCRIPTIONS["scene_video"], str(output_path))
                return str(output_path)
        except Exception as e:
            cb.on_warning("scene_video", f"Module call failed ({e})")

    # Fallback: direct ComfyUI API call
    cb.on_progress("scene_video", "Calling ComfyUI API directly")
    result = _generate_scene_via_comfyui_api(scene, output_path, config, cb)
    cb.on_complete("scene_video", STAGE_DESCRIPTIONS["scene_video"], result)
    return result


def _generate_scene_via_comfyui_api(
    scene: str,
    output_path: Path,
    config: PipelineConfig,
    cb: ProgressCallback,
) -> str:
    """Direct ComfyUI API call as fallback when video_gen module is unavailable."""
    import urllib.request
    import urllib.error

    workflow_path = config.workflows_dir / f"{config.scene_video_model}_video.json"
    if not workflow_path.exists():
        # Create a placeholder colored video
        return _create_placeholder_scene_video(output_path, config.scene_video_duration, cb)

    with open(workflow_path) as f:
        workflow = json.load(f)

    # Update workflow with scene description
    model_map = {
        "wan22": "Wan2.2_T2V_A14B.safetensors",
        "ltx": "LTX-Video-13B.safetensors",
    }
    model_filename = model_map.get(config.scene_video_model, "Wan2.2_T2V_A14B.safetensors")

    # Update CheckpointLoader
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "CheckpointLoaderSimple":
            node_data["inputs"]["ckpt_name"] = model_filename

    # Update prompts
    pos_nodes = [n for n, d in workflow.items() if d.get("class_type") == "CLIPTextEncode"]
    if pos_nodes:
        workflow[pos_nodes[0]]["inputs"]["text"] = f"UGC video style, {scene}, professional lighting, cinematic"
    neg_nodes = [n for n, d in workflow.items() if d.get("class_type") == "CLIPTextEncode"]
    if len(neg_nodes) > 1:
        workflow[neg_nodes[1]]["inputs"]["text"] = "watermark, text, logo, blurry, low quality, cartoon, anime"

    url = f"{config.comfyui_host}/prompt"
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            prompt_id = result["prompt_id"]
    except (urllib.error.URLError, ConnectionRefusedError) as e:
        cb.on_warning("scene_video", f"ComfyUI not reachable ({e}), creating placeholder")
        return _create_placeholder_scene_video(output_path, config.scene_video_duration, cb)

    # Poll for completion
    start = time.time()
    while time.time() - start < config.comfyui_timeout_secs:
        time.sleep(5)
        try:
            hist_url = f"{config.comfyui_host}/history/{prompt_id}"
            with urllib.request.urlopen(hist_url, timeout=30) as resp:
                history = json.loads(resp.read().decode("utf-8"))
            if prompt_id in history and history[prompt_id].get("outputs"):
                outputs = history[prompt_id]["outputs"]
                for node_id, output in outputs.items():
                    if isinstance(output, dict):
                        for key in ("gifs", "videos", "images"):
                            if key in output and output[key]:
                                filename = output[key][0]
                                src = f"{config.comfyui_host}/view?filename={filename}"
                                with urllib.request.urlopen(src, timeout=60) as img_resp:
                                    with open(output_path, "wb") as f:
                                        f.write(img_resp.read())
                                return str(output_path)
                break
        except Exception:
            continue

    cb.on_warning("scene_video", "ComfyUI poll timed out, creating placeholder")
    return _create_placeholder_scene_video(output_path, config.scene_video_duration, cb)


def _create_placeholder_scene_video(
    output_path: Path,
    duration: int,
    cb: ProgressCallback,
) -> str:
    """Create a solid-color placeholder video when ComfyUI is unavailable."""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=blue:s=1280x720:d={duration}:r=30",
            "-c:v", "libx264", "-preset", "ultrafast",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        cb.on_progress("scene_video", f"Placeholder scene created: {output_path}")
        return str(output_path)
    except Exception as e:
        cb.on_warning("scene_video", f"Placeholder creation failed: {e}")
        return str(output_path)


# ══════════════════════════════════════════════════════════════════════════════
# Stage 5: Composition & Polish
# ══════════════════════════════════════════════════════════════════════════════

def compose_and_polish(
    talking_head: str,
    scene_video: str,
    output_path: str | Path,
    config: PipelineConfig,
    script: dict | None = None,
    thumbnail_path: str | Path | None = None,
    progress: ProgressCallback | None = None,
) -> str:
    """Composite talking head + scene, apply LUT, captions, thumbnail.

    Args:
        talking_head: Path to talking head MP4
        scene_video: Path to scene background MP4
        output_path: Final output MP4 path
        config: Pipeline configuration
        script: Optional script dict for caption text
        thumbnail_path: Optional thumbnail output path
        progress: Progress callback

    Returns:
        Path to final video
    """
    cb = progress or ProgressCallback()
    cb.on_start("compose", STAGE_DESCRIPTIONS["compose"])

    talking_head = Path(talking_head)
    scene_video = Path(scene_video)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not talking_head.exists():
        raise FileNotFoundError(f"Talking head not found: {talking_head}")
    if not scene_video.exists():
        raise FileNotFoundError(f"Scene video not found: {scene_video}")

    # Try importing compose as module
    compose_script = config.skill_dir / "scripts" / "compose.py"
    if compose_script.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("compose_module", compose_script)
            cp_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cp_mod)

            # Build caption text from script
            caption_text = None
            if config.add_captions and script:
                parts = [script.get("hook", "")]
                for s in script.get("sections", []):
                    parts.append(s.get("speaker_text", ""))
                parts.append(script.get("cta", ""))
                caption_text = " ".join(p for p in parts if p)

            th_scale = 0.30
            th_path_str = str(thumbnail_path) if thumbnail_path else None

            cb.on_progress("compose", "Calling compose module")
            cp_mod.compose_pipeline(
                talking_head=str(talking_head),
                scene_video=str(scene_video),
                output_path=str(output_path),
                layout=config.compose_layout,
                lut=config.compose_lut,
                caption_text=caption_text,
                fade_in=config.fade_in,
                fade_out=config.fade_out,
                normalize_audio=config.normalize_audio,
                target_lufs=config.target_lufs,
                thumbnail=th_path_str,
                thumbnail_time="00:00:01",
            )

            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                cb.on_progress("compose", f"Final video saved: {output_path} ({size_mb:.1f} MB)")
                cb.on_complete("compose", STAGE_DESCRIPTIONS["compose"], str(output_path))
                return str(output_path)
        except Exception as e:
            cb.on_warning("compose", f"Module call failed ({e}), using direct FFmpeg")

    # Fallback: direct FFmpeg composition
    cb.on_progress("compose", "Using direct FFmpeg composition")
    result = _direct_ffmpeg_compose(
        talking_head, scene_video, output_path, config, cb
    )

    # Extract thumbnail if requested
    if thumbnail_path and Path(result).exists():
        _extract_thumbnail(result, Path(thumbnail_path), "00:00:01", cb)

    cb.on_complete("compose", STAGE_DESCRIPTIONS["compose"], result)
    return result


def _direct_ffmpeg_compose(
    talking_head: Path,
    scene_video: Path,
    output_path: Path,
    config: PipelineConfig,
    cb: ProgressCallback,
) -> str:
    """Direct FFmpeg composition as fallback."""
    base = output_path.with_suffix("")
    composite = base.with_name(f"{base.stem}_composite.mp4")

    if config.compose_layout == "picture_in_picture":
        w, h = config.scene_video_resolution
        pip_w = int(w * 0.30)
        pip_h = int(h * 0.30)
        pip_x = w - pip_w - 20
        pip_y = h - pip_h - 20
        vf = f"[1:v]scale={pip_w}:{pip_h}[pip];[0:v][pip]overlay={pip_x}:{pip_y}"
    elif config.compose_layout == "side_by_side":
        vf = "hstack=inputs=2"
    else:
        vf = "overlay=0:0"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(scene_video),
        "-i", str(talking_head),
        "-filter_complex", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(composite),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg composition timed out")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg composition failed: {e.stderr.decode() if e.stderr else e}")

    # Copy to final output
    shutil.copy(composite, output_path)
    composite.unlink(missing_ok=True)
    return str(output_path)


def _extract_thumbnail(
    video_path: str,
    output_path: Path,
    timestamp: str,
    cb: ProgressCallback,
) -> str:
    """Extract a thumbnail frame from video."""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", timestamp,
            "-i", video_path,
            "-vframes", "1",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        cb.on_progress("compose", f"Thumbnail saved: {output_path}")
    except Exception as e:
        cb.on_warning("compose", f"Thumbnail extraction failed: {e}")
    return str(output_path)


# ══════════════════════════════════════════════════════════════════════════════
# Main Pipeline Orchestrator
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PipelineArtifacts:
    """Artifacts produced by each pipeline stage."""
    script: Optional[dict] = None
    script_path: Optional[str] = None
    audio_path: Optional[str] = None
    talking_head_path: Optional[str] = None
    scene_video_path: Optional[str] = None
    final_video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class UGCPipeline:
    """End-to-end UGC video generation pipeline orchestrator.

    Can run all stages or resume from a specific stage given prior artifacts.

    Example:
        >>> config = PipelineConfig.load("pipeline_config.json")
        >>> pipeline = UGCPipeline(config, progress=my_callback)
        >>> results = pipeline.run(
        ...     topic="5 tips for better sleep",
        ...     reference_audio="~/models/xttsv2/samples/jenny.wav",
        ...     character_image="~/models/hedra/characters/avatar.png",
        ... )
        >>> print(results.final_video_path)
    """

    def __init__(
        self,
        config: PipelineConfig | str | Path | None = None,
        progress: ProgressCallback | None = None,
        output_dir: Path | str | None = None,
    ):
        """Initialize the pipeline.

        Args:
            config: PipelineConfig, path to config JSON, or None for defaults
            progress: ProgressCallback instance for events
            output_dir: Override output directory
        """
        if isinstance(config, (str, Path)):
            self.config = PipelineConfig.load(config)
        elif config is None:
            self.config = PipelineConfig.load()
        else:
            self.config = config

        if output_dir is not None:
            self.config.output_dir = Path(output_dir)

        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.progress = progress or ProgressCallback()

        # Temp directory for intermediate files
        self._temp_dir = Path(tempfile.mkdtemp(prefix="ugc_pipeline_"))
        self._started_at = 0.0

    def run(
        self,
        topic: str,
        reference_audio: str | None = None,
        character_image: str | None = None,
        duration: int | None = None,
        tone: str | None = None,
        caption_keywords: list | None = None,
        layout: str | None = None,
        lut: str | None = None,
        aspect_ratio: str | None = None,
        video_model: str | None = None,
        skip_stages: list[str] | None = None,
        start_stage: str | None = None,
        dry_run: bool = False,
        thumbnail: bool = True,
    ) -> PipelineArtifacts:
        """Run the full UGC pipeline.

        Args:
            topic: Video topic/description
            reference_audio: Path to voice reference audio (WAV/MP3)
            character_image: Path to character image, or text prompt to generate one
            duration: Target duration in seconds (default from config)
            tone: Script tone (default from config)
            caption_keywords: Keywords to incorporate in script
            layout: Composite layout (default from config)
            lut: LUT name (default from config)
            aspect_ratio: Video aspect ratio (default from config)
            video_model: Scene video model 'wan22' or 'ltx' (default from config)
            skip_stages: List of stage names to skip (e.g. ["scene_video"])
            start_stage: Stage to resume from (auto-detected from provided artifacts)
            dry_run: Validate pipeline without running heavy steps
            thumbnail: Extract thumbnail from final video

        Returns:
            PipelineArtifacts with paths to all generated files
        """
        self._started_at = time.time()
        artifacts = PipelineArtifacts()

        # Use config defaults for anything not specified
        duration = duration or self.config.default_duration
        tone = tone or self.config.default_tone
        layout = layout or self.config.compose_layout
        lut = lut or self.config.compose_lut
        aspect_ratio = aspect_ratio or self.config.default_aspect_ratio
        video_model = video_model or self.config.scene_video_model
        reference_audio = reference_audio or self.config.reference_audio
        character_image = character_image or self.config.character_image

        skip_stages = set(skip_stages or [])

        # Figure out which stages to run based on start_stage
        if start_stage:
            stages_to_skip = set(STAGES[:STAGES.index(start_stage)])
            skip_stages |= stages_to_skip

        self.progress.on_start("pipeline", f"UGC Pipeline: {topic}")

        if dry_run:
            return self._dry_run(topic, reference_audio, character_image,
                                  duration, tone, skip_stages)

        # ── Stage 1: Script Gen ──────────────────────────────────────────────
        if "script_gen" in skip_stages:
            self.progress.on_skip("script_gen", "skipped by request")
        else:
            script_path = self.config.output_dir / "script.json"
            artifacts.script = generate_script(
                topic=topic,
                config=self.config,
                duration=duration,
                tone=tone,
                caption_keywords=caption_keywords,
                output_path=script_path,
                progress=self.progress,
            )
            artifacts.script_path = str(script_path)

            # Build caption text for compose stage
            cap_parts = [artifacts.script.get("hook", "")]
            for s in artifacts.script.get("sections", []):
                cap_parts.append(s.get("speaker_text", ""))
            cap_parts.append(artifacts.script.get("cta", ""))
            self._caption_text = " ".join(p for p in cap_parts if p)

        # ── Stage 2: Voice Clone ─────────────────────────────────────────────
        if "voice_clone" in skip_stages:
            self.progress.on_skip("voice_clone", "skipped by request")
        elif not reference_audio:
            self.progress.on_skip("voice_clone", "no reference_audio provided")
        else:
            audio_out = self.config.output_dir / "cloned_voice.wav"
            artifacts.audio_path = clone_voice(
                script=artifacts.script,
                reference_audio=reference_audio,
                output_path=audio_out,
                config=self.config,
                progress=self.progress,
            )

        # ── Stage 3: Talking Head ───────────────────────────────────────────
        if "talking_head" in skip_stages:
            self.progress.on_skip("talking_head", "skipped by request")
        elif not artifacts.audio_path:
            self.progress.on_skip("talking_head", "no audio_path (voice clone skipped or failed)")
        else:
            th_out = self.config.output_dir / "talking_head.mp4"
            artifacts.talking_head_path = generate_talking_head(
                audio_path=artifacts.audio_path,
                character_image=character_image,
                output_path=th_out,
                config=self.config,
                progress=self.progress,
            )

        # ── Stage 4: Scene Video ────────────────────────────────────────────
        if "scene_video" in skip_stages:
            self.progress.on_skip("scene_video", "skipped by request")
        else:
            scene_out = self.config.output_dir / "scene_video.mp4"
            scene_descriptions = (artifacts.script.get("scene_sequence", [])
                                  if artifacts.script else [])
            artifacts.scene_video_path = generate_scene_video(
                scene_descriptions=scene_descriptions,
                output_path=scene_out,
                config=self.config,
                progress=self.progress,
            )

        # ── Stage 5: Compose & Polish ──────────────────────────────────────
        if "compose" in skip_stages:
            self.progress.on_skip("compose", "skipped by request")
        elif not artifacts.talking_head_path:
            self.progress.on_skip("compose", "no talking_head_path (talking head skipped or failed)")
        else:
            # Use scene_video_path or a fallback
            scene_vid = artifacts.scene_video_path
            if not scene_vid:
                # Create a minimal colored placeholder
                fallback_scene = self.config.output_dir / "scene_placeholder.mp4"
                subprocess.run([
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={duration}",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    str(fallback_scene),
                ], check=True, capture_output=True)
                scene_vid = str(fallback_scene)

            th_path = self.config.output_dir / "thumbnail.jpg" if thumbnail else None

            artifacts.final_video_path = compose_and_polish(
                talking_head=artifacts.talking_head_path,
                scene_video=scene_vid,
                output_path=self.config.output_dir / "ugc_final.mp4",
                config=self.config,
                script=artifacts.script,
                thumbnail_path=th_path,
                progress=self.progress,
            )
            if th_path and th_path.exists():
                artifacts.thumbnail_path = str(th_path)

        elapsed = time.time() - self._started_at
        self.progress.on_progress("pipeline",
            f"Pipeline complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")
        return artifacts

    def dry_run(self) -> dict:
        """Validate pipeline configuration without running heavy steps.

        Checks:
        - Config file loads correctly
        - All stage scripts exist
        - Reference audio file exists (if path provided)
        - ComfyUI is reachable (if applicable)
        - FFmpeg is available
        - LLM endpoint is reachable
        """
        checks = {}
        ok = True

        # Check config
        checks["config_loaded"] = True

        # Check stage scripts
        for stage in ["voice_clone", "talking_head", "video_gen", "compose"]:
            script = self.config.skill_dir / "scripts" / f"{stage.replace('video_gen','video_gen').replace('compose','compose').replace('talking_head','talking_head').replace('voice_clone','voice_clone')}.py"
            script_name = f"{stage}.py" if stage != "video_gen" else "video_gen.py"
            sp = self.config.skill_dir / "scripts" / script_name
            checks[f"script_{stage}_exists"] = sp.exists()
            if not sp.exists():
                ok = False

        # Check FFmpeg
        try:
            r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
            checks["ffmpeg_available"] = r.returncode == 0
        except Exception:
            checks["ffmpeg_available"] = False
            ok = False

        # Check ComfyUI
        try:
            import urllib.request
            urllib.request.urlopen(self.config.comfyui_host, timeout=5)
            checks["comfyui_reachable"] = True
        except Exception:
            checks["comfyui_reachable"] = False

        # Check LLM endpoint
        if self.config.llm_provider == "ollama":
            try:
                import urllib.request
                urllib.request.urlopen(self.config.llm_endpoint.replace("/api/generate",""), timeout=5)
                checks["ollama_reachable"] = True
            except Exception:
                checks["ollama_reachable"] = False

        # Check reference audio if configured
        if self.config.reference_audio:
            checks["reference_audio_exists"] = Path(self.config.reference_audio).expanduser().exists()

        checks["all_passed"] = ok
        return checks

    def _dry_run(
        self,
        topic: str,
        reference_audio: str | None,
        character_image: str | None,
        duration: int,
        tone: str,
        skip_stages: set,
    ) -> PipelineArtifacts:
        """Run validation-only pass through the pipeline."""
        checks = self.dry_run()
        elapsed = time.time() - self._started_at

        print(f"\n[DRY RUN] Pipeline validation complete ({elapsed:.1f}s)")
        print(f"Config: {self.config.output_dir}")
        print(f"Topic: {topic}")
        print(f"Duration: {duration}s, Tone: {tone}")
        print(f"Skip stages: {skip_stages or 'none'}")
        print(f"\nValidation checks:")
        for k, v in checks.items():
            status = "PASS" if v else "FAIL"
            print(f"  [{status}] {k}")

        if not checks.get("all_passed", False):
            print("\n[WARNING] Some checks failed. Pipeline may not run correctly.")

        return PipelineArtifacts()


# ─── Factory helper for quick CLI use ────────────────────────────────────────

def run(
    topic: str,
    reference_audio: str | None = None,
    character_image: str | None = None,
    config: str | Path | None = None,
    duration: int | None = None,
    tone: str | None = None,
    layout: str | None = None,
    lut: str | None = None,
    aspect_ratio: str | None = None,
    video_model: str | None = None,
    output_dir: str | Path | None = None,
    skip_stages: list[str] | None = None,
    start_stage: str | None = None,
    dry_run: bool = False,
    thumbnail: bool = True,
    progress: ProgressCallback | None = None,
) -> PipelineArtifacts:
    """Convenience function to run the pipeline in one call.

    Example:
        results = run(
            topic="5 tips for better sleep",
            reference_audio="~/models/xttsv2/samples/jenny.wav",
            duration=30,
        )
        print(results.final_video_path)
    """
    cfg = PipelineConfig.load(config) if config else PipelineConfig.load()
    pipeline = UGCPipeline(cfg, progress=progress, output_dir=output_dir)
    return pipeline.run(
        topic=topic,
        reference_audio=reference_audio,
        character_image=character_image,
        duration=duration,
        tone=tone,
        layout=layout,
        lut=lut,
        aspect_ratio=aspect_ratio,
        video_model=video_model,
        skip_stages=skip_stages,
        start_stage=start_stage,
        dry_run=dry_run,
        thumbnail=thumbnail,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ugc_pipeline",
        description="UGC Video Pipeline — End-to-end AI video generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Full pipeline with all defaults
  python ugc_pipeline.py --topic "5 tips for better sleep" \\
    --reference-audio ~/models/xttsv2/samples/jenny.wav \\
    --character ~/models/hedra/characters/avatar.png

  # Resume from talking head (if you already have the audio)
  python ugc_pipeline.py --topic "Product launch" \\
    --reference-audio ./voice.wav \\
    --start-stage talking_head

  # Dry run to validate setup without running heavy steps
  python ugc_pipeline.py --topic "Test" --dry-run

  # With custom config
  python ugc_pipeline.py --config pipeline_config.json --topic "Video topic"

  # Skip scene video (use colored background instead)
  python ugc_pipeline.py --topic "Quick video" --skip-stages scene_video \\
    --reference-audio voice.wav --character avatar.png

Environment variables:
  LLM_PROVIDER     LLM backend: ollama|anthropic|openai  (default: ollama)
  LLM_MODEL        Model name (default: llama3.1:70b)
  OLLAMA_ENDPOINT  Ollama API endpoint (default: http://localhost:11434/api/generate)
  COMFYUI_HOST     ComfyUI host (default: http://localhost:8188)
  ANTHROPIC_API_KEY  API key for Anthropic
  OPENAI_API_KEY     API key for OpenAI
  UGC_PIPELINE_CONFIG  Path to config JSON (default: pipeline_config.json in skill dir)
""",
    )

    # Core inputs
    parser.add_argument("--topic", "-t", required=True, help="Video topic/description")
    parser.add_argument("--reference-audio", help="Voice reference audio (WAV/MP3, 5-30s)")
    parser.add_argument("--character", "-c", help="Character image (PNG/JPG) or text prompt to generate avatar")
    parser.add_argument("--duration", type=int, help="Target duration in seconds (default: 30)")
    parser.add_argument("--tone", choices=["casual", "professional", "urgent", "playful"],
                        help="Script tone (default: casual)")

    # Config & output
    parser.add_argument("--config", help="Path to pipeline_config.json")
    parser.add_argument("--output-dir", "-o", help="Output directory (default: ~/.hermes/ugc-output)")

    # Stage options
    parser.add_argument("--layout", choices=["picture_in_picture", "side_by_side", "overlay"],
                        help="Composite layout (default: picture_in_picture)")
    parser.add_argument("--lut", help="LUT name to apply (default: cinematic, use 'none' to skip)")
    parser.add_argument("--aspect-ratio", help="Video aspect ratio (default: 9:16)")
    parser.add_argument("--video-model", choices=["wan22", "ltx"],
                        help="Scene video model (default: wan22)")

    # Pipeline control
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate pipeline config and exit without running heavy steps")
    parser.add_argument("--start-stage", choices=STAGES,
                        help=f"Resume from a specific stage (auto-detects if artifacts exist)")
    parser.add_argument("--skip-stages", nargs="+", choices=STAGES,
                        help="Explicitly skip these stages")
    parser.add_argument("--no-thumbnail", action="store_true", help="Skip thumbnail extraction")
    parser.add_argument("--captions", nargs="+", dest="caption_keywords",
                        help="Caption keywords to incorporate in script")

    args = parser.parse_args()

    # Load config
    try:
        config = PipelineConfig.load(args.config) if args.config else PipelineConfig.load()
    except Exception as e:
        print(f"[Error] Failed to load config: {e}")
        sys.exit(1)

    # Override output_dir if specified
    output_dir = Path(args.output_dir) if args.output_dir else None

    # Create pipeline
    pipeline = UGCPipeline(config, output_dir=output_dir)

    # Handle dry-run
    if args.dry_run:
        checks = pipeline.dry_run()
        all_passed = checks.pop("all_passed", False)
        print("\nValidation Results:")
        for k, v in checks.items():
            print(f"  {'[PASS]' if v else '[FAIL]'} {k}")
        sys.exit(0 if all_passed else 1)

    # Run
    try:
        results = pipeline.run(
            topic=args.topic,
            reference_audio=args.reference_audio,
            character_image=args.character,
            duration=args.duration,
            tone=args.tone,
            layout=args.layout,
            lut=args.lut,
            aspect_ratio=args.aspect_ratio,
            video_model=args.video_model,
            skip_stages=args.skip_stages,
            start_stage=args.start_stage,
            caption_keywords=args.caption_keywords,
            thumbnail=not args.no_thumbnail,
        )

        print("\n" + "=" * 60)
        print("Pipeline Complete!")
        print("=" * 60)
        print("\nOutput Files:")
        for key, value in results.to_dict().items():
            print(f"  {key}: {value}")
        print()

    except Exception as e:
        print(f"\n[Pipeline Error] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
