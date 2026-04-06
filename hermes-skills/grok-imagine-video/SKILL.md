---
name: hermes-grok-imagine-video
description: Hermes agent skill for xAI Grok Imagine API — generate, edit, and animate images and videos via natural language. Use when the user wants to create images, videos, or animations using xAI's Grok Imagine API.
version: 1.0.0
tags: [video, image, generation, xai, grok, hermes, text-to-video, image-to-video, editing]
required_env: [XAI_API_KEY]
commands: [python3]
metadata:
  hermes:
    platform: hermes-agent
    triggers:
      - "generate an image"
      - "create a video"
      - "generate a video"
      - "animate this image"
      - "edit this video"
      - "make a video of"
      - "grok imagine"
      - "xai image"
      - "xai video"
---

# Grok Imagine Video — Hermes Agent Skill

Generate images and videos using xAI's Grok Imagine API directly from the Hermes agent chat interface.

## When to Use

- User wants to generate an image from a text description
- User wants to create a video from text or an image
- User wants to animate a static image into video
- User wants to edit an existing image or video with natural language
- Keywords: imagine, generate, create video, create image, xai, grok

## Setup

**Required:** `XAI_API_KEY` from https://console.x.ai/

The skill reads the key from the `XAI_API_KEY` environment variable automatically. If not set, the agent requests it from the user before proceeding.

**Runtime:** Python 3 with the `requests` library.

## Capabilities

| Feature | Description | Latency |
|---------|-------------|---------|
| Text-to-image | Generate images from text (up to 10 variations) | Instant |
| Image editing | Edit images via natural language | Instant |
| Text-to-video | Create videos from text descriptions | ~2-3 min |
| Image-to-video | Animate a static image into video | ~2-3 min |
| Video editing | Apply filters, speed, color grading via natural language | ~2-3 min |
| Long video | Frame-chained segments via generate_movie() | Scales with length |

## Workflows

### Image Generation (instant)

**User says:** "Create an image of a cyberpunk cityscape at night"

```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))
result = client.generate_image(
    prompt="A cyberpunk cityscape at night, neon lights reflecting on wet streets",
    n=1,
    aspect_ratio="16:9",
    response_format="url"
)
print(result.get("data", [{}])[0].get("url", ""))
EOF
```

Images generate instantly. Return the URL directly to the user.

### Image Editing (instant)

**User says:** "Edit this image — make it look like a watercolor painting"

```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))
result = client.edit_image(
    image_url="https://example.com/photo.jpg",
    prompt="Make it look like a watercolor painting"
)
print(result.get("data", [{}])[0].get("url", ""))
EOF
```

### Text-to-Video (~2-3 min, async)

**User says:** "Generate a video of a sunset over the ocean"

Step 1 — Start generation:
```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))
result = client.text_to_video(
    prompt="A beautiful sunset over the ocean, golden hour lighting",
    duration=10,
    aspect_ratio="16:9",
    resolution="720p"
)
print(result.get("request_id", ""))
EOF
```

Step 2 — Poll for completion:
```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))

def progress(response):
    done = "video" in response
    print(f"Polling... {'Done!' if done else 'Pending'}")

final = client.wait_for_completion(
    "REQUEST_ID_HERE",
    poll_interval=10,
    timeout=600,
    progress_callback=progress
)
print(final.get("video", {}).get("url", ""))
EOF
```

Step 3 — Download and deliver:
```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))
output = "/tmp/video_output.mp4"
client.download_video({"video": {"url": "VIDEO_URL_HERE"}}, output)
print(output)
EOF
```

Send the file to the user with `MEDIA:/tmp/video_output.mp4`.

### Image-to-Video

**User says:** "Animate this image — make the clouds move slowly"

```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))
result = client.image_to_video(
    image_url="https://example.com/landscape.jpg",
    prompt="Make the clouds drift slowly across the sky",
    duration=10
)
print(result.get("request_id", ""))
EOF
```

Then poll with `wait_for_completion()` and download as above.

### Video Editing

**User says:** "Edit this video — add a warm sunset filter and slow it to 50% speed"

```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))
result = client.edit_video(
    video_url="https://example.com/clip.mp4",
    edit_prompt="Add a warm sunset filter and slow down to 50% speed"
)
print(result.get("request_id", ""))
EOF
```

Then poll and download.

### Long Video — generate_movie() (recommended)

For videos longer than 15 seconds, use `generate_movie()`. It takes a list of **scenes**, each with its own prompt. The last frame of each scene chains into the next automatically — giving you a narrative movie with smooth visual continuity.

