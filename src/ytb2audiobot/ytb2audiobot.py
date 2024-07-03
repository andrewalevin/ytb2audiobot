import math
import os
import argparse
import asyncio
import logging
import pathlib
import sys
import time

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BufferedInputFile

from ytb2audiobot import config
from ytb2audiobot.commands import get_command_params_of_request
from ytb2audiobot.cron import run_cron
from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.processing import processing_commands
from ytb2audiobot.pytube import get_movie_meta
from ytb2audiobot.predictor import predict_downloading_time
from ytb2audiobot.utils import seconds_to_human_readable

storage = MemoryStorage()

dp = Dispatcher(storage=storage)

load_dotenv()

token = os.environ.get("TG_TOKEN")

bot = Bot(token=token, default=DefaultBotProperties(parse_mode='HTML'))

data_dir = get_data_dir()

storage_callback_keys = dict()

contextbot = dict()


async def processing_download(command_context: dict):
    sender_id = command_context.get('sender_id')
    message_id = command_context.get('message_id')
    post_status = None
    if command_context.get('post_message_id'):
        post_status = await bot.edit_message_text(
            chat_id=sender_id,
            message_id=command_context.get('post_message_id'),
            text='⏳ Downloading ... ')
    else:
        post_status = await bot.send_message(
            chat_id=sender_id,
            reply_to_message_id=message_id,
            text='⏳ Downloading ... ')

    movie_meta = await get_movie_meta(command_context.get('id'))
    print('🚦 Movie meta: ', movie_meta, '\n')

    predict_time = predict_downloading_time(movie_meta.get('duration'))

    post_status = await post_status.edit_text(
        text=f'⏳ Downloading ~{seconds_to_human_readable(predict_time)} ... ')

    stopwatch_time = time.perf_counter()
    task = asyncio.create_task(processing_commands(command_context, movie_meta))
    result = await asyncio.wait_for(task, timeout=config.TASK_TIMEOUT_SECONDS)

    print(f'💚 Processing Result: ', result)
    print()

    if result.get('error'):
        return await post_status.edit_text('🟥 Error Processing. ' + result.get('error'))

    if result.get('warning'):
        await post_status.edit_text('🟠 Warning: ' + result.get('warning'))

    await post_status.edit_text('⌛️ Uploading to Telegram ... ')

    if result.get('subtitles'):
        full_caption = config.SUBTITLES_WITH_CAPTION_TEXT_TEMPLATE.substitute(
            caption=result.get('subtitles').get('caption'),
            subtitles=result.get('subtitles').get('text'))

        if len(full_caption) >= config.TELEGRAM_MAX_MESSAGE_TEXT_SIZE:
            await bot.send_document(
                chat_id=sender_id,
                reply_to_message_id=message_id,
                caption=result.get('subtitles').get('caption'),
                parse_mode='HTML',
                document=BufferedInputFile(
                    filename=result.get('subtitles').get('filename'),
                    file=full_caption.encode('utf-8'),))
        else:
            await bot.send_message(
                chat_id=sender_id,
                reply_to_message_id=message_id,
                text=full_caption,
                parse_mode='HTML',
                disable_web_page_preview=False)

        await post_status.delete()
        return

    for idx, audio_data in enumerate(result.get('audio_datas')):
        await bot.send_audio(
            chat_id=sender_id,
            reply_to_message_id=message_id,
            audio=FSInputFile(path=audio_data.get('audio_path'), filename=audio_data.get('audio_filename')),
            duration=audio_data.get('duration'),
            thumbnail=FSInputFile(path=audio_data.get('thumbnail_path')) if audio_data.get('thumbnail_path') else None,
            caption=audio_data.get('caption'),
            parse_mode='HTML'
        )
        # Sleep to avoid flood in Telegram API
        if idx != len(result.get('audio_datas')) - 1:
            await asyncio.sleep(math.floor(8 * math.log10(len(result.get('audio_datas')) - 1)))

    stopwatch_time = time.perf_counter() - stopwatch_time

    text = (f'🕰 Predicted: {seconds_to_human_readable(predict_time)}\n'
            f'🕰 Actual: {seconds_to_human_readable(int(stopwatch_time))}')
    await post_status.edit_text(text)

    if not result.get('error') and not result.get('warning') and not config.DEV:
        await post_status.delete()


@dp.message(CommandStart())
@dp.message(Command('help'))
async def command_start_handler(message: Message) -> None:
    await message.answer(text=config.START_COMMAND_TEXT, parse_mode='HTML')


