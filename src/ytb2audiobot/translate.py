import os
import pathlib
from typing import Optional
from ytb2audiobot import config
from ytb2audiobot.logger import logger
from ytb2audiobot.utils import get_short_youtube_url_with_http, run_command

DEBUG = False if os.getenv(config.ENV_NAME_DEBUG_MODE, 'false').lower() != 'true' else True


async def make_translate(movie_id: str, output_path: pathlib.Path, timeout: int = None) -> Optional[pathlib.Path]:
    """
    Downloads audio from a YouTube video using yt-dlp if the audio file does not already exist.

    Args:
        movie_id (str): The YouTube video ID.
        output_path (pathlib.Path): The desired output path for the audio file.
        options (str): Additional yt-dlp options for customization.

    Returns:
        Optional[pathlib.Path]: The path to the downloaded audio file, or None if download failed.
        :param output_path:
        :param movie_id:
        :param timeout:
    """
    logger.debug(f'🌎 Make transalte: {movie_id}')
    output_path = pathlib.Path(output_path)
    if output_path.exists():
        logger.info(f"📣 Audio file already exists at {output_path}")
        return output_path

    mp3_output_path = output_path.with_suffix('.mp3')
    url = get_short_youtube_url_with_http(movie_id)
    command = (f'vot-cli --output="{output_path.parent}" --output-file="{mp3_output_path.stem}" {url} '
               f'&& '
               f'ffmpeg -i {mp3_output_path} -c:a aac -b:a 48k {output_path}')

    logger.debug(f"🌎🔰 Executing command: {command}")

    stdout, stderr, return_code = await run_command(command, timeout=timeout, throttle_delay=10)

    if stdout:
        for line in stdout.splitlines():
            logger.debug(line)
    if stderr:
        for line in stderr.splitlines():
            logger.error(line)

    # Check for errors or missing file
    if return_code != 0:
        logger.error(f"📣 Download failed with return code {return_code}")
        return None
    if not output_path.exists():
        logger.error(f"📣 Expected audio file not found at {output_path}")
        return None

    logger.info(f"📣 Audio successfully downloaded to {output_path}")
    return output_path
