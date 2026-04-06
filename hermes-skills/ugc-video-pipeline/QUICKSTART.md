# UGC Video Pipeline - Quick Start Guide

A step-by-step guide to getting started with the UGC Video Pipeline skill.

## Prerequisites

- **OS:** Ubuntu 22.04+ or macOS
- **GPU:** NVIDIA GPU with 24GB VRAM (RTX 3090/4090 or equivalent)
- **Disk Space:** 80GB+ free
- **Python:** 3.9+

---

## Step 1: Run Setup Script

### Option A: Automated Setup (Recommended)

```bash
cd ~/.hermes/skills/ugc-video-pipeline
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
1. Check system requirements (GPU, RAM, disk space)
2. Install system dependencies (ffmpeg, git, etc.)
3. Install Python packages
4. Clone ComfyUI
5. Download all model weights (~63GB)
6. Verify installation

### Option B: Manual Setup

If you prefer manual installation, see [MODEL_MANIFEST.md](MODEL_MANIFEST.md) for individual model download instructions.

---

## Step 2: Configure the Pipeline

Edit the configuration file at `~/.hermes/skills/ugc-video-pipeline/pipeline_config.json`:

```json
{
  "paths": {
    "skill_dir": "~/.hermes/skills/ugc-video-pipeline",
    "output_dir": "~/.hermes/ugc-output",
    "models_dir": "~/models",
    "comfyui_dir": "~/models/ComfyUI"
  },
  "llm": {
    "provider": "anthropic",  // or "openai" or "ollama"
    "model": "claude-sonnet-4-20250514",
    "endpoint": "http://localhost:11434/api/generate"
  },
  "comfyui": {
    "host": "http://localhost:8188"
  }
}
```

### Set API Keys (if using cloud LLM)

```bash
# Anthropic
export ANTHROPIC_API_KEY="your-key-here"

# OpenAI
export OPENAI_API_KEY="your-key-here"
```

---

## Step 3: Start ComfyUI

ComfyUI is required for video generation (Stage 4).

```bash
# Option A: Run in background
cd ~/models/ComfyUI
python3 main.py --listen 0.0.0.0 --port 8188 &

# Option B: Run in foreground (to see logs)
cd ~/models/ComfyUI
python3 main.py --listen 0.0.0.0 --port 8188
```

Wait for ComfyUI to start, then access the web UI at `http://localhost:8188`.

---

## Step 4: Prepare Input Files

### Reference Audio (Required)

A 5-30 second WAV/MP3 of clear speech for voice cloning.

```bash
# Place your reference audio
cp your-voice-sample.wav ~/models/xttsv2/samples/reference.wav
```

### Character Image (Required for talking head)

A frontal face image (PNG/JPG, 512x512+ recommended).

```bash
# Place your character image
cp avatar.png ~/models/hedra/characters/avatar.png
```

---

## Step 5: Run the Pipeline

### Full Pipeline

```bash
cd ~/.hermes/skills/ugc-video-pipeline

python3 scripts/ugc_pipeline.py \
  --topic "5 tips for better sleep quality" \
  --reference-audio ~/models/xttsv2/samples/reference.wav \
  --character ~/models/hedra/characters/avatar.png \
  --duration 30 \
  --tone casual \
  --layout picture_in_picture
```

### Dry Run (Validate Without Running)

```bash
python3 scripts/ugc_pipeline.py \
  --topic "Test video" \
  --dry-run
```

### Resume from Specific Stage

```bash
# If you already have cloned voice, skip to talking head
python3 scripts/ugc_pipeline.py \
  --topic "Product launch" \
  --reference-audio ./cloned_voice.wav \
  --start-stage talking_head
```

### Skip Stages

```bash
# Skip scene video (use colored background)
python3 scripts/ugc_pipeline.py \
  --topic "Quick demo" \
  --reference-audio voice.wav \
  --character avatar.png \
  --skip-stages scene_video
```

---

## Pipeline Stages

| Stage | Script | Description | Output |
|-------|--------|-------------|--------|
| 1 | Script Gen | Generate marketing script via LLM | script.json |
| 2 | Voice Clone | Clone voice using XTTS v2 | cloned_voice.wav |
| 3 | Talking Head | Generate lip-synced head video | talking_head.mp4 |
| 4 | Video Gen | Generate scene/B-roll video | scene_video.mp4 |
| 5 | Compose | Composite + LUT + captions | ugc_final.mp4 |

---

## Output Files

All outputs go to `~/.hermes/ugc-output/`:

```
~/.hermes/ugc-output/
├── script.json           # Generated script (Stage 1)
├── cloned_voice.wav      # Cloned voice audio (Stage 2)
├── talking_head.mp4      # Lip-synced head (Stage 3)
├── scene_video.mp4       # B-roll scene (Stage 4)
├── ugc_final.mp4         # Final polished video (Stage 5)
└── thumbnail.jpg         # Thumbnail at 00:00:01
```

