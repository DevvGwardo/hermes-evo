#!/usr/bin/env python3
"""voice_clone.py — Clone voice using XTTS v2"""

import argparse
import os
import torch
from TTS.api import TTS


def clone_voice(reference_audio: str, text: str, output_path: str, language: str = "en"):
    """Clone voice using XTTS v2.
    
    Args:
        reference_audio: Path to reference WAV file (5-30 seconds, clean speech)
        text: Text to synthesize with cloned voice
        output_path: Output path for generated WAV
        language: Language code (default: en)
    """
    if not os.path.exists(reference_audio):
        raise FileNotFoundError(f"Reference audio not found: {reference_audio}")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[XTTS v2] Loading model on {device}...")
    tts = TTS("xtts_v2").to(device)
    
    print(f"[XTTS v2] Cloning voice from: {reference_audio}")
    print(f"[XTTS v2] Synthesizing: {text[:100]}...")
    
    tts.tts_to_file(
        text=text,
        speaker_wav=reference_audio,
        file_path=output_path,
        language=language
    )
    
    # Verify output
    if os.path.exists(output_path):
        size_kb = os.path.getsize(output_path) / 1024
        print(f"[XTTS v2] Voice cloned: {output_path} ({size_kb:.1f} KB)")
    else:
        raise RuntimeError("Voice cloning failed - no output file created")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clone voice using XTTS v2")
    parser.add_argument("--reference", required=True, help="Reference audio file (WAV/MP3)")
    parser.add_argument("--text", required=True, help="Text to synthesize")
    parser.add_argument("--output", required=True, help="Output WAV path")
    parser.add_argument("--language", default="en", help="Language code")
    args = parser.parse_args()
    
    clone_voice(args.reference, args.text, args.output, args.language)
