import argparse
import asyncio
import logging
import pathlib
import sys
import time

from aiogram import Bot, Dispatcher, html, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BufferedInputFile
import os

from dotenv import load_dotenv
from telegram.constants import ParseMode
from ytb2audio.ytb2audio import get_youtube_move_id

from ytb2audiobot.commands import get_command_params_of_request
from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.processing import processing_commands


storage = MemoryStorage()

dp = Dispatcher(storage=storage)

load_dotenv()
token = os.environ.get("TG_TOKEN")

bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

data_dir = get_data_dir()

keep_data_files = False

SEND_AUDIO_TIMEOUT = 120
TG_CAPTION_MAX_LONG = 1023

AUDIO_SPLIT_THRESHOLD_MINUTES = 120
AUDIO_SPLIT_DELTA_SECONDS = 5

AUDIO_BITRATE_MIN = 48
AUDIO_BITRATE_MAX = 320

TELEGRAM_MAX_MESSAGE_TEXT_SZIE = 4095

TASK_TIMEOUT_SECONDS = 60 * 30


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


@dp.callback_query(lambda c: c.data.startswith('download:'))
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    print('🚦 callback_query.data: ', callback_query.data)
    print('🚦🚦 callback_query.message.message_id: ', callback_query.message.message_id)
    print()

    command_name, url, message_id = callback_query.data.split(':_:')

    post_status = await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text='🍷 Preparing to start ... '
    )

    command_context = {
        'url': url,
        'url_started': False,
        'name': command_name,
        'params': [],
        'force_download': True,
        'message_id': message_id,
        'sender_id': callback_query.message.chat.id,
        'post_status_id': post_status.message_id
    }
    print('🌋 command_context: ', command_context)
    print()

    task = asyncio.create_task(processing_commands(command_context))
    await asyncio.wait_for(task, timeout=TASK_TIMEOUT_SECONDS)
    print('🍷 After Exit')

    return 'exit'


@dp.message()
@dp.channel_post()
async def message_parser_handler(message: Message) -> None | Message | bool:
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

    post_status = await bot.send_message(chat_id=sender_id, text=f'⌛️ Starting ... ')

    command_context = get_command_params_of_request(message.text)
    print('🔫 command_context: ', command_context)

    if not command_context.get('url'):
        return await post_status.edit_text('🟥️ Command context. Not a valid URL.')

    if not (movie_id := get_youtube_move_id(command_context.get('url'))):
        return await post_status.edit_text('🟥️ No valid youtube movie id in url.')

    command_context['id'] = movie_id
    command_context['message_id'] = message.message_id
    command_context['sender_id'] = sender_id

    if sender_type != 'user' and not command_context.get('name'):
        print('🐿 CallBack Case:')

        callback_data = 'download' + ':_:' + command_context.get('url') + ':_:' + str(message.message_id)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📣 Just Download️", callback_data=callback_data), ], ],
        )

        text = f"Choose one of these options. \nExit in seconds: 8"
        await asyncio.sleep(8)
        return

    if not command_context.get('name'):
        command_context['name'] = 'download'

    await post_status.edit_text('⌛️ Downloading ... ')

    stopwatch_time = time.perf_counter()
    task = asyncio.create_task(processing_commands(command_context))
    result = await asyncio.wait_for(task, timeout=TASK_TIMEOUT_SECONDS)
    stopwatch_time = time.perf_counter() - stopwatch_time

    print(f'💚 Processing Result: ', result)

    if result.get('error'):
        return await post_status.edit_text(text='🟥 Error Processing. ' + result.get('error'))

    if result.get('warning'):
        await post_status.edit_text(text='🟠 Warning: ' + result.get('warning'))

    await post_status.edit_text('⌛️ Uploading to Telegram ... ')

    if result.get('subtitles'):
        if len(result.get('subtitles')) >= TELEGRAM_MAX_MESSAGE_TEXT_SZIE:
            await message.reply_document(
                document=BufferedInputFile(
                    file=result.get('subtitles').encode('utf-8'),
                    filename=f'subtitles-{movie_id}.txt'))
        else:
            await message.reply(text=result.get('subtitles'), parse_mode='HTML')

        await post_status.delete()
        return

    for audio_data in result.get('audio_datas'):
        await bot.send_audio(
            chat_id=audio_data.get('chat_id'),
            reply_to_message_id=audio_data.get('reply_to_message_id'),
            audio=FSInputFile(path=audio_data.get('audio_path'), filename=audio_data.get('audio_filename')),
            duration=audio_data.get('duration'),
            thumbnail=FSInputFile(path=audio_data.get('thumbnail_path')),
            caption=audio_data.get('caption'),
            parse_mode='HTML'
        )

    await post_status.delete()

    timer_row = str(result.get('duration')) + '-' + str(int(stopwatch_time))
    with pathlib.Path('timer.txt').open(mode='a') as file:
        file.write(f'{timer_row}\n')


async def start_bot():
    await dp.start_polling(bot)


def main():
    print('🚀 Running bot ...')
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    parser = argparse.ArgumentParser(description='Bot ytb 2 audio')
    parser.add_argument('--keepfiles', type=int,
                        help='Keep raw files 1=True, 0=False (default)', default=0)
    args = parser.parse_args()

    if args.keepfiles == 1:
        global keep_data_files
        keep_data_files = True
        print('🔓🗂 Keeping Data files: ', keep_data_files)

    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
