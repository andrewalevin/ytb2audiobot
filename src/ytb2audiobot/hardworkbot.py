import asyncio
import math
import os
from string import Template

import yt_dlp
from aiogram import Bot
from aiogram.types import Message, FSInputFile, BufferedInputFile
from ytbtimecodes.timecodes import extract_timecodes, timedelta_from_seconds, standardize_time_format, \
    filter_timecodes_within_bounds

from ytb2audiobot import  config
from ytb2audiobot.config import get_thumbnail_path
from ytb2audiobot.subtitles import get_subtitles_here
from ytb2audiobot.logger import logger
from ytb2audiobot.download import download_processing, get_timecodes_formatted_text
from ytb2audiobot.utils import get_hash, write_file, seconds2humanview, capital2lower, get_filename_m4a, \
    predict_downloading_time, get_data_dir, get_big_youtube_move_id

autodownload_chat_ids_hashed = dict()
autodownload_file_hash = ''


def check_chat_id_in_dict(chat_id):
    if get_hash_salted(chat_id) in autodownload_chat_ids_hashed:
        return True
    return False


def get_hash_salted(data):
    salt = os.environ.get('SALT', '')
    return get_hash(get_hash(data) + salt)


async def periodically_autodownload_chat_ids_save(params):
    data_to_write = '\n'.join(sorted(autodownload_chat_ids_hashed.keys())).strip()

    data_hash = get_hash(data_to_write)

    global autodownload_file_hash
    if autodownload_file_hash != data_hash:
        await write_file(config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH, data_to_write)
        autodownload_file_hash = data_hash


def trim_caption(caption):
    return caption[:config.TG_CAPTION_MAX_LONG - 32] + config.CAPTION_TRIMMED_END_TEXT


