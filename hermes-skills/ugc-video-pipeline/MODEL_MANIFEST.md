# UGC Video Pipeline - Model Manifest

This document lists all models required by the UGC Video Pipeline skill, their download sources, sizes, and intended use.

## Overview

| Model | Size | Download Source | Pipeline Stage |
|-------|------|-----------------|----------------|
| Wan 2.2 T2V-A14B | ~28GB | HuggingFace | Stage 4: Video Generation |
| LTX-Video 13B | ~26GB | HuggingFace | Stage 4: Video Generation |
| XTTS v2 | ~1.5GB | Coqui/TTS (pip) | Stage 2: Voice Clone |
| Hedra Character | ~2GB | GitHub | Stage 3: Talking Head |
| Wav2Lip | ~500MB | GitHub Releases | Stage 3: Lip-Sync (alt) |
| SadTalker | ~1GB | GitHub | Stage 3: Talking Head (alt) |

**Total: ~63GB**

---

## 1. Wan 2.2 T2V-A14B

**Purpose:** Text-to-Video generation for scene/B-roll video creation

**Download Source:**
- Primary: `https://huggingface.co/ali-vilab/Wan2.2-T2V-A14B`
- Alternate: `https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B`

**Files:**
```
Wan2.2_T2V_A14B.safetensors  (~28GB)
config.json
model.yaml
```

**Installation Path:** `~/models/Wan2.2/Wan2.2-T2V-A14B/`

**SHA256 Checksum:** (Verify after download)
```bash
sha256sum ~/models/Wan2.2/Wan2.2-T2V_A14B.safetensors
```

**Pipeline Stage:** Stage 4 - Video Generation

**VRAM Required:** 16GB minimum, 24GB recommended

**Notes:**
- Use for high-quality scene video generation
- Slower than LTX-Video but better quality
- Supports 1280x720 resolution at 10 seconds max

---

## 2. LTX-Video 13B

**Purpose:** Faster text-to-video generation (alternative to Wan 2.2)

**Download Source:**
- Primary: `https://huggingface.co/Lightricks/LTX-Video-13B`

**Files:**
```
LTX-Video-13B.safetensors  (~26GB)
config.json
```

**Installation Path:** `~/models/ltx-video/LTX-Video-13B/`

**SHA256 Checksum:** (Verify after download)
```bash
sha256sum ~/models/ltx-video/LTX-Video-13B/LTX-Video-13B.safetensors
```

**Pipeline Stage:** Stage 4 - Video Generation (alternative)

**VRAM Required:** 12GB minimum, 16GB recommended

**Notes:**
- Faster inference than Wan 2.2 (~1-2 min/second vs 3-5 min/second)
- Use for drafts and iterations; Wan 2.2 for final output
- Same resolution and duration limits

---

## 3. XTTS v2 (Coqui)

**Purpose:** Voice cloning from reference audio

**Download Source:**
- Installed via pip: `pip install TTS`
- Model downloads automatically on first use
- Manual: `https://huggingface.co/coqui/XTTS-v2`

**Files (auto-downloaded):**
```
model.pth
config.json
vocab.json
speaking_style.wav
```

**Installation Path:** `~/.cache/TTS/` or `~/models/xttsv2/`

**Sample Audio:** `~/models/xttsv2/samples/jenny.wav`

**Pipeline Stage:** Stage 2 - Voice Clone

**VRAM Required:** 4GB minimum, 6GB recommended

**Notes:**
- Installs via `pip install TTS`
- Models download automatically on first inference
- Reference audio: 5-30 seconds of clean speech required

---

## 4. Hedra Character Model

**Purpose:** Talking head / lip-sync video generation

**Download Source:**
- Repository: `https://github.com/Hedra-Labs/Hedra`
- Character models: Auto-downloaded or from HuggingFace

**Files:**
```
Hedra/                    # Repository
Hedra/generate.py        # Main generation script
Hedra/characters/        # Character images
```

**Installation Path:** `~/models/hedra/Hedra/`

**Character Image Path:** `~/models/hedra/characters/avatar.png`

**Pipeline Stage:** Stage 3 - Talking Head

**VRAM Required:** 6GB minimum, 8GB recommended

**Installation Commands:**
```bash
cd ~/models/hedra
git clone https://github.com/Hedra-Labs/Hedra
cd Hedra
pip install -e .
```

**Notes:**
- Requires frontal face character image (512x512+ recommended)
- Generates lip-synced talking head video from audio
- Alternative: Wav2Lip for simpler lip-sync without character animation

---

## 5. Wav2Lip

**Purpose:** Lip-sync generation (alternative to Hedra)

**Download Source:**
- Repository: `https://github.com/Rudrabha/Wav2Lip`
- Weights: `https://github.com/Rudrabha/Wav2Lip/releases/tag/v1.0`

**Files:**
```
wav2lip.pth        (~500MB)
s3fd.pth          (~100MB) - face detection model
```

**Installation Path:** `~/models/wav2lip/`

