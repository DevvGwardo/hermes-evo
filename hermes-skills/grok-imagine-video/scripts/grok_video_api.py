#!/usr/bin/env python3
"""
xAI Grok Imagine Video API Client
Handles text-to-video, image-to-video, and video editing via natural language.
"""

import requests
import time
import json
import os
from typing import Optional, Dict, Any, List


class GrokImagineVideoClient:
    """Client for interacting with xAI Grok Imagine Video API."""

    def __init__(self, api_key: str, base_url: str = "https://api.x.ai/v1"):
        """
        Initialize the client.

        Args:
            api_key: xAI API key from environment or config
            base_url: API base URL (default: https://api.x.ai/v1)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def text_to_video(
        self,
        prompt: str,
        duration: int = 10,
        aspect_ratio: str = "16:9",
        resolution: str = "480p"
    ) -> Dict[str, Any]:
        """
        Generate video from text prompt.

        Args:
            prompt: Text description of the video to generate
            duration: Video duration in seconds (1-15)
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1, 4:3, 3:4, 3:2, 2:3)
            resolution: Resolution (480p, 720p)

        Returns:
            API response with request_id
        """
        url = f"{self.base_url}/videos/generations"
        payload = {
            "model": "grok-imagine-video",
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def _resolve_image_url(self, image_url: str) -> str:
        """
        Resolve an image URL for API calls.

        - HTTPS URLs: passed through unchanged
        - base64 data URLs: passed through unchanged
        - Local file paths (starting with / or ~): converted to base64 data URL

        The xAI API only accepts HTTPS URLs or base64 data URLs — file://
        URLs and local paths must be converted before sending.
        """
        import base64, os

        if image_url.startswith(("http://", "https://", "data:")):
            return image_url

        # Local file — convert to base64 data URL
        path = os.path.expanduser(image_url)
        if not os.path.isabs(path):
            raise ValueError(f"Invalid image path: {image_url}")

        with open(path, "rb") as f:
            data = f.read()

        # Detect MIME type from magic bytes
        if data.startswith(b"\xff\xd8"):
            mime = "image/jpeg"
        elif data.startswith(b"\x89PNG"):
            mime = "image/png"
        elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            mime = "application/octet-stream"

        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    def _resolve_video_url(self, video_url: str) -> str:
        """
        Resolve a video URL for API calls.

        - HTTPS URLs: passed through unchanged
        - base64 data URLs: passed through unchanged
        - Local file paths: converted to base64 data URL

        The xAI video API only accepts HTTPS URLs or base64 data URLs.
        Local .mp4 files are auto-converted.
        """
        import base64, os

        if video_url.startswith(("http://", "https://", "data:")):
            return video_url

        path = os.path.expanduser(video_url)
        if not os.path.isabs(path):
            raise ValueError(f"Invalid video path: {video_url}")

        with open(path, "rb") as f:
            data = f.read()

        # Videos must be .mp4 with supported codecs
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:video/mp4;base64,{b64}"

    def image_to_video(
        self,
        image_url: str,
        prompt: str = "",
        duration: int = 10,
        reference_images: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Animate a static image into video.

        Args:
            image_url: Public HTTPS URL, base64 data URL, or local file path.
                Local paths are automatically converted to base64 data URLs
                since the API does not accept file:// URLs.
            prompt: Optional text prompt to guide animation.
            duration: Video duration in seconds (1-15).
            reference_images: Optional list of image URLs for reference-to-video
                (R2V) mode. When provided, these become the source images
                (image_url is ignored by the API). Same URL restrictions as
                image_url apply — use HTTPS or local paths (auto-converted).

        Returns:
            API response with request_id
        """
        url = f"{self.base_url}/videos/generations"

        if reference_images:
            # R2V mode — reference_images as source
            payload = {
                "model": "grok-imagine-video",
                "prompt": prompt,
                "reference_images": [{"url": self._resolve_image_url(img)} for img in reference_images],
                "duration": duration
            }
        else:
            # Standard I2V mode
            payload = {
                "model": "grok-imagine-video",
                "prompt": prompt,
                "image": {"url": self._resolve_image_url(image_url)},
                "duration": duration
            }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def extend_video(
        self,
        video_url: str,
        prompt: str,
        duration: int = 6
    ) -> Dict[str, Any]:
        """
        Extend an existing video by continuing the narrative from its end.

        Uses the /v1/videos/extensions endpoint. The API generates new content
        that continues directly from where the input video ends — true
        video-to-video chaining with temporal continuity. Much more reliable
        than frame-extraction chaining for maintaining visual coherence.

        Args:
            video_url: Public URL of the video to extend. The input video
                must be between 2 and 30 seconds long.
            prompt: Description of what happens next in the video. The prompt
                should describe the action starting from where the input video ends.
            duration: Duration of the extension segment in seconds (1-10).
                Default: 6.

        Returns:
            API response with request_id
        """
        url = f"{self.base_url}/videos/extensions"
        payload = {
            "model": "grok-imagine-video",
            "prompt": prompt,
            "video": {"url": self._resolve_video_url(video_url)},
            "duration": duration
        }
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def edit_video(
        self,
        video_url: str,
        edit_prompt: str
    ) -> Dict[str, Any]:
        """
        Edit an existing video via natural language instruction.

        Args:
            video_url: Public URL of the source video
            edit_prompt: Natural language instruction for the edit

        Returns:
            API response with request_id
        """
        url = f"{self.base_url}/videos/generations"
        payload = {
            "model": "grok-imagine-video",
            "prompt": edit_prompt,
            "video": {"url": self._resolve_video_url(video_url)}
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def generate_image(
        self,
        prompt: str,
        n: int = 1,
        aspect_ratio: str = "1:1",
        response_format: str = "url"
    ) -> Dict[str, Any]:
        """
        Generate images from a text prompt.

        Args:
            prompt: Text description of the image to generate
            n: Number of image variations (1-10)
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, etc.)
            response_format: "url" for temporary URL or "b64_json" for base64 data

        Returns:
            API response with image URL(s) or base64 data
        """
        url = f"{self.base_url}/images/generations"
        payload = {
            "model": "grok-imagine-image",
            "prompt": prompt,
            "n": n,
            "aspect_ratio": aspect_ratio,
            "response_format": response_format
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def edit_image(
        self,
        image_url: str,
        prompt: str,
        n: int = 1,
        response_format: str = "url"
    ) -> Dict[str, Any]:
        """
        Edit an existing image via natural language instruction.

        Args:
            image_url: Public URL or base64 data URI of the source image
            prompt: Natural language instruction for the edit
            n: Number of variations (1-10)
            response_format: "url" for temporary URL or "b64_json" for base64 data

        Returns:
            API response with edited image URL(s) or base64 data
        """
        url = f"{self.base_url}/images/edits"
        payload = {
            "model": "grok-imagine-image",
            "prompt": prompt,
            "image": {"url": image_url, "type": "image_url"},
            "n": n,
            "response_format": response_format
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def download_image(self, image_url: str, output_path: str) -> str:
        """
        Download a generated image file.

        Args:
            image_url: URL of the generated image
            output_path: Local path to save the image

        Returns:
            Path to the downloaded file
        """
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    def get_job_status(self, request_id: str) -> Dict[str, Any]:
        """
        Check the status of a video generation request.

        Args:
            request_id: The request ID from the initial generation request

        Returns:
            Job status with fields: status (if pending), video (if done)
        """
        url = f"{self.base_url}/videos/{request_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        request_id: str,
        poll_interval: int = 10,
        timeout: int = 600,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Poll job status until completion or timeout.

        Args:
            request_id: The request ID to poll
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            progress_callback: Optional function called with progress updates

        Returns:
            Final response with video_url if successful

        Raises:
            TimeoutError: If job doesn't complete within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = self.get_job_status(request_id)

            if progress_callback:
                progress_callback(response)

            # Check if job failed
            status = response.get("status", "")
            if status == "failed":
                error = response.get("error", "unknown")
                raise RuntimeError(f"Job {request_id} failed: {error}")

            # Check if video is done (response has video object)
            if "video" in response and response.get("video", {}).get("url"):
                return response

            # If not done, wait and retry
            time.sleep(poll_interval)

        raise TimeoutError(f"Request {request_id} timed out after {timeout} seconds")

    def download_video(self, response_data: Dict[str, Any], output_path: str) -> str:
        """
        Download a completed video file.

        Args:
            response_data: Response from get_job_status (contains video.url)
            output_path: Local path to save the video

        Returns:
            Path to the downloaded file
        """
        video_url = response_data.get("video", {}).get("url")
        if not video_url:
            raise ValueError("No video URL in response")

        response = requests.get(video_url, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    # ─── Long Video ────────────────────────────────────────────────────────

    def _require_ffmpeg(self):
        """Raise a clear error if ffmpeg is not installed."""
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        except (subprocess.NotFoundError, FileNotFoundError):
            raise RuntimeError(
                "ffmpeg is required but not installed. "
                "Install it with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
            )
        except subprocess.TimeoutExpired:
            pass  # version check timed out, ffmpeg likely exists

    def _extract_last_frame(self, video_path: str, output_path: str) -> str:
        """
        Extract the last frame of a video as a JPEG image.
        Uses ffmpeg. Requires ffmpeg to be installed.
        """
        import subprocess
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-sseof", "-1",
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "2",
                output_path
            ],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to extract last frame: {result.stderr}")
        return output_path

    def generate_long_video(
        self,
        prompt: str,
        total_duration: int,
        aspect_ratio: str = "16:9",
        resolution: str = "480p",
        output_dir: str = "/tmp",
        segment_duration: int = 15,
        poll_interval: int = 10,
        timeout: int = 600,
        progress_callback: Optional[Any] = None,
        image_url: str = "",
        scenes: Optional[list] = None
    ) -> list:
        """
        Generate a video longer than 15 seconds via sequential frame-chaining.

        Each segment is generated one at a time. After a segment completes,
        its last frame is extracted and used as the input image for the next
        segment — creating smooth continuous motion instead of jump cuts.

        **Multi-scene mode:** Pass a list of scene dicts via the `scenes`
        parameter. Each scene has its own prompt (and optional image_url).
        This lets you craft a narrative movie where each scene has distinct
        action while maintaining visual continuity through frame-chaining.

        Args:
            prompt: Default prompt used for all segments if `scenes` is not set.
            total_duration: Total desired duration in seconds (unlimited).
            aspect_ratio: Aspect ratio. Default: 16:9.
            resolution: "480p" or "720p". Default: 480p.
            output_dir: Directory to save downloaded segment files.
            segment_duration: Maximum seconds per API call (1-15). Default: 15.
            poll_interval: Seconds between status checks. Default: 10.
            timeout: Maximum seconds to wait for all segments. Default: 600.
            progress_callback: Optional callable (segment_index, total, status).
            image_url: Optional starting image URL for the first segment.
            scenes: Optional list of scene dicts for multi-prompt movie mode.
                Each dict: {"prompt": "...", "duration": 10, "image_url": "..."}
                The last frame of each scene chains into the next automatically.

        Returns:
            Ordered list of local file paths for each segment.
        """
        self._require_ffmpeg()
        import math

        if not 1 <= segment_duration <= 15:
            raise ValueError("segment_duration must be between 1 and 15")

        n_segments = math.ceil(total_duration / segment_duration)
        durations = []
        remaining = total_duration
        for _ in range(n_segments):
            seg = min(segment_duration, remaining)
            durations.append(seg)
            remaining -= seg

        # ── Build per-segment prompt/image plan ───────────────────────────
        if scenes:
            # Flatten scenes into per-segment instructions
            segment_plan = []
            for scene in scenes:
                scene_dur = scene.get("duration", segment_duration)
                scene_n = math.ceil(scene_dur / segment_duration)
                for _ in range(scene_n):
                    segment_plan.append({
                        "prompt": scene.get("prompt", prompt),
                        "image_url": scene.get("image_url", ""),
                    })
        else:
            # Single-prompt chaining mode
            segment_plan = [
                {"prompt": prompt, "image_url": image_url if i == 0 else ""}
                for i in range(n_segments)
            ]

        import os as _os
        _os.makedirs(output_dir, exist_ok=True)

        current_image = image_url
        segment_paths = []
        start_time = time.time()
        total_segments = len(segment_plan)

        for i, plan in enumerate(segment_plan):
            dur = min(durations[i] if i < len(durations) else segment_duration, segment_duration)
            remaining_timeout = max(timeout - (time.time() - start_time), 60)

            seg_prompt = plan["prompt"]
            seg_image = plan["image_url"] if plan.get("image_url") else current_image

            if seg_image:
                result = self.image_to_video(
                    image_url=seg_image,
                    prompt=seg_prompt,
                    duration=dur
                )
            else:
                result = self.text_to_video(
                    prompt=seg_prompt,
                    duration=dur,
                    aspect_ratio=aspect_ratio,
                    resolution=resolution
                )

            request_id = result["request_id"]
            if progress_callback:
                progress_callback(i, total_segments, f"chaining")

            response = self.wait_for_completion(
                request_id,
                poll_interval=poll_interval,
                timeout=remaining_timeout
            )

            seg_path = _os.path.join(output_dir, f"segment_{i:04d}.mp4")
            self.download_video(response, seg_path)
            segment_paths.append(seg_path)

            if progress_callback:
                progress_callback(i, total_segments, "done")

            frame_path = _os.path.join(output_dir, f"chain_frame_{i:04d}.jpg")
            self._extract_last_frame(seg_path, frame_path)
            current_image = f"data:image/jpeg;base64,{self._image_to_base64(frame_path)}"

            if time.time() - start_time >= timeout:
                raise TimeoutError(f"Timeout reached at segment {i+1}/{total_segments}")

        return segment_paths

    def generate_movie(
        self,
        scenes: list,
        output_dir: str = "/tmp",
        resolution: str = "720p",
        poll_interval: int = 10,
        timeout: int = 1800,
        progress_callback: Optional[Any] = None
    ) -> str:
        """
        Generate a narrative movie from a list of scenes, each with its own prompt.
        Segments are frame-chained between scenes for smooth visual continuity.

        Each scene's last frame automatically becomes the first frame of the next
        scene's video, creating seamless motion across scene transitions.

        Args:
            scenes: List of scene dicts. Each dict:
                {
                    "prompt": "Description of what happens in this scene",
                    "duration": 10,          # How long this scene lasts (seconds)
                    "image_url": "..."      # Optional starting image for scene 1
                }
                Duration is split into 10s segments internally. Each segment
                chains from the last frame of the previous segment.
            output_dir: Directory for temp files. Default: /tmp.
            resolution: "480p" or "720p". Default: 720p.
            poll_interval: Seconds between status polls. Default: 10.
            timeout: Max seconds total. Default: 1800 (30 min).
            progress_callback: Optional callable (scene_index, total, status).

        Returns:
            Path to the final concatenated movie file.

        Example:
            client.generate_movie([
                {"prompt": "A superhero stands tall in a dark city, cape billowing",
                 "duration": 15, "image_url": "https://example.com/hero.jpg"},
                {"prompt": "The hero launches into the sky, lightning crackling around them",
                 "duration": 15},
                {"prompt": "Flying over a stormy ocean as the sun sets dramatically",
                 "duration": 15},
                {"prompt": "Landing gracefully on a rooftop as the city lights flicker on",
                 "duration": 15},
            ])
        """
        self._require_ffmpeg()
        import os as _os, math

        total_duration = sum(s.get("duration", 10) for s in scenes)

        def _scene_progress(scene_idx, total, status):
            if progress_callback:
                progress_callback(scene_idx, total, status)

        _os.makedirs(output_dir, exist_ok=True)

        # ── Build segment plan ───────────────────────────────────────────
        # Each scene is split into 10s segments.
        # Segment 0 of scene 0: image_to_video() with reference_images
        # All other segments: extend_video() — feeds previous video directly
        # This gives true video-to-video continuity vs frame-to-video chaining
        segment_plan = []
        for scene_idx, scene in enumerate(scenes):
            dur = scene.get("duration", 10)
            n_segs = math.ceil(dur / 10)
            for seg_i in range(n_segs):
                segment_plan.append({
                    "scene_idx": scene_idx,
                    "prompt": scene.get("prompt", ""),
                    "image_url": scene.get("image_url", ""),  # original scene image
                    "is_first_of_scene": seg_i == 0,
                    "is_first_overall": scene_idx == 0 and seg_i == 0,
                })

        total_segments = len(segment_plan)

        segment_paths = []
        segment_urls = []  # remote URLs for extend chaining
        start_time = time.time()

        for i, plan in enumerate(segment_plan):
            remaining_timeout = max(timeout - (time.time() - start_time), 60)

            if plan["is_first_overall"]:
                # Very first segment: image_to_video with scene image as source.
                result = self.image_to_video(
                    image_url=plan["image_url"],
                    prompt=plan["prompt"],
                    duration=10
                )
            elif plan["is_first_of_scene"]:
                # First segment of a new scene: start from the scene's original
                # image (different narrative moment — no chaining from prior scene)
                result = self.image_to_video(
                    image_url=plan["image_url"],
                    prompt=plan["prompt"],
                    duration=10
                )
            else:
                # Continuation of current scene: use extend_video to chain from
                # the previous segment's video URL for true temporal continuity
                prev_url = segment_urls[-1]
                result = self.extend_video(
                    video_url=prev_url,
                    prompt=plan["prompt"],
                    duration=10
                )

            request_id = result["request_id"]
            _scene_progress(plan["scene_idx"], total_segments, f"seg {i+1}/{total_segments}")

            response = self.wait_for_completion(
                request_id,
                poll_interval=poll_interval,
                timeout=remaining_timeout
            )

            seg_path = _os.path.join(output_dir, f"segment_{i:04d}.mp4")
            self.download_video(response, seg_path)
            segment_paths.append(seg_path)

            # Save remote URL for extend chaining
            remote_url = response.get("video", {}).get("url", "")
            if remote_url:
                segment_urls.append(remote_url)

            _scene_progress(plan["scene_idx"], total_segments, "done")

            if time.time() - start_time >= timeout:
                raise TimeoutError(f"Timeout at segment {i+1}/{total_segments}")

        return segment_paths

    # ─── Movie Finalization ───────────────────────────────────────────────

    def _get_video_duration(self, video_path: str) -> float:
        """Get duration of a video file in seconds."""
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             video_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())

    def _apply_crossfade_transition(
        self,
        clip_a_path: str,
        clip_b_path: str,
        output_path: str,
        fade_duration: float = 1.0
    ) -> str:
        """
        Join clip_a and clip_b with a cross-dissolve transition at the boundary.

        Audio is stripped from both clips — music/audio is applied separately
        by finalize_movie() after all transitions are applied. This allows a
        single music track to play across the entire movie without each segment's
        embedded audio bleeding through.

        Args:
            clip_a_path: Path to the first (earlier) video clip.
            clip_b_path: Path to the second (later) video clip.
            output_path: Path for the merged output file.
            fade_duration: Duration of the crossfade in seconds.

        Returns:
            Path to the merged output file.
        """
        import subprocess, os as _os

        dur_a = self._get_video_duration(clip_a_path)
        dur_b = self._get_video_duration(clip_b_path)

        # Trim A: keep everything except the last fade_duration seconds
        trim_a = max(dur_a - fade_duration, 0)
        tmp_a = clip_a_path + ".tmpfa.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-i", clip_a_path,
            "-t", str(trim_a),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an"
        ], capture_output=True)

        # Concatenate trimmed A + B, then apply xfade at the boundary
        # xfade offset = where to start the crossfade on clip_a's timeline
        # dur_a is the original clip duration (before trimming)
        # so the fade starts at dur_a - fade_duration and lasts fade_duration
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", tmp_a,
            "-i", clip_b_path,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=fade:duration={fade_duration}"
            f":offset={dur_a - fade_duration}[outv]",
            "-map", "[outv]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-t", str(trim_a + fade_duration),
            output_path
        ], capture_output=True, text=True)

        _os.remove(tmp_a)

        if result.returncode != 0:
            raise RuntimeError(f"Crossfade failed: {result.stderr}")
        return output_path

    def finalize_movie(
        self,
        segment_paths: list,
        output_path: str,
        transition_duration: float = 1.0,
        music_track: Optional[str] = "",
        music_crossfade: float = 2.0,
        video_fade_out: float = 2.0,
        output_dir: str = "/tmp"
    ) -> str:
        """
        Apply cinematic post-processing to a list of video segments.

        Workflow:
        1. Apply cross-dissolve transitions between all consecutive segments
           (audio is stripped from intermediate clips — each AI segment carries
           its own music that would clash across transitions)
        2. If music_track provided: mix it across the full movie with crossfades
           at each scene boundary (2s fade out/in)
        3. Fade to black at the end

        The key design decision: intermediate segment audio is discarded. Each
        AI-generated clip has its own background music which would otherwise
        cut abruptly at scene transitions. Provide a single music_track for
        a cohesive movie soundtrack.

        Args:
            segment_paths: Ordered list of video segment file paths.
            output_path: Final output file path.
            transition_duration: Crossfade dissolve duration in seconds between
                segments. Default: 1.0. Set to 0 to disable transitions.
            music_track: Optional path to a background music file (mp3/m4a/aac).
                If provided, it plays through the entire movie with 2-second
                fades at each scene boundary. If not provided, the final
                movie has no audio (silence).
            music_crossfade: Duration of music fade at each scene boundary.
                Default: 2.0 seconds.
            video_fade_out: Duration of fade-to-black at the end. Default: 2.0.
            output_dir: Working directory for intermediate files.

        Returns:
            Path to the finalized movie file.

        Example:
            client.finalize_movie(
                segment_paths,           # returned from generate_movie()
                "/tmp/final_movie.mp4",
                transition_duration=1.5,
                music_track="/tmp/epic_score.mp3",
                music_crossfade=2.0,
                video_fade_out=2.0,
                output_dir="/tmp"
            )
        """
        self._require_ffmpeg()
        import subprocess, os as _os, math

        if len(segment_paths) == 0:
            raise ValueError("No segment paths provided")

        _os.makedirs(output_dir, exist_ok=True)
        seg_dir = output_dir

        # ── 1. Blend segments (video-only, strip segment audio) ──────────
        raw_durs = [self._get_video_duration(p) for p in segment_paths]

        if transition_duration > 0 and len(segment_paths) > 1:
            # Sequential blending: A+B -> result, then result+C -> ...
            current_video = segment_paths[0]
            current_dur = raw_durs[0]

            for i in range(len(segment_paths) - 1):
                clip_a = current_video
                clip_b = segment_paths[i + 1]
                dur_a = current_dur
                dur_b = raw_durs[i + 1]
                t_cross = dur_a - transition_duration
                out_path = _os.path.join(seg_dir, f"blend_{i:04d}.mp4")

                # Blend video with xfade, strip all audio
                r = subprocess.run([
                    "ffmpeg", "-y",
                    "-i", clip_a, "-i", clip_b,
                    "-filter_complex",
                    f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}"
                    f":offset={t_cross}[vt]",
                    "-map", "[vt]",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-an",  # strip all audio
                    "-t", str(dur_a + dur_b - transition_duration),
                    out_path
                ], capture_output=True, text=True)

                if r.returncode != 0:
                    raise RuntimeError(f"Blend step {i} failed: {r.stderr[-300:]}")
                current_video = out_path
                current_dur = dur_a + dur_b - transition_duration

            blended_video = current_video
            blended_dur = current_dur
        else:
            # No transitions — concatenate video-only
            blended_video = _os.path.join(seg_dir, "concat_no_transition.mp4")
            concat_list = _os.path.join(seg_dir, "concat.txt")
            with open(concat_list, "w") as f:
                for p in segment_paths:
                    f.write(f"file '{_os.path.abspath(p)}'\n")
            r = subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-an",
                blended_video
            ], capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"Concat failed: {r.stderr[-300:]}")
            blended_dur = self._get_video_duration(blended_video)

        # ── 2. Add music with crossfades at scene boundaries ───────────
        if music_track and _os.path.exists(music_track):
            music_out = _os.path.join(seg_dir, "movie_with_music.mp4")

            # Build a filtergraph that:
            # - Loops the music to cover the full movie duration
            # - Crossfades the music at each scene boundary
            # - Mixes music over silent video

            # Number of scene boundaries = len(segment_paths) - 1
            n_transitions = len(segment_paths) - 1

            if n_transitions > 0:
                # Build afade sections for each transition
                # Music fades out then in at each boundary
                # First segment plays with music fading out at transition
                # Subsequent segments play with music fading back in
                fade_filter = "[m]"

                t = 0.0
                for i in range(n_transitions):
                    seg_dur = raw_durs[i]
                    fade_out_start = t + seg_dur - music_crossfade
                    fade_in_start = t + seg_dur
                    fade_filter += f"afade=t=out:st={fade_out_start:.3f}:d={music_crossfade}"
                    fade_filter += f";[m]afade=t=in:st={fade_in_start:.3f}:d={music_crossfade}[m]"
                    t += seg_dur - music_crossfade  # overlap at transition

                # Loop music to match video duration
                music_filter = (
                    f"[m]aloop=loop=-1:size=2e9,atrim=0:{blended_dur:.3f},"
                    f"asetpts=PTS-STARTPTS,{fade_filter},volume=2[mout]"
                )
            else:
                # No transitions — just loop and trim music
                music_filter = (
                    f"[m]aloop=loop=-1:size=2e9,atrim=0:{blended_dur:.3f},"
                    f"asetpts=PTS-STARTPTS,volume=2[mout]"
                )

            r = subprocess.run([
                "ffmpeg", "-y",
                "-i", blended_video,
                "-stream_loop", "-1", "-i", music_track,
                "-filter_complex", music_filter,
                "-map", "[0:v]", "-map", "[mout]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                music_out
            ], capture_output=True, text=True)

            if r.returncode != 0:
                import warnings
                warnings.warn(f"Music mix failed, using silent video: {r.stderr[:200]}")
                music_out = blended_video
        else:
            music_out = blended_video

        # ── 3. Fade to black at end ─────────────────────────────────────
        final_out = _os.path.join(seg_dir, "movie_final.mp4")
        if video_fade_out > 0:
            fade_start = max(blended_dur - video_fade_out, 0)
            r = subprocess.run([
                "ffmpeg", "-y",
                "-i", music_out,
                "-vf", f"fade=t=out:st={fade_start:.3f}:d={video_fade_out}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                final_out
            ], capture_output=True, text=True)
        else:
            final_out = music_out

        # Copy to final output path
        if final_out != output_path:
            import shutil
            shutil.copy2(final_out, output_path)

        # ── 4. Cleanup ─────────────────────────────────────────────────
        for f in _os.listdir(seg_dir):
            if f.startswith(("blend_", "concat", "movie_")):
                try:
                    _os.remove(_os.path.join(seg_dir, f))
                except Exception:
                    pass

        return output_path

    def _image_to_base64(self, image_path: str) -> str:
        """Read an image file and return its base64-encoded string."""
        import base64
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def concatenate_segments(self, segment_paths: list, output_path: str) -> str:
        """
        Concatenate video segments into a single file using ffmpeg.

        Requires ffmpeg to be installed and accessible in PATH.

        Args:
            segment_paths: Ordered list of local segment file paths.
            output_path: Local path for the final concatenated video.

        Returns:
            The output_path that was written.
        """
        self._require_ffmpeg()
        import subprocess, tempfile as _tempfile, os as _os

        for path in segment_paths:
            if not _os.path.exists(path):
                raise FileNotFoundError(f"Segment not found: {path}")

        out_dir = _os.path.dirname(_os.path.abspath(output_path))
        if out_dir:
            _os.makedirs(out_dir, exist_ok=True)

        with _tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            concat_list = f.name
            for path in segment_paths:
                f.write(f"file '{_os.path.abspath(path)}'\n")

        try:
            result = subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", concat_list, "-c", "copy", output_path],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
        finally:
            _os.unlink(concat_list)

        return output_path


