import asyncio
import pathlib
from datetime import timedelta
from string import Template

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import load_dotenv
from telegram.constants import ParseMode

from ytb2audio.ytb2audio import YT_DLP_OPTIONS_DEFAULT, get_youtube_move_id, download_audio_by_movie_meta, \
    download_thumbnail_by_movie_meta
from audio2splitted.audio2splitted import DURATION_MINUTES_MIN, DURATION_MINUTES_MAX, get_split_audio_scheme, \
    make_split_audio

from ytb2audiobot.subtitles import get_subtitles
from ytb2audiobot.datadir import get_data_dir

from ytb2audiobot.mp4mutagen import get_mp4object
from ytb2audiobot.pytube import get_movie_meta
from ytb2audiobot.thumbnail import image_compress_and_resize
from ytb2audiobot.timecodes import get_timecodes, filter_timestamp_format
from ytb2audiobot.utils import capital2lower, filename_m4a

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


async def processing_commands(command: dict):
    context = dict()
    context['warning'] = ''
    context['error'] = ''

    movie_id = command.get('id')

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
        if param < AUDIO_BITRATE_MIN or AUDIO_BITRATE_MAX < param:
            context['error'] = f'🟥️ Bitrate. Param {param} is out of [{AUDIO_BITRATE_MIN}, ... , {AUDIO_BITRATE_MAX}]'
            return context

        movie_meta['ytdlprewriteoptions'] = movie_meta.get('ytdlprewriteoptions').replace('48k', f'{param}k')
        movie_meta['additional_meta_text'] = f'{param}k bitrate'

    elif command.get('name') == 'subtitles':
        param = ''
        if command.get('params'):
            params = command.get('params')
            param = ' '.join(params)

        text, _err = await get_subtitles(movie_id, param)
        if _err:
            context['error'] = f'🟥️ Subtitles. Internal error: {_err}'
            return context

        context['subtitles'] = text

        return context

    movie_meta = await get_movie_meta(movie_meta, movie_id)

    tasks = [
        download_audio_by_movie_meta(movie_meta),
        download_thumbnail_by_movie_meta(movie_meta)
    ]
    results = await asyncio.gather(*tasks)

    audio = results[0]
    movie_meta['thumbnail_path'] = results[1]

    if not audio.exists():
        context['error'] = f'🔴 Download. Audio file does not exist.'
        return context

    if not pathlib.Path(movie_meta['thumbnail_path']).exists():
        context['warning'] = f'🟠 Thumbnail. Not exists.\n'

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

    thumbnail_compressed = results[0]
    audios = results[1]
    mp4obj = results[2]

    if not thumbnail_compressed.exists():
        context['warning'] = f'🟠 Thumbnail Compression. Problem with image compression.'
    else:
        movie_meta['thumbnail_path'] = thumbnail_compressed

    if not mp4obj:
        context['warning'] = f'🟠 MP4 Mutagen .m4a.'

    if not movie_meta['description'] and mp4obj.get('desc'):
        movie_meta['description'] = mp4obj.get('desc')

    timecodes, _err = await get_timecodes(scheme, movie_meta['description'])
    if _err:
        context['warning'] = f'🟠 Timecodes. Error creation.'

    caption_head = CAPTION_HEAD_TEMPLATE.safe_substitute(
        movieid=movie_meta['id'],
        title=capital2lower(movie_meta['title']),
        author=capital2lower(movie_meta['author']),
        additional=movie_meta['additional']
    )
    filename = filename_m4a(movie_meta['title'])

    context['audio_datas'] = []

    context['duration'] = movie_meta['duration']

    for idx, audio_part in enumerate(audios, start=1):
        print('💜 Idx: ', idx, 'part: ', audio_part)

        caption = Template(caption_head).safe_substitute(
            partition='' if len(audios) == 1 else f'[Part {idx} of {len(audios)}]',
            timecodes=timecodes[idx-1],
            duration=filter_timestamp_format(timedelta(seconds=audio_part.get('duration')))
        )

        audio_data = {
            'chat_id': command.get('sender_id'),
            'reply_to_message_id': command.get('message_id') if idx == 1 else None,
            'audio_path': audio_part['path'],
            'audio_filename': filename if len(audios) == 1 else f'p{idx}_of{len(audios)} {filename}',
            'duration': audio_part['duration'],
            'thumbnail_path': movie_meta['thumbnail_path'],
            'caption': caption if len(caption) < TG_CAPTION_MAX_LONG else caption[:TG_CAPTION_MAX_LONG - 8] + '\n...',
        }
        context['audio_datas'].append(audio_data)


    # await bot.delete_message(
    #    chat_id=command.get('sender_id'),
    #    message_id=command.get('message_id')
    # )

    # if not keep_data_files:
    #    print('🗑❌ Empty Files')
    #    await delete_files_by_movie_id(data_dir, movie_id)

    return context
