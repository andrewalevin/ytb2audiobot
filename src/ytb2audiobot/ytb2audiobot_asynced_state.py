import argparse
import asyncio
import logging
import re
import sys
from string import Template

from aiogram import Bot, Dispatcher, html, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import os
import pathlib
from dotenv import load_dotenv
from telegram.constants import ParseMode
from mutagen.mp4 import MP4
from datetime import timedelta

from ytb2audio.ytb2audio import YT_DLP_OPTIONS_DEFAULT, get_youtube_move_id, download_thumbnail_by_movie_meta, \
    download_audio_by_movie_meta
from audio2splitted.audio2splitted import get_split_audio_scheme, make_split_audio, DURATION_MINUTES_MIN, \
    DURATION_MINUTES_MAX

from ytb2audiobot.commands import get_command_params_of_request
from ytb2audiobot.subtitles import get_subtitles
from ytb2audiobot.thumbnail import image_compress_and_resize
from ytb2audiobot.timecodes import filter_timestamp_format
from ytb2audiobot.utils import delete_file_async, capital2lower
from ytb2audiobot.timecodes import get_timecodes
from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.pytube import get_movie_meta


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

MAX_TELEGRAM_BOT_TEXT_SIZE = 4095

TASK_TIMEOUT_SECONDS = 60 * 30

CAPTION_HEAD_TEMPLATE = Template('''
$partition $title
<a href=\"youtu.be/$movieid\">youtu.be/$movieid</a> [$duration] $additional
$author

$timecodes
''')


pushed_button = False


def filename_m4a(text):
    name = (re.sub(r'[^\w\s\-\_\(\)\[\]]', ' ', text)
            .replace('    ', ' ')
            .replace('   ', ' ')
            .replace('  ', ' ')
            .strip())
    return f'{name}.m4a'


async def get_mp4object(path: pathlib.Path):
    path = pathlib.Path(path)
    try:
        mp4object = MP4(path.as_posix())
    except Exception as e:
        return {}
    return mp4object


async def delete_files_by_movie_id(datadir, movie_id):
    for file in list(filter(lambda f: (f.name.startswith(movie_id)), datadir.iterdir())):
        await delete_file_async(file)