@dp.callback_query(lambda c: c.data.startswith('download:'))
async def process_callback_button(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    storage_callback_keys[callback_query.data] = ''

    parts = callback_query.data.split(':_:')
    context = {
        'name': parts[0],
        'id': parts[1],
        'message_id': int(parts[2]),
        'sender_id': int(parts[3]),
        'post_message_id': callback_query.message.message_id,
    }

    await processing_download(context)


@dp.message()
@dp.channel_post()
async def message_parser_handler(message: Message):
    sender_id = None
    sender_type = None
    if message.from_user:
        sender_id = message.from_user.id
        sender_type = 'user'
    if message.sender_chat:
        sender_id = message.sender_chat.id
        sender_type = message.sender_chat.type
    if not sender_id:
        return
    if not message.text:
        return

    command_context = get_command_params_of_request(message.text)
    print('🔫 command_context: ', command_context)

    if not command_context.get('id'):
        return

    command_context['message_id'] = message.message_id
    command_context['sender_id'] = sender_id

    if sender_type != 'user' and not command_context.get('name'):
        callback_data = ':_:'.join([
            'download',
            str(command_context['id']),
            str(command_context['message_id']),
            str(command_context['sender_id'])])

        post_status = await bot.send_message(
            chat_id=sender_id,
            reply_to_message_id=message.message_id,
            text=f'Choose one of these options. \nExit in seconds: {config.CALLBACK_WAIT_TIMEOUT}',
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text='📣 Just Download️', callback_data=callback_data), ], ],))

        # Wait timeout pushing button Just Download
        await asyncio.sleep(contextbot.get('callback_button_timeout_seconds'))

        # After timeout clear key from storage if button pressed. Otherwies
        # todo refactor
        if callback_data in storage_callback_keys:
            del storage_callback_keys[callback_data]
        else:
            await post_status.delete()
        return

    if not command_context.get('name'):
        command_context['name'] = 'download'

    await processing_download(command_context)


async def start_bot():
    await asyncio.gather(
        run_cron(),
        dp.start_polling(bot),
    )


def main():
    print('🚀 Running bot ...')
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    parser = argparse.ArgumentParser(
        description='🥭 Bot. Youtube to audio telegram bot with subtitles',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--keepfiles', type=int, default=0,
                        help='Keep raw files 1=True, 0=False (default)')
    parser.add_argument('--split-delta', type=int, default=5,
                        help=f'Delta seconds in splitting audio in range '
                             f'[{config.AUDIO_SPLIT_DELTA_SECONDS_MIN}, {config.AUDIO_SPLIT_DELTA_SECONDS_MAX}]')
    parser.add_argument('--keep-files-time', type=int, default=60,
                        help=f'Keep tmp files tim in minutes in range [{config.KEEP_FILE_TIME_MINUTES_MIN}, ... ]. '
                             f'Set very big number to disable.')
    parser.add_argument('--telegram-callback-button-timeout', type=int, default=8,
                        help=f'Timeout for telegram callback button in channel. '
                             f'Range [{config.TELEGRAM_CALLBACK_BUTTON_TIMEOUT_SECONDS_MIN}, '
                             f'{config.TELEGRAM_CALLBACK_BUTTON_TIMEOUT_SECONDS_MAX}] ')

    # todo
    # threshold_seconds': AUDIO_SPLIT_THRESHOLD_MINUTES * 60,
    #         'split_duration_minutes': 39,
    #         'ytdlprewriteoptions

    args = parser.parse_args()

    if args.keepfiles == 1:
        global keep_data_files
        keep_data_files = True
        print('🔓🗂 Keeping Data files: ', keep_data_files)

    if args.split_delta:
        delta = int(args.split_delta)
        if delta < config.AUDIO_SPLIT_DELTA_SECONDS_MIN or config.AUDIO_SPLIT_DELTA_SECONDS_MAX < delta:
            print('🔴 CLI option --split-delta out of range!')
            return
        contextbot['split_delta_seconds'] = delta

    if args.keep_files_time:
        value = int(args.keep_files_time)
        if value < config.KEEP_FILE_TIME_MINUTES_MIN:
            print('🔴 CLI option --keep-files-time out of range!')
            return
        contextbot['keep_files_time_seconds'] = value * 60

    if args.telegram_callback_button_timeout:
        value = int(args.telegram_callback_button_timeout)
        if value < config.TELEGRAM_CALLBACK_BUTTON_TIMEOUT_SECONDS_MIN or config.TELEGRAM_CALLBACK_BUTTON_TIMEOUT_SECONDS_MAX < value:
            print('🔴 CLI option --telegram-callback-button-timeout out of range!')
            return
        contextbot['callback_button_timeout_seconds'] = value

    for file in data_dir.iterdir():
        file.unlink()

    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
