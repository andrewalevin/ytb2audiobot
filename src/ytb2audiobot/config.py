import logging
import pathlib
from string import Template
from ytb2audio.ytb2audio import YT_DLP_OPTIONS_DEFAULT

# main
DEV = True

CALLBACK_WAIT_TIMEOUT_SECONDS = 8

KEEP_FILE_TIME_MINUTES_MIN = 5

AUDIO_SPLIT_DELTA_SECONDS_MIN = 0
AUDIO_SPLIT_DELTA_SECONDS_MAX = 60

TELEGRAM_CALLBACK_BUTTON_TIMEOUT_SECONDS_MIN = 2
TELEGRAM_CALLBACK_BUTTON_TIMEOUT_SECONDS_MAX = 60

START_COMMAND_TEXT = '''
<b>🥭 Ytb2audo bot</b>

Youtube to audio telegram bot with subtitles
Description: 

'''

SUBTITLES_WITH_CAPTION_TEXT_TEMPLATE = Template('''
$caption

$subtitles
''')

TELEGRAM_MAX_MESSAGE_TEXT_SIZE = 4096 - 4


# processing

SEND_AUDIO_TIMEOUT = 120
TG_CAPTION_MAX_LONG = 1023

AUDIO_SPLIT_THRESHOLD_MINUTES = 101
AUDIO_SPLIT_DELTA_SECONDS = 5

AUDIO_BITRATE_MIN = 48
AUDIO_BITRATE_MAX = 320

MAX_TELEGRAM_BOT_TEXT_SIZE = 4095

TASK_TIMEOUT_SECONDS = 60 * 30

CAPTION_HEAD_TEMPLATE = Template('''
$partition $title
<a href=\"youtu.be/$movieid\">youtu.be/$movieid</a> [$duration]
$author $additional

$timecodes
''')

CAPTION_TRIMMED_END_TEXT = '…\n…\n⚔️ [Text truncated to fit Telegram’s caption limit]'

ADDITIONAL_INFO_FORCED_SPLITTED = '\n\n🎏 [forced splitted due to max orig file size]'

DEFAULT_MOVIE_META = {
    'id': '',
    'title': '',
    'author': '',
    'description': '',
    'thumbnail_url': '',
    'thumbnail_path': None,
    'additional': '',
    'duration': 0,
    'timecodes': [''],
    'threshold_seconds': AUDIO_SPLIT_THRESHOLD_MINUTES * 60,
    'split_duration_minutes': 39,
    'ytdlprewriteoptions': YT_DLP_OPTIONS_DEFAULT,
    'additional_meta_text': '',
    'store': pathlib.Path('data')
}


MAX_FILE_SIZE_UPLOADING_TELEGRAM_BOT_BYTES = 3300000


COMMANDS_SPLIT = [
    {'name': 'split', 'alias': 'split'},
    {'name': 'split', 'alias': 'spl'},
    {'name': 'split', 'alias': 'sp'},
    {'name': 'split', 'alias': 'разделить'},
    {'name': 'split', 'alias': 'раздел'},
    {'name': 'split', 'alias': 'разд'},
    {'name': 'split', 'alias': 'раз'},
]

COMMANDS_SPLIT_BY_TIMECODES = [
    {'name': 'splittimecodes', 'alias': 'timecodes'},
    {'name': 'splittimecodes', 'alias': 'timecode'},
    {'name': 'splittimecodes', 'alias': 'time'},
    {'name': 'splittimecodes', 'alias': 'tm'},
    {'name': 'splittimecodes', 'alias': 't'},
]

COMMANDS_BITRATE = [
    {'name': 'bitrate', 'alias': 'bitrate'},
    {'name': 'bitrate', 'alias': 'bitr'},
    {'name': 'bitrate', 'alias': 'bit'},
    {'name': 'bitrate', 'alias': 'битрейт'},
    {'name': 'bitrate', 'alias': 'битр'},
    {'name': 'bitrate', 'alias': 'бит'},
]

