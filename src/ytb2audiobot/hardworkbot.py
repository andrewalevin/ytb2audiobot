import asyncio
import math
import os

import yt_dlp
from aiogram import Bot
from aiogram.types import Message, FSInputFile

from ytb2audiobot import  config
from ytb2audiobot.commands import get_big_youtube_move_id
from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.logger import logger
from ytb2audiobot.predictor import predict_downloading_time
from ytb2audiobot.processing import download_processing
from ytb2audiobot.utils import get_hash, write_file, seconds2humanview, tabulation2text, pprint_format

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
        return {}

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
    logger.debug(f'⏰ Predict time: {predict_time}')

    info_message = await info_message.edit_text(text=f'⏳ Downloading ~ {seconds2humanview(predict_time)} ... ')

    # todo refactor Movie meta

    movie_meta = config.DEFAULT_MOVIE_META.copy()
    movie_meta['id'] = movie_id
    movie_meta['store'] = get_data_dir()

    mapping = {
        'title': 'title',
        'description': 'description',
        'uploader': 'author',
        'thumbnail': 'thumbnail_url',
        'duration': 'duration'
    }

    for yt_key, meta_key in mapping.items():
        if yt_info.get(yt_key):
            movie_meta[meta_key] = yt_info.get(yt_key)

    logger.debug(f'🚦 Movie meta: \n{tabulation2text(pprint_format(movie_meta))}')

    # todo add depend on predict
    try:
        audio_items, err = await asyncio.wait_for(
            asyncio.create_task(download_processing(movie_meta)),
            timeout=config.TASK_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        await info_message.edit_text(text='🚫 Download processing timed out. Please try again later.')
        return
    except Exception as e:
        await info_message.edit_text(text=f'🚫 Error during download_processing(): \n\n{str(e)}')
        return

    if err:
        await info_message.edit_text(text=f'🚫 Error during download_processing(): \n\n{str(err)}')
        return

    if not audio_items:
        await info_message.edit_text(text='💔 Nothing to send you after downloading. Sorry :(')
        return

    await info_message.edit_text('⌛🚀️ Uploading to Telegram ... ')

    for idx, item in enumerate(audio_items):
        logger.info(f'💚 Uploading audio item: ' + str(item.get('audio_path')))
        await bot.send_audio(
            chat_id=sender_id,
            reply_to_message_id=message_id,
            audio=FSInputFile(path=item.get('audio_path'), filename=item.get('audio_filename')),
            duration=item.get('duration'),
            thumbnail=FSInputFile(path=item.get('thumbnail_path')) if item.get('thumbnail_path') else None,
            caption=item.get('caption'),
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