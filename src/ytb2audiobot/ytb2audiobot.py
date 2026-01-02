
import logging
import os
import argparse
import asyncio
import signal
import sys
from functools import wraps
from importlib.metadata import version



from aiogram import Bot, Dispatcher, types, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from ytb2audiobot import config
from ytb2audiobot.autodownload_chat_manager import AutodownloadChatManager
from ytb2audiobot.callback_storage_manager import StorageCallbackManager
from ytb2audiobot.config import START_AND_HELP_TEXT, TEXT_SAY_HELLO_BOT_OWNER_AT_STARTUP
from ytb2audiobot.cron import run_periodically, empty_data_dir_by_cron
from ytb2audiobot.hardworkbot import job_downloading, make_subtitles
from ytb2audiobot.logger import logger
from ytb2audiobot.utils import remove_all_in_dir, get_data_dir, get_big_youtube_move_id, create_inline_keyboard
from ytb2audiobot.cron import update_pip_package_ytdlp


bot = Bot(token=config.TELEGRAM_VALID_TOKEN_IMAGINARY_DEFAULT)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

data_dir = get_data_dir()

callback_storage_manager = StorageCallbackManager()

autodownload_chat_manager = AutodownloadChatManager(path=config.AUTO_DOWNLOAD_CHAT_IDS_STORAGE_FILENAME)


def log_debug_function_name(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        # Log the function call
        logger.debug(config.LOG_FORMAT_CALLED_FUNCTION.substitute(fname=func.__name__))
        try:
            return await func(message, *args, **kwargs)
        except Exception as e:
            logger.error(f"An error occurred in {func.__name__}: {e}", exc_info=True)
    return wrapper


@dp.message(CommandStart())
@dp.message(Command('help'))
@log_debug_function_name
async def handler_command_start_and_help(message: Message) -> None:
    await message.answer(text=START_AND_HELP_TEXT, parse_mode='HTML')


@dp.message(Command('cli'))
async def handler_command_cli_info(message: Message) -> None:
    await message.answer(text=config.DESCRIPTION_BLOCK_CLI , parse_mode='HTML')


@dp.channel_post(Command('autodownload'))
async def handler_autodownload_switch_state(message: types.Message) -> None:
    toggle = await autodownload_chat_manager.toggle_chat_state(message.sender_chat.id)
    if toggle:
        await message.answer('💾 Added Chat ID to autodownloads.\n\nCall /autodownload again to remove.')
    else:
        await message.answer('♻️🗑 Removed Chat ID to autodownloads.\n\nCall /autodownload again to add.')


@dp.message(Command('autodownload'))
async def handler_autodownload_command_in_bot(message: types.Message) -> None:
    await message.answer('<b>❌ This command works only in Channels.</b>\nPlease add this bot to the list of admins and try again.')


def cli_action_parser(text: str):
    action = ''
    attributes = {}

    attributes_text = text.split(maxsplit=1)[1] if " " in text else ""

    matching_attr = next((attr for attr in config.CLI_ACTIVATION_ALL if attr in attributes_text), None)
    logger.debug(f'🍔 cli_action_parser: {matching_attr}')

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

    if matching_attr in config.CLI_ACTIVATION_SUMMARIZE:
        action = config.ACTION_NAME_SUMMARIZE

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
            except Exception as e:
                logger.error(f'🔷 Cant convert input cli val to float. Continue: \n{e}')

    if matching_attr in config.CLI_ACTIVATION_FORCE_REDOWNLOAD:
        action = config.ACTION_NAME_FORCE_REDOWNLOAD

    return action, attributes


@dp.message()
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

    elif cli_action == config.ACTION_NAME_SUMMARIZE:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
            message_text=message.text, configurations={'action': cli_action})
    else:
        await job_downloading(
            bot=bot, sender_id=message.from_user.id, reply_to_message_id=message.message_id,
            message_text=message.text)


@dp.channel_post()
async def handler_channel_post(message: Message):
    cli_action, cli_attributes = cli_action_parser(message.text)

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
    """Handle the SIGTSTP signal (Ctrl+Z)."""
    logger.info("🔫 Process suspended. Exiting...")
    # No need to pause manually; the system handles the suspension
    sys.exit(0)


def handle_interrupt(_signal, _frame):
    """Handle the SIGINT signal (Ctrl+C)."""
    logger.info("🔫 Process interrupted by user. Exiting...")
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

    logger.info('🗂 Data Dir: ' + f'{data_dir.resolve().as_posix()}')

    global bot
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode='HTML'))

    dp.include_router(router)

    try:
        asyncio.run(run_bot_asynchronously())
    except Exception as e:
        logger.error(f'🦀 Error Running asyncio.run: \n{e}')


if __name__ == "__main__":
    main()
