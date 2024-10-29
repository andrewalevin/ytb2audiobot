import pathlib
from ytb2audiobot.logger import logger
from ytb2audiobot.utils import run_command


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

