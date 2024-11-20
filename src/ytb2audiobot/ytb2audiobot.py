import inspect
import logging
import os
import argparse
import asyncio
import signal
import sys

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
from ytb2audiobot.slice import time_hhmmss_check_and_convert
from ytb2audiobot.utils import remove_all_in_dir, get_data_dir, get_big_youtube_move_id, create_inline_keyboard
from ytb2audiobot.cron import update_pip_package_ytdlp

load_dotenv()

bot = Bot(token=config.DEFAULT_TELEGRAM_TOKEN_IMAGINARY)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

data_dir = get_data_dir()

# Example usage
callback_storage_manager = StorageCallbackManager()

autodownload_chat_manager = AutodownloadChatManager(data_dir=data_dir)


class StateFormMenuExtra(StatesGroup):
    options = State()
    split_by_duration = State()
    bitrate = State()
    subtitles_options = State()
    subtitles_search_word = State()
    slice_start_time = State()
    slice_end_time = State()
    url = State()
    translate = State()


@dp.message(CommandStart())
@dp.message(Command('help'))
async def handler_command_start_and_help(message: Message) -> None:
    logger.debug('💈 handler_command_start_and_help(): ')
    await message.answer(text=config.START_COMMAND_TEXT, parse_mode='HTML')


@dp.message(Command(commands=['version', 'ver', 'v']))
async def handler_version_bot(message: Message) -> None:
    logger.debug('💈 handler_version_bot(): ')

    await message.reply(f"🟢 {config.PACKAGE_NAME} version: {version(config.PACKAGE_NAME)}")


TG_EXTRA_OPTIONS_LIST = ['extra', 'options', 'advanced', 'ext', 'ex', 'opt', 'op', 'adv', 'ad']


@dp.channel_post(Command(commands=TG_EXTRA_OPTIONS_LIST))
async def handler_extra_options_except_channel_post(message: Message) -> None:
    logger.debug('💈 handler_extra_options_except_channel_post(): ')

    await message.answer('❌ This command works only in bot not in channels.')


SEND_YOUTUBE_LINK_TEXT = '🔗 Give me your YouTube link:'


TEXT_EXTRA_OPTIONS = '''<b>🔮 Advanced options:</b> 

    - ✂️ Split by duration

    - 🚦️ Split by timecodes

    - 🎸 Set audio Bitrate

    - ✏️ Get subtitles
    
    - 🍰️ Get slice of audio
    
    - 🌎️ Translate from any language into Russian
    
Select one of the []
'''


@dp.message(Command(commands=TG_EXTRA_OPTIONS_LIST), StateFilter(default_state))
async def case_show_options(message: types.Message, state: FSMContext):
    logger.debug('💈 case_show_options(): ')

    await state.set_state(StateFormMenuExtra.options)
    await bot.send_message(
        chat_id=message.from_user.id,
        reply_to_message_id=None,
        text=TEXT_EXTRA_OPTIONS,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='✂️ By duration', callback_data=config.ACTION_NAME_SPLIT_BY_DURATION),
                InlineKeyboardButton(text='🚦️ By timecodes', callback_data=config.ACTION_NAME_SPLIT_BY_TIMECODES)],
            [
                InlineKeyboardButton(text='🎸 Set bitrate', callback_data=config.ACTION_NAME_BITRATE_CHANGE),
                InlineKeyboardButton(text='✏️ Get subtitles', callback_data=config.ACTION_NAME_SUBTITLES_SHOW_OPTIONS)],
            [
                InlineKeyboardButton(text='🍰 Get slice', callback_data=config.ACTION_NAME_SLICE),
                InlineKeyboardButton(text='🌎 Translate', callback_data=config.ACTION_NAME_TRANSLATE)],
            [
                InlineKeyboardButton(text='🔚 Exit', callback_data=config.ACTION_NAME_OPTIONS_EXIT)],]))


BITRATE_VALUES_ROW_ONE = ['48k', '64k', '96k', '128k']
BITRATE_VALUES_ROW_TWO = ['196k', '256k', '320k']
BITRATE_VALUES_ALL = BITRATE_VALUES_ROW_ONE + BITRATE_VALUES_ROW_TWO


SPLIT_DURATION_VALUES_ROW_1 = ['2', '3', '5', '7', '11', '13', '17', '19']
SPLIT_DURATION_VALUES_ROW_2 = ['23', '29', '31', '37', '41', '43']
SPLIT_DURATION_VALUES_ROW_3 = ['47', '53', '59', '61', '67']
SPLIT_DURATION_VALUES_ROW_4 = ['73', '79', '83', '89']
SPLIT_DURATION_VALUES_ALL = SPLIT_DURATION_VALUES_ROW_1 + SPLIT_DURATION_VALUES_ROW_2 + SPLIT_DURATION_VALUES_ROW_3 + SPLIT_DURATION_VALUES_ROW_4


