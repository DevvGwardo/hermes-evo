#!/usr/bin/env python3
"""
talking_head.py — Generate lip-synced talking head video.

Supports multiple backends in priority order:
  1. Hedra       (https://github.com/Hedra-Labs/Hedra) — audio+image → animated talking head
  2. SadTalker   (https://github.com/Winfredy/SadTalker) — audio+image → talking head video
  3. Wav2Lip     (https://github.com/Rudrabha/Wav2Lip)  — lip-sync to face image/video

Also includes an avatar generator using Stable Diffusion / FLUX.1
if no character image is provided.

Usage:
    python talking_head.py --audio <audio.wav> --character <image.png> --output <out.mp4>
    python talking_head.py --audio <audio.wav> --character "blonde woman smiling" --output <out.mp4>
    python talking_head.py --audio <audio.wav> --character <image.png> --output <out.mp4> --backend sadtalker
"""

import argparse
import os
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Literal

# ─── Model paths ──────────────────────────────────────────────────────────────

HEDRA_REPO      = os.path.expanduser("~/models/hedra")
WAV2LIP_MODEL   = os.path.expanduser("~/models/wav2lip/wav2lip.pth")
SADTALKER_REPO  = os.path.expanduser("~/models/sadtalker")
SD_MODELS_DIR   = os.path.expanduser("~/models/stable-diffusion")
COMFYUI_PORT    = 8188  # ComfyUI default port

# ─── Backend priority ─────────────────────────────────────────────────────────

BACKEND_PRIORITY = ["hedra", "sadtalker", "wav2lip"]


# ══════════════════════════════════════════════════════════════════════════════
# Stage 0: Avatar / Character Image Generation
# ══════════════════════════════════════════════════════════════════════════════

def generate_avatar(
    prompt: str,
    output_path: str,
    model: str = "sd-xl",
    seed: int = 42,
    width: int = 1024,
    height: int = 1024,
) -> str:
    """
    Generate a character avatar image from a text prompt.

    Tries multiple backends in order:
      1. Stable Diffusion via Diffusers (local)
      2. FLUX via Diffusers (local)
      3. Stable Diffusion via ComfyUI (local API)
      4. DALL-E 3 / FLUX via OpenAI API (cloud fallback)

    Args:
        prompt: Text description of the character
        output_path: Where to save the generated image
        model: Which model to use (sd-xl, flux-schnell, flux-dev)
        seed: Random seed
        width, height: Output resolution

    Returns:
        Path to the generated image file
    """
    print(f"[Avatar] Generating avatar from prompt: '{prompt[:60]}...'")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # ── Strategy 1: Diffusers (local SD/FLUX) ──────────────────────────────
    try:
        import torch
        from diffusers import StableDiffusionImg2ImgPipeline, FluxPipeline
        from PIL import Image

        if model in ("flux-schnell", "flux-dev"):
            pipe = FluxPipeline.from_pretrained(
                "black-forest-labs/FLUX.1-schnell" if model == "flux-schnell"
                else "black-forest-labs/FLUX.1-dev",
                torch_dtype=torch.bfloat16 if model != "flux-schnell" else torch.float16,
                local_files_only=False,
            )
            if torch.cuda.is_available():
                pipe = pipe.to("cuda")
            else:
                pipe = pipe.to("cpu")

        else:  # sd-xl
            pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                local_files_only=False,
            )
            if torch.cuda.is_available():
                pipe = pipe.to("cuda")
            else:
                pipe = pipe.to("cpu")

        # Generate from a simple starting point
        init_image = Image.new("RGB", (width, height), color=(128, 128, 128))

        result = pipe(
            prompt=prompt,
            image=init_image,
            num_inference_steps=25,
            guidance_scale=7.5,
            seed=seed,
        ).images[0]

        result.save(output_path)
        size_kb = os.path.getsize(output_path) / 1024
        print(f"[Avatar] Generated via Diffusers ({model}): {output_path} ({size_kb:.0f} KB)")
        return output_path

    except ImportError as e:
        print(f"[Avatar] Diffusers not available: {e}")
    except Exception as e:
        print(f"[Avatar] Diffusers generation failed: {e}")

    # ── Strategy 2: ComfyUI (local SD/FLUX via API) ────────────────────────
    try:
        import requests
        import json

        # Check if ComfyUI is running
        try:
            resp = requests.get(f"http://localhost:{COMFYUI_PORT}/system_stats", timeout=5)
            comfyui_available = resp.status_code == 200
        except Exception:
            comfyui_available = False

        if not comfyui_available:
            raise RuntimeError("ComfyUI not running")

        # Build a simple SD img2img workflow
        workflow = _build_comfyui_avatar_workflow(prompt, seed, width, height)
        resp = requests.post(
            f"http://localhost:{COMFYUI_PORT}/prompt",
            json={"prompt": workflow},
            timeout=300,
        )
        resp.raise_for_status()
        prompt_id = resp.json()["prompt_id"]

        # Poll for completion
        for _ in range(120):  # 2 min timeout
            history = requests.get(
                f"http://localhost:{COMFYUI_PORT}/history/{prompt_id}", timeout=10
            ).json()
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node_id, data in outputs.items():
                    if data.get("type") == "image":
                        # Download image
                        img_url = f"http://localhost:{COMFYUI_PORT}/view?filename={data['images'][0]['filename']}"
                        img_resp = requests.get(img_url, timeout=30)
                        img_resp.raise_for_status()
                        with open(output_path, "wb") as f:
                            f.write(img_resp.content)
                        print(f"[Avatar] Generated via ComfyUI: {output_path}")
                        return output_path
                break
            import time
            time.sleep(1)

    except Exception as e:
        print(f"[Avatar] ComfyUI generation failed: {e}")

    # ── Strategy 3: OpenAI Image API (DALL-E 3 / FLUX) ────────────────────
    try:
        import openai

        client = openai.OpenAI()
        model_name = "dall-e-3" if "gpt" not in os.environ.get("OPENAI_API_KEY", "") else "dall-e-3"

        result = client.images.generate(
            model="dall-e-3",
            prompt=f"Portrait photo of {prompt}, face centered, frontal view, realistic, professional lighting",
            size=f"{width}x{height}",
            n=1,
            response_format="url",
        )
        image_url = result.data[0].url

        # Download the image
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(img_resp.content)

        size_kb = os.path.getsize(output_path) / 1024
        print(f"[Avatar] Generated via DALL-E 3: {output_path} ({size_kb:.0f} KB)")
        return output_path

    except Exception as e:
        print(f"[Avatar] OpenAI image generation failed: {e}")

    raise RuntimeError(
        "[Avatar] All avatar generation strategies failed. "
        "Install diffusers, start ComfyUI, or set OPENAI_API_KEY."
    )


