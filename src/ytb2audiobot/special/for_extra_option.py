from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from audio2splitted.audio2splitted import DURATION_MINUTES_MIN, DURATION_MINUTES_MAX

from src.ytb2audiobot import config, logger
from src.ytb2audiobot.utils import remove_m4a_file_if_exists, read_file
from src.ytb2audiobot.ytb2audiobot import dp

command = dict()
context = dict()
movie_meta = dict()


async def func():
    if command.get('name') == 'split':
        if not command.get('params'):
            context['error'] = '🟥️ Split. No params of split command. Set param of minutes to split'
            return context
        param = command.get('params')[0]
        if not param.isnumeric():
            context['error'] = '🟥️ Split. Param if split [not param.isnumeric()]'
            return context

        param = int(param)
        if param < DURATION_MINUTES_MIN or DURATION_MINUTES_MAX < param:
            context['error'] = (f'🟥️ Split. Param if split = {param} '
                                f'is out of [{DURATION_MINUTES_MIN}, {DURATION_MINUTES_MAX}]')
            return context

        # Make split with Default split
        movie_meta['threshold_seconds'] = 1
        movie_meta['split_duration_minutes'] = param

    elif command.get('name') == 'bitrate':
        if not command.get('params'):
            context['error'] = '🟥️ Bitrate. No essential param of bitrate.'
            return context

        param = command.get('params')[0]
        if not param.isnumeric():
            context['error'] = '🟥️ Bitrate. Essential param is not numeric'
            return context

        param = int(param)
        if param < config.AUDIO_BITRATE_MIN or config.AUDIO_BITRATE_MAX < param:
            context['error'] = (f'🟥️ Bitrate. Param {param} is out of [{config.AUDIO_BITRATE_MIN},'
                                f' ... , {config.AUDIO_BITRATE_MAX}]')
            return context

        await remove_m4a_file_if_exists(movie_meta.get('id'), movie_meta['store'])

        movie_meta['ytdlprewriteoptions'] = movie_meta.get('ytdlprewriteoptions').replace('48k', f'{param}k')
        movie_meta['additional_meta_text'] = f'\n{param}k bitrate'


@dp.message(Command('timers'))
async def timers_show_handler(message: Message, command: CommandObject) -> None:
    logger.debug('🍅 timers_show_handler():')

    global bot
    if not config.TIMERS_FILE_PATH.exists():
        await bot.send_message(chat_id=message.from_user.id, text='No timers file')

    data_text = await read_file(config.TIMERS_FILE_PATH)

    # Inverse and cut and inverse back
    if len(data_text) > config.MAX_TELEGRAM_BOT_TEXT_SIZE:
        data_text = '\n'.join(data_text.split('\n')[::-1])
        data_text = data_text[:config.MAX_TELEGRAM_BOT_TEXT_SIZE - 8]
        data_text = '...\n' + '\n'.join(data_text.split('\n')[::-1])

    await bot.send_message(chat_id=message.from_user.id, text=data_text)