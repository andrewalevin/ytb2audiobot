import asyncio
import math
import os
import pathlib
from string import Template

import yt_dlp
from aiogram import Bot
from aiogram.types import FSInputFile, BufferedInputFile
from ytbtimecodes.timecodes import extract_timecodes, timedelta_from_seconds, standardize_time_format

from ytb2audiobot import config
from ytb2audiobot.config import get_yt_dlp_options
from ytb2audiobot.segmentation import segments_verification, get_segments_by_duration, \
    add_paddings_to_segments, make_magic_tail, get_segments_by_timecodes_from_dict
from ytb2audiobot.subtitles import get_subtitles_here, highlight_words_file_text
from ytb2audiobot.logger import logger
from ytb2audiobot.download import download_thumbnail_from_download, \
    make_split_audio_second, get_chapters, get_timecodes_dict, filter_timecodes_within_bounds, \
    get_timecodes_formatted_text, download_audio_from_download
from ytb2audiobot.translate import make_translate
from ytb2audiobot.utils import seconds2humanview, capital2lower, \
    predict_downloading_time, get_data_dir, get_big_youtube_move_id, trim_caption_to_telegram_send, get_file_size, \
    truncate_filename_for_telegram, get_short_youtube_url

DEBUG = False if os.getenv(config.ENV_NAME_DEBUG_MODE, 'false').lower() != 'true' else True


async def make_subtitles(
        bot: Bot,
        sender_id: int,
        url: str = '',
        word: str = '',
        reply_message_id: int | None = None,
        editable_message_id: int | None = None):
    info_message = await bot.edit_message_text(
        chat_id=sender_id,
        message_id=editable_message_id,
        text='⏳ Getting ready …'
    ) if editable_message_id else await bot.send_message(
        chat_id=sender_id,
        reply_to_message_id=reply_message_id,
        text='⏳ Getting ready …')

    info_message = await info_message.edit_text(text='⏳ Fetching subtitles …')

    if not (movie_id := get_big_youtube_move_id(url)):
        await info_message.edit_text('🔴 Can t get valid youtube movie id out of your url')
        return

    print(f'🐸 WORD SEARCH - url={url}, word={word}')
    text = await get_subtitles_here(url, word)
    print('RESULT: ', text)
    print()

    caption = f'✏️ Subtitles\n\n{get_short_youtube_url(movie_id)}\n\n '

    if word:
        caption += f'🔎 Search word: {word}\n\n' if text else '🔦 Nothing Found! 😉\n\n'

    if len(caption + text) < config.TELEGRAM_MAX_MESSAGE_TEXT_SIZE:
        await bot.send_message(
            chat_id=sender_id,
            text=f'{caption}{text}',
            parse_mode='HTML')
        await info_message.delete()
    else:
        text = highlight_words_file_text(text, word)
        await bot.send_document(
            chat_id=sender_id,
            caption=caption,
            document=BufferedInputFile(
                filename=f'subtitles-{movie_id}.txt',
                file=text.encode('utf-8')))
        await info_message.delete()