@dp.callback_query(StateFormMenuExtra.options)
async def case_options(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=inspect.currentframe().f_code.co_name))

    action = callback_query.data
    if action == config.ACTION_NAME_SPLIT_BY_DURATION:
        await state.update_data(action=action)
        await state.set_state(StateFormMenuExtra.split_by_duration)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="✂️ Select duration split parts (in minutes): ",
            reply_markup=create_inline_keyboard([
                SPLIT_DURATION_VALUES_ROW_1,
                SPLIT_DURATION_VALUES_ROW_2,
                SPLIT_DURATION_VALUES_ROW_3,
                SPLIT_DURATION_VALUES_ROW_4]))

    elif action == config.ACTION_NAME_SPLIT_BY_TIMECODES:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=SEND_YOUTUBE_LINK_TEXT)
        await state.set_state(StateFormMenuExtra.url)

    elif action == config.ACTION_NAME_BITRATE_CHANGE:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="🎸 Select preferable bitrate (in kbps): ",
            reply_markup=create_inline_keyboard([
                BITRATE_VALUES_ROW_ONE,
                BITRATE_VALUES_ROW_TWO]))
        await state.set_state(StateFormMenuExtra.bitrate)

    elif action == config.ACTION_NAME_SUBTITLES_SHOW_OPTIONS:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="✏️ Subtitles options: ",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='🔮 Retrieve All', callback_data=config.ACTION_NAME_SUBTITLES_GET_ALL),
                InlineKeyboardButton(text='🔍 Search by word', callback_data=config.ACTION_NAME_SUBTITLES_SEARCH_WORD)]]))
        await state.set_state(StateFormMenuExtra.subtitles_options)

    elif action == config.ACTION_NAME_SLICE:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text="🍰 Step 1/2. Give me a START time of your slice.\n "
                 "In format 01:02:03. (hh:mm:ss) or 02:02 (mm:ss) or 78 seconds")
        await state.set_state(StateFormMenuExtra.slice_start_time)

    elif action == config.ACTION_NAME_TRANSLATE:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=SEND_YOUTUBE_LINK_TEXT)
        await state.set_state(StateFormMenuExtra.url)

    elif action == config.ACTION_NAME_OPTIONS_EXIT:
        await state.clear()


@dp.callback_query(StateFormMenuExtra.split_by_duration)
async def case_split_by_duration_processing(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug('💈 case_split_by_duration_processing(): ')

    split_duration = callback_query.data
    if split_duration not in SPLIT_DURATION_VALUES_ALL:
        await bot.edit_message_text(
            text=f'🔴 An unexpected unknown split duration value was received. (split_duration={split_duration})')
        await state.clear()

    await state.update_data(split_duration=split_duration)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
        text=SEND_YOUTUBE_LINK_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.callback_query(StateFormMenuExtra.bitrate)
async def case_bitrate_processing(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug('💈 case_bitrate_processing(): ')

    bitrate = callback_query.data
    if bitrate not in BITRATE_VALUES_ALL:
        await bot.edit_message_text(
            text=f'🔴 An unexpected unknown bitrate value was received. (bitrate={bitrate})')
        await state.clear()

    await state.update_data(bitrate=bitrate)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
        text=SEND_YOUTUBE_LINK_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.callback_query(StateFormMenuExtra.subtitles_options)
async def case_subtitles_options_processing(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug('💈 case_subtitles_options_processing(): ')

    action = callback_query.data
    if action == config.ACTION_NAME_SUBTITLES_GET_ALL:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
            text=SEND_YOUTUBE_LINK_TEXT)
        await state.set_state(StateFormMenuExtra.url)

    elif action == config.ACTION_NAME_SUBTITLES_SEARCH_WORD:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
            text=f"🔍 Input word to search: ")
        await state.set_state(StateFormMenuExtra.subtitles_search_word)


@dp.message(StateFormMenuExtra.subtitles_search_word)
async def case_subtitles_search_word(message: types.Message, state: FSMContext):
    logger.debug('💈 case_subtitles_search_word(): ')

    subtitles_search_word = message.text
    await state.update_data(subtitles_search_word=subtitles_search_word)
    await message.answer(text=SEND_YOUTUBE_LINK_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.message(StateFormMenuExtra.slice_start_time)
async def case_slice_start_time(message: types.Message, state: FSMContext):
    logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=inspect.currentframe().f_code.co_name))

    start_time = message.text
    start_time = time_hhmmss_check_and_convert(start_time)
    if start_time is None:
        await state.clear()
        await message.answer(text=f'❌ Not valid time format. Try again')

    await state.update_data(slice_start_time=start_time)
    await message.answer(text=f'🍰 Step 2/2. Now give me an END time  of your slice. \n'
                              f'In format 01:02:03. (hh:mm:ss) or 02:02 (mm:ss) 78 seconds')
    await state.set_state(StateFormMenuExtra.slice_end_time)


