from string import Template
from importlib.metadata import version

CALLBACK_WAIT_TIMEOUT_SECONDS = 8

TASK_TIMEOUT_SECONDS = 60 * 30

SEGMENT_DURATION_PADDING_SEC = 6

SEGMENT_AUDIO_DURATION_SEC = 39 * 60

SEGMENT_AUDIO_DURATION_SPLIT_THRESHOLD_SEC = 101 * 60

ACTION_TRANSLATE_OVERLAY_DEFAULT = 0.3



DATA_DIR_DIRNAME_IN_TEMPDIR = 'pip-ytb2audiobot-data'
DATA_DIR_NAME = 'data'

ENV_NAME_TOKEN = 'TG_TOKEN'
ENV_NAME_DEBUG_MODE = 'YTB2AUDIO_DEBUG_MODE'
ENV_NAME_KEEP_DATA_FILES = 'KEEP_DATA_FILES'
ENV_TG_BOT_OWNER_ID = 'TG_BOT_OWNER_ID'
ENV_REBALANCE_SEGMENTS_TO_FIT_TIMECODES = 'REBALANCE_SEGMENTS_TO_FIT_TIMECODES'






TELEGRAM_MAX_CAPTION_TEXT_SIZE = 1024 - 2

TELEGRAM_MAX_MESSAGE_TEXT_SIZE = 4096 - 4

TELEGRAM_MAX_FILE_SIZE_BYTES = 47000000

TELEGRAM_VALID_TOKEN_IMAGINARY = '123456789:AAE_O0RiWZRJOeOB8Nn8JWia_uUTqa2bXGU'

FORMAT_TEMPLATE = Template('<b><s>$text</s></b>')
ADDITION_ROWS_NUMBER = 1
IS_TEXT_FORMATTED = True


# todo
PACKAGE_NAME = 'ytb2audiobot'

CALLBACK_DATA_CHARS_SEPARATOR = ':_:'


# todo

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


# 255 max - minus additionals
TG_MAX_FILENAME_LEN = 61

CLI_ACTIVATION_SUBTITLES = ['subtitles', 'subs', 'sub']
CLI_ACTIVATION_MUSIC = ['music', 'song']
CLI_ACTIVATION_TRANSLATION = ['translation', 'translate', 'transl', 'trans', 'tran', 'tra', 'tr']
CLI_ACTIVATION_ALL = CLI_ACTIVATION_SUBTITLES + CLI_ACTIVATION_MUSIC + CLI_ACTIVATION_TRANSLATION


ADDITIONAL_CHAPTER_BLOCK = Template('\n\n📌 <b>$title</b>\n[Chapter +${time_shift}]')


LOG_FORMAT_CALLED_FUNCTION = Template('💈💈 ${fname}():')


CAPTION_SLICE = Template('🍰 Slice from ${start_time} to ${end_time}')


SEND_YOUTUBE_LINK_TEXT = '🔗 Give me your YouTube link:'

DESCRIPTION_BLOCK_COMMANDS = f'''
<b>Commands</b>
/help
/extra - 🔮Advanced options
/autodownload - 🏂‍ (Works only in channels) See about #todo
'''.strip()

DESCRIPTION_BLOCK_EXTRA_OPTIONS = '''
<b>🔮 Advanced options:</b> 

 - Split by duration
 - Split by timecodes
 - Set audio Bitrate
 - Get subtitles
 - Get slice of audio
 - Translate from any language
'''.strip()

DESCRIPTION_BLOCK_CLI = f'''
<b>📟 CLI options</b>

 - one
 - two
'''.strip()


DESCRIPTION_BLOCK_REFERENCES = f'''
<b>References</b>

- https://t.me/ytb2audiostartbot (LTS)
- https://t.me/ytb2audiobetabot (BETA) #todo-all-logs-info

- https://andrewalevin.github.io/ytb2audiobot/
- https://github.com/andrewalevin/ytb2audiobot
- https://pypi.org/project/ytb2audiobot/
- https://hub.docker.com/r/andrewlevin/ytb2audiobot
'''.strip()


DESCRIPTION_BLOCK_OKAY_AFTER_EXIT = f'''
👋 Okay!
Anytime you can give me a youtube link to download its audio or select one of the command:

{DESCRIPTION_BLOCK_COMMANDS}
'''.strip()

BITRATE_VALUES_ROW_ONE = ['48k', '64k', '96k', '128k']
BITRATE_VALUES_ROW_TWO = ['196k', '256k', '320k']
BITRATE_VALUES_ALL = BITRATE_VALUES_ROW_ONE + BITRATE_VALUES_ROW_TWO



SPLIT_DURATION_VALUES_ROW_1 = ['2', '3', '5', '7', '11', '13', '17', '19']
SPLIT_DURATION_VALUES_ROW_2 = ['23', '29', '31', '37', '41', '43']
SPLIT_DURATION_VALUES_ROW_3 = ['47', '53', '59', '61', '67']
SPLIT_DURATION_VALUES_ROW_4 = ['73', '79', '83', '89']
SPLIT_DURATION_VALUES_ALL = SPLIT_DURATION_VALUES_ROW_1 + SPLIT_DURATION_VALUES_ROW_2 + SPLIT_DURATION_VALUES_ROW_3 + SPLIT_DURATION_VALUES_ROW_4


CAPTION_HEAD_TEMPLATE = Template('''
$partition $title
<a href=\"youtu.be/$movieid\">youtu.be/$movieid</a> [$duration]
$author $additional

$timecodes
''')

CAPTION_TRIMMED_END_TEXT = '…\n…\n⚔️ [Text truncated to fit Telegram’s caption limit]'


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

YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be']


BITRATE_AUDIO_FILENAME_FORMAT_TEMPLATE = Template('-bitrate${bitrate}')
AUDIO_FILENAME_TEMPLATE = Template('${movie_id}${bitrate}${extension}')
THUMBNAIL_FILENAME_TEMPLATE = Template('${movie_id}-thumbnail${extension}')

BITRATES_VALUES = ['48k', '64k', '96k', '128k'] + ['196k', '256k', '320k']

ACTION_MUSIC_HIGH_BITRATE = BITRATES_VALUES[-1]

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
ACTION_TRANSLATE_GET_SOLO_WORDS = ['solo', 'alone', 'one', 'only']

DESCRIPTION_BLOCK_WELCOME = f'''
<b>🪩 Hello!</b>
(version:  {version(PACKAGE_NAME)})
🐐
I can download .... #todo
 - one
 - two
'''.strip()

START_AND_HELP_TEXT = f'''
{DESCRIPTION_BLOCK_WELCOME}

{DESCRIPTION_BLOCK_COMMANDS}

{DESCRIPTION_BLOCK_EXTRA_OPTIONS}

{DESCRIPTION_BLOCK_CLI}

{DESCRIPTION_BLOCK_REFERENCES}
'''.strip()

TEXT_SAY_HELLO_BOT_OWNER_AT_STARTUP = f'''
🚀 Bot has started! 

📦 Package Version: {version(PACKAGE_NAME)}

{DESCRIPTION_BLOCK_COMMANDS}
'''.strip()
