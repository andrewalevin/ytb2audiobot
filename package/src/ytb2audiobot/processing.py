import asyncio
import math
from datetime import timedelta
from string import Template

from audio2splitted.audio2splitted import DURATION_MINUTES_MIN, DURATION_MINUTES_MAX, get_split_audio_scheme, \
    make_split_audio


from ytb2audiobot import config
from ytb2audiobot.subtitles import get_subtitles
from ytb2audiobot.mp4mutagen import get_mp4object
from ytb2audiobot.thumbnail import image_compress_and_resize
from ytb2audiobot.timecodes import get_timecodes, filter_timestamp_format
from ytb2audiobot.thumbnail import download_thumbnail_by_movie_meta
from ytb2audiobot.audio import download_audio_by_movie_meta
from ytb2audiobot.utils import capital2lower, filename_m4a, remove_m4a_file_if_exists, get_file_size

keep_data_files = False


async def processing_commands(command: dict, movie_meta: dict):
    context = dict()
    context['warning'] = ''
    context['error'] = ''

    if command.get('name') == 'split':
        if not command.get('params'):
            context['error'] = '🟥️ Split. No params of split command. Set param of minutes to split'
            return context
        param = command.get('params')[0]
        if not param.isnumeric():
            context['error'] = '🟥️ Split. Param if split [not param.isnumeric()]'
            return context

        param = int(param)
        if param < DURATION_MINUTES_MIN or DURATION_MINUTES_MAX < param:
            context['error'] = (f'🟥️ Split. Param if split = {param} '
                                f'is out of [{DURATION_MINUTES_MIN}, {DURATION_MINUTES_MAX}]')
            return context

        # Make split with Default split
        movie_meta['threshold_seconds'] = 1
        movie_meta['split_duration_minutes'] = param

    elif command.get('name') == 'bitrate':
        if not command.get('params'):
            context['error'] = '🟥️ Bitrate. No essential param of bitrate.'
            return context

        param = command.get('params')[0]
        if not param.isnumeric():
            context['error'] = '🟥️ Bitrate. Essential param is not numeric'
            return context

        param = int(param)
        if param < config.AUDIO_BITRATE_MIN or config.AUDIO_BITRATE_MAX < param:
            context['error'] = (f'🟥️ Bitrate. Param {param} is out of [{config.AUDIO_BITRATE_MIN},'
                                f' ... , {config.AUDIO_BITRATE_MAX}]')
            return context

        await remove_m4a_file_if_exists(movie_meta.get('id'), movie_meta['store'])

        movie_meta['ytdlprewriteoptions'] = movie_meta.get('ytdlprewriteoptions').replace('48k', f'{param}k')
        movie_meta['additional_meta_text'] = f'\n{param}k bitrate'

    caption_head = config.CAPTION_HEAD_TEMPLATE.safe_substitute(
        movieid=movie_meta['id'],
        title=capital2lower(movie_meta['title']),
        author=capital2lower(movie_meta['author']),
    )
    filename = filename_m4a(movie_meta['title'])

    if command.get('name') == 'subtitles':
        param = ''
        if command.get('params'):
            params = command.get('params')
            param = ' '.join(params)

        text, _err = await get_subtitles(movie_meta.get('id'), param)
        if _err:
            context['error'] = f'🟥️ Subtitles. Internal error: {_err}'
            return context

        caption = Template(caption_head).safe_substitute(partition='', timecodes='', duration='', additional='')
        caption = caption.replace('\n\n\n', '\n')
        caption = caption.replace('[]', '')

        caption_subtitles = '📝 Subtitles'
        if param:
            caption_subtitles += f' 🔎 Search [{param}]'
        caption = caption.strip() + '\n\n' + caption_subtitles

        context['subtitles'] = {
            'caption': caption,
            'text': text,
            'filename': 'subtitles-' + filename.replace('.m4a', '') + '-' + movie_meta.get('id') + '.txt'
        }

        return context

    tasks = [
        download_audio_by_movie_meta(movie_meta),
        download_thumbnail_by_movie_meta(movie_meta)
    ]
    results = await asyncio.gather(*tasks)

    audio = results[0]
    thumbnail = results[1]
    movie_meta['thumbnail_path'] = thumbnail

    if not audio.exists():
        context['error'] = f'🔴 Download. Audio file does not exist.'
        return context

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

    print('🌈 Scheme: ', scheme, '\n')

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
    print('🍫 Audios: ', audios, '\n')

    if not movie_meta['description'] and mp4obj.get('desc'):
        movie_meta['description'] = mp4obj.get('desc')

    timecodes, _err_timecodes = await get_timecodes(scheme, movie_meta['description'])
    print('🍡 Timecodes: ', timecodes, '\n')

    context['audio_datas'] = []

    context['duration'] = movie_meta['duration']

    for idx, audio_part in enumerate(audios, start=1):
        print('💜 Idx: ', idx, 'part: ', audio_part)

        # Add additional seconds to total duration to disable timecode link
        caption = Template(caption_head).safe_substitute(
            partition='' if len(audios) == 1 else f'[Part {idx} of {len(audios)}]',
            timecodes=timecodes[idx-1],
            duration=filter_timestamp_format(timedelta(seconds=audio_part.get('duration')+1)),
            additional=movie_meta['additional_meta_text']
        )

        audio_data = {
            'chat_id': command.get('sender_id'),
            'reply_to_message_id': command.get('message_id') if idx == 1 else None,
            'audio_path': audio_part['path'],
            'audio_filename': filename if len(audios) == 1 else f'p{idx}_of{len(audios)} {filename}',
            'duration': audio_part['duration'],
            'thumbnail_path': movie_meta['thumbnail_path'],
            'caption': caption if len(caption) < config.TG_CAPTION_MAX_LONG else caption[:config.TG_CAPTION_MAX_LONG - 32] + config.CAPTION_TRIMMED_END_TEXT,
        }
        context['audio_datas'].append(audio_data)

    return context
