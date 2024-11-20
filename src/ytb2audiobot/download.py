import pathlib
from typing import Optional, List, Dict

from audio2splitted.audio2splitted import time_format
from audio2splitted.utils import run_cmds
from ytbtimecodes.timecodes import standardize_time_format

from ytb2audiobot.utils import capital2lower, get_short_youtube_url_with_http, timedelta_from_seconds
from ytb2audiobot.logger import logger
from ytb2audiobot.utils import run_command


def get_timecodes_formatted_text(timecodes_dict: Dict[int, Dict], start_time: int = 0) -> str:
    """
    Formats a dictionary of timecodes into a string with each timecode on a new line.

    Args:
        timecodes_dict (Dict[int, Dict[str, str]]): A dictionary where keys are timecodes in seconds (int),
                                                    and values are dictionaries with at least a 'title' key.
        start_time (int): An optional starting time in seconds to offset all timecodes.

    Returns:
        str: Formatted timecodes as a string with each entry on a new line.
    """
    if not timecodes_dict:
        logger.info("No timecodes provided.")
        return ''

    formatted_timecodes = []
    for time, value in timecodes_dict.items():
        # Adjust the time relative to the start_time, ensuring it remains positive
        adjusted_time = max(0, time - start_time)

        try:
            _time = standardize_time_format(timedelta_from_seconds(adjusted_time))
            title = capital2lower(value.get('title', 'Untitled'))
            formatted_timecodes.append(f"{_time} - {title}")
        except Exception as e:
            logger.error(f"🔴 Error processing timecode at {time}: {e}")
            continue

    return '\n'.join(formatted_timecodes)


async def make_split_audio_second(audio_path: pathlib.Path, segments: list) -> list:
    if segments is None:
        segments = []

    if len(segments) == 1:
        segments[0]['path'] = audio_path
        return segments

    convert_option = '-c copy'
    if audio_path.suffix == '.mp3':
        pass

    cmds_list = []
    for idx, segment in enumerate(segments):
        segment_file = audio_path.with_stem(f'{audio_path.stem}-p{idx + 1}-of{len(segments)}')
        print('💜', segment_file)
        segments[idx]['path'] = segment_file
        cmd = (
            f'ffmpeg -i {audio_path.as_posix()} -ss {time_format(segment['start'])} -to {time_format(segment['end'])} {convert_option} -y {segment_file.as_posix()}')
        print('💜💜', cmd, type(cmd))
        cmds_list.append(cmd)

    print('💜 cmds_list: ', cmds_list)
    print()

    results, all_success = await run_cmds(cmds_list)
    print('results, all_success', results, all_success)
    print()

    print("🟢 All Done! Lets see .m4a files and their length")

    return segments


def get_chapters(chapters_yt_info: List[Dict]) -> Dict[int, Dict]:
    """
    Extracts chapters with start times and titles from YouTube chapter information.

    Args:
        chapters_yt_info (List[Dict[str, Any]]): List of dictionaries, each containing chapter info with 'title' and 'start_time'.

    Returns:
        Dict[int, Dict[str, str]]: Dictionary where keys are start times (int) and values are dictionaries with 'title' and 'type'.
    """
    if not chapters_yt_info:
        return {}

    chapters = {}
    for chapter in chapters_yt_info:
        title = chapter.get('title')
        start_time = chapter.get('start_time')

        # Skip if either title or start_time is missing
        if not title or start_time is None:
            continue

        try:
            time = int(start_time)
            chapters[time] = {'title': title, 'type': 'chapter'}
        except ValueError:
            continue  # Skip entries where start_time is not a valid integer

    return chapters


def get_timecodes_dict(timecodes: Optional[List]) -> Dict:
    """
    Converts a list of timecodes into a dictionary where each timecode's 'time' is the key.

    Args:
        timecodes (Optional[List[Dict[str, str]]]): A list of dictionaries where each dictionary contains 'time' and 'title' keys.

    Returns:
        Dict[int, Dict[str, str]]: A dictionary where the keys are 'time' values and the values are dictionaries containing 'title' and 'type'.
    """
    if not timecodes:
        return {}

    timecodes_dict = {}
    for timecode in timecodes:
        time = timecode.get('time')
        title = timecode.get('title')

        if time is not None:  # Ensure the 'time' key exists and is not None
            timecodes_dict[time] = {
                'title': title if title else 'Untitled',  # Default to 'Untitled' if no title is provided
                'type': 'timecode'
            }

    return timecodes_dict


def filter_timecodes_within_bounds(timecodes: dict, start_time: int, end_time: int) -> dict:
    """Filters timecodes that fall within the specified start and end times."""

    return {k: v for k, v in timecodes.items() if start_time <= k <= end_time}


async def download_thumbnail_from_download(
    movie_id: str,
    output_path: pathlib.Path
) -> Optional[pathlib.Path]:
    """
    Downloads a thumbnail for the given movie ID using yt-dlp and saves it as a JPEG image.

    Args:
        movie_id (str): The ID of the movie/video for which to download the thumbnail.
        output_path (pathlib.Path): Path where the thumbnail should be saved.

    Returns:
        Optional[pathlib.Path]: Path to the downloaded thumbnail if successful, None otherwise.
    """
    output_path = pathlib.Path(output_path)
    if output_path.exists():
        logger.info(f"🌅 Thumbnail already exists at {output_path}")
        return output_path

    url = get_short_youtube_url_with_http(movie_id)
    output_path = output_path.with_suffix(".jpg")
    command = (
        f'yt-dlp --write-thumbnail --skip-download --convert-thumbnails jpg '
        f'--output "{output_path.with_suffix('').as_posix()}" {url}')

    logger.debug(f"🌅🔰 Running thumbnail download command: {command}")
    stdout, stderr, return_code = await run_command(command)

    # Log output from command
    if stdout:
        for line in stdout.splitlines():
            logger.debug(line)
    if stderr:
        for line in stderr.splitlines():
            logger.error(line)

    # Error and file existence checks
    if return_code != 0:
        logger.error(f"🌅 Thumbnail download failed for movie ID: {movie_id} with return code {return_code}")
        return None

    if not output_path.exists():
        logger.error(f"🌅 Thumbnail file not found at {output_path.with_suffix('.jpg')}")
        return None

    logger.info(f"🌅 Thumbnail successfully downloaded at {output_path.as_posix()}")
    return output_path


async def download_audio_from_download(
        movie_id: str,
        output_path: pathlib.Path,
        options: str = '') -> Optional[pathlib.Path]:
    """
    Downloads audio from a YouTube video using yt-dlp if the audio file does not already exist.

    Args:
        movie_id (str): The YouTube video ID.
        output_path (pathlib.Path): The desired output path for the audio file.
        options (str): Additional yt-dlp options for customization.

    Returns:
        Optional[pathlib.Path]: The path to the downloaded audio file, or None if download failed.
    """
    output_path = pathlib.Path(output_path)
    if output_path.exists():
        logger.info(f"📣 Audio file already exists at {output_path}")
        return output_path

    url = get_short_youtube_url_with_http(movie_id)
    command = f'yt-dlp {options} --output "{output_path.as_posix()}" {url}'

    logger.debug(f"📣🔰 Executing command: {command}")

    stdout, stderr, return_code = await run_command(command)

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