@dp.message(StateFormMenuExtra.slice_end_time)
async def case_slice_start_time(message: types.Message, state: FSMContext):
    logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=inspect.currentframe().f_code.co_name))

    end_time = message.text
    end_time = time_hhmmss_check_and_convert(end_time)
    if end_time is None:
        await state.clear()
        await message.answer(text=f'❌ Not valid time format. Try again')

    data = await state.get_data()
    start_time = int(data.get('slice_start_time', ''))
    if start_time >= end_time:
        await state.clear()
        await message.answer(text=f'❌ Start time should be less then end time. Try again')

    await state.update_data(slice_end_time=end_time)
    await message.answer(text=SEND_YOUTUBE_LINK_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.message(StateFormMenuExtra.url)
async def case_url(message: Message, state: FSMContext) -> None:
    logger.debug('💈 case_url(): ')

    url = message.text
    data = await state.get_data()
    await state.clear()

    if not get_big_youtube_move_id(url):
        await message.answer(
            text=f'🔴 Unable to extract a valid YouTube URL from your input. (url={url})')
        return

    action = data.get('action', '')

    if action == config.ACTION_NAME_SUBTITLES_GET_ALL:
        await make_subtitles(
            bot=bot, sender_id=message.from_user.id, url=url, reply_message_id=message.message_id)

    elif action == config.ACTION_NAME_SUBTITLES_SEARCH_WORD:
        if word := data.get('subtitles_search_word', ''):
            await make_subtitles(
                bot=bot, sender_id=message.from_user.id, url=url, word=word, reply_message_id=message.message_id)

    elif action == config.ACTION_NAME_SPLIT_BY_DURATION:
        split_duration = data.get('split_duration', '')
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id, message_text=url,
            info_message_id=None, configurations={'action': action, 'split_duration_minutes': split_duration})

    elif action == config.ACTION_NAME_SPLIT_BY_TIMECODES:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id, message_text=url,
            info_message_id=None, configurations={'action': action})

    elif action == config.ACTION_NAME_BITRATE_CHANGE:
        bitrate = data.get('bitrate', '')

        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id, message_text=url,
            info_message_id=None, configurations={'action': action, 'bitrate': bitrate})

    elif action == config.ACTION_NAME_SLICE:
        slice_start_time = data.get('slice_start_time', '')
        slice_end_time = data.get('slice_end_time', '')

        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id, message_text=url,
            info_message_id=None, configurations={
                'action': action, 'slice_start_time': slice_start_time, 'slice_end_time': slice_end_time})

    elif action == config.ACTION_NAME_TRANSLATE:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id, message_text=url,
            info_message_id=None, configurations={'action': action})


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

    await message.answer(
        text='❌ This command works only in Channels. Add this bot to the list of admins and call it call then')


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
        bot=bot, sender_id=sender_id, reply_to_message_id=message_id, message_text=f'youtu.be/{movie_id}',
        info_message_id=info_message_id)


def cli_action_parser(text: str):
    action = ''
    attributes = {}

    matching_attr = next((attr for attr in config.CLI_ACTIVATION_ALL if attr in text), None)

    logger.debug(f'🌀 cli_action_parser: 1 matching_attr={matching_attr}')
    if matching_attr is None:
        return action, attributes

    if matching_attr in config.CLI_ACTIVATION_SUBTITLES:
        action = config.ACTION_NAME_SUBTITLES_GET_ALL

        parts = text.split(matching_attr)
        attributes['url'] = parts[0].strip()

        if len(parts) > 1:
            word = parts[1].strip()
            if word:
                action = config.ACTION_NAME_SUBTITLES_SEARCH_WORD
                attributes['word'] = word

    logger.debug(f'🌀 cli_action_parser: 4 matching_attr={matching_attr}')
    if matching_attr in config.CLI_ACTIVATION_MUSIC:
        action = config.ACTION_NAME_MUSIC

    return action, attributes


@dp.message()
async def handler_message(message: Message):
    logger.debug('💈🏧  handler_message(): ')

    cli_action, cli_attributes = cli_action_parser(message.text)

    if cli_action == config.ACTION_NAME_SUBTITLES_GET_ALL:
        if cli_attributes['url']:
            await make_subtitles(
                bot=bot, sender_id=message.from_user.id, url=cli_attributes['url'], reply_message_id=message.message_id)
            return

    if cli_action == config.ACTION_NAME_SUBTITLES_SEARCH_WORD:
        if cli_attributes['url'] and cli_attributes['word']:
            await make_subtitles(
                bot=bot, sender_id=message.from_user.id, url=cli_attributes['url'], reply_message_id=message.message_id,
                word=cli_attributes['word'])
            return

    if cli_action == config.ACTION_NAME_MUSIC:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
            message_text=message.text,
            configurations={'action': config.ACTION_NAME_BITRATE_CHANGE, 'bitrate': config.ACTION_MUSIC_HIGH_BITRATE})
        return

    logger.debug('🈯 DIRECT MESSAGE: ')
    await job_downloading(
        bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
        message_text=message.text)