def _build_comfyui_avatar_workflow(prompt: str, seed: int, width: int, height: int) -> dict:
    """Build a minimal ComfyUI img2img workflow for avatar generation."""
    # This is a simplified workflow — adapt to your actual ComfyUI node IDs
    return {
        "1": {
            "inputs": {"text": prompt, "clip": ["3", 1]},
            "class_type": "CLIPTextEncode",
        },
        "2": {
            "inputs": {
                "text": "blurry, low quality, distorted, watermark, text, logo",
                "clip": ["3", 1],
            },
            "class_type": "CLIPTextEncode",
        },
        "3": {
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors",
            },
            "class_type": "CheckpointLoaderSimple",
        },
        "4": {
            "inputs": {
                "model": ["3", 0],
                "positive": ["1", 0],
                "negative": ["2", 0],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": 25,
                "cfg": 7.5,
                "sampler_name": "euler",
            },
            "class_type": "KSampler",
        },
        "5": {
            "inputs": {"samples": ["4", 0], "width": width, "height": height},
            "class_type": "VAEEncode",
        },
        "6": {
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        "7": {
            "inputs": {"samples": ["4", 0]},
            "class_type": "VAEDecode",
        },
        "8": {
            "inputs": {"images": ["7", 0], "filename_prefix": "avatar", "output_path": ""},
            "class_path": "Image Save",
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1: Hedra (primary talking head backend)
# ══════════════════════════════════════════════════════════════════════════════

def _hedra_available() -> bool:
    """Check if Hedra is installed and accessible."""
    try:
        result = subprocess.run(
            ["hedra", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def _install_hedra() -> None:
    """Install Hedra from source."""
    print("[Hedra] Installing Hedra from source...")
    hedra_dir = Path(HEDRA_REPO)
    if not hedra_dir.exists():
        subprocess.run(
            ["git", "clone", "https://github.com/Hedra-Labs/Hedra", str(hedra_dir)],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(hedra_dir)],
        check=True,
        capture_output=True,
    )
    print("[Hedra] Installation complete.")


def _download_hedra_default_character() -> str:
    """Download the default Hedra character image if not present."""
    import urllib.request

    char_dir = Path(HEDRA_REPO) / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)
    dest = char_dir / "default_avatar.png"

    if dest.exists():
        return str(dest)

    # Try to download from Hedra's repo assets
    url = "https://raw.githubusercontent.com/Hedra-Labs/Hedra/main/examples/assets/avatar.png"
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"[Hedra] Downloaded default character to {dest}")
    except Exception:
        # Fallback: use a built-in avatar generator
        print("[Hedra] Could not download default character — using avatar generator")
        generate_avatar(
            prompt="professional headshot photo of a friendly person, frontal face, studio lighting",
            output_path=str(dest),
        )
    return str(dest)


def generate_hedra(
    audio_path: str,
    character_image: str,
    output_path: str,
    aspect_ratio: str = "9:16",
    seed: int = 42,
) -> str:
    """
    Generate talking head using Hedra.

    Hedra CLI/API (v1.x):
        hedra generate --audio <path> --image <path> --output <path>
                       [--aspect-ratio 9:16|16:9|1:1] [--seed 42]
                       [--num-video-steps 100]

    Python API:
        from hedra import Hedra, HedraCharacter, HedraAudio, HedraHeadOptions
        hedra = Hedra()
        character = HedraCharacter(image_path=character_image)
        audio = HedraAudio(source_path=audio_path)
        options = HedraHeadOptions(aspect_ratio=aspect_ratio, seed=seed)
        result = hedra.generate(audio=audio, character=character, options=options)

    Args:
        audio_path: Path to audio file (WAV, 16kHz mono recommended)
        character_image: Path to character image (PNG/JPG, frontal face)
        output_path: Output MP4 path
        aspect_ratio: Video aspect ratio (9:16, 16:9, 1:1)
        seed: Random seed

    Returns:
        Path to generated video file
    """
    if not _hedra_available():
        _install_hedra()

    # Validate inputs
    audio_path = os.path.abspath(audio_path)
    character_image = os.path.abspath(character_image)
    output_path = os.path.abspath(output_path)

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not os.path.exists(character_image):
        raise FileNotFoundError(f"Character image not found: {character_image}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"[Hedra] Generating talking head...")
    print(f"[Hedra]   Audio:     {audio_path}")
    print(f"[Hedra]   Character: {character_image}")
    print(f"[Hedra]   Output:    {output_path}")
    print(f"[Hedra]   Aspect:    {aspect_ratio}  Seed: {seed}")

    # Try CLI first, then fall back to Python API
    cli_success = False
    try:
        cmd = [
            "hedra", "generate",
            "--audio", audio_path,
            "--image", character_image,
            "--output", output_path,
            "--aspect-ratio", aspect_ratio,
            "--seed", str(seed),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600
        )
        if result.returncode == 0 and os.path.exists(output_path):
            cli_success = True
        else:
            print(f"[Hedra] CLI failed: {result.stderr[:300]}")
    except FileNotFoundError:
        print("[Hedra] 'hedra' CLI not found — trying Python API")
    except subprocess.TimeoutExpired:
        print("[Hedra] CLI timed out — trying Python API")
    except Exception as e:
        print(f"[Hedra] CLI error: {e} — trying Python API")

    if not cli_success:
        # Python API fallback
        try:
            from hedra import Hedra, HedraCharacter, HedraAudio, HedraHeadOptions

            hedra = Hedra(device="cuda" if _has_cuda() else "cpu")
            character = HedraCharacter(image_path=character_image)
            audio = HedraAudio(source_path=audio_path)
            options = HedraHeadOptions(
                aspect_ratio=aspect_ratio,
                seed=seed,
                num_video_steps=100,
            )
            result = hedra.generate(audio=audio, character=character, options=options)
            # Hedra returns a path or saves to output_path automatically
            if result and os.path.exists(result):
                if result != output_path:
                    shutil.copy(result, output_path)
            print(f"[Hedra] Talking head generated: {output_path}")
        except ImportError:
            raise RuntimeError(
                "Hedra not installed. Run: pip install git+https://github.com/Hedra-Labs/Hedra"
            )
        except Exception as e:
            raise RuntimeError(f"Hedra generation failed: {e}")

    # Verify output
    if not os.path.exists(output_path):
        raise RuntimeError("Hedra generation failed — no output file created")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[Hedra] Talking head generated: {output_path} ({size_mb:.1f} MB)")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2: SadTalker (fallback talking head)
# ══════════════════════════════════════════════════════════════════════════════

def _sadtalker_available() -> bool:
    """Check if SadTalker is installed."""
    sadtalker_inference = Path(SADTALKER_REPO) / "inference.py"
    return sadtalker_inference.exists()


def _install_sadtalker() -> None:
    """Clone and install SadTalker."""
    print("[SadTalker] Installing SadTalker from source...")
    repo_dir = Path(SADTALKER_REPO)
    if not repo_dir.exists():
        subprocess.run(
            ["git", "clone", "https://github.com/Winfredy/SadTalker", str(repo_dir)],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(repo_dir)],
        check=True,
        capture_output=True,
    )
    # Download SadTalker models
    _download_sadtalker_models()
    print("[SadTalker] Installation complete.")


def _download_sadtalker_models() -> None:
    """Download SadTalker model checkpoints."""
    import urllib.request
    import zipfile

    model_dir = Path(SADTALKER_REPO) / "checkpoints"
    model_dir.mkdir(parents=True, exist_ok=True)

    # SadTalker model URLs (from official repo)
    urls = {
        "SadTalker_V0.0.2_latest.pth": (
            "https://github.com/Winfredy/SadTalker/releases/download/V0.0.2/SadTalker_V0.0.2_latest.pth"
        ),
    }

    for filename, url in urls.items():
        dest = model_dir / filename
        if dest.exists():
            continue
        print(f"[SadTalker] Downloading {filename}...")
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as e:
            print(f"[SadTalker] Failed to download {filename}: {e}")


def generate_sadtalker(
    audio_path: str,
    character_image: str,
    output_path: str,
    expression_scale: float = 1.0,
    enhancer: Optional[str] = None,
) -> str:
    """
    Generate talking head using SadTalker.

    SadTalker CLI:
        python inference.py --driven_audio <audio>
                           --source_image <image>
                           --result_dir <output_dir>
                           [--expression_scale 1.0]
                           [--enhancer gfpgan]
                           [--still]

    Args:
        audio_path: Path to audio file
        character_image: Path to character image
        output_path: Output MP4 path
        expression_scale: Expression intensity (0.5–2.0)
        enhancer: Optional face enhancer (gfpgan, CodeFormer)

    Returns:
        Path to generated video file
    """
    if not _sadtalker_available():
        _install_sadtalker()

    audio_path = os.path.abspath(audio_path)
    character_image = os.path.abspath(character_image)
    output_path = os.path.abspath(output_path)

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not os.path.exists(character_image):
        raise FileNotFoundError(f"Character image not found: {character_image}")

    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    print(f"[SadTalker] Generating talking head from {audio_path}")
    print(f"[SadTalker]   Image:   {character_image}")
    print(f"[SadTalker]   Output:  {output_path}")

    cmd = [
        sys.executable,
        str(Path(SADTALKER_REPO) / "inference.py"),
        "--driven_audio", audio_path,
        "--source_image", character_image,
        "--result_dir", output_dir,
        "--expression_scale", str(expression_scale),
    ]
    if enhancer:
        cmd += ["--enhancer", enhancer]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        print(f"[SadTalker] STDERR: {result.stderr[:500]}")
        raise RuntimeError(f"SadTalker generation failed: {result.stderr[:300]}")

    # SadTalker saves to result_dir with a generated filename — find it
    generated = _find_video_in_dir(output_dir)
    if generated and os.path.exists(generated):
        if generated != output_path:
            shutil.copy(generated, output_path)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[SadTalker] Talking head generated: {output_path} ({size_mb:.1f} MB)")
        return output_path

    raise RuntimeError("SadTalker generation failed — no output file found")


def _find_video_in_dir(directory: str) -> Optional[str]:
    """Find a generated MP4 video in a directory."""
    for ext in ("*.mp4", "*.avi", "*.mov"):
        matches = list(Path(directory).glob(ext))
        if matches:
            # Return the most recently modified video
            return str(max(matches, key=os.path.getmtime))
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Stage 3: Wav2Lip (lip-sync only, no head pose animation)
# ══════════════════════════════════════════════════════════════════════════════

def _wav2lip_available() -> bool:
    """Check if Wav2Lip is available."""
    if not os.path.exists(WAV2LIP_MODEL):
        return False
    try:
        subprocess.run(
            [sys.executable, "-m", "wav2lip.inference", "--help"],
            capture_output=True,
            timeout=10,
            check=True,
        )
        return True
    except Exception:
        return False


def _download_wav2lip_model() -> str:
    """Download Wav2Lip model weights."""
    import urllib.request

    model_dir = Path(WAV2LIP_MODEL).parent
    model_dir.mkdir(parents=True, exist_ok=True)

    if os.path.exists(WAV2LIP_MODEL):
        return WAV2LIP_MODEL

    # Official Wav2Lip model URL
    url = "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip.pth"
    print(f"[Wav2Lip] Downloading model from {url}...")
    try:
        urllib.request.urlretrieve(url, WAV2LIP_MODEL)
        print(f"[Wav2Lip] Model saved to {WAV2LIP_MODEL}")
    except Exception as e:
        raise RuntimeError(
            f"Failed to download Wav2Lip model: {e}\n"
            f"Manually download from: https://github.com/Rudrabha/Wav2Lip/releases"
        )
    return WAV2LIP_MODEL


def _install_wav2lip() -> None:
    """Clone and install Wav2Lip."""
    print("[Wav2Lip] Installing Wav2Lip...")
    repo_dir = Path("~/models/wav2lip").expanduser()
    if not repo_dir.exists():
        subprocess.run(
            ["git", "clone", "https://github.com/Rudrabha/Wav2Lip", str(repo_dir)],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(repo_dir)],
        check=True,
        capture_output=True,
    )
    _download_wav2lip_model()
    print("[Wav2Lip] Installation complete.")


