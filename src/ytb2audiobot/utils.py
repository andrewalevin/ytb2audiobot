import asyncio
import pathlib
from pathlib import Path

import aiofiles
import aiofiles.os


async def create_directory_async(path):
    path = pathlib.Path(path)
    if path.exists():
        return path
    try:
        await aiofiles.os.mkdir(path)
    except Exception as e:
        print(f"🔴 Create file async. Error: {e}")
        return

    return path


async def delete_file_async(path: Path):
    try:
        async with aiofiles.open(path, 'r'):  # Ensure the file exists
            pass
        await asyncio.to_thread(path.unlink)
    except Exception as e:
        print(f"🔴 Delete file async. Error: {e}")