def main():
    """Example usage."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        print("Error: XAI_API_KEY environment variable not set")
        return 1

    client = GrokImagineVideoClient(api_key)

    # Choose mode:
    # 1. Text-to-video
    # 2. Image-to-video
    # 3. Video editing

    mode = "text"  # Change to "image" or "edit" for other modes

    if mode == "text":
        # Example: Text-to-video
        print("Starting text-to-video generation...")
        result = client.text_to_video("A beautiful sunset over the ocean", duration=10)
        request_id = result.get("request_id")
        print(f"Job started: {request_id}")

    elif mode == "image":
        # Example: Image-to-video
        print("Starting image-to-video generation...")
        result = client.image_to_video(
            image_url="https://example.com/landscape.jpg",
            prompt="Animate the clouds and add gentle wind",
            duration=10
        )
        request_id = result.get("request_id")
        print(f"Job started: {request_id}")

    elif mode == "edit":
        # Example: Video editing
        print("Starting video edit...")
        result = client.edit_video(
            video_url="https://example.com/source.mp4",
            edit_prompt="Add a warm sunset filter"
        )
        request_id = result.get("request_id")
        print(f"Job started: {request_id}")

    # Wait for completion
    print("Waiting for completion...")
    final_response = client.wait_for_completion(
        request_id,
        progress_callback=lambda r: print(f"Polling... {'Done!' if 'video' in r else 'Pending'}")
    )

    video_url = final_response.get("video", {}).get("url")
    print(f"Video ready: {video_url}")

    # Download
    output_path = "/tmp/video_output.mp4"
    client.download_video(final_response, output_path)
    print(f"Downloaded to: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
