import logging
import os
import argparse
import asyncio
from dotenv import load_dotenv
from importlib.metadata import version

from aiogram import Bot, Dispatcher, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, StatesGroup, State
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from ytb2audiobot import config
from ytb2audiobot.autodownload_chat_manager import AutodownloadChatManager
from ytb2audiobot.callback_storage_manager import StorageCallbackManager
from ytb2audiobot.cron import run_periodically, empty_dir_by_cron
from ytb2audiobot.hardworkbot import job_downloading, make_subtitles
from ytb2audiobot.logger import logger
from ytb2audiobot.utils import remove_all_in_dir, green_text, bold_text, get_data_dir, get_big_youtube_move_id, \
    create_inline_keyboard
from ytb2audiobot.cron import update_pip_package_ytdlp


bot = Bot(token=config.DEFAULT_TELEGRAM_TOKEN_IMAGINARY)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

data_dir = get_data_dir()

# Example usage
callback_storage_manager = StorageCallbackManager()

autodownload_chat_manager = AutodownloadChatManager(data_dir=data_dir)


class StateFormMenuExtra(StatesGroup):
    url = State()
    options = State()
    split = State()
    bitrate = State()
    subtitles_options = State()
    subtitles_search = State()


ADVANCED_OPTIONS_TEXT = '''
🎬 Advanced options can help you to:
    
    -	✂️ Split audio into parts of a desired length
    -	🎷 Bitrate adjustment for audio
    -	📝 Subtitles download and word search
    
🔗 Send me your link to YouTube\'s video ... 
'''

TG_EXTRA_OPTIONS_LIST = ['extra', 'options', 'advanced']


@dp.message(CommandStart())
@dp.message(Command('help'))
async def handler_command_start_and_help(message: Message) -> None:
    logger.debug('💈 handler_command_start_and_help(): ')
    await message.answer(text=config.START_COMMAND_TEXT, parse_mode='HTML')


@dp.message(Command('version'))
async def handler_version_bot(message: Message) -> None:
    logger.debug('💈 handler_version_bot(): ')

    await message.reply(f"🟢 {config.PACKAGE_NAME} version: {version(config.PACKAGE_NAME)}")


@dp.message(Command(commands=TG_EXTRA_OPTIONS_LIST), StateFilter(default_state))
async def case_url_set(message: Message, state: FSMContext) -> None:
    logger.debug('💈 case_url_set(): ')

    await message.answer(text=ADVANCED_OPTIONS_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.channel_post(Command(commands=TG_EXTRA_OPTIONS_LIST))
async def handler_extra_options_except_channel_post(message: Message) -> None:
    logger.debug('💈 handler_extra_options_except_channel_post(): ')

    await message.answer('❌ This command works only in bot not in channels.')


@dp.message(StateFormMenuExtra.url)
async def case_show_options(message: types.Message, state: FSMContext):
    logger.debug('💈 case_show_options(): ')

    url = message.text
    # todo

    await state.update_data(url=url)
    await state.set_state(StateFormMenuExtra.options)
    await bot.send_message(
        chat_id=message.from_user.id,
        reply_to_message_id=None,
        text=f'🤔 Select advanced option? .',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✂️ Split duration', callback_data='split'),
             InlineKeyboardButton(text='🎷 Set audio Bitrate', callback_data='bitrate')],
            [InlineKeyboardButton(text='📝 Get subtitles', callback_data='subtitles')]]))


@dp.callback_query(StateFormMenuExtra.options)
async def case_options(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug('💈 case_options(): ')

    action = callback_query.data

    if action == 'split':
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="✂️ Select duration split parts (in minutes): ",
            reply_markup=create_inline_keyboard([
                [2, 3, 5, 7, 11, 13, 17, 19],
                [23, 29, 31, 37, 41, 43],
                [47, 53, 59, 61, 67],
                [73, 79, 83, 89]]))
        await state.set_state(StateFormMenuExtra.split)

    elif action == 'bitrate':
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="🎷 Select preferable bitrate (in kbps): ",
            reply_markup=create_inline_keyboard([
                ['48k', '64k', '96k', '128k'],
                ['196k', '256k', '320k']]))
        await state.set_state(StateFormMenuExtra.bitrate)

    elif action == 'subtitles':
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="📝 Subtitles option: ",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='🍱 All subtitles', callback_data='download'),
                InlineKeyboardButton(text='🍝 Search word inside', callback_data='search')]]))
        await state.set_state(StateFormMenuExtra.subtitles_options)


@dp.callback_query(StateFormMenuExtra.split)
async def case_split_processing(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug('💈 case_split_processing(): ')

    duration = callback_query.data
    data = await state.get_data()
    url = data.get('url')

    # todo

    await state.clear()
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=f"✂️ Split: duration={duration}, url={url}")