def generate_wav2lip(
    audio_path: str,
    face_image: str,
    output_path: str,
    resize_factor: int = 2,
    pad: tuple = (0, 0, 0, 0),
) -> str:
    """
    Generate lip-synced video using Wav2Lip.

    Wav2Lip CLI:
        python inference.py --checkpoint_path <model.pth>
                            --audio <audio.wav>
                            --face <image_or_video>
                            --outfile <output.mp4>
                            [--resize_factor 2]
                            [--pad [left top right bottom]]

    Wav2Lip is a lip-sync-only model — it re-syncs the lips in the video to
    match the audio. Unlike Hedra/SadTalker, it does NOT animate a static image
    from scratch; it works on video files or images where the face is already present.

    For static images, Wav2Lip first generates a "talking face video" then re-lipsyncs.
    The quality is lower than Hedra/SadTalker for pure image→video generation.

    Args:
        audio_path: Path to audio file
        face_image: Path to face image (JPG/PNG) or face video (MP4)
        output_path: Output MP4 path
        resize_factor: Upscaling factor (2 = 2x larger)
        pad: Padding as [left, top, right, bottom]

    Returns:
        Path to generated video file
    """
    if not _wav2lip_available():
        _install_wav2lip()

    audio_path = os.path.abspath(audio_path)
    face_image = os.path.abspath(face_image)
    output_path = os.path.abspath(output_path)

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not os.path.exists(face_image):
        raise FileNotFoundError(f"Face image not found: {face_image}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"[Wav2Lip] Generating lip-sync...")
    print(f"[Wav2Lip]   Audio:  {audio_path}")
    print(f"[Wav2Lip]   Face:   {face_image}")
    print(f"[Wav2Lip]   Output: {output_path}")

    cmd = [
        sys.executable, "-m", "wav2lip.inference",
        "--checkpoint_path", WAV2LIP_MODEL,
        "--audio", audio_path,
        "--face", face_image,
        "--outfile", output_path,
        "--resize_factor", str(resize_factor),
        "--pad", str(pad[0]), str(pad[1]), str(pad[2]), str(pad[3]),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        # Wav2Lip sometimes fails on static images without a face detection
        # fallback: use the face image directly and let it try
        print(f"[Wav2Lip] First attempt failed: {result.stderr[:300]}")
        # Try without padding
        cmd[-4:] = ["--resize_factor", str(resize_factor)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"Wav2Lip generation failed: {result.stderr[:500]}")

    if not os.path.exists(output_path):
        raise RuntimeError("Wav2Lip generation failed — no output file created")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[Wav2Lip] Lip-sync complete: {output_path} ({size_mb:.1f} MB)")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# Stage 4: FOMM / First Order Motion Model (legacy fallback)
# ══════════════════════════════════════════════════════════════════════════════

def generate_fomm(
    audio_path: str,
    driving_video: str,
    output_path: str,
) -> str:
    """
    Animate a source image using First Order Motion Model.
    This is a legacy fallback that requires a driving video.

    CLI:
        python inference.py --config <config.yaml>
                            --checkpoint <checkpoint.pth>
                            --image <source_image>
                            --audio <audio>
                            --outdir <output_dir>

    Note: FOMM needs a driving video — it's not a pure audio-driven model.
    This is mostly here for completeness.
    """
    print("[FOMM] Generating animation (driving video required)...")

    fomm_dir = Path("~/models/fomm").expanduser()
    config_path = fomm_dir / "config" / "vox-256.yaml"
    checkpoint_path = fomm_dir / "checkpoint" / "vox-adv-256.pth"

    if not config_path.exists() or not checkpoint_path.exists():
        raise RuntimeError(
            f"FOMM not installed. Clone to ~/models/fomm:\n"
            f"  git clone https://github.com/AliaksandrSiarohin/first-order-model {fomm_dir}\n"
            f"  wget -P {fomm_dir}/checkpoint https://www.dropbox.com/s/6kq6r2q1lmv6owf/vox-adv-256.pth"
        )

    cmd = [
        sys.executable, str(fomm_dir / "inference.py"),
        "--config", str(config_path),
        "--checkpoint", str(checkpoint_path),
        "--image", driving_video,  # FOMM uses video as source in this mode
        "--audio", audio_path,
        "--outdir", os.path.dirname(output_path) or ".",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FOMM generation failed: {result.stderr[:300]}")

    generated = _find_video_in_dir(os.path.dirname(output_path) or ".")
    if generated:
        if generated != output_path:
            shutil.copy(generated, output_path)
        return output_path
    raise RuntimeError("FOMM generation failed — no output found")


# ══════════════════════════════════════════════════════════════════════════════
# Utility helpers
# ══════════════════════════════════════════════════════════════════════════════

def _has_cuda() -> bool:
    """Check if CUDA (GPU) is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def _prepare_character_image(
    character_image: str,
    temp_dir: Optional[str] = None,
) -> str:
    """
    Resolve character_image: if it's a text prompt, generate an avatar.
    If it's a file path, validate it exists.

    Returns:
        Valid path to a character image file
    """
    if not character_image:
        # Generate a default avatar
        fd, path = tempfile.mkstemp(suffix=".png", dir=temp_dir)
        os.close(fd)
        return generate_avatar(
            prompt="professional headshot photo of a friendly person, frontal face, studio lighting",
            output_path=path,
        )

    # Check if it looks like a file path or a text prompt
    if os.path.exists(character_image):
        return character_image

    # Treat as text prompt — generate an avatar
    ext = os.path.splitext(character_image)[1].lower()
    if not ext or ext not in (".png", ".jpg", ".jpeg", ".webp"):
        # It's a text prompt without file extension
        prompt = character_image
    else:
        prompt = character_image  # treat whole string as prompt

    fd, path = tempfile.mkstemp(suffix=".png", dir=temp_dir)
    os.close(fd)
    return generate_avatar(prompt=prompt, output_path=path)


# ══════════════════════════════════════════════════════════════════════════════
# Main dispatcher
# ══════════════════════════════════════════════════════════════════════════════

def generate_talking_head(
    audio_path: str,
    character_image: str,
    output_path: str,
    backend: Optional[Literal["hedra", "sadtalker", "wav2lip", "auto"]] = "auto",
    aspect_ratio: str = "9:16",
    seed: int = 42,
    use_wav2lip_fallback: bool = True,
) -> str:
    """
    Generate a lip-synced talking head video.

    Args:
        audio_path: Path to cloned voice audio (WAV/MP3)
        character_image: Path to character image, OR a text prompt describing the character.
                         If not provided, a default avatar is generated.
        output_path: Output MP4 path
        backend: Which backend to use ("auto", "hedra", "sadtalker", "wav2lip")
                 "auto" tries each in priority order until one succeeds.
        aspect_ratio: Video aspect ratio (9:16, 16:9, 1:1)
        seed: Random seed for reproducibility
        use_wav2lip_fallback: If True, fall back to Wav2Lip on failure

    Returns:
        Path to the generated video file

    Example:
        >>> generate_talking_head(
        ...     audio_path="output/voice.wav",
        ...     character_image="output/avatar.png",  # or a text prompt
        ...     output_path="output/talking_head.mp4",
        ...     backend="auto",
        ...     aspect_ratio="9:16",
        ... )
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Prepare character image (may generate from prompt)
    temp_dir = tempfile.mkdtemp(prefix="talking_head_")
    try:
        character_image = _prepare_character_image(character_image, temp_dir)
    except Exception as e:
        raise RuntimeError(
            f"Failed to prepare character image: {e}\n"
            "Provide a valid image path or a text prompt describing the character."
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # ── Dispatch to requested backend ─────────────────────────────────────
    if backend != "auto":
        backends = [backend]
    else:
        backends = BACKEND_PRIORITY.copy()

    errors = []

    for b in backends:
        try:
            if b == "hedra":
                return generate_hedra(
                    audio_path, character_image, output_path,
                    aspect_ratio=aspect_ratio, seed=seed,
                )
            elif b == "sadtalker":
                return generate_sadtalker(
                    audio_path, character_image, output_path,
                    expression_scale=1.0,
                )
            elif b == "wav2lip":
                return generate_wav2lip(
                    audio_path, character_image, output_path,
                )
        except Exception as e:
            errors.append(f"{b}: {e}")
            print(f"[Warning] {b} failed: {e}")
            continue

    # All auto backends failed — last resort: Wav2Lip even if not in backends list
    if use_wav2lip_fallback and "wav2lip" not in backends:
        try:
            return generate_wav2lip(audio_path, character_image, output_path)
        except Exception as e:
            errors.append(f"wav2lip_fallback: {e}")

    error_summary = " | ".join(f"{k}: {v}" for k, v in [(b, e) for b, e in zip(backends, errors)])
    raise RuntimeError(
        f"All talking head backends failed.\n"
        f"Errors: {error_summary}\n"
        f"Hint: Install at least one backend - "
        f"Hedra (recommended): pip install git+https://github.com/Hedra-Labs/Hedra"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLI entrypoint
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate lip-synced talking head video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using an existing character image
  python talking_head.py --audio voice.wav --character avatar.png --output head.mp4

  # Using a text prompt to generate the character
  python talking_head.py --audio voice.wav --character "blonde woman smiling" --output head.mp4

  # Force a specific backend
  python talking_head.py --audio voice.wav --character avatar.png --output head.mp4 --backend sadtalker

  # Auto-select backend with Wav2Lip fallback
  python talking_head.py --audio voice.wav --character avatar.png --output head.mp4 --use-wav2lip-fallback
""",
    )
    parser.add_argument(
        "--audio", required=True,
        help="Input audio file (WAV/MP3, 16kHz mono recommended)"
    )
    parser.add_argument(
        "--character",
        default="",
        help="Character image path (PNG/JPG) OR text prompt describing the character. "
             "If not provided, generates a default avatar."
    )
    parser.add_argument(
        "--output", required=True,
        help="Output MP4 path"
    )
    parser.add_argument(
        "--backend",
        default="auto",
        choices=["auto", "hedra", "sadtalker", "wav2lip"],
        help="Which lip-sync backend to use (default: auto, tries hedra → sadtalker → wav2lip)"
    )
    parser.add_argument(
        "--aspect-ratio", default="9:16",
        choices=["9:16", "16:9", "1:1"],
        help="Video aspect ratio (default: 9:16 for vertical social video)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--use-wav2lip-fallback", action="store_true",
        help="Use Wav2Lip as final fallback if all other backends fail"
    )
    parser.add_argument(
        "--avatar-model",
        default="sd-xl",
        choices=["sd-xl", "flux-schnell", "flux-dev"],
        help="Avatar generation model (if character is a text prompt)"
    )
    parser.add_argument(
        "--avatar-seed", type=int, default=42,
        help="Seed for avatar generation"
    )

    args = parser.parse_args()

    try:
        output = generate_talking_head(
            audio_path=args.audio,
            character_image=args.character,
            output_path=args.output,
            backend=args.backend,
            aspect_ratio=args.aspect_ratio,
            seed=args.seed,
            use_wav2lip_fallback=args.use_wav2lip_fallback,
        )
        print(f"\n✓ Talking head generated: {output}")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