async def job_downloading(
        bot: Bot,
        sender_id: int,
        message_id: id,
        movie_id: str,
        info_message_id: int = 0
):
    logger.info(f'🐝 Making job_downloading(): sender_id={sender_id}, message_id={message_id}, movie_id={movie_id}')

    # Inverted logic refactor
    info_message = await bot.send_message(
        chat_id=sender_id,
        reply_to_message_id=message_id,
        text='⏳ Preparing ... '
    ) if not info_message_id else await bot.edit_message_text(
        chat_id=sender_id,
        message_id=info_message_id,
        text='⏳ Preparing ... '
    )

    # movie_meta = await get_movie_meta(movie_id)

    ydl_opts = {
        'logtostderr': False,  # Avoids logging to stderr, logs to the logger instead
        'quiet': True,  # Suppresses default output,
        'nocheckcertificate': True,
        'no_warnings': True,
    }

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

    if not any(format_item.get('filesize') is not None for format_item in yt_info.get('formats', [])):
        await info_message.edit_text(text='❌🎬🤔 Audiо file for this video is unavailable for an unknown reason.')
        return

    if not yt_info.get('title') or not yt_info.get('duration'):
        await info_message.edit_text(text='❌🎬💔 No title or duration info of this video.')
        return

    predict_time = predict_downloading_time(yt_info.get('duration'))
    info_message = await info_message.edit_text(text=f'⏳ Downloading ~ {seconds2humanview(predict_time)} ... ')

    data_dir = get_data_dir()
    title = yt_info.get('title')
    description = yt_info.get('description')
    duration = yt_info.get('duration')
    author = yt_info.get('uploader')

    # todo add depend on predict
    try:
        audio_items = await asyncio.wait_for(
            asyncio.create_task(
                download_processing(
                    movie_id=movie_id,
                    data_dir=data_dir,
                    duration=duration,
                    ytdlprewriteoptions=config.YT_DLP_OPTIONS_DEFAULT)),
            timeout=config.TASK_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        await info_message.edit_text(text='🚫 Download processing timed out. Please try again later.')
        return
    except Exception as e:
        logger.error(f'🚫 Error during download_processing(): {e}')
        await info_message.edit_text(text=f'🚫 Error during download_processing(): \n\n{str(e)}')
        return

    if not audio_items:
        await info_message.edit_text(text='💔 Nothing to send you after downloading. Sorry :(')
        return

    thumbnail_path = get_thumbnail_path(data_dir, movie_id)
    try:
        timecodes = extract_timecodes(description)
    except Exception as e:
        timecodes = []

    filename = get_filename_m4a(title)
    caption_head = config.CAPTION_HEAD_TEMPLATE.safe_substitute(
        movieid=movie_id,
        title=capital2lower(title),
        author=capital2lower(author),
    )

    await info_message.edit_text('⌛🚀️ Uploading to Telegram ... ')
    for idx, item in enumerate(audio_items):
        logger.info(f'💚 Uploading audio item: ' + str(item.get('audio_path')))

        boundaries_timecodes = filter_timecodes_within_bounds(timecodes, item.get('start'), item.get('end'))
        print('boundaries_timecodes: ')
        print(boundaries_timecodes)
        print()

        timecodes_text = get_timecodes_formatted_text(boundaries_timecodes)

        caption = Template(caption_head).safe_substitute(
            partition='' if len(audio_items) == 1 else f'[Part {idx+1} of {len(audio_items)}]',
            duration=standardize_time_format(timedelta_from_seconds(item.get('duration') + 1)),
            timecodes=timecodes_text,
            additional=''
        )

        await bot.send_audio(
            chat_id=sender_id,
            reply_to_message_id=message_id,
            audio=FSInputFile(
                path=item.get('audio_path'),
                filename=filename if len(audio_items) == 1 else f'p{idx+1}_of{len(audio_items)} {filename}'),
            duration=item.get('duration'),
            thumbnail=FSInputFile(path=thumbnail_path) if thumbnail_path.exists() else None,
            caption=caption if len(caption) < config.TG_CAPTION_MAX_LONG else trim_caption(caption),
            parse_mode='HTML'
        )

        # Sleep to avoid flood in Telegram API
        if idx < len(audio_items) - 1:
            sleep_duration = math.floor(8 * math.log10(len(audio_items) + 1))
            logger.debug(f'💤😴 Sleep sleep_duration={sleep_duration}')
            await asyncio.sleep(sleep_duration)

    await info_message.delete()
    logger.info(f'💚💚 Done! ')


async def direct_message_and_post_work(bot: Bot, message: Message):

    logger.debug('💈 Handler. Direct Message and Post')

    sender_id = (
        message.from_user.id if message.from_user else
        message.sender_chat.id if message.sender_chat else
        None
    )

    # Return if sender_id is not found or if the message has no text
    if not sender_id or not message.text:
        return

    movie_id = get_big_youtube_move_id(message.text)
    logger.debug(f'🔫 movie_id={movie_id}')

    if not movie_id:
        # todo
        return

    await job_downloading(
        bot=bot,
        sender_id=sender_id,
        message_id=message.message_id,
        movie_id=movie_id)

    # todo LATER
    if False:
        if check_chat_id_in_dict(sender_id):
            await job_downloading(
                sender_id=sender_id,
                message_id=message_id,
                movie_id=movie_id)
            return

        # extra For Button in Channels
        if sender_type != 'user':
            callback_data = ':_:'.join([
                'download',
                str('id'),
                str('message_id'),
                str('sender_id')])

            post_status = await bot.send_message(
                chat_id=sender_id,
                reply_to_message_id=message.message_id,
                text=f'Choose one of these options. \nExit in seconds: {config.CALLBACK_WAIT_TIMEOUT}',
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text='📣 Just Download️', callback_data=callback_data), ], ], ))

            # Wait timeout pushing button Just Download
            await asyncio.sleep(contextbot.get('callback_button_timeout_seconds'))

            # After timeout clear key from storage if button pressed. Otherwies
            # todo refactor
            if callback_data in storage_callback_keys:
                del storage_callback_keys[callback_data]
            else:
                await post_status.delete()
            return


async def autodownload_work(bot: Bot, message: Message):
    hash_salted = get_hash_salted(message.sender_chat.id)
    if check_chat_id_in_dict(message.sender_chat.id):
        del autodownload_chat_ids_hashed[hash_salted]
        await message.reply(f'Remove from Dict: {hash_salted}')
    else:
        autodownload_chat_ids_hashed[hash_salted] = None
        await message.reply(f'Add to Dict: {hash_salted}')


async def make_subtitles(bot: Bot, sender_id, url: str, word: str = ''):
    text = await get_subtitles_here(url, word)

    text = '🔦 Nothing Found! 😉' if word else 'No subtitles! 😉' if not text else text
    caption = f"📝 Subtitles{f': 🔎 Search word:[{word}]' if word else ''}"

    if len(f'{caption}\n\n{text}') <= config.TELEGRAM_MAX_MESSAGE_TEXT_SIZE:
        await bot.send_message(
            chat_id=sender_id,
            text=f'{caption}\n\n{text}',
            parse_mode='HTML',
            disable_web_page_preview=False)
    else:
        text = (text.replace('<b><s><b><s>', ' 🔹 ')
                .replace(f'{word}</s></b></s></b>', f'{word.upper()}')
                .replace('  ', ' '))
        await bot.send_document(
            chat_id=sender_id,
            caption=caption,
            parse_mode='HTML',
            document=BufferedInputFile(filename='subtitles.txt', file=text.encode('utf-8'), ))

