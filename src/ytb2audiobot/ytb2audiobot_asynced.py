import argparse
import asyncio
import logging
import re
import sys
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

from utils4audio.duration import get_duration_asynced
from ytb2audio.ytb2audio import download_audio, download_thumbnail, YT_DLP_OPTIONS_DEFAULT, get_youtube_move_id
from audio2splitted.audio2splitted import get_split_audio_scheme, make_split_audio, DURATION_MINUTES_MIN, \
    DURATION_MINUTES_MAX

from ytb2audiobot.subtitles import get_subtitles
from ytb2audiobot.commands import get_command_params_of_request
from ytb2audiobot.thumbnail import image_compress_and_resize
from ytb2audiobot.timecodes import capital2lower_letters_filter, get_timecodes_text, get_timestamps_group, \
    filter_timestamp_format
from ytb2audiobot.utils import delete_file_async, create_directory_async

from ytb2audiobot.timecodes import get_timecodes

dp = Dispatcher()

load_dotenv()
token = os.environ.get("TG_TOKEN")

bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

DATA_DIR = '../../data'

keepfiles_global = False

SEND_AUDIO_TIMEOUT = 120
TELEGRAM_CAPTION_TEXT_LONG_MAX = 1024-8

AUDIO_SPLIT_THRESHOLD_MINUTES = 120
AUDIO_SPLIT_DELTA_SECONDS = 5

AUDIO_BITRATE_MIN = 48
AUDIO_BITRATE_MAX = 320

MAX_TELEGRAM_BOT_TEXT_SIZE = 4095

TASK_TIMEOUT_SECONDS = 60 * 30


def output_filename_in_telegram(text):
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
        return {}, e

    return mp4object, ''


async def get_data_dir():
    data_dir = pathlib.Path(DATA_DIR)
    return await create_directory_async(data_dir)


async def delete_files_by_movie_id(data_dir, movie_id):
    for file in list(filter(lambda file: (file.name.startswith(movie_id)), data_dir.iterdir())):
        await delete_file_async(file)


def get_title(mp4obj, movie_id):
    title = str(movie_id)
    if mp4obj.get('\xa9nam'):
        title = mp4obj.get('\xa9nam')[0]

    return capital2lower_letters_filter(title)


def get_youtube_link_html(movie_id):
    url_youtube = f'youtu.be/{movie_id}'
    return f'<a href=\"{url_youtube}\">{url_youtube}</a>'

