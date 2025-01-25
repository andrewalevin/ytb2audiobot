import inspect
import logging
import os
import argparse
import asyncio
import signal
import sys
from functools import wraps
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
from ytb2audiobot.config import DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT, DESCRIPTION_BLOCK_EXTRA_OPTIONS, \
    DESCRIPTION_BLOCK_OKAY_AFTER_EXIT, SPLIT_DURATION_VALUES_ROW_1, \
    SPLIT_DURATION_VALUES_ROW_2, SPLIT_DURATION_VALUES_ROW_3, SPLIT_DURATION_VALUES_ROW_4, BITRATE_VALUES_ROW_ONE, \
    BITRATE_VALUES_ROW_TWO, SPLIT_DURATION_VALUES_ALL, BITRATE_VALUES_ALL, START_AND_HELP_TEXT, \
    TEXT_SAY_HELLO_BOT_OWNER_AT_STARTUP
from ytb2audiobot.cron import run_periodically, empty_data_dir_by_cron
from ytb2audiobot.hardworkbot import job_downloading, make_subtitles
from ytb2audiobot.logger import logger
from ytb2audiobot.slice import time_hhmmss_check_and_convert
from ytb2audiobot.utils import remove_all_in_dir, get_data_dir, get_big_youtube_move_id, create_inline_keyboard
from ytb2audiobot.cron import update_pip_package_ytdlp


bot = Bot(token=config.TELEGRAM_VALID_TOKEN_IMAGINARY_DEFAULT)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

data_dir = get_data_dir()

callback_storage_manager = StorageCallbackManager()

autodownload_chat_manager = AutodownloadChatManager(path=config.AUTO_DOWNLOAD_CHAT_IDS_STORAGE_FILENAME)

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


def log_debug_function_name(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        # Log the function call
        logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=func.__name__))
        try:
            return await func(message, *args, **kwargs)
        except Exception as err:
            logger.error(f"An error occurred in {func.__name__}: {err}", exc_info=True)
    return wrapper


@dp.message(CommandStart())
@dp.message(Command('help'))
@log_debug_function_name
async def handler_command_start_and_help(message: Message) -> None:
    await message.answer(text=START_AND_HELP_TEXT, parse_mode='HTML')


@dp.message(Command('cli'))
@log_debug_function_name
async def handler_command_cli_info(message: Message) -> None:
    await message.answer(text=config.DESCRIPTION_BLOCK_CLI , parse_mode='HTML')


TG_EXTRA_OPTIONS_LIST = ['extra', 'options', 'advanced', 'ext', 'ex', 'opt', 'op', 'adv', 'ad']
@dp.channel_post(Command(commands=TG_EXTRA_OPTIONS_LIST))
@log_debug_function_name
async def handler_extra_options_except_channel_post(message: Message) -> None:
    await message.answer('❌ This command works only in the bot, not in channels.')


@dp.message(Command(commands=TG_EXTRA_OPTIONS_LIST), StateFilter(default_state))
@log_debug_function_name
async def case_show_options(message: types.Message, state: FSMContext):
    await state.set_state(StateFormMenuExtra.options)
    await bot.send_message(
        chat_id=message.from_user.id,
        reply_to_message_id=None,
        text=f'{DESCRIPTION_BLOCK_EXTRA_OPTIONS}\n\nSelect one of the option:',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='✂️ By duration', callback_data=config.ACTION_NAME_SPLIT_BY_DURATION),
                InlineKeyboardButton(text='⏱️️ By timecodes', callback_data=config.ACTION_NAME_SPLIT_BY_TIMECODES)],
            [
                InlineKeyboardButton(text='🎸 Set bitrate', callback_data=config.ACTION_NAME_BITRATE_CHANGE),
                InlineKeyboardButton(text='✏️ Get subtitles', callback_data=config.ACTION_NAME_SUBTITLES_SHOW_OPTIONS)],
            [
                InlineKeyboardButton(text='🍰 Get slice', callback_data=config.ACTION_NAME_SLICE),
                InlineKeyboardButton(text='🌎 Translate', callback_data=config.ACTION_NAME_TRANSLATE)],
            [
                InlineKeyboardButton(text='Close', callback_data=config.ACTION_NAME_OPTIONS_EXIT)],]))


