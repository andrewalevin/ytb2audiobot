import asyncio
import inspect
import math
import os
import pathlib
from string import Template

import yt_dlp
from aiogram import Bot
from aiogram.types import FSInputFile, BufferedInputFile, Message
from ytbtimecodes.timecodes import extract_timecodes, timedelta_from_seconds, standardize_time_format

from ytb2audiobot import config
from ytb2audiobot.audio_mixer import mix_audio_m4a
from ytb2audiobot.config import get_yt_dlp_options
from ytb2audiobot.segmentation import segments_verification, get_segments_by_duration, \
    add_paddings_to_segments, make_magic_tail, get_segments_by_timecodes_from_dict, rebalance_segments_long_timecodes
from ytb2audiobot.subtitles import get_subtitles_here, highlight_words_file_text
from ytb2audiobot.logger import logger
from ytb2audiobot.download import download_thumbnail_from_download, \
    make_split_audio_second, get_chapters, get_timecodes_dict, filter_timecodes_within_bounds, \
    get_timecodes_formatted_text, download_audio_from_download, empty
from ytb2audiobot.translate import make_translate
from ytb2audiobot.utils import seconds2humanview, capital2lower, \
    predict_downloading_time, get_data_dir, get_big_youtube_move_id, trim_caption_to_telegram_send, get_file_size, \
    get_short_youtube_url

DEBUG = False if os.getenv(config.ENV_NAME_DEBUG_MODE, 'false').lower() != 'true' else True

REBALANCE_SEGMENTS_TO_FIT_TIMECODES = False if os.getenv(config.ENV_REBALANCE_SEGMENTS_TO_FIT_TIMECODES, 'false').lower() != 'true' else True
# todo
logger.info(f'🎆 REBALANCE_SEGMENTS_TO_FIT_TIMECODES: {REBALANCE_SEGMENTS_TO_FIT_TIMECODES}')

async def telegram_send_large_text(send_func, text, max_size=4096, delay=0.5, **kwargs):
    """
    Sends a large text message by splitting it into chunks if it exceeds `max_size`,
    with a delay between each chunk to avoid hitting Telegram API limits.

    Args:
        send_func (callable): The function to send the text (e.g., bot.send_message or message.edit_text).
        text (str): The text to send.
        max_size (int): Maximum size of a single message (default is 4096 for Telegram).
        delay (float): Delay in seconds between sending chunks to avoid API flood (default is 0.5).
        **kwargs: Additional arguments to pass to the send function (e.g., chat_id, parse_mode).
    """
    # Split text into chunks
    text_chunks = [text[i:i + max_size] for i in range(0, len(text), max_size)]

    # Send the first chunk
    await send_func(text=text_chunks[0], **kwargs)

    # Send additional chunks (if any), with delay
    for chunk in text_chunks[1:]:
        await asyncio.sleep(delay)  # Delay to avoid flooding
        await send_func(text=chunk, **kwargs)