@dp.channel_post()
async def handler_channel_post(message: Message):
    logger.debug('💈 handler_channel_post(): ')

    cli_action, cli_attributes = cli_action_parser(message.text)

    if cli_action == config.ACTION_NAME_SUBTITLES_GET_ALL:
        if cli_attributes['url']:
            await make_subtitles(
                bot=bot, sender_id=message.from_user.id, url=cli_attributes['url'], reply_message_id=message.message_id)
            return

    if cli_action == config.ACTION_NAME_SUBTITLES_SEARCH_WORD:
        if cli_attributes['url'] and cli_attributes['word']:
            await make_subtitles(
                bot=bot, sender_id=message.from_user.id, url=cli_attributes['url'], reply_message_id=message.message_id,
                word=cli_attributes['word'])
            return

    if cli_action == config.ACTION_NAME_MUSIC:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
            message_text=message.text, configurations={'action': cli_action, 'bitrate': config.ACTION_MUSIC_HIGH_BITRATE})
        return

    if autodownload_chat_manager.is_chat_id_inside(message.sender_chat.id):
        await job_downloading(
            bot=bot, sender_id=message.sender_chat.id, reply_to_message_id=message.message_id,
            message_text=message.text)
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

    # Say Hello at startup to bot owner by its ID
    if owner_id := os.getenv(config.ENV_TG_BOT_OWNER_ID, ''):
        try:
            await bot.send_message(
                chat_id=owner_id,
                text=config.TEXT_SAY_HELLO_BOT_OWNER_AT_STARTUP.substitute(
                    package_bot_version=version(config.PACKAGE_NAME),
                    help_commands_text=config.HELP_COMMANDS_TEXT))
        except Exception as e:
            logger.error(f'🔴 Error with Say hello. Maybe user id is not valid: \n{e}')

    if os.environ.get('KEEP_DATA_FILES', 'false').lower() != 'true':
        logger.info('♻️🗑 Remove last files in DATA')
        remove_all_in_dir(data_dir)

    await asyncio.gather(
        run_periodically(30, empty_dir_by_cron, {'age': 3600}),
        run_periodically(43200, update_pip_package_ytdlp, {}),
        dp.start_polling(bot),
        run_periodically(600, autodownload_chat_manager.save_hashed_chat_ids, {}))


def handle_suspend(signal, frame):
    """Handle the SIGTSTP signal (Ctrl+Z)."""
    logger.info("Process suspended. Exiting...")
    # No need to pause manually; the system handles the suspension
    sys.exit(0)


def handle_interrupt(signal, frame):
    """Handle the SIGINT signal (Ctrl+C)."""
    logger.info("Process interrupted by user. Exiting...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGTSTP, handle_suspend)
    signal.signal(signal.SIGINT, handle_interrupt)
    logger.info("Starting ... Press Ctrl+C to stop or Ctrl+Z to suspend.")

    parser = argparse.ArgumentParser(
        description='🥭 Bot. Youtube to audio telegram bot with subtitles',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    if os.getenv(config.ENV_NAME_DEBUG_MODE, 'false').lower() == 'true':
        logger.setLevel(logging.DEBUG)
        logger.debug('🎃 DEBUG mode is set. All debug messages will be in stdout.')
        logger.debug('📌 Set KEEP_DATA_FILES Tue')
        os.environ[config.ENV_NAME_KEEP_DATA_FILES] = 'true'

    if not os.getenv(config.ENV_NAME_TOKEN, ''):
        logger.error('🔴 No TG_TOKEN variable set in env. Make add and restart bot.')
        return

    # todo add salt to use it
    if not os.getenv(config.ENV_NAME_TOKEN, ''):
        logger.error('🔴 No HASH_SALT variable set in .env. Make add any random hash with key SALT!')
        return

    logger.info('🗂 data_dir: ' + f'{data_dir.resolve().as_posix()}')

    global bot
    bot = Bot(token=os.environ.get(config.ENV_NAME_TOKEN, config.DEFAULT_TELEGRAM_TOKEN_IMAGINARY),
              default=DefaultBotProperties(parse_mode='HTML'))

    dp.include_router(router)

    asyncio.run(run_bot_asynchronously())


if __name__ == "__main__":
    main()