async def processing_commands(command: dict):
    if not command.get('post_status_id'):
        print('🍟 Create post_status message')
        post_status = await bot.send_message(
            chat_id=command.get('sender_id'),
            reply_to_message_id=command.get('message_id'),
            text=f'⌛️ Starting ... '
        )
        command['post_status_id'] = post_status.message_id

    if not (movie_id := get_youtube_move_id(command.get('url'))):
        return await bot.edit_message_text('🟥️ Not a Youtube Movie ID')

    movie_meta = dict()
    movie_meta['id'] = movie_id
    movie_meta['title'] = ''
    movie_meta['author'] = ''
    movie_meta['description'] = ''
    movie_meta['thumbnail_url'] = ''
    movie_meta['thumbnail_path'] = None
    movie_meta['additional'] = ''
    movie_meta['duration'] = 0
    movie_meta['timecodes'] = ['']

    movie_meta['threshold_seconds'] = AUDIO_SPLIT_THRESHOLD_MINUTES * 60
    movie_meta['split_duration_minutes'] = 39
    movie_meta['ytdlprewriteoptions'] = YT_DLP_OPTIONS_DEFAULT
    movie_meta['additional_meta_text'] = ''
    movie_meta['store'] = data_dir

    if not command.get('name'):
        return await bot.edit_message_text(
            chat_id=command.get('sender_id'),
            message_id=command.get('post_status_id'),
            text='🟥️ No Command'
        )

    if command.get('name') == 'split':
        # Make split with Default split
        movie_meta['threshold_seconds'] = 1

        if command.get('params'):
            param = command.get('params')[0]
            if not param.isnumeric():
                return await bot.edit_message_text(
                    chat_id=command.get('sender_id'),
                    message_id=command.get('post_status_id'),
                    text='🟥️ Param if split [not param.isnumeric()]')
            param = int(param)
            if param < DURATION_MINUTES_MIN or DURATION_MINUTES_MAX < param:
                return await bot.edit_message_text(
                    chat_id=command.get('sender_id'),
                    message_id=command.get('post_status_id'),
                    text=f'🟥️ Param if split = {param} is out of [{DURATION_MINUTES_MIN}, {DURATION_MINUTES_MAX}]')
            movie_meta['split_duration_minutes'] = param

    elif command.get('name') == 'bitrate':
        if not command.get('params'):
            return await bot.edit_message_text('🟥️ Bitrate. Not params in command context')

        param = command.get('params')[0]
        if not param.isnumeric():
            return await bot.edit_message_text('🟥️ Bitrate. Essential param is not numeric')

        param = int(param)
        if param < AUDIO_BITRATE_MIN or AUDIO_BITRATE_MAX < param:
            return await bot.edit_message_text(f'🟥️ Bitrate. Param {param} '
                                               f'is out of [{AUDIO_BITRATE_MIN}, ... , {AUDIO_BITRATE_MAX}]')

        movie_meta['ytdlprewriteoptions'] = movie_meta['ytdlprewriteoptions'].replace('48k', f'{param}k')
        movie_meta['additional_meta_text'] = f'{param}k bitrate'

    elif command.get('name') == 'subtitles':
        param = ''
        if command.get('params'):
            params = command.get('params')
            param = ' '.join(params)

        text, _err = await get_subtitles(movie_id, param)
        if _err:
            return await bot.edit_message_text(f'🟥️ Subtitles: {_err}')
        if not text:
            return await bot.edit_message_text(f'🟥️ Error Subtitle: no text')

        if len(text) < MAX_TELEGRAM_BOT_TEXT_SIZE:
            await bot.edit_message_text(
                chat_id=command.get('sender_id'),
                message_id=command.get('post_status_id'),
                text=text,
                parse_mode='HTML')
            return
        else:
            await bot.send_document(
                chat_id=command.get('sender_id'),
                document=BufferedInputFile(text.encode('utf-8'), filename=f'subtitles-{movie_id}.txt'),
                reply_to_message_id=command.get('message_id'),
            )
            #todo
            await post_status.delete()
            return

    await bot.edit_message_text(
        chat_id=command.get('sender_id'),
        message_id=command.get('post_status_id'),
        text=f'⌛️ Downloading ... ')

    movie_meta = await get_movie_meta(movie_meta, movie_id)

    tasks = [
        download_audio_by_movie_meta(movie_meta),
        download_thumbnail_by_movie_meta(movie_meta)
    ]
    results = await asyncio.gather(*tasks)
    print("🌵 Gather 1. All tasks completed")

    audio = results[0]
    movie_meta['thumbnail_path'] = results[1]

    if not audio.exists():
        return await bot.edit_message_text(
            chat_id=command.get('sender_id'),
            message_id=command.get('post_status_id'),
            text=f'🔴 Download. Not exists file')

    if not pathlib.Path(movie_meta['thumbnail_path']).exists():
        return await bot.edit_message_text(
            chat_id=command.get('sender_id'),
            message_id=command.get('post_status_id'),
            text=f'🟠 Thumbnail. Not exists.')

    scheme = get_split_audio_scheme(
        source_audio_length=movie_meta['duration'],
        duration_seconds=movie_meta['split_duration_minutes'] * 60,
        delta_seconds=AUDIO_SPLIT_DELTA_SECONDS,
        magic_tail=True,
        threshold_seconds=movie_meta['threshold_seconds']
    )

    tasks = [
        image_compress_and_resize(movie_meta['thumbnail_path']),
        make_split_audio(
            audio_path=audio,
            audio_duration=movie_meta['duration'],
            output_folder=data_dir,
            scheme=scheme
        ),
        get_mp4object(audio)
    ]
    results = await asyncio.gather(*tasks)
    print("🌵🌵 Gather 2. All tasks completed")

    thumbnail_compressed = results[0]
    audios = results[1]
    mp4obj = results[2]

    if not thumbnail_compressed.exists():
        await bot.edit_message_text(
            chat_id=command.get('sender_id'),
            message_id=command.get('post_status_id'),
            text=f'🟠 Thumbnail Compression. Problem with image compression.')
    else:
        movie_meta['thumbnail_path'] = thumbnail_compressed

    if not mp4obj:
        await bot.edit_message_text(
            chat_id=command.get('sender_id'),
            message_id=command.get('post_status_id'),
            text=f'🟠 MP4 Mutagen .m4a.')

    print('🤠 Before Uploading: post_status_id: ', command.get('post_status_id'))

    await bot.edit_message_text(
        chat_id=command.get('sender_id'),
        message_id=command.get('post_status_id'),
        text='⌛ Uploading to Telegram ... ')

    print('🤠🤠 After-1: ')

    if not movie_meta['description'] and mp4obj.get('desc'):
        movie_meta['description'] = mp4obj.get('desc')

    timecodes, _err = await get_timecodes(scheme, movie_meta['description'])
    if _err:
        await bot.edit_message_text(
            chat_id=command.get('sender_id'),
            message_id=command.get('post_status_id'),
            text=f'🟠 Timecodes. Error creation.')

    caption_head = CAPTION_HEAD_TEMPLATE.safe_substitute(
        movieid=movie_meta['id'],
        title=capital2lower(movie_meta['title']),
        author=capital2lower(movie_meta['author']),
        additional=movie_meta['additional']
    )
    filename = filename_m4a(movie_meta['title'])
    for idx, audio_part in enumerate(audios, start=1):
        print('💜 Idx: ', idx, 'part: ', audio_part)

        caption = Template(caption_head).safe_substitute(
            partition='' if len(audios) == 1 else f'[Part {idx} of {len(audios)}]',
            timecodes=timecodes[idx-1],
            duration=filter_timestamp_format(timedelta(seconds=audio_part.get('duration')))
        )

        await bot.send_audio(
            chat_id=command.get('sender_id'),
            reply_to_message_id=command.get('message_id') if idx == 1 else None,
            audio=FSInputFile(
                path=audio_part['path'],
                filename=filename if len(audios) == 1 else f'p{idx}_of{len(audios)} {filename}',
            ),
            duration=audio_part['duration'],
            thumbnail=FSInputFile(
                path=movie_meta['thumbnail_path']),
            caption=caption if len(caption) < TG_CAPTION_MAX_LONG else caption[:TG_CAPTION_MAX_LONG - 8] + '\n...',
            parse_mode=ParseMode.HTML
        )

    await bot.delete_message(
        chat_id=command.get('sender_id'),
        message_id=command.get('message_id')
    )

    if not keep_data_files:
        print('🗑❌ Empty Files')
        await delete_files_by_movie_id(data_dir, movie_id)

    print(f'💚 Success! [{movie_id}]\n')


