import pathlib
from string import Template

from ytb2audio.ytb2audio import YT_DLP_OPTIONS_DEFAULT

# main
DEV = True

CALLBACK_WAIT_TIMEOUT = 8

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

TASK_TIMEOUT_SECONDS = 60 * 30


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
<a href=\"youtu.be/$movieid\">youtu.be/$movieid</a> [$duration] $additional
$author

$timecodes
''')

CAPTION_TRIMMED_END_TEXT = ' …\n…\n[⚔️ max caption length]'

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

TELEGRAM_MAX_AUDIO_BOT_FILE_SIZE_BYTES_BINARY = 46000000
TELEGRAM_MAX_AUDIO_BOT_FILE_SIZE_BYTES_BINARY = 3000000



###### Commands

COMMANDS_SPLIT = [
    {'name': 'split', 'alias': 'split'},
    {'name': 'split', 'alias': 'spl'},
    {'name': 'split', 'alias': 'sp'},
    {'name': 'split', 'alias': 'разделить'},
    {'name': 'split', 'alias': 'раздел'},
    {'name': 'split', 'alias': 'разд'},
    {'name': 'split', 'alias': 'раз'},
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

ALL_COMMANDS = COMMANDS_SPLIT + COMMANDS_BITRATE + COMMANDS_SUBTITLES

YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be']

PARAMS_MAX_COUNT = 2


# datadir

DIRNAME_IN_TEMPDIR = 'pip-ytb2audiobot-data'
DIRNAME_DATA = 'data-ytb2audiobot'


# subtitles

FORMAT_TEMPLATE = Template('<b><s>$text</s></b>')
ADDITION_ROWS_NUMBER = 1
IS_TEXT_FORMATTED = True


# timecodes

MOVIES_TEST_TIMCODES = '''
Как миграция убивает францию
https://www.youtube.com/watch?v=iR0ETOSis7Y

Ремизов
youtu.be/iI3qo1Bxi0o 

'''