async def job_downloading(
        bot: Bot,
        sender_id: int,
        reply_to_message_id: int | None = None,
        message_text: str = '',
        info_message_id: int | None = None,
        configurations=None):
    if configurations is None:
        configurations = {}

    logger.debug(f'💹 Options: {configurations}')

    movie_id = get_big_youtube_move_id(message_text)
    if not movie_id:
        return

    # Inverted logic refactor
    info_message = await bot.edit_message_text(
        chat_id=sender_id,
        message_id=info_message_id,
        text='⏳ Getting ready …'
    ) if info_message_id else await bot.send_message(
        chat_id=sender_id,
        text='⏳ Getting ready …')

    ydl_opts = {
        'logtostderr': False,  # Avoids logging to stderr, logs to the logger instead
        'quiet': True,  # Suppresses default output,
        'nocheckcertificate': True,
        'no_warnings': True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            yt_info = ydl.extract_info(f"https://www.youtube.com/watch?v={movie_id}", download=False)
    except Exception as e:
        logger.error(f'🍅 Cant Extract YT_DLP info. \n{e}')
        await info_message.edit_text(text=f'🍅 Cant Extract YT_DLP info. \n{e}')
        return

    if yt_info.get('is_live'):
        await info_message.edit_text(
            text='❌🎬💃 This movie video is now live and unavailable for download. Please try again later')
        return

    if not yt_info.get('title') or not yt_info.get('duration'):
        await info_message.edit_text(text='❌🎬💔 No title or duration info of this video.')
        return

    if not yt_info.get('filesize_approx', ''):
        await info_message.edit_text(
            text='❌🛰 This movie video is now live but perhapse in processes of changing. Try again later')
        return

    if not any(format_item.get('filesize') is not None for format_item in yt_info.get('formats', [])):
        await info_message.edit_text(
            text='❌🎬🤔 Audio file for this video is unavailable for an unknown reason.')
        return

    action = configurations.get('action', '')
    
    if action == config.ACTION_NAME_TRANSLATE:
        language = yt_info.get('language', '')
        if language == 'ru':
            await info_message.edit_text(
                text=f'🌎🚫 This movie is still in Russian. You can download its audio directly. '
                     f'Please give its URL again: ')
            return
        info_message = await info_message.edit_text(text=f'⏳ Translation starting. It could takes some time ... ')

    else:
        predict_time = predict_downloading_time(yt_info.get('duration'))
        info_message = await info_message.edit_text(text=f'⏳ Downloading ~ {seconds2humanview(predict_time)} ... ')

    data_dir = get_data_dir()
    title = yt_info.get('title', '')
    description = yt_info.get('description', '')
    author = yt_info.get('uploader', '')
    duration = yt_info.get('duration')
    timecodes = extract_timecodes(description)

    timecodes_dict = get_timecodes_dict(timecodes)

    chapters = get_chapters(yt_info.get('chapters', []))

    timecodes_dict.update(chapters)

    # todo add depend on predict

    thumbnail_path = config.get_thumbnail_path(data_dir, movie_id)

    yt_dlp_options = get_yt_dlp_options()

    logger.debug(f'🈺 action = {action}\n\n')
    logger.debug(f'🈴 yt_dlp_options = {yt_dlp_options}\n\n')

    bitrate = '48k'

    if action == config.ACTION_NAME_BITRATE_CHANGE:
        new_bitrate = configurations.get('bitrate', '')
        if new_bitrate in config.BITRATES_VALUES:
            bitrate = new_bitrate
        yt_dlp_options = get_yt_dlp_options({'audio-quality': bitrate})

    if action == config.ACTION_NAME_SLICE:
        start_time = str(configurations.get('slice_start_time'))
        end_time = str(configurations.get('slice_end_time'))

        start_time_hhmmss = standardize_time_format(timedelta_from_seconds(start_time))
        end_time_hhmmss = standardize_time_format(timedelta_from_seconds(end_time))

        yt_dlp_options += f' --postprocessor-args \"-ss {start_time_hhmmss} -t {end_time_hhmmss}\"'
        print(f'🍰 Slice yt_dlp_options = {yt_dlp_options}')

    audio_filename = config.AUDIO_FILENAME_TEMPLATE.substitute(
        movie_id=movie_id,
        bitrate=f'-{bitrate}',
        extension='.m4a')
    audio_path = data_dir.joinpath(audio_filename)
    thumbnail_filename = config.THUMBNAIL_FILENAME_TEMPLATE.substitute(
        movie_id=movie_id,
        extension='.jpg')
    thumbnail_path = audio_path.parent.joinpath(thumbnail_filename)

    logger.debug(f'🈴🈴 yt_dlp_options = {yt_dlp_options}\n\n')

    # Run tasks with timeout
    async def handle_download():
        try:
            func_main_down = download_audio_from_download(
                movie_id=movie_id, output_path=audio_path, options=yt_dlp_options)

            if action == config.ACTION_NAME_TRANSLATE:
                func_main_down = make_translate(
                    movie_id=movie_id,
                    output_path=audio_path,
                    timeout=60*23)

            result = await asyncio.wait_for(
                timeout=config.TASK_TIMEOUT_SECONDS,
                fut=asyncio.gather(
                    asyncio.create_task(
                       func_main_down),
                    asyncio.create_task(
                        download_thumbnail_from_download(
                            movie_id=movie_id, output_path=thumbnail_path))))
            return result
        except asyncio.TimeoutError:
            await info_message.edit_text(text='🚫 Download processing timed out. Please try again later.')
            return None, None
        except Exception as e:
            logger.error(f'🚫 Error during download_processing(): {e}')
            await info_message.edit_text(text=f'🚫 Error during download_processing(): \n\n{str(e)}')
            return None, None

    audio_path, thumbnail_path = await handle_download()
    if audio_path is None:
        return []

    audio_path = pathlib.Path(audio_path)

    if not audio_path.exists():
        return []

    if thumbnail_path is not None:
        thumbnail_path = pathlib.Path(thumbnail_path)

    segments = [{'path': audio_path, 'start': 0, 'end': duration, 'title': ''}]

    _THRESHOLD_SPLIT_MIN = 101
    _SEGMENT_DURATION = 39

    if action == config.ACTION_NAME_SPLIT_BY_DURATION:
        split_duration_minutes = int(configurations.get('split_duration_minutes', 0))
        if split_duration_minutes > 0:
            segments = get_segments_by_duration(
                total_duration=duration,
                segment_duration=60 * split_duration_minutes)

    elif action == config.ACTION_NAME_SPLIT_BY_TIMECODES:
        segments = get_segments_by_timecodes_from_dict(timecodes=timecodes_dict, total_duration=duration)

    elif duration > 60 * _THRESHOLD_SPLIT_MIN:
        segments = get_segments_by_duration(
            total_duration=duration,
            segment_duration=60 * _SEGMENT_DURATION)

    print(f'🌈 Segments:: {segments}')
    print()

    segments = add_paddings_to_segments(segments, config.SEGMENTS_PADDING_SEC)
    print(f'🌈 After Padding Segments:: {segments}')
    print()

    audio_file_size = await get_file_size(audio_path)

    max_segment_duration = int(0.89 * duration * config.TELEGRAM_BOT_FILE_MAX_SIZE_BYTES / audio_file_size)

    segments = make_magic_tail(segments, max_segment_duration)

    segments = segments_verification(segments, max_segment_duration)

    print('🌈🌈 segments_audio After Verification: ', segments)

    if not segments:
        await info_message.edit_text(text='💔 Nothing to send you after downloading. Sorry :(')
        return

    try:
        segments = await make_split_audio_second(audio_path, segments)
    except Exception as e:
        print('Error:', e)
        # logger.error(f'💔 Error with Audio Split \n\n{e}')
        # await info_message.edit_text(text=f'💔 Error with Audio Split \n\n{e}')
        return

    if not segments:
        await info_message.edit_text(text='💔 Nothing to send you after audio split. Sorry :(')
        return

    caption_head = config.CAPTION_HEAD_TEMPLATE.safe_substitute(
        movieid=movie_id,
        title=capital2lower(title),
        author=capital2lower(author))

    additional_caption_text = ''

    if action == config.ACTION_NAME_SLICE:
        start_time = str(configurations.get('slice_start_time'))
        end_time = str(configurations.get('slice_end_time'))

        start_time_hhmmss = standardize_time_format(timedelta_from_seconds(start_time))
        end_time_hhmmss = standardize_time_format(timedelta_from_seconds(end_time))

        additional_caption_text += f'\n\n{config.CAPTION_SLICE.substitute(
            start_time=start_time_hhmmss, end_time=end_time_hhmmss)}'

    if action == config.ACTION_NAME_TRANSLATE:
        caption_head = '🌎 Translation: \n' + caption_head

    await info_message.edit_text('⌛🚀️ Uploading to Telegram ... ')

    for idx, segment in enumerate(segments):
        logger.info(f'💚 Uploading audio item: ' + str(segment.get('audio_path')))
        start = segment.get('start')
        end = segment.get('end')
        filtered_timecodes_dict = filter_timecodes_within_bounds(
            timecodes=timecodes_dict, start_time=start + config.SEGMENTS_PADDING_SEC, end_time=end - config.SEGMENTS_PADDING_SEC -1)
        timecodes_text = get_timecodes_formatted_text(filtered_timecodes_dict, start)

        if segment.get('title'):
            additional_caption_text += config.ADDITIONAL_CHAPTER_BLOCK.substitute(
                time_shift=standardize_time_format(timedelta_from_seconds(segment.get('start'))),
                title=segment.get('title'))
            timecodes_text = ''

        segment_duration = end - start
        caption = Template(caption_head).safe_substitute(
            partition='' if len(segments) == 1 else f'[Part {idx + 1} of {len(segments)}]',
            duration=standardize_time_format(timedelta_from_seconds(segment_duration)),
            timecodes=timecodes_text,
            additional=additional_caption_text)

        # todo English filename EX https://www.youtube.com/watch?v=gYeyOZTgf2g
        audio_filename_for_telegram = f'{title}-' + pathlib.Path(segment.get('path')).name
        _filename = audio_filename_for_telegram if len(segments) == 1 else f'p{idx + 1}_of{len(segments)} {audio_filename_for_telegram}'

        await bot.send_audio(
            chat_id=sender_id,
            audio=FSInputFile(
                path=segment.get('path'),
                filename=truncate_filename_for_telegram(_filename)),
            duration=segment_duration,
            thumbnail=FSInputFile(path=thumbnail_path) if thumbnail_path is not None else None,
            caption=caption if len(caption) < config.TG_CAPTION_MAX_LONG else trim_caption_to_telegram_send(caption),
            parse_mode='HTML')

        # Sleep to avoid flood in Telegram API
        if idx < len(segments) - 1:
            sleep_duration = math.floor(8 * math.log10(len(segments) + 1))
            logger.debug(f'💤😴 Sleep sleep_duration={sleep_duration}')
            await asyncio.sleep(sleep_duration)

    await info_message.delete()
    logger.info(f'💚💚 Done! ')