async def handle_error(e: Exception, info_message: Message, notice: str):
    text = f'❌ {notice}\n\n{e}'
    logger.error(text)
    await telegram_send_large_text(info_message, text)


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
        text = '⏳ Preparing...'
    ) if editable_message_id else await bot.send_message(
        chat_id=sender_id,
        reply_to_message_id=reply_message_id,
        text = '⏳ Preparing...')

    info_message = await info_message.edit_text('⏳ Fetching subtitles...')

    if not (movie_id := get_big_youtube_move_id(url)):
        await info_message.edit_text('❌ Unable to extract a valid YouTube movie ID from the provided URL.')
        return

    text = await get_subtitles_here(url, word)

    caption = f'✏️ Subtitles\n\n{get_short_youtube_url(movie_id)}'
    if word:
        caption += f'\n\n'
        caption += f'🔎 Search word: {word}' if text else '🔦 Nothing Found! 😉'

    if len(f'{caption}\n\n{text}') < config.TELEGRAM_MAX_MESSAGE_TEXT_SIZE:
        await bot.send_message(
            chat_id=sender_id,
            text=f'{caption}\n\n{text}',
            parse_mode='HTML')
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

    logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=inspect.currentframe().f_code.co_name))
    logger.debug(f'💹 Configurations have started: {configurations}')

    movie_id = get_big_youtube_move_id(message_text)
    if not movie_id:
        return

    # Inverted logic refactor
    info_message = await bot.edit_message_text(
        chat_id=sender_id,
        message_id=info_message_id,
        text='⏳ Preparing...'
    ) if info_message_id else await bot.send_message(
        chat_id=sender_id,
        text='⏳ Preparing...')

    ydl_opts = {
        'logtostderr': False,  # Avoids logging to stderr, logs to the logger instead
        'quiet': True,  # Suppresses default output,
        'nocheckcertificate': True,
        'no_warnings': True,
        'skip_download': True,}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            yt_info = ydl.extract_info(f"https://www.youtube.com/watch?v={movie_id}", download=False)
    except Exception as e:
        logger.error(f'❌ Unable to extract YT-DLP info. \n\n{e}')
        await info_message.edit_text('❌ Unable to extract YT-DLP info for this movie.')
        return

    if yt_info.get('is_live'):
        await info_message.edit_text('❌🎬💃 This movie is now live and unavailable for download. Please try again later.')
        return

    if not yt_info.get('title') or not yt_info.get('duration'):
        await info_message.edit_text('❌🎬💔 No title or duration information available for this video.')
        return

    if not yt_info.get('filesize_approx', ''):
        await info_message.edit_text('❌🛰 This movie is currently live, but it may be in the process of being updated. Please try again later.')
        return

    if not any(format_item.get('filesize') is not None for format_item in yt_info.get('formats', [])):
        await info_message.edit_text('❌🎬🤔 The audio file for this video is unavailable due to an unknown reason.')
        return

    action = configurations.get('action', '')
    
    if action == config.ACTION_NAME_TRANSLATE:
        language = yt_info.get('language', '')
        if language == 'ru':
            await info_message.edit_text(
                '🌎🚫 This movie is still in Russian. You can download its audio directly. '
                'Please provide its URL again:')
            return

        # todo time
        info_message = await info_message.edit_text('⏳🌎 Translation is starting. It may take some time...')

    else:
        predict_time = predict_downloading_time(yt_info.get('duration'))
        info_message = await info_message.edit_text(f'⏳ Downloading ~ {seconds2humanview(predict_time)}...')

    title = yt_info.get('title', '')
    description = yt_info.get('description', '')
    author = yt_info.get('uploader', '')
    duration = yt_info.get('duration')
    timecodes = extract_timecodes(description)

    timecodes_dict = get_timecodes_dict(timecodes)

    chapters = get_chapters(yt_info.get('chapters', []))

    timecodes_dict.update(chapters)

    # todo add depend on predict

    yt_dlp_options = get_yt_dlp_options()

    logger.debug(f'🈺 Action: {action}\n\n')
    logger.debug(f'🈴 yt-dlp options: {yt_dlp_options}\n\n')

    bitrate = '48k'

    if action == config.ACTION_NAME_BITRATE_CHANGE:
        new_bitrate = configurations.get('bitrate', '')
        if new_bitrate in config.BITRATES_VALUES:
            bitrate = new_bitrate
        yt_dlp_options = get_yt_dlp_options({'audio-quality': bitrate})

    data_dir = get_data_dir()
    audio_path = data_dir / f'{movie_id}-{bitrate}.m4a'
    thumbnail_path = data_dir / f'{movie_id}-thumbnail.jpg'
    audio_path_translate_original = data_dir / f'{movie_id}-transl-ru-{bitrate}-original.m4a'
    audio_path_translate_final = data_dir / f'{movie_id}-transl-ru-{bitrate}.m4a'

    if action == config.ACTION_NAME_SLICE:
        start_time = str(configurations.get('slice_start_time'))
        end_time = str(configurations.get('slice_end_time'))

        start_time_hhmmss = standardize_time_format(timedelta_from_seconds(start_time))
        end_time_hhmmss = standardize_time_format(timedelta_from_seconds(end_time))

        yt_dlp_options += f' --postprocessor-args \"-ss {start_time_hhmmss} -t {end_time_hhmmss}\"'

    logger.debug(f'🈴🈴 yt-dlp options: {yt_dlp_options}\n\n')

    # Run tasks with timeout
    async def handle_download():
        try:
            tasks = [
                asyncio.create_task(
                    download_audio_from_download(movie_id=movie_id, output_path=audio_path, options=yt_dlp_options)),
                asyncio.create_task(
                    download_thumbnail_from_download(movie_id=movie_id, output_path=thumbnail_path)),
                asyncio.create_task(
                    empty())
            ]

            if action == config.ACTION_NAME_TRANSLATE:
                # todo timeout
                tasks[2] = (asyncio.create_task(
                    make_translate(movie_id=movie_id, output_path=audio_path_translate_original, timeout=60*23)))

            result = await asyncio.wait_for(
                timeout=config.TASK_TIMEOUT_SECONDS,
                fut=asyncio.gather(*tasks))

            return result
        except asyncio.TimeoutError:
            logger.error(f'❌ TimeoutError occurred during download_processing().')
            await info_message.edit_text('❌ TimeoutError occurred during download_processing().')
            return None, None
        except Exception as e:
            logger.error(f'❌ Error occurred during download_processing().\n\n{e}')
            await info_message.edit_text('❌ Error occurred during download_processing().')
            return None, None

    audio_path, thumbnail_path, audio_path_translate_original = await handle_download()
    logger.debug(f'audio_path={audio_path}, thumbnail_pat={thumbnail_path}, audio_path_translate_original={audio_path_translate_original}')
    if audio_path is None:
        logger.error(f'❌ audio_path is None after downloading. Exiting.')
        await info_message.edit_text('❌ Error: audio_path is None after downloading. Exiting.')
        return

    audio_path = pathlib.Path(audio_path)
    if not audio_path.exists():
        logger.error(f'❌ audio_path does not exist after downloading. Exiting.')
        await info_message.edit_text('❌ Error: audio_path does not exist after downloading. Exiting.')
        return

    if thumbnail_path is not None:
        thumbnail_path = pathlib.Path(thumbnail_path)
        if not thumbnail_path.exists():
            thumbnail_path = None

    if action == config.ACTION_NAME_TRANSLATE:
        if audio_path_translate_original is None:
            logger.error(f'❌ audio_path_translate_original is None after downloading. Exiting.')
            await info_message.edit_text('❌ Error: audio_path_translate_original is None after downloading. Exiting.')
            return

        if configurations.get('overlay') == 0.0:
            audio_path = audio_path_translate_original
        else:
            audio_path_translate_final = await asyncio.wait_for(
                mix_audio_m4a(audio_path, audio_path_translate_original, audio_path_translate_final, configurations.get('overlay'), bitrate),
                timeout=config.TASK_TIMEOUT_SECONDS
            )

            if not audio_path_translate_final or not audio_path_translate_final.exists():
                logger.error(f'❌ audio_path_translate_final does not exist after downloading. Exiting.')
                await info_message.edit_text('❌ Error: audio_path_translate_final does not exist after downloading. Exiting.')
                return

            audio_path = audio_path_translate_final

    segments = [{'path': audio_path, 'start': 0, 'end': duration, 'title': ''}]

    if action == config.ACTION_NAME_SPLIT_BY_DURATION:
        split_duration_minutes = int(configurations.get('split_duration_minutes', 0))
        if split_duration_minutes > 0:
            segments = get_segments_by_duration(
                total_duration=duration,
                segment_duration=60 * split_duration_minutes)

    elif action == config.ACTION_NAME_SPLIT_BY_TIMECODES:
        segments = get_segments_by_timecodes_from_dict(timecodes=timecodes_dict, total_duration=duration)

    elif duration > config.SEGMENT_AUDIO_DURATION_SPLIT_THRESHOLD_SEC:
        segments = get_segments_by_duration(
            total_duration=duration,
            segment_duration=config.SEGMENT_AUDIO_DURATION_SEC)

    segments = add_paddings_to_segments(segments, config.SEGMENT_DUARITION_PADDING_SEC)

    audio_file_size = await get_file_size(audio_path)

    max_segment_duration = int(0.89 * duration * config.TELEGRAM_BOT_FILE_MAX_SIZE_BYTES / audio_file_size)

    segments = make_magic_tail(segments, max_segment_duration)

    segments = segments_verification(segments, max_segment_duration)


    # Make head before check rebalance
    caption_head = config.CAPTION_HEAD_TEMPLATE.safe_substitute(
        movieid=movie_id,
        title=capital2lower(title),
        author=capital2lower(author))

    caption_head_additional = ''

    if action == config.ACTION_NAME_SLICE:
        caption_head_additional += '\n\n'
        caption_head_additional += config.CAPTION_SLICE.substitute(
            start_time=standardize_time_format(timedelta_from_seconds(str(configurations.get('slice_start_time')))),
            end_time=standardize_time_format(timedelta_from_seconds(str(configurations.get('slice_end_time')))))

    if action == config.ACTION_NAME_TRANSLATE:
        caption_head = '🌎 Translation: \n' + caption_head

    # Check Rebalance by Timecodes
    if REBALANCE_SEGMENTS_TO_FIT_TIMECODES:
        segments = rebalance_segments_long_timecodes(
            segments,
            config.TG_CAPTION_MAX_LONG - len(caption_head),
            timecodes_dict,
            config.SEGMENT_AUDIO_DURATION_SEC)

        segments = add_paddings_to_segments(segments, config.SEGMENT_DUARITION_PADDING_SEC)

    if not segments:
        logger.error(f'❌ No audio segments found after processing. This could be an internal error.')
        await info_message.edit_text(f'❌ Error: No audio segments found after processing. This could be an internal error.')
        return

    try:
        segments = await make_split_audio_second(audio_path, segments)
    except Exception as e:
        logger.error(f'❌ Error occurred while splitting audio into segments: {e}')
        await info_message.edit_text(f'❌ Error: Failed to split audio into segments.')
    if not segments:
        logger.error(f'❌ No audio segments found after splitting.')
        await info_message.edit_text(f'❌ Error: No audio segments found after processing.')
        return

    await info_message.edit_text('⌛🚀 Uploading to Telegram...')

    for idx, segment in enumerate(segments):
        logger.info(f'💚 Uploading audio item: {segment.get("audio_path")}')
        start = segment.get('start')
        end = segment.get('end')
        filtered_timecodes_dict = filter_timecodes_within_bounds(
            timecodes=timecodes_dict, start_time=start + config.SEGMENT_DUARITION_PADDING_SEC, end_time=end - config.SEGMENT_DUARITION_PADDING_SEC - 1)
        timecodes_text = get_timecodes_formatted_text(filtered_timecodes_dict, start)

        if segment.get('title'):
            caption_head_additional += config.ADDITIONAL_CHAPTER_BLOCK.substitute(
                time_shift=standardize_time_format(timedelta_from_seconds(segment.get('start'))),
                title=segment.get('title'))
            timecodes_text = ''

        segment_duration = end - start
        caption = Template(caption_head).safe_substitute(
            partition='' if len(segments) == 1 else f'[Part {idx + 1} of {len(segments)}]',
            duration=standardize_time_format(timedelta_from_seconds(segment_duration)),
            timecodes=timecodes_text,
            additional=caption_head_additional)

        segment_path = pathlib.Path(segment.get('path'))

        # todo English filename EX https://www.youtube.com/watch?v=gYeyOZTgf2g
        fname_suffix = segment_path.name
        fname_prefix = '' if len(segments) == 1 else f'p{idx + 1}_of{len(segments)}-'
        fname_title_size = config.TG_MAX_FILENAME_LEN - len(fname_prefix) - len(fname_suffix)
        fname_title = title[:fname_title_size]+'-' if fname_title_size > 6 else ''

        await bot.send_audio(
            chat_id=sender_id,
            audio=FSInputFile(
                path=segment.get('path'),
                filename=fname_prefix + fname_title + fname_suffix),
            duration=segment_duration + 1,
            thumbnail=FSInputFile(path=thumbnail_path) if thumbnail_path is not None else None,
            caption=caption if len(caption) < config.TG_CAPTION_MAX_LONG else trim_caption_to_telegram_send(caption),
            parse_mode='HTML')

        # Sleep to avoid flood in Telegram API
        if idx < len(segments) - 1:
            sleep_duration = math.floor(8 * math.log10(len(segments) + 1))
            logger.debug(f'💤😴 Sleeping for {sleep_duration} seconds.')
            await asyncio.sleep(sleep_duration)

    await info_message.delete()
    logger.info('💚💚 Done!')
