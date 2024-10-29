import asyncio
import pathlib
import math
from datetime import timedelta
from string import Template

from audio2splitted.audio2splitted import get_split_audio_scheme, make_split_audio
from ytb2audio.ytb2audio import download_audio

from ytb2audiobot import config
from ytb2audiobot.config import get_thumbnail_path, get_audio_path
from ytb2audiobot.timecodes import get_timecodes, filter_timestamp_format
from ytb2audiobot.thumbnail import download_thumbnail
from ytb2audiobot.utils import capital2lower, get_filename_m4a, get_file_size
from ytb2audiobot.logger import logger


async def audio_download(
        movie_id: str,
        audio_path: pathlib.Path,
        ytdlprewriteoptions: str
):
    if audio_path.exists():
        return audio_path

    audio_result_path = await download_audio(movie_id=movie_id, data_dir=audio_path.parent, ytdlprewriteoptions=ytdlprewriteoptions)
    if not audio_result_path or not audio_result_path.exists():
        return None

    return audio_result_path


async def download_processing(movie_meta: dict, description: str):
    logger.debug(f'🐿 download_processing():')

    caption_head = config.CAPTION_HEAD_TEMPLATE.safe_substitute(
        movieid=movie_meta['id'],
        title=capital2lower(movie_meta['title']),
        author=capital2lower(movie_meta['author']),
    )
    filename = get_filename_m4a(movie_meta['title'])

    movie_id = movie_meta['id']
    data_dir = pathlib.Path(movie_meta['store'])
    audio_path = get_audio_path(data_dir, movie_id)
    thumbnail_path = get_thumbnail_path(data_dir, movie_id)

    print('❇️ Before downloads')

    results = await asyncio.gather(
        audio_download(movie_id=movie_id, audio_path=audio_path, ytdlprewriteoptions=movie_meta.get('ytdlprewriteoptions')),
        download_thumbnail(movie_id=movie_id, thumbnail_path=thumbnail_path),
        return_exceptions=False
    )

    print('❇️❇️ After downloads')

    audio = results[0]
    if not audio:
        return []

    duration_seconds = movie_meta['split_duration_minutes'] * 60
    threshold_seconds = movie_meta['threshold_seconds']

    if True:
        duration_seconds = 60*15
        threshold_seconds = 10

    scheme = get_split_audio_scheme(
        source_audio_length=movie_meta['duration'],
        duration_seconds=duration_seconds,
        delta_seconds=config.AUDIO_SPLIT_DELTA_SECONDS,
        magic_tail=True,
        threshold_seconds=threshold_seconds
    )
    if len(scheme) == 1:
        size = await get_file_size(audio)
        if size and size > config.TELEGRAM_BOT_FILE_MAX_SIZE_BYTES:
            number_parts = math.ceil(size / config.TELEGRAM_BOT_FILE_MAX_SIZE_BYTES)
            movie_meta['additional_meta_text'] = config.ADDITIONAL_INFO_FORCED_SPLITTED

            scheme = get_split_audio_scheme(
                source_audio_length=movie_meta['duration'],
                duration_seconds=movie_meta['duration'] // number_parts,
                delta_seconds=config.AUDIO_SPLIT_DELTA_SECONDS,
                magic_tail=True,
                threshold_seconds=1
            )

    print(f'🌈 Scheme: {scheme}')

    tasks = [
        make_split_audio(
            audio_path=audio,
            audio_duration=movie_meta['duration'],
            output_folder=movie_meta['store'],
            scheme=scheme
        )
    ]
    results = await asyncio.gather(*tasks)
    audios = results[0]

    logger.info(f'🍫 Audios: {audios}')

    timecodes = await get_timecodes(scheme, description)
    logger.info(f'🍡 Timecodes: {timecodes}')

    audio_items = []

    print(f'🌈 Scheme: {scheme}')

    for idx, audio_part in enumerate(audios, start=1):
        logger.info(f'💜 Idx: {idx} part: {audio_part}')

        # Add additional seconds to total duration to disable timecode link
        caption = Template(caption_head).safe_substitute(
            partition='' if len(audios) == 1 else f'[Part {idx} of {len(audios)}]',
            timecodes=timecodes[idx-1],
            duration=filter_timestamp_format(timedelta(seconds=audio_part.get('duration')+1)),
            additional=movie_meta['additional_meta_text']
        )

        audio_data = {
            'audio_path': audio_part['path'],
            'duration': audio_part['duration'],
            'start': scheme[idx-1][0],
            'end': scheme[idx-1][1]
        }
        audio_items.append(audio_data)

    return audio_items