class Form(StatesGroup):
    age = State()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


@dp.callback_query(lambda c: c.data.startswith('download:'))
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    print('🚦 callback_query.data: ', callback_query.data)
    print('🚦🚦 callback_query.message.message_id: ', callback_query.message.message_id)
    print()

    global pushed_button
    pushed_button = True
    state_with: FSMContext = FSMContext(
        storage=dp.storage,
        key=StorageKey(
            chat_id=callback_query.from_user.id,
            user_id=callback_query.from_user.id,
            bot_id=bot.id))

    await state_with.set_state('pushed')
    await state_with.update_data({"data_name": 'pushed'})

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
async def message_parser_handler(message: Message) -> None:
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

    print('📬 Message.text: ', message.text)
    command_context = get_command_params_of_request(message.text)
    print('🔫 Command_context After: ', command_context)
    print()

    if not command_context.get('url'):
        return

    command_context['message_id'] = message.message_id
    command_context['sender_id'] = sender_id

    print('🪁 command_context: ', command_context)
    print()

    state_with: FSMContext = FSMContext(
        storage=dp.storage,
        key=StorageKey(
            chat_id=sender_id,
            user_id=sender_id,
            bot_id=bot.id))
    await state_with.set_state('showed')

    if sender_type != 'user' and not command_context.get('name'):

        print('🐿 Case Callack: ')

        callback_data = 'download' + ':_:' + command_context.get('url') + ':_:' + str(message.message_id)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📣 Just Download️", callback_data=callback_data), ], ],
        )

        timer = 8
        text = f"Choose one of these options. \nExit in seconds: 8"
        post = await message.reply(text=text, reply_markup=keyboard)
        await asyncio.sleep(8)
        print('😈 After 8 sec: pushed_button: ', pushed_button)

        state_info = await state_with.get_state()
        print('😈😈 state_info: ', state_info)

        data_state = await state_with.get_data()
        print('😈😈😈 data_state: ', data_state)

        return

    if not command_context.get('name'):
        command_context['name'] = 'download'

    print('🍒 command_context: ', command_context)
    task = asyncio.create_task(processing_commands(command_context))
    await asyncio.wait_for(task, timeout=TASK_TIMEOUT_SECONDS)


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
