import asyncio
import json
import os
import pprint
import re
import pathlib
import datetime
import time
from typing import Union

import aiofiles
import aiofiles.os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytube.extract import video_id
from urlextract import URLExtract
import tempfile
import zlib
import hashlib

from ytb2audiobot import config
from ytb2audiobot.logger import logger

CAPITAL_LETTERS_PERCENT_THRESHOLD = 0.3


def timedelta_from_seconds(seconds: Union[str, int, float]) -> str:
    """
    Converts a number of seconds into a string representation of a timedelta object.

    Args:
        seconds (Union[str, int, float]): The number of seconds as a string, integer, or float.

    Returns:
        str: The formatted string representation of the timedelta.

    Raises:
        ValueError: If the input cannot be converted to an integer.
    """
    try:
        # Convert to integer to ensure compatibility with timedelta
        seconds_int = int(float(seconds))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid input for seconds: {seconds}") from e

    time_delta = datetime.timedelta(seconds=seconds_int)
    return str(time_delta)

def get_youtube_move_id(url: str):
    try:
        movie_id = video_id(url)
    except Exception as e:
        return None
    return movie_id


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


async def delete_file_async(path: pathlib.Path):
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


def get_filename_m4a(text):
    name = (re.sub(r'[^\w\s\-\_\(\)\[\]]', ' ', text)
            .replace('    ', ' ')
            .replace('   ', ' ')
            .replace('  ', ' ')
            .strip())
    return f'{name}.m4a'


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


async def run_command_old(cmd):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    return stdout.decode(), stderr.decode(), process.returncode


async def run_command(cmd: str, timeout: int = None, throttle_delay: int = 0):
    """
    Run a command asynchronously with a timeout option and log output in real-time.

    Args:
        cmd (str): The shell command to execute.
        timeout (int or None): Timeout in seconds. If None, no timeout is applied.

    Returns:
        tuple: (stdout, stderr, return_code)
        :param cmd:
        :param timeout:
        :param throttle_delay:
    """
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Read stdout and stderr line by line and log immediately
    stdout_lines = []
    stderr_lines = []

    async def read_stream(stream, log_func, lines, _throttle_delay):
        """Helper to read a stream line by line and log each line with a throttle delay."""
        last_log_time = time.time()

        while True:
            line = await stream.readline()
            if line:
                decoded_line = line.decode().strip()

                # Apply throttle logic: only log if enough time has passed
                current_time = time.time()
                if current_time - last_log_time >= _throttle_delay:
                    log_func(decoded_line)
                    last_log_time = current_time

                lines.append(decoded_line)  # Store the line for final return
            else:
                break

    try:
        # Use asyncio.gather with a timeout if specified
        if timeout is not None:
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, logger.debug, stdout_lines, throttle_delay),
                    read_stream(process.stderr, logger.error, stderr_lines, throttle_delay)
                ),
                timeout=timeout
            )
            # Wait for the process to exit within the timeout
            return_code = await asyncio.wait_for(process.wait(), timeout=timeout)
        else:
            # No timeout applied
            await asyncio.gather(
                read_stream(process.stdout, logger.debug, stdout_lines, throttle_delay),
                read_stream(process.stderr, logger.error, stderr_lines, throttle_delay)
            )
            return_code = await process.wait()

    except asyncio.TimeoutError:
        logger.error("Command timed out. Killing process.")
        process.kill()
        await process.wait()  # Ensure process cleanup
        return "\n".join(stdout_lines), "\n".join(stderr_lines), None

    return "\n".join(stdout_lines), "\n".join(stderr_lines), return_code

def remove_all_in_dir(data_dir: pathlib.Path):
    for item in data_dir.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            for subitem in item.rglob('*'):
                if subitem.is_file():
                    subitem.unlink()
                elif subitem.is_dir():
                    subitem.rmdir()
            item.rmdir()


def pprint_format(data):
    try:
        text = pprint.pformat(data)
    except Exception as e:
        return str(object)
    else:
        return text


def tabulation2text(text, tab='\t'):
    return '\n'.join(tab + line for line in text.splitlines())


def green_text(text):
    return f"\033[92m{text}\033[0m"


def bold_text(text):
    return f"\033[1m{text}\033[0m"


def is_youtube_url(text):
    return any(domain in text for domain in config.YOUTUBE_DOMAINS)


def get_big_youtube_move_id(text):
    text = text.strip()
    if not is_youtube_url(text):
        return ''

    urls = URLExtract().find_urls(text)
    url = ''
    for url in urls:
        url = url.strip()
        if is_youtube_url(url):
            break

    movie_id = get_youtube_move_id(url)
    if not movie_id:
        return ''

    return movie_id


def get_md5(data, length=999999999):
    md5_hash = hashlib.md5()
    md5_hash.update(data.encode('utf-8'))
    return md5_hash.hexdigest()[:length]


def get_hash_adler32(text):
    return zlib.adler32(text.encode('utf-8'))


def get_data_dir():
    _hash = hex(get_hash_adler32(pathlib.Path.cwd().as_posix()))[-8:]
    temp_dir = pathlib.Path(tempfile.gettempdir())

    if temp_dir.exists():
        data_dir = temp_dir.joinpath(f'{config.DATA_DIR_DIRNAME_IN_TEMPDIR}-{_hash}')
        data_dir.mkdir(parents=True, exist_ok=True)

        symlink = pathlib.Path(config.DATA_DIR_NAME)
        if not symlink.exists():
            symlink.symlink_to(data_dir)

        return symlink
    else:
        data_dir = pathlib.Path(config.DATA_DIR_NAME)
        if data_dir.is_symlink():
            try:
                data_dir.unlink()
            except Exception as e:
                print(f'❌ Error symlink unlink: {e}')

        data_dir.mkdir(parents=True, exist_ok=True)

        return data_dir


def round_to_10(number):
    return round(number / 10) * 10


def predict_downloading_time(duration):
    time = int(0.04 * duration + 10)
    return round_to_10(time)


def trim_caption_to_telegram_send(text):
    return text[:config.TG_CAPTION_MAX_LONG - 32] + config.CAPTION_TRIMMED_END_TEXT


def create_inline_keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in row]
        for row in rows
    ])


def get_short_youtube_url(movie_id: str = ''):
    return f'youtu.be/{movie_id}'


def get_short_youtube_url_with_http(movie_id: str = ''):
    return f'https://youtu.be/{movie_id}'






def truncate_filename_for_telegram(filename: str) -> str:
    parts = filename.split('.')
    if len(parts) < 2:
        return filename if len(filename) < config.MAX_TELEGRAM_FILENAME_LENGTH else filename[:config.MAX_TELEGRAM_FILENAME_LENGTH]

    ext = '.' + parts[-1]
    all = '.'.join(parts[:-1])
    size = config.MAX_TELEGRAM_FILENAME_LENGTH
    size -= len(ext)
    all = all if len(all) < size else filename[:size]
    return all + ext
