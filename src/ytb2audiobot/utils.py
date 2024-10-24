import asyncio
import hashlib
import json
import os
import pathlib
import pprint
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


def make_first_capital(text):
    return text[0].upper() + text[1:]


def capital2lower(text):
    count_capital = sum(1 for char in text if char.isupper())
    if count_capital / len(text) < CAPITAL_LETTERS_PERCENT_THRESHOLD:
        return make_first_capital(text)

    return make_first_capital(text.lower())


def filename_m4a(text):
    name = (re.sub(r'[^\w\s\-\_\(\)\[\]]', ' ', text)
            .replace('    ', ' ')
            .replace('   ', ' ')
            .replace('  ', ' ')
            .strip())
    return f'{name}.m4a'


import datetime


def seconds2humanview(seconds):
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


async def get_file_size0(path):
    path = pathlib.Path(path)
    async with aiofiles.open(path.as_posix(), 'r'):
        file_size = aiofiles.os.path.getsize(path.as_posix())
    return file_size


async def read_file(path):
    path = pathlib.Path(path)
    async with aiofiles.open(path.resolve(), 'r') as file:
        contents = await file.read()
    return contents


async def write_file(path, data):
    path = pathlib.Path(path)
    async with aiofiles.open(path.resolve(), 'w') as file:
        await file.write(data)


def write_json(path: str, data: dict) -> str:
    path = pathlib.Path(path)
    with open(path.as_posix(), 'w+', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    return path.as_posix()

async def get_file_size1(path):
    path = pathlib.Path(path)
    print('⛺️: ', path)
    print(path.as_posix())
    print()

    file_stat = await aiofiles.os.stat(str(path.as_posix))
    file_size = file_stat.st_size

    return file_size


async def get_file_size(file_path):
    size = 0
    try:
        async with aiofiles.open(file_path, mode='rb') as f:
            # Move the cursor to the end of the file
            await f.seek(0, os.SEEK_END)
            # Get the current position of the cursor, which is the size of the file
            size = await f.tell()
    except Exception as e:
        return 0

    return size


def get_hash(data):
    if not isinstance(data, str):
        data = str(data)

    return hashlib.sha256(data.encode('utf-8')).hexdigest()


async def check_autodownload_hashs(ids_dict):
    pass


async def run_command(cmd):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    return stdout.decode(), stderr.decode(), process.returncode


def remove_all_in_dir(data_dir: Path):
    # Удаление всех файлов и каталогов
    for item in data_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            for subitem in item.rglob('*'):
                if subitem.is_file():
                    subitem.unlink()
                elif subitem.is_dir():
                    subitem.rmdir()
            item.rmdir()  # Удаление пустого каталога


def pprint_format(data):
    try:
        text = pprint.pformat(data)
    except Exception as e:
        return str(object)
    else:
        return text


def tabulation2text(text, tab='\t'):
    return '\n'.join(tab + line for line in text.splitlines())
