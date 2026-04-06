#!/usr/bin/env python3
"""video_gen.py — Generate scene video using Wan 2.2 or LTX-Video via ComfyUI API

This script submits video generation workflows to a local ComfyUI server.
It supports Wan 2.2 T2V-A14B and LTX-Video 13B models.

ComfyUI API format (prompt dict):
{
    "node_id": {
        "class_type": "NodeTypeName",
        "inputs": {
            "field_name": value  // or [source_node_id, output_index] for links
        }
    }
}
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "http://localhost:8188")
COMFYUI_TIMEOUT = int(os.environ.get("COMFYUI_TIMEOUT", "300"))


def check_comfyui_running() -> bool:
    """Check if ComfyUI server is running."""
    import urllib.request
    try:
        urllib.request.urlopen(COMFYUI_HOST, timeout=5)
        return True
    except Exception:
        return False


def find_node_by_type(workflow: dict, class_type: str) -> Optional[tuple]:
    """Find a node by its class_type. Returns (node_id, node_dict) or None."""
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == class_type:
            return node_id, node_data
    return None


def find_nodes_by_type(workflow: dict, class_type: str) -> list:
    """Find all nodes matching a class_type. Returns list of (node_id, node_dict)."""
    return [
        (node_id, node_data)
        for node_id, node_data in workflow.items()
        if node_data.get("class_type") == class_type
    ]


def queue_prompt(prompt_dict: dict) -> str:
    """Submit a workflow to ComfyUI queue."""
    import urllib.request
    import urllib.error

    url = f"{COMFYUI_HOST}/prompt"
    data = json.dumps({"prompt": prompt_dict}).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["prompt_id"]
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot connect to ComfyUI at {COMFYUI_HOST}: {e}")


def get_history(prompt_id: str) -> dict:
    """Get execution history for a prompt."""
    import urllib.request

    url = f"{COMFYUI_HOST}/history/{prompt_id}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_video_path(history: dict, prompt_id: str) -> Optional[str]:
    """Extract video path from completed execution."""
    if prompt_id not in history:
        return None

    outputs = history[prompt_id].get("outputs", {})
    for node_id, output in outputs.items():
        if isinstance(output, dict):
            if "gifs" in output and output["gifs"]:
                return output["gifs"][0]
            if "videos" in output and output["videos"]:
                return output["videos"][0]
            # ComfyUI SaveVideo node typically outputs with "images" key for video
            if "images" in output and output["images"]:
                return output["images"][0]
    return None


def update_workflow_prompt(workflow: dict, positive_prompt: str, negative_prompt: str,
                           output_prefix: str, seed: int = 42, steps: int = 20,
                           cfg: float = 7.5, fps: int = 24) -> dict:
    """Update workflow with user-supplied parameters.

    Args:
        workflow: The workflow dict (keys are node IDs as strings)
        positive_prompt: Positive prompt text
        negative_prompt: Negative prompt text
        output_prefix: Filename prefix for output
        seed: Random seed
        steps: Number of sampling steps
        cfg: CFG scale
        fps: Frames per second for output

    Returns:
        Updated workflow dict
    """
    workflow = json.loads(json.dumps(workflow))  # Deep copy

    # Update CLIPTextEncode nodes (positive and negative)
    clip_encode_nodes = find_nodes_by_type(workflow, "CLIPTextEncode")
    for i, (node_id, node_data) in enumerate(clip_encode_nodes):
        if i == 0:  # First CLIPTextEncode = positive
            node_data["inputs"]["text"] = positive_prompt
        elif i == 1:  # Second CLIPTextEncode = negative
            node_data["inputs"]["text"] = negative_prompt

    # Update KSampler with generation parameters
    ksampler_nodes = find_nodes_by_type(workflow, "KSampler")
    for node_id, node_data in ksampler_nodes:
        node_data["inputs"]["seed"] = seed
        node_data["inputs"]["steps"] = steps
        node_data["inputs"]["cfg"] = cfg

    # Update SaveVideo prefix and fps
    save_nodes = find_nodes_by_type(workflow, "SaveVideo")
    for node_id, node_data in save_nodes:
        if "filename_prefix" in node_data["inputs"]:
            node_data["inputs"]["filename_prefix"] = output_prefix
        if "fps" in node_data["inputs"]:
            node_data["inputs"]["fps"] = fps

    return workflow


def update_workflow_model(workflow: dict, model_name: str) -> dict:
    """Update the checkpoint/model name in the workflow.

    Args:
        workflow: The workflow dict
        model_name: Model filename (e.g., 'Wan2.2_T2V_A14B.safetensors')

    Returns:
        Updated workflow dict
    """
    workflow = json.loads(json.dumps(workflow))  # Deep copy

    # Update CheckpointLoaderSimple
    checkpoint_nodes = find_nodes_by_type(workflow, "CheckpointLoaderSimple")
    for node_id, node_data in checkpoint_nodes:
        node_data["inputs"]["ckpt_name"] = model_name

    return workflow


def generate_scene_video(
    scene_description: str,
    duration: int = 5,
    model: str = "wan22",
    output_path: str = "./output/scene_video.mp4",
    resolution: tuple = (1280, 720),
    seed: int = 42,
    steps: int = 20,
    cfg: float = None
) -> str:
    """Generate a scene video from text description via ComfyUI.

    Args:
        scene_description: Text description of the scene to generate
        duration: Duration in seconds (max 10 for Wan/LTX)
        model: Model to use ('wan22' or 'ltx')
        output_path: Output MP4 path
        resolution: Video resolution (width, height) — informational only
        seed: Random seed for reproducibility
        steps: Sampling steps
        cfg: CFG scale (auto-set based on model if not specified)

    Returns:
        Path to generated video file

    Raises:
        ConnectionError: If ComfyUI is not running
        TimeoutError: If generation times out
        FileNotFoundError: If workflow file is missing
    """
    if not check_comfyui_running():
        raise ConnectionError(
            f"ComfyUI is not running at {COMFYUI_HOST}. "
            "Please start ComfyUI first: cd ~/models/ComfyUI && python main.py"
        )

    # Model-specific defaults
    if model == "wan22":
        base_prompt = f"UGC video style, {scene_description}, professional lighting, cinematic, 4K quality"
        negative = "watermark, text, logo, blurry, low quality, cartoon, anime, distorted"
        model_filename = "Wan2.2_T2V_A14B.safetensors"
        workflow_path = Path("~/.hermes/skills/ugc-video-pipeline/workflows/wan22_video.json")
        default_cfg = 7.5
    elif model == "ltx":
        base_prompt = f"realistic video, {scene_description}, cinematic lighting, high quality"
        negative = "cartoon, anime, watermark, text, distorted, low quality"
        model_filename = "LTX-Video-13B.safetensors"
        workflow_path = Path("~/.hermes/skills/ugc-video-pipeline/workflows/ltx_video.json")
        default_cfg = 4.5
    else:
        raise ValueError(f"Unknown model: {model}. Use 'wan22' or 'ltx'")

    if cfg is None:
        cfg = default_cfg

    # Expand user path
    workflow_path = workflow_path.expanduser()

    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    # Load workflow template
    with open(workflow_path) as f:
        workflow = json.load(f)

    # Update workflow parameters
    # 1. Set the checkpoint/model name
    workflow = update_workflow_model(workflow, model_filename)

    # 2. Set prompts and generation parameters
    output_prefix = Path(output_path).stem or "ugc_scene"
    workflow = update_workflow_prompt(
        workflow,
        positive_prompt=base_prompt,
        negative_prompt=negative,
        output_prefix=output_prefix,
        seed=seed,
        steps=steps,
        cfg=cfg
    )

    print(f"[ComfyUI] Generating scene: {scene_description}")
    print(f"[ComfyUI] Model: {model} ({model_filename})")
    print(f"[ComfyUI] Duration: {duration}s (max 10)")
    print(f"[ComfyUI] Resolution: {resolution[0]}x{resolution[1]}")
    print(f"[ComfyUI] Seed: {seed}, Steps: {steps}, CFG: {cfg}")

    # Queue and execute
    prompt_id = queue_prompt(workflow)
    print(f"[ComfyUI] Queued prompt: {prompt_id}")

    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < COMFYUI_TIMEOUT:
        time.sleep(5)
        try:
            history = get_history(prompt_id)
            if prompt_id in history and history[prompt_id].get("outputs"):
                video_path = get_video_path(history, prompt_id)
                if video_path and os.path.exists(video_path):
                    print(f"[ComfyUI] Video generated: {video_path}")
                    return video_path
        except Exception as e:
            print(f"[ComfyUI] Polling error: {e}")
            continue

    raise TimeoutError(f"Video generation timed out after {COMFYUI_TIMEOUT}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate scene video using Wan 2.2 or LTX-Video via ComfyUI API"
    )
    parser.add_argument("--scene", required=True, help="Scene description")
    parser.add_argument("--duration", type=int, default=5, help="Duration in seconds (max 10)")
    parser.add_argument("--model", default="wan22", choices=["wan22", "ltx"],
                        help="Video model ('wan22' for Wan 2.2 T2V-A14B, 'ltx' for LTX-Video 13B)")
    parser.add_argument("--output", required=True, help="Output MP4 path")
    parser.add_argument("--resolution", default="1280x720",
                        help="Resolution WxH (informational, actual generation may vary)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--steps", type=int, default=20, help="Sampling steps")
    parser.add_argument("--cfg", type=float, default=None,
                        help="CFG scale (auto-set based on model if not specified)")
    parser.add_argument("--host", default="http://localhost:8188", help="ComfyUI host URL")

    args = parser.parse_args()

    # Update global host if specified
    if args.host != "http://localhost:8188":
        COMFYUI_HOST = args.host

    # Parse resolution
    if "x" in args.resolution:
        width, height = map(int, args.resolution.split("x"))
        resolution = (width, height)
    else:
        resolution = (1280, 720)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    try:
        result = generate_scene_video(
            scene_description=args.scene,
            duration=args.duration,
            model=args.model,
            output_path=args.output,
            resolution=resolution,
            seed=args.seed,
            steps=args.steps,
            cfg=args.cfg
        )
        print(f"Output: {result}")
    except Exception as e:
        print(f"[Error] {e}")
        sys.exit(1)