@dp.callback_query(StateFormMenuExtra.options)
@log_debug_function_name
async def case_options(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data
    if action == config.ACTION_NAME_SPLIT_BY_DURATION:
        await state.update_data(action=action)
        await state.set_state(StateFormMenuExtra.split_by_duration)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=config.DESCRIPTION_BLOCK_SPLIT_BY_DURATION,
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
            text=DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT)
        await state.set_state(StateFormMenuExtra.url)

    elif action == config.ACTION_NAME_BITRATE_CHANGE:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=config.DESCRIPTION_BLOCK_BITRATE,
            reply_markup=create_inline_keyboard([
                BITRATE_VALUES_ROW_ONE,
                BITRATE_VALUES_ROW_TWO]))
        await state.set_state(StateFormMenuExtra.bitrate)

    elif action == config.ACTION_NAME_SUBTITLES_SHOW_OPTIONS:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=config.DESCRIPTION_BLOCK_SUBTITLES,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='🔮 Retrieve All', callback_data=config.ACTION_NAME_SUBTITLES_GET_ALL),
                InlineKeyboardButton(text='🔍 Search by Word', callback_data=config.ACTION_NAME_SUBTITLES_SEARCH_WORD)]]))
        await state.set_state(StateFormMenuExtra.subtitles_options)

    elif action == config.ACTION_NAME_SLICE:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=config.DESCRIPTION_BLOCK_SLICE_PART_ONE)
        await state.set_state(StateFormMenuExtra.slice_start_time)

    elif action == config.ACTION_NAME_TRANSLATE:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT)
        await state.set_state(StateFormMenuExtra.url)

    elif action == config.ACTION_NAME_OPTIONS_EXIT:
        await state.clear()
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            text=DESCRIPTION_BLOCK_OKAY_AFTER_EXIT)


@dp.callback_query(StateFormMenuExtra.split_by_duration)
@log_debug_function_name
async def case_split_by_duration_processing(callback_query: types.CallbackQuery, state: FSMContext):
    split_duration = callback_query.data
    if split_duration not in SPLIT_DURATION_VALUES_ALL:
        await bot.edit_message_text(f'<b>❌ An unexpected or invalid split duration value was received.</b>\n(split_duration={split_duration})')
        await state.clear()

    await state.update_data(split_duration=split_duration)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
        text=DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.callback_query(StateFormMenuExtra.bitrate)
@log_debug_function_name
async def case_bitrate_processing(callback_query: types.CallbackQuery, state: FSMContext):
    bitrate = callback_query.data
    if bitrate not in BITRATE_VALUES_ALL:
        await bot.edit_message_text(f'<b>❌ An unexpected or invalid bitrate value was received.</b>\n(bitrate={bitrate})')
        await state.clear()

    await state.update_data(bitrate=bitrate)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
        text=DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.callback_query(StateFormMenuExtra.subtitles_options)
@log_debug_function_name
async def case_subtitles_options_processing(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data
    if action == config.ACTION_NAME_SUBTITLES_GET_ALL:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
            text=DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT)
        await state.set_state(StateFormMenuExtra.url)

    elif action == config.ACTION_NAME_SUBTITLES_SEARCH_WORD:
        await state.update_data(action=action)
        await bot.edit_message_text(
            chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
            text=f"🔍 Enter the word to search for in subtitles:")
        await state.set_state(StateFormMenuExtra.subtitles_search_word)


