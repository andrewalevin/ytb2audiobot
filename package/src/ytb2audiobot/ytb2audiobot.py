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
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BufferedInputFile

from ytb2audiobot import config
from ytb2audiobot.commands import get_command_params_of_request
from ytb2audiobot.cron import run_periodically, empty_dir_by_cron
from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.processing import processing_commands
from ytb2audiobot.pytube import get_movie_meta
from ytb2audiobot.predictor import predict_downloading_time
from ytb2audiobot.utils import seconds_to_human_readable, read_file, get_hash, write_file
from ytb2audiobot.cron import update_pip_package_ytdlp
from ytb2audiobot.logger import logger

storage = MemoryStorage()

dp = Dispatcher(storage=storage)

load_dotenv()

bot = Bot(token=config.DEFAULT_TELEGRAM_TOKEN_IMAGINARY)
salt = 'salt0'

data_dir = get_data_dir()

storage_callback_keys = dict()

contextbot = dict()

autodownload_chat_ids_hashed = dict()
autodownload_file_hash = ''

timerlogger_handler = logging.FileHandler(config.TIMERS_FILE_PATH.resolve(), mode='a', encoding='utf-8')
timerlogger_handler.setFormatter(
    logging.Formatter(
        fmt="%(asctime)s : %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
)

timerlogger = logging.getLogger(__name__)
timerlogger.addHandler(timerlogger_handler)
timerlogger.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log2.log'),  # Log to file
        logging.StreamHandler()          # Log to console
    ]
)

dev_mode = False


def get_hash_salted(data):
    global salt
    return get_hash(get_hash(data) + salt)


def check_chat_id_in_dict(chat_id):
    if get_hash_salted(chat_id) in autodownload_chat_ids_hashed:
        return True
    return False


async def periodically_autodownload_chat_ids_save(params):
    data_to_write = '\n'.join(sorted(autodownload_chat_ids_hashed.keys())).strip()

    data_hash = get_hash(data_to_write)

    global autodownload_file_hash
    if autodownload_file_hash != data_hash:
        await write_file(config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH, data_to_write)
        autodownload_file_hash = data_hash


async def processing_download(command_context: dict):
    global bot
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

    if command_context.get('name') != 'subtitles':
        post_status = await post_status.edit_text(
            text=f'⏳ Downloading ~ {seconds_to_human_readable(predict_time)} ... ')

    stopwatch_time = time.perf_counter()

    task = asyncio.create_task(processing_commands(command_context, movie_meta))
    result = await asyncio.wait_for(task, timeout=config.TASK_TIMEOUT_SECONDS)
    print(f'💚 Processing Result: ', result, '\n')

    await post_status.edit_text('⌛️ Uploading to Telegram ... ')

    if result.get('subtitles'):
        full_caption = config.SUBTITLES_WITH_CAPTION_TEXT_TEMPLATE.substitute(
            caption=result.get('subtitles').get('caption'),
            subtitles=result.get('subtitles').get('text'))

        if len(full_caption) >= config.TELEGRAM_MAX_MESSAGE_TEXT_SIZE:
            full_caption = full_caption.replace('<b><s><b><s>', '🔹')
            full_caption = full_caption.replace('</s></b></s></b>', '🔹')
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

    if not result.get('audio_datas') or not isinstance(result.get('audio_datas'), list):
        print('🟠 Warning! No Audio datas or is not NoneType. Exit.')
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

    if result.get('error') or result.get('warning'):
        await post_status.edit_text('🟥 Error or 🟠 Warning: \n' + result.get('warning') + '\n\n' + result.get('error'))
    else:
        await post_status.delete()

    # Save Timer in Dev mode
    global dev_mode
    if dev_mode:
        stopwatch_time = int(time.perf_counter() - stopwatch_time)
        timerlogger.info(f'duration_' + str(movie_meta.get('duration')) + f' :  predict_{predict_time} : actual_{stopwatch_time} : delta_{int(stopwatch_time - predict_time)}')



@dp.message(CommandStart())
@dp.message(Command('help'))
async def command_start_handler(message: Message) -> None:
    await message.answer(text=config.START_COMMAND_TEXT, parse_mode='HTML')


