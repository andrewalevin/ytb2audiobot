import asyncio
import os
import pathlib
import re
from pathlib import Path

import aiofiles
import aiofiles.os


CAPITAL_LETTERS_PERCENT_THRESHOLD = 0.3


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


async def get_files_by_movie_id(movie_id: str, folder):
    folder = pathlib.Path(folder)
    return list(filter(lambda f: (f.name.startswith(movie_id)), folder.iterdir()))


async def remove_m4a_file_if_exists(movie_id, store):
    movie_ids_files = await get_files_by_movie_id(movie_id, store)
    m4a_files = list(filter(lambda f: (f.name.endswith('.m4a')), movie_ids_files))
    if m4a_files:
        print('💕 m4a_files: ', m4a_files)
        print('🚮🗑 Remove file in new bitrate')
        for f in m4a_files:
            print('\t', '🔹', f.name)
            f.unlink()


async def async_iterdir(directory):
    directory = pathlib.Path(directory)
    async with aiofiles.open(directory.as_posix()) as dir_handle:
        async for entry in await dir_handle.iterdir():
            yield entry


async def get_creation_time_async(path):
    path = pathlib.Path(path)
    try:
        # Open the file asynchronously
        async with aiofiles.open(path.as_posix(), mode='rb') as f:
            # Get file descriptor
            fd = f.fileno()

            # Get file stats asynchronously
            file_stats = await asyncio.to_thread(os.fstat, fd)

            # Return the creation time (st_ctime)
            return file_stats.st_ctime
    except Exception as e:
        print(f"Error: {e}")
        return None


def capital2lower(text):
    count_capital = sum(1 for char in text if char.isupper())
    if count_capital / len(text) < CAPITAL_LETTERS_PERCENT_THRESHOLD:
        return text

    text = text.lower()
    text = text[0].upper() + text[1:]
    return text


def filename_m4a(text):
    name = (re.sub(r'[^\w\s\-\_\(\)\[\]]', ' ', text)
            .replace('    ', ' ')
            .replace('   ', ' ')
            .replace('  ', ' ')
            .strip())
    return f'{name}.m4a'


import datetime


def seconds_to_human_readable(seconds):
    # Create a timedelta object representing the duration
    duration = datetime.timedelta(seconds=seconds)

    # Extract hours, minutes, and seconds from the duration
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60

    # Format into hh:mm:ss or mm:ss depending on whether there are hours
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


async def get_file_size(path):
    path = pathlib.Path(path)
    async with aiofiles.open(path.as_posix(), 'r'):
        file_size = aiofiles.os.path.getsize(path.as_posix())
    return file_size