@dp.message(StateFormMenuExtra.subtitles_search_word)
@log_debug_function_name
async def case_subtitles_search_word(message: types.Message, state: FSMContext):
    subtitles_search_word = message.text
    await state.update_data(subtitles_search_word=subtitles_search_word)
    await message.answer(text=DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.message(StateFormMenuExtra.slice_start_time)
@log_debug_function_name
async def case_slice_start_time(message: types.Message, state: FSMContext):
    start_time = message.text
    start_time = time_hhmmss_check_and_convert(start_time)
    if start_time is None:
        await state.clear()
        await message.answer(f'❌ Invalid time format. Please try again.')

    await state.update_data(slice_start_time=start_time)
    await message.answer(config.DESCRIPTION_BLOCK_SLICE_PART_TWO)
    await state.set_state(StateFormMenuExtra.slice_end_time)


@dp.message(StateFormMenuExtra.slice_end_time)
@log_debug_function_name
async def case_slice_start_time(message: types.Message, state: FSMContext):
    end_time = message.text
    end_time = time_hhmmss_check_and_convert(end_time)
    if end_time is None:
        await state.clear()
        await message.answer(f'❌ Invalid time format. Please try again.')

    data = await state.get_data()
    start_time = int(data.get('slice_start_time', ''))
    if start_time >= end_time:
        await state.clear()
        await message.answer(f'❌ Start time must be earlier than the end time. Please try again.')

    await state.update_data(slice_end_time=end_time)
    await message.answer(text=DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT)
    await state.set_state(StateFormMenuExtra.url)


@dp.message(StateFormMenuExtra.url)
@log_debug_function_name
async def case_url(message: Message, state: FSMContext) -> None:
    url = message.text
    data = await state.get_data()
    await state.clear()

    if not get_big_youtube_move_id(url):
        await message.answer(f'<b>❌ Unable to extract a valid YouTube URL from your input.</b>\n(url={url})')
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
@log_debug_function_name
async def handler_autodownload_switch_state(message: types.Message) -> None:
    toggle = await autodownload_chat_manager.toggle_chat_state(message.sender_chat.id)
    if toggle:
        await message.answer('💾 Added Chat ID to autodownloads.\n\nCall /autodownload again to remove.')
    else:
        await message.answer('♻️🗑 Removed Chat ID to autodownloads.\n\nCall /autodownload again to add.')


@dp.message(Command('autodownload'))
@log_debug_function_name
async def handler_autodownload_command_in_bot(message: types.Message) -> None:
    await message.answer('<b>❌ This command works only in Channels.</b>\nPlease add this bot to the list of admins and try again.')


@dp.callback_query(lambda c: c.data.startswith('download:'))
@log_debug_function_name
async def process_callback_button(callback_query: types.CallbackQuery):
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
    logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=inspect.currentframe().f_code.co_name))

    action = ''
    attributes = {}

    matching_attr = next((attr for attr in config.CLI_ACTIVATION_ALL if attr in text), None)

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

    if matching_attr in config.CLI_ACTIVATION_MUSIC:
        action = config.ACTION_NAME_MUSIC

    if matching_attr in config.CLI_ACTIVATION_TRANSLATION:
        action = config.ACTION_NAME_TRANSLATE
        attributes['overlay'] = config.TRANSLATION_OVERLAY_ORIGIN_AUDIO_TRANSPARENCY

        parts = text.split(matching_attr)
        if len(parts) > 1:
            trans_param = parts[1].strip()
            try:
                overlay_value = float(trans_param)
                overlay_value = max(0.0, min(overlay_value, 1.0))
                attributes['overlay'] = overlay_value
            except Exception as err:
                logger.info('🔷 Cant convert input cli val to float. Continue:')

    if matching_attr in config.CLI_ACTIVATION_FORCE_REDOWNLOAD:
        action = config.ACTION_NAME_FORCE_REDOWNLOAD

    return action, attributes


@dp.message()
@log_debug_function_name
async def handler_message(message: Message):
    cli_action, cli_attributes = cli_action_parser(message.text)

    if cli_action == config.ACTION_NAME_SUBTITLES_GET_ALL:
        if cli_attributes['url']:
            await make_subtitles(
                bot=bot, sender_id=message.from_user.id, url=cli_attributes['url'], reply_message_id=message.message_id)

    elif cli_action == config.ACTION_NAME_SUBTITLES_SEARCH_WORD:
        if cli_attributes['url'] and cli_attributes['word']:
            await make_subtitles(
                bot=bot, sender_id=message.from_user.id, url=cli_attributes['url'], reply_message_id=message.message_id,
                word=cli_attributes['word'])

    elif cli_action == config.ACTION_NAME_MUSIC:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
            message_text=message.text,
            configurations={'action': config.ACTION_NAME_BITRATE_CHANGE, 'bitrate': config.ACTION_MUSIC_HIGH_BITRATE})

    elif cli_action == config.ACTION_NAME_TRANSLATE:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
            message_text=message.text, configurations={
                'action': cli_action,
                'overlay': cli_attributes.get('overlay', '')
            })
    elif cli_action == config.ACTION_NAME_FORCE_REDOWNLOAD:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
            message_text=message.text, configurations={'action': cli_action})
    else:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
            message_text=message.text)


