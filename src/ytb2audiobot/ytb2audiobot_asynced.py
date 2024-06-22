import argparse
import asyncio
import logging
import re
import sys
from string import Template

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, BufferedInputFile
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

dp = Dispatcher()

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


async def processing_commands(message: Message, command: dict, sender_id):
    post_status = await message.reply(f'⌛️ Starting ... ')

    if not (movie_id := get_youtube_move_id(message.text)):
        return await post_status.edit_text('🟥️ Not a Youtube Movie ID')

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
        return await post_status.edit_text('🟥️ No Command')

    if command.get('name') == 'split':
        # Make split with Default split
        movie_meta['threshold_seconds'] = 1

        if command.get('params'):
            param = command.get('params')[0]
            if not param.isnumeric():
                return await post_status.edit_text('🟥️ Param if split [not param.isnumeric()]')
            param = int(param)
            if param < DURATION_MINUTES_MIN or DURATION_MINUTES_MAX < param:
                return await post_status.edit_text(f'🟥️ Param if split = {param} '
                                                   f'is out of [{DURATION_MINUTES_MIN}, {DURATION_MINUTES_MAX}]')
            movie_meta['split_duration_minutes'] = param

    elif command.get('name') == 'bitrate':
        if not command.get('params'):
            return await post_status.edit_text('🟥️ Bitrate. Not params in command context')

        param = command.get('params')[0]
        if not param.isnumeric():
            return await post_status.edit_text('🟥️ Bitrate. Essential param is not numeric')

        param = int(param)
        if param < AUDIO_BITRATE_MIN or AUDIO_BITRATE_MAX < param:
            return await post_status.edit_text(f'🟥️ Bitrate. Param {param} '
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
            return await post_status.edit_text(f'🟥️ Subtitles: {_err}')
        if not text:
            return await post_status.edit_text(f'🟥️ Error Subtitle: no text')

        if len(text) < MAX_TELEGRAM_BOT_TEXT_SIZE:
            await message.reply(text=text, parse_mode='HTML')
            await post_status.delete()
            return
        else:
            await bot.send_document(
                chat_id=sender_id,
                document=BufferedInputFile(text.encode('utf-8'), filename=f'subtitles-{movie_id}.txt'),
                reply_to_message_id=message.message_id,
            )
            await post_status.delete()
            return

    await post_status.edit_text(f'⌛️ Downloading ... ')

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
        return await post_status.edit_text(f'🔴 Download. Not exists file')

    if not pathlib.Path(movie_meta['thumbnail_path']).exists():
        return await post_status.edit_text(f'🟠 Thumbnail. Not exists.')

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
        await post_status.edit_text(f'🟠 Thumbnail Compression. Problem with image compression.')
    else:
        movie_meta['thumbnail_path'] = thumbnail_compressed

    if not mp4obj:
        await post_status.edit_text(f'🟠 MP4 Mutagen .m4a.')

    await post_status.edit_text('⌛ Uploading to Telegram ... ')

    if not movie_meta['description'] and mp4obj.get('desc'):
        movie_meta['description'] = mp4obj.get('desc')

    timecodes, _err = await get_timecodes(scheme, movie_meta['description'])
    if _err:
        await post_status.edit_text(f'🟠 Timecodes. Error creation.')

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
            chat_id=sender_id,
            reply_to_message_id=message.message_id if idx == 1 else None,
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

    await post_status.delete()

    if not keep_data_files:
        print('🗑❌ Empty Files')
        await delete_files_by_movie_id(data_dir, movie_id)

    print(f'💚 Success! [{movie_id}]\n')


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


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

    command_context = get_command_params_of_request(message.text)

    if not command_context.get('url'):
        return

    if sender_type != 'user' and not command_context.get('name'):
        return

    if not command_context.get('name'):
        command_context['name'] = 'download'

    print('🍒 command_context: ', command_context)
    task = asyncio.create_task(processing_commands(message, command_context, sender_id))
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
