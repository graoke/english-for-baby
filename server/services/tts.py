"""TTS pre-generation service using edge-tts."""

import asyncio
import subprocess
from pathlib import Path


async def generate_tts(text: str, output_path: str, voice: str = "en-US-AnaNeural", speed: str = "-10%"):
    """Generate TTS audio file using edge-tts.

    Args:
        text: English text to synthesize.
        output_path: Where to save the mp3 file.
        voice: Edge-TTS voice name. AnaNeural is a child-friendly female voice.
        speed: Speed adjustment, e.g. "-10%" for slower.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "edge-tts",
        f"--voice={voice}",
        f"--rate={speed}",
        f"--text={text}",
        f"--write-media={str(output)}",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"edge-tts failed: {stderr.decode()}")

    return str(output)


def generate_tts_sync(text: str, output_path: str, voice: str = "en-US-AnaNeural", speed: str = "-10%"):
    """Synchronous wrapper for generate_tts."""
    return asyncio.run(generate_tts(text, output_path, voice, speed))
