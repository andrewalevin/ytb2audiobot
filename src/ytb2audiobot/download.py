import pathlib

from audio2splitted.audio2splitted import get_split_audio_scheme, make_split_audio, get_audio_segments_by_timecodes, \
    time_format
from audio2splitted.utils import run_cmds
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


def get_timecodes_formatted_text_from_dict(timecodes_dict, start_time: int = 0):
    # Return an empty string if there are no timecodes
    if not timecodes_dict:
        return ''

    formatted_timecodes = []
    for time, value in timecodes_dict.items():
        # Extract time and title from the current stamp
        if time - start_time > 0:
            time = time - start_time
        _time = standardize_time_format(timedelta_from_seconds(time))
        title = capital2lower(value.get('title'))

        formatted_timecodes.append(f"{_time} - {title}")

    # Join the list into a single string with each timecode on a new line
    return '\n'.join(formatted_timecodes)


async def download_thumbnail(movie_id: str, thumbnail_path: pathlib.Path) -> pathlib.Path | None:
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

    # todo add age update

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


async def audio_download(movie_id: str, audio_path: pathlib.Path) -> pathlib.Path | None:
    if audio_path.exists():
        return audio_path

    # audio_result_path = await

    return audio_path


async def make_split_audio_second(audio_path: pathlib.Path, segments: list) -> list:
    if segments is None:
        segments = []

    if len(segments) == 1:
        segments[0]['path'] = audio_path
        return segments

    cmds_list = []
    for idx, segment in enumerate(segments):
        segment_file = audio_path.with_stem(f'{audio_path.stem}-p{idx + 1}-of{len(segments)}')
        print('💜', segment_file)
        segments[idx]['path'] = segment_file
        cmd = (
            f'ffmpeg -i {audio_path.as_posix()} -ss {time_format(segment['start'])} -to {time_format(segment['end'])} -c copy -y {segment_file.as_posix()}')
        print('💜💜', cmd, type(cmd))
        cmds_list.append(cmd)

    print('💜 cmds_list: ', cmds_list)
    print()

    results, all_success = await run_cmds(cmds_list)
    print('results, all_success', results, all_success)
    print()

    print("🟢 All Done! Lets see .m4a files and their length")

    return segments


def get_chapters(chapters_yt_info):
    if not chapters_yt_info:
        return {}

    chapters = dict()
    for chapter in chapters_yt_info:
        if not chapter.get('title', ''):
            continue

        if not chapter.get('start_time', ''):
            continue

        #   _end = chapter.get('end_time')

        time = int(chapter.get('start_time'))

        chapters[time] = {
            'title': chapter.get('title'),
            'type': 'chapter'}

    return chapters


def get_timecodes_dict(timecodes: list) -> dict:
    if timecodes is None:
        return {}

    timecodes_dict = dict()
    for timecode in timecodes:
        time = timecode.get('time')
        timecodes_dict[time] = {
            'title': timecode.get('title'),
            'type': 'timecode'}

    return timecodes_dict


def filter_timecodes_within_bounds_with_dict(timecodes: dict, start_time: int, end_time: int) -> dict:
    """Filters timecodes that fall within the specified start and end times."""

    filtered_dict = {k: v for k, v in timecodes.items() if start_time <= k <= end_time}
    return filtered_dict