@dp.callback_query(StateFormMenuExtra.bitrate)
async def case_bitrate_processing(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug('💈 case_bitrate_processing(): ')

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
    logger.debug('💈 case_subtitle_options_processing(): ')

    action = callback_query.data
    data = await state.get_data()
    url = data.get('url')

    if action == 'download':
        await state.clear()

        info_message = await callback_query.message.edit_text(text='⏳ Downloading subtitles ... ')
        await make_subtitles(bot=bot, sender_id=callback_query.from_user.id, url=url, info_message_id=info_message.message_id)
    elif action == 'search':
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=f"🍝 Input word to search: ")
        await state.set_state(StateFormMenuExtra.subtitles_search)
    else:
        await state.clear()


@dp.message(StateFormMenuExtra.subtitles_search)
async def case_subtitles_search(message: types.Message, state: FSMContext):
    logger.debug('💈 case_subtitles_search(): ')

    word = message.text
    data = await state.get_data()
    url = data.get('url')

    await state.clear()
    info_message = await message.answer(text='⏳ Downloading subtitles and search word inside ... ')

    await make_subtitles(bot=bot, sender_id=message.from_user.id, url=url, word=word, info_message_id=info_message.message_id)


@dp.channel_post(Command('autodownload'))
async def handler_autodownload_switch_state(message: types.Message) -> None:
    logger.debug('💈 handler_autodownload_switch_state(): ')

    if autodownload_chat_manager.toggle_chat_state(message.sender_chat.id):
        await message.answer('💾 Added Chat ID to autodownloads.\n\nCall /autodownload again to remove.')
    else:
        await message.answer('♻️🗑 Removed Chat ID to autodownloads.\n\nCall /autodownload again to add.')


@dp.message(Command('autodownload'))
async def handler_autodownload_command_in_bot(message: types.Message) -> None:
    logger.debug('💈 handler_autodownload_command_in_bot():')

    await message.answer('❌ This command works only in Channels. Add this bot to the list of admins and call it call then')


@dp.callback_query(lambda c: c.data.startswith('download:'))
async def process_callback_button(callback_query: types.CallbackQuery):
    logger.debug('💈 process_callback_button(): ')

    await bot.answer_callback_query(callback_query.id)

    # Remove this key from list of callbacks
    callback_storage_manager.remove_key(key=callback_query.data)

    callback_parts = callback_query.data.split(':_:')
    sender_id = int(callback_parts[1])
    message_id = int(callback_parts[2])
    movie_id = callback_parts[3]

    info_message_id = callback_query.message.message_id

    await job_downloading(
        bot=bot,
        sender_id=sender_id,
        message_id=message_id,
        message_text=f'youtu.be/{movie_id}',
        info_message_id=info_message_id)


@dp.message()
async def handler_message(message: Message):
    logger.debug('💈 handler_message(): ')

    await job_downloading(bot, message.from_user.id, message.message_id, message.text)


@dp.channel_post()
async def handler_channel_post(message: Message):
    logger.debug('💈 handler_channel_post(): ')

    if autodownload_chat_manager.is_chat_id_inside(message.sender_chat.id):
        await job_downloading(bot, message.sender_chat.id, message.message_id, message.text)
        return

    if not (movie_id := get_big_youtube_move_id(message.text)):
        return

    callback_data = config.CALLBACK_DATA_CHARS_SEPARATOR.join([
        'download',
        str(message.sender_chat.id),
        str(message.message_id),
        str(movie_id)])

    info_message = await message.reply(
        text=f'Choose one of these options. \nExit in seconds: {config.CALLBACK_WAIT_TIMEOUT_SECONDS}',
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='📣 Just Download️', callback_data=callback_data)]]))

    callback_storage_manager.add_key(key=callback_data)

    await asyncio.sleep(config.CALLBACK_WAIT_TIMEOUT_SECONDS)

    if callback_storage_manager.check_key_inside(key=callback_data):
        await info_message.delete()


async def run_bot_asynchronously():
    me = await bot.get_me()
    logger.info(f'🚀 Telegram bot: f{me.full_name} https://t.me/{me.username}')

    if True or os.getenv('DEBUG', 'false') == 'true':
        await bot.send_message(
            chat_id=config.OWNER_SENDER_ID,
            text=f'🚀 Bot has started! \n📦 Package Version: {version(config.PACKAGE_NAME)}\n{config.HELP_COMMANDS_TEXT}')

    if os.environ.get('KEEP_DATA_FILES', 'false') != 'true':
        logger.info('♻️🗑 Remove last files in DATA')
        remove_all_in_dir(data_dir)

    await asyncio.gather(
        run_periodically(30, empty_dir_by_cron, {'age': 3600}),
        run_periodically(43200, update_pip_package_ytdlp, {}),
        dp.start_polling(bot),
        run_periodically(600, autodownload_chat_manager.save_hashed_chat_ids, {}),
    )


def main():
    logging.info("\n")
    logger.info(bold_text(green_text(f'🚀🚀  Launching bot app. Package version: {version(config.PACKAGE_NAME)}')))

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
