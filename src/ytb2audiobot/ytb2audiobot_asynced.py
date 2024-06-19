import argparse
import asyncio
import logging
import re
import sys
import aiofiles.os
from PIL import Image
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, BufferedInputFile
from urlextract import URLExtract
from ytb2audio.ytb2audio import get_youtube_move_id
import os
import pathlib
from audio2splitted.audio2splitted import get_split_audio_scheme, make_split_audio, DURATION_MINUTES_MIN, \
    DURATION_MINUTES_MAX
from dotenv import load_dotenv
from telegram.constants import ParseMode
from mutagen.mp4 import MP4
from utils4audio.duration import get_duration_asynced

from ytb2audio.ytb2audio import download_audio, download_thumbnail, YT_DLP_OPTIONS_DEFAULT
from datetime import timedelta

from ytb2audiobot.subtitles import get_subtitles
from ytb2audiobot.ytb2audiobot_asynced import get_timecodes_text

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()

load_dotenv()
token = os.environ.get("TG_TOKEN")

bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

DATA_DIR = '../../data'

keepfiles = False


SEND_AUDIO_TIMEOUT = 120
TELEGRAM_CAPTION_TEXT_LONG_MAX = 1024-8

COMMANDS_SPLIT = [
    {'name': 'split', 'alias': 'split'},
    {'name': 'split', 'alias': 'spl'},
    {'name': 'split', 'alias': 'sp'},
]

COMMANDS_BITRATE = [
    {'name': 'bitrate', 'alias': 'bitrate'},
    {'name': 'bitrate', 'alias': 'bitr'},
    {'name': 'bitrate', 'alias': 'bit'},
]

COMMANDS_SUBTITLES = [
    {'name': 'subtitles', 'alias': 'subtitles'},
    {'name': 'subtitles', 'alias': 'subt'},
    {'name': 'subtitles', 'alias': 'subs'},
    {'name': 'subtitles', 'alias': 'sub'},
    {'name': 'subtitles', 'alias': 'su'},
]

COMMANDS_FORCE_DOWNLOAD = [
    {'name': 'download', 'alias': 'download'},
    {'name': 'download', 'alias': 'down'},
    {'name': 'download', 'alias': 'dow'},
    {'name': 'download', 'alias': 'd'},
    {'name': 'download', 'alias': 'bot'},
    {'name': 'download', 'alias': 'скачать'},
    {'name': 'download', 'alias': 'скач'},
    {'name': 'download', 'alias': 'ск'},
]


ALL_COMMANDS = COMMANDS_SPLIT + COMMANDS_BITRATE + COMMANDS_SUBTITLES + COMMANDS_FORCE_DOWNLOAD

AUDIO_SPLIT_THRESHOLD_MINUTES = 120
AUDIO_SPLIT_DELTA_SECONDS = 5

AUDIO_BITRATE_MIN = 48
AUDIO_BITRATE_MAX = 320


async def image_compress_and_resize(
        path: pathlib.Path,
        output: pathlib.Path = None,
        quality: int = 80,
        thumbnail_size=(960, 960)
):
    image = Image.open(path)
    image.thumbnail(thumbnail_size)
    if not output:
        output = path
    image.save(output, optimize=True, quality=quality)
    return output


def output_filename_in_telegram(text):
    name = (re.sub(r'[^\w\s\-\_\(\)\[\]]', ' ', text)
            .replace('    ', ' ')
            .replace('   ', ' ')
            .replace('  ', ' ')
            .strip())

    return f'{name}.m4a'

















async def get_data_dir():
    data_dir = pathlib.Path(DATA_DIR)
    if not data_dir.exists():
        await aiofiles.os.mkdir(data_dir.as_posix())

    return data_dir


async def get_mp4_oject(path: pathlib.Path):
    path = pathlib.Path(path)
    try:
        mp4object = MP4(path.as_posix())
    except Exception as e:
        return {}, e

    return mp4object, ''


MAX_TELEGRAM_BOT_TEXT_SIZE = 4095


