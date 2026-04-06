# UGC Video Pipeline

Local AI-powered UGC video generation pipeline for social media marketing.

## Overview

This pipeline generates talking-head + scene video composites with:
- **Voice cloning** (XTTS v2)
- **Lip-sync talking head** (Hedra / Wav2Lip)
- **Scene video generation** (Wan 2.2 / LTX-Video via ComfyUI)
- **Composition & polish** (FFmpeg + LUTs + captions)

## Quick Start

```bash
# 1. Install dependencies
pip install torch TTS anthropic openai opencv-python pillow
apt-get install ffmpeg libx264 libass

# 2. Download models
mkdir -p ~/models/xttsv2 ~/models/hedra ~/models/Wan2.2

# 3. Run pipeline
python scripts/ugc_pipeline.py \
  --topic "5 tips for better sleep" \
  --reference-audio ~/models/xttsv2/samples/jenny.wav \
  --character ~/models/hedra/characters/avatar.png \
  --duration 30
```

## Pipeline Stages

1. **Script Generation** → LLM generates video script
2. **Voice Clone** → XTTS v2 clones voice from reference
3. **Talking Head** → Hedra/Wav2Lip generates lip-sync video
4. **Scene Video** → Wan 2.2/LTX-Video generates B-roll
5. **Composition** → FFmpeg composites + applies LUT
6. **Output** → Final MP4 ready for social media

## Directory Structure

```
ugc-video-pipeline/
├── SKILL.md              # Full skill documentation
├── README.md             # This file
├── scripts/
│   ├── ugc_pipeline.py   # End-to-end orchestrator
│   ├── voice_clone.py    # XTTS v2 voice cloning
│   ├── talking_head.py   # Hedra/Wav2Lip lip-sync
│   ├── video_gen.py      # ComfyUI video generation
│   └── compose.py        # FFmpeg composition
├── workflows/
│   ├── wan22_video.json  # ComfyUI workflow for Wan 2.2
│   └── ltx_video.json    # ComfyUI workflow for LTX-Video
├── luts/                 # Color LUT files (.cube)
└── prompts/             # Prompt templates
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | LLM backend (anthropic/openai/ollama) |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Model name |
| `ANTHROPIC_API_KEY` | - | API key for Anthropic |
| `OPENAI_API_KEY` | - | API key for OpenAI |
| `COMFYUI_HOST` | `http://localhost:8188` | ComfyUI server URL |

### Command Line Options

```bash
--topic TEXT           Video topic/keyword (required)
--reference-audio PATH Voice reference audio (required)
--character PATH       Character image PNG (required)
--duration INT         Target duration seconds (default: 30)
--tone TEXT            casual|professional|urgent (default: casual)
--layout TEXT          picture_in_picture|side_by_side|overlay
--lut TEXT             LUT name (default: cinematic)
--video-model TEXT     wan22|ltx (default: wan22)
--aspect-ratio TEXT    Video aspect ratio (default: 9:16)
```

## GPU Requirements

| Stage | VRAM |
|-------|------|
| Voice Clone | 4-6 GB |
| Talking Head | 6-8 GB |
| Video Gen (Wan 2.2) | 16-24 GB |
| Video Gen (LTX) | 12-16 GB |

**Total**: 24GB+ recommended (run stages sequentially)

## Troubleshooting

### "CUDA out of memory"
- Reduce video resolution
- Use LTX-Video instead of Wan 2.2
- Clear GPU cache between stages

### "ComfyUI not running"
- Start ComfyUI: `cd ~/models/ComfyUI && python main.py`
- Check host: `echo $COMFYUI_HOST`

### "FFmpeg not found"
- Ubuntu/Debian: `apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

## License

Part of the Hermes Skills ecosystem.