---

## CLI Options Reference

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--topic` | string | required | Video topic/description |
| `--reference-audio` | path | required | Voice reference WAV (5-30s) |
| `--character` | path/text | required | Character image or text prompt |
| `--duration` | int | 30 | Target duration (seconds) |
| `--tone` | str | casual | Script tone (casual/professional/urgent) |
| `--layout` | str | pip | Composite layout (pip/side_by_side/overlay) |
| `--lut` | str | cinematic | LUT to apply (cinematic/warm_social/none) |
| `--video-model` | str | wan22 | Scene model (wan22/ltx) |
| `--aspect-ratio` | str | 9:16 | Video aspect ratio (9:16/16:9/1:1) |
| `--output-dir` | path | ~/.hermes/ugc-output/ | Output directory |
| `--dry-run` | flag | false | Validate without running |
| `--start-stage` | str | - | Resume from stage |
| `--skip-stages` | list | - | Skip these stages |
| `--config` | path | pipeline_config.json | Config file |

---

## Using Individual Stage Scripts

Each stage can be run independently:

### Voice Clone Only
```bash
python3 scripts/voice_clone.py \
  --reference ~/models/xttsv2/samples/reference.wav \
  --text "Your script text here" \
  --output ./output/cloned_voice.wav
```

### Talking Head Only
```bash
python3 scripts/talking_head.py \
  --audio ./output/cloned_voice.wav \
  --character ~/models/hedra/characters/avatar.png \
  --output ./output/talking_head.mp4
```

### Scene Video Only
```bash
python3 scripts/video_gen.py \
  --scene "cozy bedroom with morning sunlight" \
  --duration 5 \
  --model wan22 \
  --output ./output/scene_video.mp4
```

### Composition Only
```bash
python3 scripts/compose.py \
  --talking-head ./output/talking_head.mp4 \
  --scene ./output/scene_video.mp4 \
  --output ./output/final.mp4 \
  --layout picture_in_picture \
  --lut cinematic
```

---

## Troubleshooting

### CUDA OOM (Out of Memory)
```bash
# Run stages sequentially, clear GPU cache
python3 scripts/ugc_pipeline.py ... --video-model ltx  # Use smaller model
```

### FFmpeg Not Found
```bash
# Ubuntu
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Model Download Failed
```bash
# Install git-lfs
git lfs install

# Try individual file download
wget <model-url>
```

### ComfyUI Won't Start
```bash
cd ~/models/ComfyUI
pip install -r requirements.txt
python3 main.py --listen 0.0.0.0 --port 8188
```

### XTTS v2 Model Not Found
```bash
# Models download automatically on first use
python3 -c "from TTS.api import TTS; tts = TTS('xtts_v2')"
```

---

## Example Commands

### Basic TikTok/Reels Style (9:16)
```bash
python3 scripts/ugc_pipeline.py \
  --topic "Why sleep matters" \
  --reference-audio ~/models/xttsv2/samples/reference.wav \
  --character ~/models/hedra/characters/avatar.png \
  --duration 30 \
  --tone casual \
  --layout picture_in_picture \
  --lut cinematic
```

### YouTube Style (16:9)
```bash
python3 scripts/ugc_pipeline.py \
  --topic "Product review: Wireless earbuds" \
  --reference-audio voice.wav \
  --character avatar.png \
  --duration 60 \
  --aspect-ratio 16:9 \
  --layout side_by_side
```

### Generate Character from Text Prompt
```bash
python3 scripts/ugc_pipeline.py \
  --topic "Morning routine tips" \
  --reference-audio voice.wav \
  --character "friendly woman with curly hair, natural makeup" \
  --duration 30
```

---

## File Locations

| Component | Path |
|-----------|------|
| Skill directory | `~/.hermes/skills/ugc-video-pipeline/` |
| Models | `~/models/` |
| ComfyUI | `~/models/ComfyUI/` |
| Output | `~/.hermes/ugc-output/` |
| Config | `~/.hermes/skills/ugc-video-pipeline/pipeline_config.json` |
| LUTs | `~/.hermes/skills/ugc-video-pipeline/luts/` |
| Workflows | `~/.hermes/skills/ugc-video-pipeline/workflows/` |

---

## Quick Reference

```bash
# Full setup
./scripts/setup.sh

# Start ComfyUI
cd ~/models/ComfyUI && python3 main.py &

# Run pipeline
python3 scripts/ugc_pipeline.py --topic "Your topic" --reference-audio ref.wav --character avatar.png

# Check output
ls -la ~/.hermes/ugc-output/
```