```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))

def progress(scene_idx, total, status):
    print(f"[Scene {scene_idx+1}] {status}")

movie = client.generate_movie(
    scenes=[
        {
            "prompt": "A superhero stands tall in a dark city, cape billowing dramatically in the wind. Dramatic lighting, epic scale.",
            "duration": 15,
            "image_url": "https://example.com/hero.jpg"
        },
        {
            "prompt": "The hero launches into the sky, lightning crackling around them. Clouds rush past as the city shrinks below.",
            "duration": 15
        },
        {
            "prompt": "Flying over a stormy ocean at sunset, golden light reflecting off massive waves. Epic aerial cinematography.",
            "duration": 15
        },
        {
            "prompt": "Descending toward a mountain peak, landing gracefully as the last light of day fades into a starry night.",
            "duration": 15
        },
    ],
    resolution="720p",
    output_dir="/tmp",
    progress_callback=progress
)
print(movie)
EOF
```

Send the final file with `MEDIA:/tmp/movie.mp4`.

### Long Video — generate_long_video() (single prompt)

If you just want one continuous shot with the same motion throughout, use `generate_long_video()` with a single prompt. Frame-chaining is still applied automatically:

```
segments = client.generate_long_video(
    prompt="A slow zoom out from a superhero standing in a city, cape billowing in the wind",
    total_duration=60,
    segment_duration=10,       # 10s recommended for smooth chaining
    resolution="720p",
    output_dir="/tmp",
    image_url="https://example.com/hero.jpg"
)
client.concatenate_segments(segments, "/tmp/long_video.mp4")
```

## Parameters Reference

### Image Generation

| Param | Default | Notes |
|-------|---------|-------|
| `prompt` | required | Be descriptive |
| `n` | 1 | 1-10 variations |
| `aspect_ratio` | 1:1 | 16:9, 9:16, 4:3, 3:4, 3:2, 2:3 |
| `response_format` | url | or b64_json |

### Video Generation (text-to-video, image-to-video)

| Param | Default | Notes |
|-------|---------|-------|
| `prompt` | required | Specific, include camera direction |
| `duration` | 10 | 1-15 seconds |
| `aspect_ratio` | 16:9 | same options as image |
| `resolution` | 480p | 480p (faster) or 720p (quality) |

### Long Video

| Param | Default | Notes |
|-------|---------|-------|
| `total_duration` | required | Any length |
| `segment_duration` | 15 | Max 15s per API call |
| `resolution` | 480p | 480p or 720p |

## Error Handling

| Error | Response |
|-------|----------|
| `401 Unauthorized` | API key missing or invalid — request key from user |
| `429 Rate limit` | Wait and retry with exponential backoff |
| `400 Content policy` | Rephrase prompt to comply with content guidelines |
| `TimeoutError` | Reduce duration or complexity |
| `FileNotFoundError` | Install ffmpeg (`brew install ffmpeg` on macOS) |

## Video-to-Video Chaining (extend_video)

New: The API supports true video-to-video continuation via `extend_video()`:

```
r = client.extend_video(
    video_url="https://example.com/segment_0.mp4",   # previous segment URL
    prompt="The hero launches into the sky, lightning crackling around them",
    duration=10
)
```

This uses `POST /v1/videos/extensions` — the API generates content that continues **directly from the end of the input video**, giving far better temporal continuity than frame-extraction chaining.

## generate_movie() — Scene-Based Narrative

Uses video-to-video chaining for intra-scene continuity, and `reference_images` for character consistency:

```
segments = client.generate_movie(
    scenes=[
        {
            "prompt": "A superhero stands on a rooftop, cape billowing in the wind",
            "duration": 20,
            "image_url": "https://example.com/hero.jpg"
        },
        {
            "prompt": "The hero launches into the sky, lightning crackling around them",
            "duration": 20
        },
        {
            "prompt": "Landing gracefully on a mountain peak at sunset",
            "duration": 20
        },
    ],
    resolution="720p",
    output_dir="/tmp/movie_build"
)
# segments = list of local segment file paths

# Then finalize with transitions and music:
final = client.finalize_movie(
    segments,
    "/tmp/final_movie.mp4",
    transition_duration=1.5,
    music_track="/tmp/epic_score.mp3",
    video_fade_out=2.0
)
```

**How chaining works:**
- First segment: `image_to_video()` with `reference_images` (all scene images) for character consistency
- Subsequent segments within same scene: `extend_video()` using previous segment's URL — true video-to-video
- First segment of a new scene: `image_to_video()` with `reference_images` (resets character appearance)

## Finalizing a Movie

