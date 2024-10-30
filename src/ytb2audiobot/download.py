import asyncio
import math
import pathlib

from audio2splitted.audio2splitted import get_split_audio_scheme, make_split_audio
from ytb2audio.ytb2audio import download_audio
from ytbtimecodes.timecodes import standardize_time_format, timedelta_from_seconds

from ytb2audiobot import config
from ytb2audiobot.utils import get_file_size, capital2lower
from ytb2audiobot.logger import logger
from ytb2audiobot.utils import run_command


def get_timecodes_formatted_text(timecodes):
    # Return an empty string if there are no timecodes
    if not timecodes:
        return ''

    formatted_timecodes = []
    for stamp in timecodes:
        # Extract time and title from the current stamp
        time = standardize_time_format(timedelta_from_seconds(stamp.get('time')))
        title = capital2lower(stamp.get('title'))

        formatted_timecodes.append(f"{time} - {title}")

    # Join the list into a single string with each timecode on a new line
    return '\n'.join(formatted_timecodes)


async def download_thumbnail(movie_id: str, thumbnail_path: pathlib.Path):
    """
    Downloads a thumbnail for the given movie ID using yt-dlp and saves it as a JPEG image.

    Args:
        movie_id (str): The ID of the movie/video for which to download the thumbnail.
        thumbnail_path (pathlib.Path): Path where the thumbnail should be saved.

    Returns:
        pathlib.Path: Path to the downloaded thumbnail if successful, None otherwise.
    """
    if thumbnail_path.exists():
        return thumbnail_path

    command = f'yt-dlp --write-thumbnail --skip-download --convert-thumbnails jpg -o {thumbnail_path.with_suffix('')} {movie_id}'

    logger.debug(f"🏞 🔫 Command Thumbnail: {command}")

    stdout, stderr, return_code = await run_command(command)

    # Log stdout and stderr output line by line
    for line in stdout.splitlines():
        logger.debug(line)
    for line in stderr.splitlines():
        logger.error(line)

    # Check for errors or missing file
    if return_code != 0:
        logger.error(f"🏞 Thumbnail download failed for movie ID: {movie_id} with return code {return_code}")
        return None

    if not thumbnail_path.exists():
        logger.error(f"🏞 Thumbnail file not found at {thumbnail_path}")
        return None

    logger.info(f"🏞 Thumbnail successfully downloaded at {thumbnail_path}")
    return thumbnail_path


async def audio_download(movie_id: str, audio_path: pathlib.Path):
    if audio_path.exists():
        return audio_path

    audio_result_path = await download_audio(
        movie_id=movie_id,
        data_dir=audio_path.parent,
        ytdlprewriteoptions=config.YT_DLP_OPTIONS_DEFAULT)
    if not audio_result_path or not audio_result_path.exists():
        return None

    return audio_result_path


async def download_processing(
        movie_id: str,
        data_dir: pathlib.Path,
        duration: int):
    logger.debug(f'🐿 download_processing():')

    audio_path = config.get_audio_path(data_dir, movie_id)
    thumbnail_path = config.get_thumbnail_path(data_dir, movie_id)

    results = await asyncio.gather(
        audio_download(movie_id=movie_id, audio_path=audio_path),
        download_thumbnail(movie_id=movie_id, thumbnail_path=thumbnail_path),
        return_exceptions=False
    )

    audio = results[0]
    if not audio:
        return []

    scheme = get_split_audio_scheme(
        source_audio_length=duration,
        duration_seconds=60 * 39,
        delta_seconds=config.AUDIO_SPLIT_DELTA_SECONDS,
        magic_tail=True,
        threshold_seconds=60 * 101
    )
    if len(scheme) == 1:
        size = await get_file_size(audio)
        if size and size > config.TELEGRAM_BOT_FILE_MAX_SIZE_BYTES:
            number_parts = math.ceil(size / config.TELEGRAM_BOT_FILE_MAX_SIZE_BYTES)

            scheme = get_split_audio_scheme(
                source_audio_length=duration,
                duration_seconds=duration // number_parts,
                delta_seconds=config.AUDIO_SPLIT_DELTA_SECONDS,
                magic_tail=True,
                threshold_seconds=1)

    print(f'🌈 Scheme: {scheme}')

    results = await asyncio.gather(
        make_split_audio(
            audio_path=audio,
            audio_duration=duration,
            output_folder=data_dir,
            scheme=scheme))
    audios = results[0]

    logger.info(f'🍫 Audios: {audios}')

    audio_items = []
    for idx, item in enumerate(audios):
        audio_items.append({
            'audio_path': item['path'],
            'duration': item['duration'],
            'start': scheme[idx][0],
            'end': scheme[idx][1]
        })

    return audio_items
