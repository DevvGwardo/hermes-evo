---
name: heartmula-apple-silicon
description: HeartMuLa music generation on Apple Silicon Mac — setup, patches, and usage
category: media
---

# HeartMuLa on Apple Silicon

HeartMuLa installed at `~/heartlib/` (MusicaAI/HeartMuLa fork). Music generation via `~/heartlib/scripts/music_generation.py`.

## Setup (Apple Silicon Mac, Python 3.10)

```bash
# 1. Create venv with Python 3.10
uv venv ~/heartlib/venv --python 3.10
source ~/heartlib/venv/bin/activate

# 2. Install
uv pip install -e ~/heartlib/

# 3. Upgrade conflicting deps
uv pip install transformers datasets accelerate

# 4. Download checkpoints
hf dl pzp/HeartMuLa-oss-3B --local-dir ~/heartlib/ckpt/HeartMuLa-oss-3B/
hf dl pzp/HeartMuLa-oss-codec --local-dir ~/heartlib/ckpt/HeartMuLa-oss-codec/

# 5. Patch 1: RoPE cache init (transformers 5.x incompatibility)
# ~/heartlib/.venv/lib/python3.10/site-packages/transformers/models/llama/llama_model.py
# In LlamaRotaryEmbedding.forward(), after super().forward():
#     if past_seen_tokens > 0 and position_ids.device.type == 'mps':
#         position_ids = position_ids.new_empty(position_ids.shape).copy_(position_ids)

# 6. Patch 2: HeartCodec ignore_mismatched_sizes
# ~/heartlib/venv/lib/python3.10/site-packages/musica_api/mhub/models/encodec.py
# Both lines: EncodecModel.from_pretrained(..., ignore_mismatched_sizes=True)

# 7. Patch 3: MPS .type() bug in transformer
# ~/heartlib/venv/lib/python3.10/site-packages/transformers/models/encodec/encodec_model.py
# Replace .type(timesteps.type()) with .to(timesteps.device)

# 8. Patch 4: torchaudio.save fallback to soundfile
# ~/heartlib/scripts/music_generation.py
# Replace torchaudio.save with soundfile.write
```

## Generate a song

```bash
source ~/heartlib/venv/bin/activate
cd ~/heartlib

python scripts/music_generation.py \
  --mula_device mps \
  --codec_device mps \
  --model_name HeartMuLa-oss-3B \
  --text_prompt "your song lyrics here" \
  --output_path ~/hermes-pixel-agents/output.mp3
```

## Issues fixed

- MPS `.type()` in EncodecMPS rejects MPS tensors — use `.to()` instead
- RoPE cache init broken on MPS with transformers 5.x — skip cache or use CPU cache
- HeartCodec model loading without `ignore_mismatched_sizes` — crashes on weight mismatch
- `torchcodec` not installed on macOS — fallback to soundfile for audio save