async def processing_commands(message: Message, command: dict, sender_id):
    post_status = await message.reply(f'⌛️ Starting ... ')

    if not (movie_id := get_youtube_move_id(message.text)):
        return await post_status.edit_text('🟥️ Not a Youtube Movie ID')

    context = {
        'threshold_seconds': AUDIO_SPLIT_THRESHOLD_MINUTES * 60,
        'split_duration_minutes': 39,
        'ytdlprewriteoptions': YT_DLP_OPTIONS_DEFAULT,
        'additional_meta_text': ''
    }

    if not command.get('name'):
        return await post_status.edit_text('🟥️ No Command')

    if command.get('name') == 'split':
        # Make split with Default split
        context['threshold_seconds'] = 1

        if command.get('params'):
            param = command.get('params')[0]
            if not param.isnumeric():
                return await post_status.edit_text('🟥️ Param if split [not param.isnumeric()]')
            param = int(param)
            if param < DURATION_MINUTES_MIN or DURATION_MINUTES_MAX < param:
                return await post_status.edit_text(f'🟥️ Param if split = {param} '
                                                   f'is out of [{DURATION_MINUTES_MIN}, {DURATION_MINUTES_MAX}]')
            context['split_duration_minutes'] = param

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

        context['ytdlprewriteoptions'] = context.get('ytdlprewriteoptions').replace('48k', f'{param}k')
        context['additional_meta_text'] = f'{param}k bitrate'

    elif command.get('name') == 'subtitles':
        param = ''
        if command.get('params'):
            params = command.get('params')
            param = ' '.join(params)

        text, _err = await get_subtitles(movie_id, param)

        print('🫐 Get subtitles: ')
        print(text, _err)

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

    data_dir = await get_data_dir()

    audio = await download_audio(movie_id, data_dir, context.get('ytdlprewriteoptions'))
    audio = pathlib.Path(audio)
    if not audio.exists():
        return await post_status.edit_text(f'🟥 Download. Unexpected error. After Check m4a_file.exists.')

    thumbnail = await download_thumbnail(movie_id, data_dir)
    thumbnail = pathlib.Path(thumbnail)
    if not thumbnail.exists():
        return await post_status.edit_text(f'🟥 Thumbnail. Unexpected error. After Check thumbnail.exists().')

    thumbnail_compressed = await image_compress_and_resize(thumbnail)
    if thumbnail_compressed.exists():
        thumbnail = thumbnail_compressed
    else:
        await post_status.edit_text(f'🟥 Thumbnail Compression. Problem with image compression.')

    audio_duration = await get_duration_asynced(audio)

    scheme = get_split_audio_scheme(
        source_audio_length=audio_duration,
        duration_seconds=context['split_duration_minutes'] * 60,
        delta_seconds=AUDIO_SPLIT_DELTA_SECONDS,
        magic_tail=True,
        threshold_seconds=context['threshold_seconds']
    )
    print('📊 scheme: ', scheme)

    audios = await make_split_audio(
        audio_path=audio,
        audio_duration=audio_duration,
        output_folder=data_dir,
        scheme=scheme
    )
    await post_status.edit_text('⌛ Uploading to Telegram ... ')

    mp4obj, _err = await get_mp4object(audio)
    if _err:
        await post_status.edit_text(f'🟥 Exception as e: [m4a = MP4(m4a_file.as_posix())]. \n\n{_err}')

    title = get_title(mp4obj, movie_id)
    movie_link_html = get_youtube_link_html(movie_id)
    author = mp4obj.get('\xa9ART', ['Unknown'])[0]

    print('👺 Author: ', author)
    caption_head = f'{title}\n{movie_link_html} [DURATION]' + context.get('additional_meta_text')
    caption_head += f'\n{author}'

    filename_head = output_filename_in_telegram(title)

    timecodes = await get_timecodes(scheme, mp4obj.get('desc'))

    for idx, audio_part in enumerate(audios, start=1):
        print('💜 Idx: ', idx, 'part: ', audio_part)

        duration_formatted = filter_timestamp_format(timedelta(seconds=audio_part.get('duration')))
        filename = 'FILENAME'
        caption = 'CAPTION'

        if len(audios) == 1:
            filename = filename_head
            caption = caption_head.replace('[DURATION]', f'[{duration_formatted}]')
        else:
            filename = f'(p{idx}-of{len(audios)}) {filename_head}'
            caption = f'[Part {idx} of {len(audios)}] {caption_head}'.replace('[DURATION]', f'[{duration_formatted}]')

        caption += f'\n\n{timecodes[idx-1]}'

        if len(caption) > TELEGRAM_CAPTION_TEXT_LONG_MAX-8:
            caption_trimmed = caption[:TELEGRAM_CAPTION_TEXT_LONG_MAX-8]
            caption = f'{caption_trimmed}\n...'

        await bot.send_audio(
            chat_id=sender_id,
            reply_to_message_id=message.message_id,
            audio=FSInputFile(audio_part.get('path'), filename=filename),
            duration=audio_part.get('duration'),
            thumbnail=FSInputFile(thumbnail),
            caption=caption,
            parse_mode=ParseMode.HTML
        )

    await post_status.delete()

    if not keepfiles_global:
        print('🗑❌ Empty Files')
        await delete_files_by_movie_id(data_dir, movie_id)

    print(f'💚 Success! [{movie_id}]\n')


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")


@dp.message()
@dp.channel_post()
async def message_parser(message: Message) -> None:
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
    print('🚀 Run bot ...')
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    parser = argparse.ArgumentParser(description='Bot ytb 2 audio')
    parser.add_argument('--keepfiles', type=int,
                        help='Keep raw files 1=True, 0=False (default)', default=0)

    args = parser.parse_args()

    if args.keepfiles == '1':
        keepfiles_global = True

    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