COMMANDS_SUBTITLES = [
    {'name': 'subtitles', 'alias': 'subtitles'},
    {'name': 'subtitles', 'alias': 'subtitle'},
    {'name': 'subtitles', 'alias': 'subt'},
    {'name': 'subtitles', 'alias': 'subs'},
    {'name': 'subtitles', 'alias': 'sub'},
    {'name': 'subtitles', 'alias': 'su'},
    {'name': 'subtitles', 'alias': 'саб'},
    {'name': 'subtitles', 'alias': 'сабы'},
    {'name': 'subtitles', 'alias': 'субтитры'},
    {'name': 'subtitles', 'alias': 'субт'},
    {'name': 'subtitles', 'alias': 'суб'},
    {'name': 'subtitles', 'alias': 'сб'},
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

COMMANDS_QUOTE = [
    {'name': 'quote', 'alias': 'quote'},
    {'name': 'quote', 'alias': 'qu'},
    {'name': 'quote', 'alias': 'q'},
]

ALL_COMMANDS = COMMANDS_SPLIT + COMMANDS_BITRATE + COMMANDS_SUBTITLES + COMMANDS_QUOTE

YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be']

PARAMS_MAX_COUNT = 2

DATA_DIR_DIRNAME_IN_TEMPDIR = 'pip-ytb2audiobot-data'
DATA_DIR_NAME = 'data'

FORMAT_TEMPLATE = Template('<b><s>$text</s></b>')
ADDITION_ROWS_NUMBER = 1
IS_TEXT_FORMATTED = True

MOVIES_TEST_TIMCODES = '''
Как миграция убивает францию
https://www.youtube.com/watch?v=iR0ETOSis7Y

Ремизов
youtu.be/iI3qo1Bxi0o 

'''

TELEGRAM_BOT_FILE_MAX_SIZE_BYTES = 47000000

TIMERS_FILE_PATH = pathlib.Path('timers.log')

AUTODOWNLOAD_CHAT_IDS_HASHED_PATH = pathlib.Path('autodownload_chat_ids_hashed.txt')

LOG_LEVEL = logging.DEBUG

DEFAULT_TELEGRAM_TOKEN_IMAGINARY = '123456789:AAE_O0RiWZRJOeOB8Nn8JWia_uUTqa2bXGU'

# Function to set the environment variable
# config.py

# Function to set the environment variable

PACKAGE_NAME = 'ytb2audiobot'

YOUTUBE_URL = Template('youtu.be/$movieid')
TIMEOUT_DOWNLOAD_PROCESSING_MULTIPLIRE_BY_PREDICT_TIME = 1

CALLBACK_DATA_CHARS_SEPARATOR = ':_:'
CALLBACK_SLEEP_TIME_SECONDS = 8

TEXT_STARTED_HEAD = '🚀 Bot has started!'

HELP_COMMANDS_TEXT = '''
/extra - 🔮Extra options
/help - 🤔 Help'
/autodownload - 🏂‍ (Works only in channels)
'''


def get_thumbnail_path(data_dir, movie_id):
    return pathlib.Path(data_dir).joinpath(f'{movie_id}-thumbnail.jpg')


def get_audio_path(data_dir, movie_id):
    return pathlib.Path(data_dir).joinpath(f'{movie_id}.m4a')


BITRATE_AUDIO_FILENAME_FORMAT_TEMPLATE = Template('-bitrate${bitrate}')
AUDIO_FILENAME_TEMPLATE = Template('${movie_id}${bitrate}${extension}')
THUMBNAIL_FILENAME_TEMPLATE = Template('${movie_id}-thumbnail${extension}')

BITRATES_VALUES = ['48k', '64k', '96k', '128k'] + ['196k', '256k', '320k']

ACTION_NAME_BITRATE_CHANGE = 'bitrate_change'
ACTION_NAME_SPLIT_BY_TIMECODES = 'split_by_timecodes'
ACTION_NAME_SPLIT_BY_DURATION = 'split_by_duration'
ACTION_NAME_SUBTITLES_SEARCH_WORD = 'subtitles_search_word'
ACTION_NAME_SUBTITLES_GET_ALL = 'subtitles_get_all'
ACTION_NAME_SUBTITLES_SHOW_OPTIONS = 'subtitles_show_options'
ACTION_NAME_MUSIC = 'music_high_bitrate'
ACTION_NAME_SLICE = 'slice'
ACTION_NAME_OPTIONS_EXIT = 'options_exit'
ACTION_NAME_TRANSLATE = 'translate'

ENV_NAME_TOKEN = 'TG_TOKEN'
ENV_NAME_SALT = 'HASH_SALT'
ENV_NAME_DEBUG_MODE = 'YTB2AUDIO_DEBUG_MODE'
ENV_NAME_KEEP_DATA_FILES = 'KEEP_DATA_FILES'
ENV_TG_BOT_OWNER_ID = 'TG_BOT_OWNER_ID'

YT_DLP_OPTIONS_DEFAULT = {
    'extract-audio': True,
    'audio-format': 'm4a',
    'audio-quality': '48k',
    'embed-thumbnail': True,
    'console-title': True,
    'embed-metadata': True,
    'newline': True,
    'progress-delta': '2',
    'break-on-existing': True
}


def get_yt_dlp_options(override_options=None):
    if override_options is None:
        override_options = {}

    options = YT_DLP_OPTIONS_DEFAULT

    options.update(override_options)

    rows = []

    for key, value in options.items():
        if isinstance(value, bool):
            if value:
                rows.append(f'--{key}')
            else:
                continue
        else:
            rows.append(f'--{key} {value}')

    return ' '.join(rows)


# 255 max - minus additionals
MAX_TELEGRAM_FILENAME_LENGTH = 64

CLI_ACTIVATION_SUBTITLES = ['subtitles', 'subs', 'sub']
CLI_ACTIVATION_MUSIC = ['music', 'song']
CLI_ACTIVATION_ALL = CLI_ACTIVATION_SUBTITLES + CLI_ACTIVATION_MUSIC

ACTION_MUSIC_HIGH_BITRATE = BITRATES_VALUES[-1]

ADDITIONAL_CHAPTER_BLOCK = Template('\n\n📌 <b>$title</b>\n[Chapter +${time_shift}]')

SEGMENTS_PADDING_SEC = 6


TEXT_SAY_HELLO_BOT_OWNER_AT_STARTUP = Template(
    '🚀 Bot has started! \n\n📦 Package Version: ${package_bot_version}\n${help_commands_text}')

LOG_FORMAT_CALLED_FUNCTION = Template('💈💈 ${fname}():')


CAPTION_SLICE = Template('🍰 Slice from ${start_time} to ${end_time}')

YT_DLP_OPTIONS_DEFAULT_2 = ('--extract-audio --audio-format m4a --audio-quality 48k'
                          ' --embed-thumbnail --console-title --embed-metadata'
                          ' --newline --progress-delta 2 --break-on-existing')

