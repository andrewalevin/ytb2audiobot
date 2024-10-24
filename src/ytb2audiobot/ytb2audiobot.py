import logging
import os
import argparse
import asyncio

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, StatesGroup, State
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ytb2audiobot import config
from ytb2audiobot.cron import run_periodically, empty_dir_by_cron
from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.hardworkbot import direct_message_and_post_work, autodownload_work, job_downloading
from ytb2audiobot.logger import BOLD_GREEN, RESET, logger
from ytb2audiobot.utils import remove_all_in_dir
from ytb2audiobot.cron import update_pip_package_ytdlp
from importlib.metadata import version

bot = Bot(token=config.DEFAULT_TELEGRAM_TOKEN_IMAGINARY)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

data_dir = get_data_dir()

storage_callback_keys = dict()


@dp.message(CommandStart())
@dp.message(Command('help'))
async def command_start_handler(message: Message) -> None:
    await message.answer(text=config.START_COMMAND_TEXT, parse_mode='HTML')


@dp.message(Command('version'))
async def autodownload_handler(message: Message) -> None:
    await message.reply(f"🟢 {config.PACKAGE_NAME} version: {version(config.PACKAGE_NAME)}")


class StateFormMenuExtra(StatesGroup):
    url = State()
    options = State()
    split = State()
    bitrate = State()
    subtitles_options = State()
    subtitles_search = State()


@dp.message(Command(commands='extra'), StateFilter(default_state))
async def case_url_set(message: Message, state: FSMContext) -> None:
    await message.answer("🎬🔗 Paste youtube URL to make extra options: ")
    await state.set_state(StateFormMenuExtra.url)


@dp.message(StateFormMenuExtra.url)
async def case_show_options(message: types.Message, state: FSMContext):
    url = message.text
    # todo

    await state.update_data(url=url)
    await state.set_state(StateFormMenuExtra.options)
    await bot.send_message(
        chat_id=message.from_user.id,
        reply_to_message_id=None,
        text=f'🤔 What to do? .',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✂️ Split duration', callback_data='split'),
             InlineKeyboardButton(text='🎸 Set audio Bitrate', callback_data='bitrate')],
            [InlineKeyboardButton(text='📝 Get subtitles', callback_data='subtitles')]]))


prime_numbers_row1 = [2, 3, 5, 7, 11, 13, 17, 19]
prime_numbers_row2 = [23, 29, 31, 37, 41, 43]
prime_numbers_row3 = [47, 53, 59, 61, 67,]
prime_numbers_row4 = [73, 79, 83, 89]

keyboard_split_duration = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in prime_numbers_row1],
    [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in prime_numbers_row2],
    [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in prime_numbers_row3],
    [InlineKeyboardButton(text=str(number), callback_data=str(number)) for number in prime_numbers_row4]])

keyboard_bitrate_values = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text='48k', callback_data='48'),
    InlineKeyboardButton(text='64k', callback_data='64'),
    InlineKeyboardButton(text='96k', callback_data='96'),
    InlineKeyboardButton(text='128k', callback_data='128')],[
    InlineKeyboardButton(text='196k', callback_data='196'),
    InlineKeyboardButton(text='256k', callback_data='256'),
    InlineKeyboardButton(text='320k', callback_data='320')]])

keyboard_subtitles = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text='🍱 All subtitles', callback_data='download'),
    InlineKeyboardButton(text='🍝 Search word inside', callback_data='search')]])


@dp.callback_query(StateFormMenuExtra.options)
async def case_options(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data

    if action == 'split':
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="✂️ Select duration split parts (in minutes): ",
            reply_markup=keyboard_split_duration)
        await state.set_state(StateFormMenuExtra.split)

    elif action == 'bitrate':
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="🎷 Select preferable bitrate (in kbps): ",
            reply_markup=keyboard_bitrate_values)
        await state.set_state(StateFormMenuExtra.bitrate)

    elif action == 'subtitles':
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="📝 Subtitles option: ",
            reply_markup=keyboard_subtitles)
        await state.set_state(StateFormMenuExtra.subtitles_options)


@dp.callback_query(StateFormMenuExtra.split)
async def case_split_processing(callback_query: types.CallbackQuery, state: FSMContext):
    duration = callback_query.data
    data = await state.get_data()
    url = data.get('url')

    #todo

    await state.clear()
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=f"✂️ Split: duration={duration}, url={url}")


@dp.callback_query(StateFormMenuExtra.bitrate)
async def case_bitrate_processing(callback_query: types.CallbackQuery, state: FSMContext):
    bitrate = callback_query.data
    data = await state.get_data()
    url = data.get('url')

    # todo

    await state.clear()
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=f"🎷 Bitrate: bitrate={bitrate}, url={url}")


@dp.callback_query(StateFormMenuExtra.subtitles_options)
async def case_subtitle_options_processing(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data
    data = await state.get_data()
    url = data.get('url')

    if action == 'search':
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=f"🍝 Input word to search: ")
        # todo Call Subtitles func
        await state.set_state(StateFormMenuExtra.subtitles_search)

    elif action == 'download':
        await state.clear()
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=f"🍱 Entirely download subtitles for: url={url}")

        # todo Call Sabtitles func


@dp.message(StateFormMenuExtra.subtitles_search)
async def case_subtitles_search(message: types.Message, state: FSMContext):
    word = message.text
    data = await state.get_data()
    url = data.get('url')

    await state.clear()
    await message.answer(
        text=f"🍝 Word to search: \nword={word}, url={url}")

    # todo Function


@dp.channel_post(Command('autodownload'))
async def autodownload_handler(message: Message) -> None:
    await autodownload_work(bot=bot, message=message)


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
        bot=bot,
        sender_id=sender_id,
        message_id=message_id,
        movie_id=movie_id,
        info_message_id=info_message_id)


@dp.message()
@dp.channel_post()
async def direct_message_and_post_handler(message: Message):
    logger.debug('💈 Handler. direct_message_and_post_handler(): ')

    await direct_message_and_post_work(bot, message)


async def run_bot_asynchronously():
    me = await bot.get_me()
    logger.info(f'🚀 Telegram bot: f{me.full_name} https://t.me/{me.username}')

    if True or os.getenv('DEBUG', 'false') == 'true':
        await bot.send_message(
            chat_id=config.OWNER_SENDER_ID,
            text=f'🚀 Bot has started! \n\nversion: {version(config.PACKAGE_NAME)} \n\n'
                 f'Commands:\n/extra - Extra options\n/help - Help')

    if os.environ.get('KEEP_DATA_FILES', 'false') != 'true':
        logger.info('♻️🗑 Remove last files in DATA')
        remove_all_in_dir(data_dir)

    if False:
        pass
        # if config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH.exists():
        #    with config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH.resolve().open('r') as file:
        #        data = file.read()
        #
        #   global autodownload_file_hash
        #    autodownload_file_hash = get_hash(data)
        #
        #    autodownload_chat_ids_hashed = {row: None for row in data.split('\n')}
        #   logger.debug(f'🧮 Hashed Dict Init:  {autodownload_chat_ids_hashed}', )

    # run_periodically(
    #             10, periodically_autodownload_chat_ids_save,
    #             {
    #                 'dict': autodownload_chat_ids_hashed,
    #                 'file_hash': 'HASH',
    #             }),

    await asyncio.gather(
        run_periodically(30, empty_dir_by_cron, {'age': 3600}),

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
    dp.include_router(router)

    asyncio.run(run_bot_asynchronously())


if __name__ == "__main__":
    main()