async def delete_files(data_dir, movie_id):
    files = list(filter(lambda f: (f.name.startswith(movie_id)), data_dir.iterdir()))
    for f in files:
        f.unlink()


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

    audio_mp4obj, _err = await get_mp4_oject(audio)
    if _err:
        await post_status.edit_text(f'🟥 Exception as e: [m4a = MP4(m4a_file.as_posix())]. \n\n{_err}')

    if not audio_mp4obj:
        await post_status.edit_text('🟥 Unexpected error. [not audio in MP4 metadata].')

    title = str(movie_id)
    if audio_mp4obj.get('\xa9nam'):
        title = audio_mp4obj.get('\xa9nam')[0]

    url_youtube = f'youtu.be/{movie_id}'
    link_html = f'<a href=\"{url_youtube}\">{url_youtube}</a>'

    title = capital2lower_letters_filter(title)
    caption_head = f'{title}\n{link_html}'
    filename_head = output_filename_in_telegram(title)

    timecodes = ['' for part in range(len(scheme))]
    if timecodes_text := get_timecodes_text(audio_mp4obj.get('desc')):
        timecodes = get_timestamps_group(timecodes_text, scheme)

    for idx, audio_part in enumerate(audios, start=1):
        print('💜 Idx: ', idx, 'part: ', audio_part)

        duration_formatted = filter_timestamp_format(timedelta(seconds=audio_part.get('duration')))
        filename = filename_head
        caption = f'{caption_head} [{duration_formatted}] ' + context.get('additional_meta_text')
        if len(audios) != 1:
            filename = f'(p{idx}-of{len(audios)}) {filename_head}'
            caption = f'[Part {idx} of {len(audios)}] {caption_head} [{duration_formatted}]'

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

    if not keepfiles:
        await delete_files(data_dir, movie_id)

    print(f'💚 Success! [{movie_id}]\n')


def parser_words(text):
    context = {
        'url': None,
        'is_url_starting': False,
        'params': [],
    }
    return


def is_youtube_url(text):
    YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be']
    for domain in YOUTUBE_DOMAINS:
        if domain in text:
            return True
    return False


def get_command_params_of_request2(text):
    command_context = dict()
    command_context['url'] = ''
    command_context['url_started'] = False
    command_context['name'] = ''
    command_context['params'] = []

    text = text.strip()
    if not is_youtube_url(text):
        return command_context

    urls = URLExtract().find_urls(text)
    for url in urls:
        url = url.strip()
        if is_youtube_url(url):
            command_context['url'] = url
    if not command_context['url']:
        return command_context

    if text.startswith(command_context.get('url')):
        command_context['url_started'] = True

    text = text.replace(command_context.get('url'), '')
    text = text.strip()
    text = text.replace('   ', ' ')
    text = text.replace('  ', ' ')
    parts = text.split(' ')

    if not len(parts):
        return command_context

    command_index = -1
    for idx, command in enumerate(ALL_COMMANDS):
        if command.get('alias') == parts[0]:
            command_index = idx

    if command_index < 0:
        return command_context

    command_context['name'] = ALL_COMMANDS[command_index].get('name')

    if len(parts) < 2:
        return command_context

    PARAMS_MAX_COUNT = 2
    command_context['params'] = parts[1:PARAMS_MAX_COUNT+1]

    return command_context


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

    command_context = get_command_params_of_request2(message.text)

    if not command_context.get('url'):
        return

    if sender_type != 'user' and not command_context.get('name'):
        return

    if not command_context.get('name'):
        command_context['name'] = 'download'

    print('🍒 command_context: ', command_context)
    await asyncio.create_task(processing_commands(message, command_context, sender_id))


async def start_bot():
    await dp.start_polling(bot)


def main():
    parser = argparse.ArgumentParser(description='Bot ytb 2 audio')
    parser.add_argument('--keepfiles', type=int,
                        help='Keep raw files 1=True, 0=False (default)', default=0)

    args = parser.parse_args()

    if args.keepfiles=='1':
        keepfiles = True

    asyncio.run(start_bot())


if __name__ == "__main__":
    print('😄 Start')
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()