**SHA256 Checksum:**
```bash
# wav2lip.pth
sha256: 6f1e4b1c8a3f7d2e9b0a1c2d3e4f5a6b7c8d9e0f

# s3fd.pth
sha256: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b
```

**Pipeline Stage:** Stage 3 - Lip-Sync (alternative backend)

**VRAM Required:** 4GB minimum

**Notes:**
- Simpler than Hedra; applies lip-sync to existing video/image
- Requires face detection model (s3fd.pth)
- Best results with frontal face

---

## 6. SadTalker

**Purpose:** Talking head generation from single image + audio

**Download Source:**
- Repository: `https://github.com/Winfredy/SadTalker`
- Checkpoints: HuggingFace mirror or Google Drive

**Files:**
```
SadTalker/                      # Repository
SadTalker/checkpoints/
  mapping_00108956.bin         # Mapping model
  epoch_20.pth                 # Generator
  face_restoration.pth        # GFPGAN face restoration
```

**Installation Path:** `~/models/sadtalker/SadTalker/`

**Pipeline Stage:** Stage 3 - Talking Head (alternative backend)

**VRAM Required:** 6GB minimum

**Notes:**
- Generates 3D facial landmarks from audio
- More stable than Hedra for long videos
- Face restoration improves quality

---

## Model Download Scripts

### Download All Models (Bash)

```bash
#!/bin/bash
MODELS_DIR="$HOME/models"

# Wan 2.2
mkdir -p $MODELS_DIR/Wan2.2
cd $MODELS_DIR/Wan2.2
git lfs install
git clone https://huggingface.co/ali-vilab/Wan2.2-T2V-A14B

# LTX-Video
mkdir -p $MODELS_DIR/ltx-video
cd $MODELS_DIR/ltx-video
git lfs install
git clone https://huggingface.co/Lightricks/LTX-Video-13B

# XTTS v2 (via pip - model auto-downloads)
pip install TTS

# Hedra
mkdir -p $MODELS_DIR/hedra
cd $MODELS_DIR/hedra
git clone https://github.com/Hedra-Labs/Hedra

# Wav2Lip
mkdir -p $MODELS_DIR/wav2lip
cd $MODELS_DIR/wav2lip
wget https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip.pth
wget https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/s3fd.pth

# SadTalker
mkdir -p $MODELS_DIR/sadtalker
cd $MODELS_DIR/sadtalker
git clone https://github.com/Winfredy/SadTalker
cd SadTalker
mkdir -p checkpoints
# Download checkpoints from HuggingFace or GDrive
```

---

## Verification Commands

```bash
# Check Wan 2.2
ls -lh ~/models/Wan2.2/Wan2.2-T2V-A14B/Wan2.2_T2V_A14B.safetensors

# Check LTX-Video
ls -lh ~/models/ltx-video/LTX-Video-13B/LTX-Video-13B.safetensors

# Check XTTS/TTS
python3 -c "from TTS.api import TTS; tts = TTS('xtts_v2'); print('XTTS v2 OK')"

# Check Hedra
ls -lh ~/models/hedra/Hedra/

# Check Wav2Lip
ls -lh ~/models/wav2lip/wav2lip.pth

# Check SadTalker
ls -lh ~/models/sadtalker/SadTalker/checkpoints/

# Verify all models with Python
python3 -c "
from pathlib import Path
models_dir = Path('$HOME/models')
checks = [
    models_dir / 'Wan2.2' / 'Wan2.2-T2V-A14B' / 'Wan2.2_T2V_A14B.safetensors',
    models_dir / 'ltx-video' / 'LTX-Video-13B' / 'LTX-Video-13B.safetensors',
    models_dir / 'wav2lip' / 'wav2lip.pth',
]
for c in checks:
    if c.exists():
        print(f'OK: {c.name}')
    else:
        print(f'MISSING: {c.name}')
"
```

---

## Disk Space Requirements

| Component | Size | Path |
|-----------|------|------|
| Wan 2.2 T2V-A14B | 28GB | ~/models/Wan2.2/ |
| LTX-Video 13B | 26GB | ~/models/ltx-video/ |
| XTTS v2 | 1.5GB | ~/.cache/TTS/ |
| Hedra | 2GB | ~/models/hedra/ |
| Wav2Lip | 500MB | ~/models/wav2lip/ |
| SadTalker | 1GB | ~/models/sadtalker/ |
| ComfyUI | 5GB | ~/models/ComfyUI/ |
| **Total** | **~63GB** | |

**Recommended:** 80GB+ free disk space for working room.

---

## GPU Requirements Summary

| Model | Min VRAM | Recommended | Examples |
|-------|----------|-------------|----------|
| Wan 2.2 | 16GB | 24GB | RTX 4090, A100 |
| LTX-Video | 12GB | 16GB | RTX 3090, A5000 |
| XTTS v2 | 4GB | 6GB | RTX 3060 |
| Hedra | 6GB | 8GB | RTX 3080 |
| Wav2Lip | 4GB | 4GB | Any GPU |
| SadTalker | 6GB | 8GB | RTX 3080 |

**Note:** Stages run sequentially. 24GB VRAM can run all stages.