@dp.channel_post(Command('autodownload'))
async def autodownload_handler(message: Message, command: CommandObject) -> None:
    hash_salted = get_hash_salted(message.sender_chat.id)
    if check_chat_id_in_dict(message.sender_chat.id):
        del autodownload_chat_ids_hashed[hash_salted]
        await message.reply(f'Remove from Dict: {hash_salted}')
    else:
        autodownload_chat_ids_hashed[hash_salted] = None
        await message.reply(f'Add to Dict: {hash_salted}')


@dp.message(Command('timers'))
async def timers_show_handler(message: Message, command: CommandObject) -> None:
    global bot
    print('🍅 timers_show_handler():')
    print()

    if not config.TIMERS_FILE_PATH.exists():
        await bot.send_message(chat_id=message.from_user.id, text='No timers file')

    data_text = await read_file(config.TIMERS_FILE_PATH)

    # Inverse and cut and inverse back
    if len(data_text) > config.MAX_TELEGRAM_BOT_TEXT_SIZE:
        data_text = '\n'.join(data_text.split('\n')[::-1])
        data_text = data_text[:config.MAX_TELEGRAM_BOT_TEXT_SIZE-8]
        data_text = '...\n' + '\n'.join(data_text.split('\n')[::-1])

    await bot.send_message(chat_id=message.from_user.id, text=data_text)


@dp.callback_query(lambda c: c.data.startswith('download:'))
async def process_callback_button(callback_query: types.CallbackQuery):
    global bot
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
    global bot
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
    logging.debug('🔫 command_context: ', command_context)

    if not command_context.get('id'):
        return

    command_context['message_id'] = message.message_id
    command_context['sender_id'] = sender_id

    if check_chat_id_in_dict(sender_id):
        await processing_download(command_context)
        return

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


async def start_bot(params=None):
    global bot

    if params is None:
        params = {}

    if 'keep_data_files' in params:
        global keep_data_files
        keep_data_files = params['keep_data_files']

    global dev_mode
    if 'dev_mode' in params:
        dev_mode = params['dev_mode']
    if dev_mode:
        for file in data_dir.iterdir():
            file.unlink()
        logger.setLevel(logging.DEBUG)
        logger.info('🛠🧬 DEV Logging Mode')

    global autodownload_chat_ids_hashed
    if config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH.exists():
        with config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH.resolve().open('r') as file:
            data = file.read()

        global autodownload_file_hash
        autodownload_file_hash = get_hash(data)

        autodownload_chat_ids_hashed = {row: None for row in data.split('\n')}
    print('🧮 Hashed Dict Init:  ', autodownload_chat_ids_hashed)

    await asyncio.gather(
        run_periodically(30, empty_dir_by_cron, {'age': 3600}),
        run_periodically(
            10, periodically_autodownload_chat_ids_save,
            {
                'dict': autodownload_chat_ids_hashed,
                'file_hash': 'HASH',
            }),
        run_periodically(43200, update_pip_package_ytdlp, {}),
        dp.start_polling(bot),
    )


def run_bot(params):
    print('🚀 Running bot ... with params: ', params.keys())
    print('🏠 Current instance data_dir: ', data_dir.resolve())

    global bot
    bot = Bot(token=params['token'], default=DefaultBotProperties(parse_mode='HTML'))

    global salt
    salt = params['salt']

    if params.get('dev_mode'):
        print(params)
        print()

    asyncio.run(start_bot(params))


def main():
    logger.debug("This is a debug message")

    print('🦎 Preparing CLI ...')
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
    parser.add_argument('--dev', default=False, action=argparse.BooleanOptionalAction)

    args = parser.parse_args()
    params = dict()
    if args.keepfiles == 1:
        params['keep_data_files'] = True
        print('🔓🗂 Keeping Data files: ', keep_data_files)

    if args.dev:
        params['dev_mode'] = True

    params['token'] = os.environ.get("TG_TOKEN")
    params['salt'] = os.environ.get("SALT")

    if not params['salt']:
        print('🔴 No Salt set  in .env. Make add any random hash with key SALT!')
        return

    run_bot(params)


if __name__ == "__main__":
    main()
