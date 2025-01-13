import asyncio
import math
import pathlib

from mutagen.mp4 import MP4


async def get_duration(path: pathlib.Path):
    """
    Asynchronously get the duration of an .m4a file in seconds using mutagen.

    Args:
        path (str): Path to the .m4a file.

    Returns:
        int: Duration of the audio file in seconds, or None if an error occurs.
    """
    try:
        # Simulate async I/O (if needed, you can add file I/O operations here)
        await asyncio.sleep(0)  # Ensure it's non-blocking
        audio = MP4(path)
        duration = math.ceil(audio.info.length)
        return duration
    except Exception as e:
        print(f"Error reading file {path}: {e}")
        return None