@dp.channel_post()
@log_debug_function_name
async def handler_channel_post(message: Message):
    cli_action, cli_attributes = cli_action_parser(message.text)

    logger.debug(f'message.sender_chat.id={message.sender_chat.id}')
    logger.debug(f'message.from_user.id={message.from_user.id}')

    if cli_action == config.ACTION_NAME_SUBTITLES_GET_ALL:
        if cli_attributes['url']:
            await make_subtitles(
                bot=bot, sender_id=message.sender_chat.id, url=cli_attributes['url'], reply_message_id=message.message_id)
            return

    if cli_action == config.ACTION_NAME_SUBTITLES_SEARCH_WORD:
        if cli_attributes['url'] and cli_attributes['word']:
            await make_subtitles(
                bot=bot, sender_id=message.sender_chat.id, url=cli_attributes['url'], reply_message_id=message.message_id,
                word=cli_attributes['word'])
            return

    if cli_action == config.ACTION_NAME_MUSIC:
        await job_downloading(
            bot=bot, sender_id=message.sender_chat.id, reply_to_message_id=message.message_id,
            message_text=message.text, configurations={'action': cli_action, 'bitrate': config.ACTION_MUSIC_HIGH_BITRATE})
        return

    if cli_action == config.ACTION_NAME_FORCE_REDOWNLOAD:
        await job_downloading(
            bot=bot, sender_id=message.sender_chat.id, reply_to_message_id=message.message_id,
            message_text=message.text, configurations={'action': cli_action})
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
        text=f'Choose one of these options. \nExit in seconds: {config.BUTTON_CHANNEL_WAITING_DOWNLOADING_TIMEOUT_SEC}',
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text='📣 Just Download️', callback_data=callback_data)]]))

    callback_storage_manager.add_key(key=callback_data)

    await asyncio.sleep(config.BUTTON_CHANNEL_WAITING_DOWNLOADING_TIMEOUT_SEC)

    if callback_storage_manager.check_key_inside(key=callback_data):
        await info_message.delete()


async def run_bot_asynchronously():
    logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=inspect.currentframe().f_code.co_name))

    me = await bot.get_me()
    logger.info(f'🚀 Telegram bot: f{me.full_name} https://t.me/{me.username}')

    # Say Hello at startup to bot owner by its ID
    if config.OWNER_BOT_ID_TO_SAY_HELLOW:
        try:
            await bot.send_message(chat_id=config.OWNER_BOT_ID_TO_SAY_HELLOW, text='🟩')
            await bot.send_message(chat_id=config.OWNER_BOT_ID_TO_SAY_HELLOW, text=TEXT_SAY_HELLO_BOT_OWNER_AT_STARTUP)
        except Exception as e:
            logger.error(f'❌ Error with Say hello. Maybe user id is not valid: \n{e}')

    # todo
    if not (config.KEEP_DATA_FILES or config.DEBUG_MODE):
        logger.info('♻️🗑 Remove last files in DATA')
        remove_all_in_dir(data_dir)

    # todo empty cron
    await asyncio.gather(
        run_periodically(30, empty_data_dir_by_cron, {
            'age': config.REMOVE_AGED_DATA_FILES_SEC,
            'keep_files': config.KEEP_DATA_FILES,
            'folder': data_dir,
        }),
        run_periodically(43200, update_pip_package_ytdlp, {}),
        dp.start_polling(bot),
        run_periodically(600, autodownload_chat_manager.save_hashed_chat_ids, {}))


def handle_suspend(_signal, _frame):
    logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=inspect.currentframe().f_code.co_name))

    """Handle the SIGTSTP signal (Ctrl+Z)."""
    logger.info("Process suspended. Exiting...")
    # No need to pause manually; the system handles the suspension
    sys.exit(0)


def handle_interrupt(_signal, _frame):
    logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=inspect.currentframe().f_code.co_name))

    """Handle the SIGINT signal (Ctrl+C)."""
    logger.info("Process interrupted by user. Exiting...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGTSTP, handle_suspend)
    signal.signal(signal.SIGINT, handle_interrupt)
    logger.info("Starting ... Press Ctrl+C to stop or Ctrl+Z to suspend.")

    _parser = argparse.ArgumentParser(
        description='🥭 Bot. Youtube to audio telegram bot with subtitles',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    if config.DEBUG_MODE:
        logger.setLevel(logging.DEBUG)
        logger.debug('🎃 DEBUG mode is set. All debug messages will be in stdout.')

    logger.info(f'💎 Version of [{config.PACKAGE_NAME}]: {version(config.PACKAGE_NAME)}')

    token = os.getenv(config.ENV_NAME_TG_TOKEN, config.TELEGRAM_VALID_TOKEN_IMAGINARY_DEFAULT)
    if not token:
        logger.error(f'❌ No {config.ENV_NAME_TG_TOKEN} variable set in env. Make add and restart bot.')
        return

    # todo add salt to use it
    if not os.getenv(config.ENV_NAME_HASH_SALT, ''):
        logger.error(f'❌ No {config.ENV_NAME_HASH_SALT} variable set in .env. Make add any random hash with key SALT!')
        return

    logger.info('🗂 data_dir: ' + f'{data_dir.resolve().as_posix()}')

    global bot
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode='HTML'))

    dp.include_router(router)

    try:
        asyncio.run(run_bot_asynchronously())
    except Exception as err:
        logger.debug(f'🦀 Send Error')
        logger.error(err)


if __name__ == "__main__":
    main()
