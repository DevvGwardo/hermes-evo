---
name: ascii-video-pipeline
description: Generate generative ASCII art videos — numpy + PIL + ffmpeg pipeline, 6 scene types, Telegram/Discord upload
category: creative
---

# ASCII Video Pipeline

Generate generative ASCII art videos using numpy + PIL + ffmpeg.

## Pipeline

1. **Generate per-scene MP4s** with ffmpeg from numpy frame arrays
2. **Concatenate** with ffmpeg concat demuxer (list file)
3. **Upload** via Telegram MEDIA protocol

## Key Constraints

- ffmpeg concat demuxer uses numeric patterns like `%03d.png` — do NOT use f-string syntax inside ffmpeg commands (e.g., `scene_%s.mp4` where scene name is a string). Use separate output dirs per scene with `-frames:v 144` and numeric output naming.
- Each scene's frames must be numbered starting at 1: `ffmpeg ... frame_%03d.png`
- Concatenate with a list file:
  ```
  file 'scene1/output.mp4'
  file 'scene2/output.mp4'
  ```
- The concat demuxer (not filter) is simpler and more reliable: `ffmpeg -f concat -safe 0 -i list.txt -c copy final.mp4`

## Scene Types (Tested)

| Scene | Effect |
|-------|--------|
| vortex | Rotating concentric rings, particle scatter |
| matrix | Falling character streams with glow heads |
| aurora | Horizontal sine-wave bands, color cycling |
| fire | Rising flames, red→orange→yellow gradient |
| stars | 3D starfield with orbital dots and trails |
| spiral | Double-helix twist, hue-shifting dots |

## Upload

- **Telegram**: Use `MEDIA:/path/to/file.mp4` in response
- **Discord**: Upload to catbox.moe first, return MP4 link

## Dependencies

```bash
brew install ffmpeg
pip install numpy pillow
```
