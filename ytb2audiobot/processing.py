import asyncio
import math
from datetime import timedelta
from string import Template

from audio2splitted.audio2splitted import get_split_audio_scheme, \
    make_split_audio

from ytb2audiobot import config
from ytb2audiobot.mp4mutagen import get_mp4object
from ytb2audiobot.thumbnail import image_compress_and_resize
from ytb2audiobot.timecodes import get_timecodes, filter_timestamp_format
from ytb2audiobot.thumbnail import download_thumbnail_by_movie_meta
from ytb2audiobot.audio import download_audio_by_movie_meta
from ytb2audiobot.utils import capital2lower, filename_m4a, get_file_size
from ytb2audiobot.logger import logger


async def download_processing(movie_meta: dict):
    logger.debug(f'🐿 download_processing():')

    caption_head = config.CAPTION_HEAD_TEMPLATE.safe_substitute(
        movieid=movie_meta['id'],
        title=capital2lower(movie_meta['title']),
        author=capital2lower(movie_meta['author']),
    )
    filename = filename_m4a(movie_meta['title'])

    tasks = [
        download_audio_by_movie_meta(movie_meta),
        download_thumbnail_by_movie_meta(movie_meta)
    ]
    results = await asyncio.gather(*tasks)

    audio = results[0]
    thumbnail = results[1]
    movie_meta['thumbnail_path'] = thumbnail

    if not audio.exists():
        return [], f'🔴 Download. Audio file does not exist.'

    duration_seconds = movie_meta['split_duration_minutes'] * 60

    scheme = get_split_audio_scheme(
        source_audio_length=movie_meta['duration'],
        duration_seconds=duration_seconds,
        delta_seconds=config.AUDIO_SPLIT_DELTA_SECONDS,
        magic_tail=True,
        threshold_seconds=movie_meta['threshold_seconds']
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

    logger.info(f'🌈 Scheme: {scheme}')

    tasks = [
        image_compress_and_resize(movie_meta['thumbnail_path']),
        make_split_audio(
            audio_path=audio,
            audio_duration=movie_meta['duration'],
            output_folder=movie_meta['store'],
            scheme=scheme
        ),
        get_mp4object(audio)
    ]
    results = await asyncio.gather(*tasks)
    movie_meta['thumbnail_path'] = results[0]
    audios = results[1]
    mp4obj = results[2]
    logger.info(f'🍫 Audios: {audios}')

    if not movie_meta['description'] and mp4obj.get('desc'):
        movie_meta['description'] = mp4obj.get('desc')

    timecodes, _err_timecodes = await get_timecodes(scheme, movie_meta['description'])
    logger.info(f'🍡 Timecodes: {timecodes}')

    audio_items = []

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
            'audio_filename': filename if len(audios) == 1 else f'p{idx}_of{len(audios)} {filename}',
            'duration': audio_part['duration'],
            'thumbnail_path': movie_meta['thumbnail_path'],
            'caption': caption if len(caption) < config.TG_CAPTION_MAX_LONG else caption[:config.TG_CAPTION_MAX_LONG - 32] + config.CAPTION_TRIMMED_END_TEXT,
        }
        audio_items.append(audio_data)

    return audio_items, ''
