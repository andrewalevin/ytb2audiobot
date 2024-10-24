import math
import os
import argparse
import asyncio
import logging

import yt_dlp
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from ytb2audiobot import config
from ytb2audiobot.commands import get_big_youtube_move_id
from ytb2audiobot.cron import run_periodically, empty_dir_by_cron
from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.processing import download_processing
from ytb2audiobot.predictor import predict_downloading_time
from ytb2audiobot.utils import seconds2humanview, get_hash, write_file, remove_all_in_dir, \
    pprint_format, tabulation2text
from ytb2audiobot.cron import update_pip_package_ytdlp
from ytb2audiobot.logger import logger, BOLD_GREEN, RESET
from importlib.metadata import version


storage = MemoryStorage()
dp = Dispatcher(storage=storage)

bot = Bot(token=config.DEFAULT_TELEGRAM_TOKEN_IMAGINARY)

data_dir = get_data_dir()

storage_callback_keys = dict()

contextbot = dict()

autodownload_chat_ids_hashed = dict()
autodownload_file_hash = ''

if False:
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


def get_hash_salted(data):
    salt = os.environ.get('SALT', '')
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


async def job_downloading(
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


@dp.callback_query(lambda c: c.data == 'split')
async def process_callback_split(callback_query: types.CallbackQuery):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Split!'
    )


@dp.callback_query(lambda c: c.data == 'bitrate')
async def process_callback_split(callback_query: types.CallbackQuery):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='Bitrate!'
    )


form_router = Router()
dp.include_router(form_router)


# Определяем состояния для FSM (Finite State Machine)
class Form(StatesGroup):
    movie_url_and_search = State()


@dp.callback_query(lambda c: c.data == 'subtitles')
async def process_callback_split(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text='📝 Subtitles! Send me yotuube link and add search words after'
    )

    await state.set_state(Form.movie_url_and_search)


@form_router.message(Form.movie_url_and_search)
async def process_movie_url(message: Message, state: FSMContext) -> None:
    await state.update_data(movie_url_and_search=message.text)
    await message.answer('Got. Now Preocessing')


@dp.message(Command('version'))
async def autodownload_handler(message: Message, command: CommandObject) -> None:
    await message.reply(f"🟢 {config.PACKAGE_NAME} version: {version(config.PACKAGE_NAME)}")


@dp.message(Command('extra'))
async def autodownload_handler(message: Message, command: CommandObject) -> None:
    logger.debug('🍟 Extra Options')

    menu_message = await bot.send_message(
        chat_id=message.from_user.id,
        reply_to_message_id=None,
        text=f'Choose one of these extra options.',
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text='📣 Split', callback_data=f'split'),
                    InlineKeyboardButton(text='📣 Bitrate', callback_data=f'bitrate'), ],
                [
                    InlineKeyboardButton(text='📣 Subtitles', callback_data=f'subtitles'), ],
            ], ))


@dp.callback_query(lambda c: c.data.startswith('download:'))
async def process_callback_button(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    storage_callback_keys[callback_query.data] = ''

    parts = callback_query.data.split(':_:')

    sender_id = int(parts[3])
    message_id = int(parts[2])
    movie_id = parts[1]
    info_message_id = callback_query.message.message_id

    await job_downloading(
        sender_id=sender_id,
        message_id=message_id,
        movie_id=movie_id,
        info_message_id=info_message_id)


@dp.message()
@dp.channel_post()
async def direct_message_and_post_handler(message: Message):
    global bot
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
    logging.debug(f'🔫 movie_id={movie_id}')

    if not movie_id:
        # todo
        return

    await job_downloading(
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


async def run_bot_asynchronously():
    global bot

    me = await bot.get_me()
    logger.info(f'🚀 Telegram bot: f{me.full_name} https://t.me/{me.username}')

    if True or os.getenv('DEBUG', 'false') == 'true':
        await bot.send_message(
            chat_id=config.OWNER_SENDER_ID,
            text=f'🚀👋 Bot started. Version: {version(config.PACKAGE_NAME)}')

    if os.environ.get('KEEP_DATA_FILES', 'false') != 'true':
        logger.info('♻️🗑 Remove last files in DATA')
        remove_all_in_dir(data_dir)

    global autodownload_chat_ids_hashed
    if config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH.exists():
        with config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH.resolve().open('r') as file:
            data = file.read()

        global autodownload_file_hash
        autodownload_file_hash = get_hash(data)

        autodownload_chat_ids_hashed = {row: None for row in data.split('\n')}
    logger.debug(f'🧮 Hashed Dict Init:  {autodownload_chat_ids_hashed}', )

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


def main():
    logging.info("\n")
    logger.info(f'{BOLD_GREEN}🚀🚀  Launching bot app. Package version: {version(config.PACKAGE_NAME)} {RESET}')

    load_dotenv()

    parser = argparse.ArgumentParser(
        description='🥭 Bot. Youtube to audio telegram bot with subtitles',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--debug', action='store_true', help='Debug mode.')
    parser.add_argument('--keep-data-files', action='store_true', help='Keep Data Files')

    args = parser.parse_args()

    os.environ['DEBUG'] = 'true' if args.debug else 'false'

    if os.getenv('DEBUG', 'false') == 'true':
        logger.setLevel(logging.DEBUG)
        logger.debug('🎃 DEBUG mode is set. All debug messages will be in stdout.')

        os.environ['KEEP_DATA_FILES'] = 'true'

    if not os.getenv("TG_TOKEN", ''):
        logger.error('🔴 No TG_TOKEN variable set in env. Make add and restart bot.')
        return

    if not os.getenv("HASH_SALT", ''):
        logger.error('🔴 No HASH_SALT variable set in .env. Make add any random hash with key SALT!')
        return

    logger.info('🗂 data_dir: ' + f'{data_dir.resolve().as_posix()}')

    global bot
    bot = Bot(
        token=os.environ.get('TG_TOKEN', config.DEFAULT_TELEGRAM_TOKEN_IMAGINARY),
        default=DefaultBotProperties(parse_mode='HTML'))

    asyncio.run(run_bot_asynchronously())


if __name__ == "__main__":
    main()