After generating segments with `generate_movie()`, use `finalize_movie()` to apply cinematic post-processing:

```
python3 - << 'EOF'
import os, sys
sys.path.insert(0, 'scripts')
from grok_video_api import GrokImagineVideoClient

client = GrokImagineVideoClient(os.getenv("XAI_API_KEY"))

# Step 1: Generate the raw chained segments
segments = client.generate_movie(
    scenes=[
        {
            "prompt": "A superhero stands heroically on a dark city rooftop, cape billowing in the wind. City lights glow below.",
            "duration": 20,
            "image_url": "https://example.com/hero.jpg"
        },
        {
            "prompt": "High above the clouds, cape streaming behind. Lightning crackles around the hero as clouds rush past.",
            "duration": 20
        },
        {
            "prompt": "Landing gracefully on a mountain peak at golden hour. The hero turns to the camera and says 'I'm here to save the day'.",
            "duration": 20
        },
    ],
    output_dir="/tmp/movie_build",
    resolution="720p"
)
# segments is a list of segment file paths — pass it directly to finalize_movie()

# Step 2: Apply cinematic transitions and effects
final = client.finalize_movie(
    segment_paths=segments,         # returned from generate_movie()
    output_path="/tmp/cinematic.mp4",
    transition_duration=1.5,         # 1.5s cross-dissolve between segments
    video_fade_out=2.0,            # 2s fade-to-black at the end
    output_dir="/tmp/movie_build"
)
print(final)
EOF
```

### Transition Parameters

| Param | Default | Notes |
|-------|---------|-------|
| `transition_duration` | 1.0 | Seconds of cross-dissolve between segments. Set 0 to disable. |
| `video_fade_out` | 2.0 | Fade-to-black at the very end. Set 0 to disable. |
| `music_track` | — | Path to background music file (mp3/m4a/aac). |
| `music_crossfade` | 2.0 | Music crossfade duration at each scene boundary. |
| `audio_tracks` | — | Per-scene ambient audio files (city sounds, wind, etc.). |

## Best Practices
### Prompt Writing

- **Be descriptive** — specify subject, setting, lighting, mood, and camera direction
- **Include camera motion** — "slow zoom out", "tracking shot left", "drone shot over"
- **State the starting condition explicitly** — each scene prompt should describe *what the frame looks like* at the start, not just what happens next
- **Avoid "continuation" language** — write "The hero is now high above the clouds" not "The hero continues flying upward"
- **Overlap scene transitions** — last 2-3 seconds of scene N's prompt should describe what flows into scene N+1's first seconds

### Long Video / Movie Production

- **Use `generate_movie()` for multi-scene videos** — each scene gets its own prompt while maintaining frame-chain continuity
- **10s segments, not 15s** — shorter segments keep each clip tight and reduce AI drift from the source frame
- **Chain length limit: ~60-90s max** — beyond this, accumulated degradation becomes noticeable; reset with the original image every 3-4 scenes if longer
- **Overlap prompts at scene boundaries** — make the end of one scene's description match the beginning of the next scene's description
- **Use camera motion to hide seams** — slow pans, zooms, and rotations at scene boundaries make imperfect frame continuity less noticeable than hard cuts
- **Upload frames to CDN instead of base64** — for production, extract and host chain frames externally to reduce quality loss through the encoding cycle
- **Each scene prompt describes the frame the viewer sees** — not what just happened, but what they see at the start of the scene

### Frame-Chain Continuity

The AI regenerates each segment from scratch using the chained frame as input. It receives the *content* (colors, costume, setting) but cannot guarantee temporal coherence — a character facing left at the end of scene 1 might face right at the start of scene 2. Frame chaining gives you visual consistency, not true video-to-video continuity.

Techniques to work with this:
- Describe the chained frame's composition in the next scene's prompt so the AI interprets it correctly
- Use wide shots or environmental shots rather than tight close-ups at scene boundaries (less sensitive to subtle continuity errors)
- Add subtle camera motion to mask micro-drift between segments

### General

- **Images generate instantly** — deliver URLs immediately without polling
- **Videos take 2-3 minutes per segment** — send progress updates while polling
- **Use 480p for fast iteration** — switch to 720p for final output
- **Download promptly** — image/video URLs are temporary and expire quickly
- **Deliver via MEDIA:** — use `MEDIA:/path/to/file` to send files natively in chat

## File Structure

```
hermes-grok-imagine-video/
SKILL.md                              ← This file
scripts/grok_video_api.py             ← API client
references/api_reference.md            ← Full API documentation
README.md
LICENSE
```
