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

from ytb2audiobot.commands import get_command_params_of_request
from ytb2audiobot.cron import run_cron
from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.processing import processing_commands
from ytb2audiobot.utils import delete_files_by_movie_id

storage = MemoryStorage()

dp = Dispatcher(storage=storage)

load_dotenv()
token = os.environ.get("TG_TOKEN")

bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

data_dir = get_data_dir()

keep_data_files = False

TELEGRAM_MAX_MESSAGE_TEXT_SIZE = 4095

TASK_TIMEOUT_SECONDS = 60 * 30

storage_callback_keys = dict()

CALLBACK_WAIT_TIMEOUT = 8


async def processing_download(sender_id, message_id, command_context: dict, post_status_message_id = None):
    post_status = None
    if post_status_message_id:
        post_status = await bot.edit_message_text(
            chat_id=sender_id,
            message_id=post_status_message_id,
            text='⌛️ Downloading ... ')
    else:
        post_status = await bot.send_message(
            chat_id=sender_id,
            reply_to_message_id=message_id,
            text='⌛️ Downloading ... ')

    stopwatch_time = time.perf_counter()

    result = {}
    task = asyncio.create_task(processing_commands(command_context))
    result = await asyncio.wait_for(task, timeout=TASK_TIMEOUT_SECONDS)
    stopwatch_time = time.perf_counter() - stopwatch_time

    print(f'💚 Processing Result: ', result)

    if result.get('error'):
        return await post_status.edit_text('🟥 Error Processing. ' + result.get('error'))

    if result.get('warning'):
        await post_status.edit_text('🟠 Warning: ' + result.get('warning'))

    await post_status.edit_text('⌛️ Uploading to Telegram ... ')

    if result.get('subtitles'):
        caption_total = result.get('subtitles').get('caption') + '\n\n' + result.get('subtitles').get('text')
        if len(caption_total) + 8 >= TELEGRAM_MAX_MESSAGE_TEXT_SIZE:
            await bot.send_document(
                chat_id=sender_id,
                reply_to_message_id=message_id,
                document=BufferedInputFile(
                    file=result.get('subtitles').get('text').encode('utf-8'),
                    filename=result.get('subtitles').get('filename')),
                caption=result.get('subtitles').get('caption')
            )
        else:
            await bot.send_message(
                chat_id=sender_id,
                reply_to_message_id=message_id,
                text=caption_total,
                parse_mode='HTML')

        await post_status.delete()
        return

    for audio_data in result.get('audio_datas'):
        await bot.send_audio(
            chat_id=sender_id,
            reply_to_message_id=message_id,
            audio=FSInputFile(path=audio_data.get('audio_path'), filename=audio_data.get('audio_filename')),
            duration=audio_data.get('duration'),
            thumbnail=FSInputFile(path=audio_data.get('thumbnail_path')),
            caption=audio_data.get('caption'),
            parse_mode=ParseMode.HTML
        )

    if not result.get('error') and not result.get('warning'):
        await post_status.delete()

    timer_row = str(result.get('duration')) + '-' + str(int(stopwatch_time))
    with pathlib.Path('timer.txt').open(mode='a') as file:
        file.write(f'{timer_row}\n')


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


@dp.callback_query(lambda c: c.data.startswith('download:'))
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    storage_callback_keys[callback_query.data] = ''

    print('🚦 callback_query.data: ', callback_query.data)

    parts = callback_query.data.split(':_:')
    context = dict()
    context['name'] = parts[0]
    context['id'] = parts[1]
    context['message_id'] = int(parts[2])
    context['sender_id'] = int(parts[3])

    print('🚦🚦 command_context: ', context)

    await processing_download(context['sender_id'], context['message_id'], context, callback_query.message.message_id)


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
        return await bot.send_message(chat_id=sender_id, text='🟥️ Command context. Not a valid movie id.')

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
            text=f'Choose one of these options. \nExit in seconds: {CALLBACK_WAIT_TIMEOUT}',
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(
                    text='📣 Just Download️',
                    callback_data=callback_data), ], ],))

        await asyncio.sleep(CALLBACK_WAIT_TIMEOUT)

        if callback_data in storage_callback_keys:
            del storage_callback_keys[callback_data]
        else:
            await post_status.delete()
        return

    if not command_context.get('name'):
        command_context['name'] = 'download'

    await processing_download(sender_id, message.message_id, command_context)


async def start_bot():
    await asyncio.gather(
        run_cron(),
        dp.start_polling(bot),
    )


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
