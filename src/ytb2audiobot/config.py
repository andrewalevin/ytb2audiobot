import os
from string import Template
from importlib.metadata import version

BUTTON_CHANNEL_WAITING_DOWNLOADING_TIMEOUT_SEC = int(os.getenv('Y2A_BUTTON_CHANNEL_WAITING_DOWNLOADING_TIMEOUT_SEC', 8))

KILL_JOB_DOWNLOAD_TIMEOUT_SEC = int(os.getenv('Y2A_KILL_JOB_DOWNLOAD_TIMEOUT_SEC', 42 * 60))

SEGMENT_AUDIO_DURATION_SEC = int(os.getenv('Y2A_SEGMENT_AUDIO_DURATION_SEC', 39 * 60))

SEGMENT_AUDIO_DURATION_SPLIT_THRESHOLD_SEC = int(os.getenv('Y2A_SEGMENT_AUDIO_DURATION_SPLIT_THRESHOLD_SEC', 101 * 60))

SEGMENT_DURATION_PADDING_SEC = int(os.getenv('Y2A_SEGMENT_DURATION_PADDING_SEC', 6))

SEGMENT_REBALANCE_TO_FIT_TIMECODES = bool(os.getenv('Y2A_SEGMENT_REBALANCE_TO_FIT_TIMECODES', 'true').lower() == 'true')

TRANSLATION_OVERLAY_ORIGIN_AUDIO_TRANSPARENCY = float(os.getenv('Y2A_TRANSLATION_OVERLAY_ORIGIN_AUDIO_TRANSPARENCY', 0.3))

OWNER_BOT_ID_TO_SAY_HELLOW = os.getenv('Y2A_OWNER_BOT_ID_TO_SAY_HELLOW', '')

# Values: '48k', '64k', '96k', '128k',  '196k', '256k', '320k'
AUDIO_QUALITY_BITRATE = os.getenv('Y2A_AUDIO_QUALITY_BITRATE', '48k')

DEBUG_MODE = bool(os.getenv('Y2A_DEBUG_MODE', 'false').lower() == 'true')

KEEP_DATA_FILES = bool(os.getenv('Y2A_KEEP_DATA_FILES', 'false').lower() == 'true')

REMOVE_AGED_DATA_FILES_SEC = int(os.getenv('Y2A_REMOVE_AGED_DATA_FILES_SEC', 60 * 60))

AUTO_DOWNLOAD_CHAT_IDS_STORAGE_FILENAME = os.getenv('Y2A_AUTO_DOWNLOAD_CHAT_IDS_STORAGE_FILENAME', 'autodownload-hashed-chat-ids.yaml')

REPLY_TO_ORIGINAL = bool(os.getenv('Y2A_REPLY_TO_ORIGINAL', 'true').lower() == 'true')

# RETRY_JOB_ENABLED = os.getenv('Y2A_RETRY_JOB_ENABLED', 'true').lower() == 'true'
# RETRY_JOB_ATTEMPT_INTERVAL = os.getenv('Y2A_RETRY_JOB_ATTEMPT_INTERVAL', 5 * 60)
# RETRY_JOB_MAX_RETRY_DURATION = os.getenv('Y2A_RETRY_JOB_MAX_RETRY_DURATION', 2 * 60 * 60)


ENV_NAME_TG_TOKEN = 'Y2A_TG_TOKEN'
ENV_NAME_HASH_SALT = 'Y2A_HASH_SALT'
ENV_NAME_DEBUG_MODE = 'Y2A_DEBUG_MODE'


# Other
DATA_DIR_DIRNAME_IN_TEMPDIR = 'pip-ytb2audiobot-data'
DATA_DIR_NAME = 'data'



TELEGRAM_MAX_CAPTION_TEXT_SIZE = 1024 - 2

TELEGRAM_MAX_MESSAGE_TEXT_SIZE = 4096 - 4

TELEGRAM_MAX_FILE_SIZE_BYTES = 47000000

TELEGRAM_VALID_TOKEN_IMAGINARY_DEFAULT = '123456789:AAE_O0RiWZRJOeOB8Nn8JWia_uUTqa2bXGU'

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
    'audio-quality': AUDIO_QUALITY_BITRATE,
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
CLI_ACTIVATION_FORCE_REDOWNLOAD = ['force', 'forc', 'for', 'f']
CLI_ACTIVATION_SUMMARIZE = ['summarize', 'summary', 'summar', 'summ', 'sum']

CLI_ACTIVATION_ALL = CLI_ACTIVATION_SUBTITLES + CLI_ACTIVATION_MUSIC + CLI_ACTIVATION_TRANSLATION + CLI_ACTIVATION_FORCE_REDOWNLOAD + CLI_ACTIVATION_SUMMARIZE


ADDITIONAL_CHAPTER_BLOCK = Template('\n\n📌 <b>$title</b>\n[Chapter +${time_shift}]')

LOG_FORMAT_CALLED_FUNCTION = Template('💈💈 ${fname}():')

CAPTION_SLICE = Template('🍰 Slice from ${start_time} to ${end_time}')


DESCRIPTION_BLOCK_COMMANDS = f'''
<b>Commands</b>
• /help - Show this help message
• /extra - 🔮Advanced options
• /autodownload - 🏂‍ (Works only in channels) See about #todo
'''


DESCRIPTION_BLOCK_EXTRA_OPTIONS = '''
<b>🔮 Advanced Options:</b>
Choose from the following options to enhance your experience:

<b>• ✂️ Split by Duration:</b> Divide audio into equal-length segments.
<b>• ⏱️ Split by Timecodes:</b> Split audio based on specific timecodes.
<b>• 🎸 Set Audio Bitrate:</b> Adjust the audio quality to your preference.
<b>• 📝 Get Subtitles:</b> Extract subtitles from your media.
<b>• 🎙️ Get Audio Slice:</b> Choose a specific portion of the audio to save.
<b>• 🌍 Translate Any Language:</b> Translate text from any language to your desired one.

Please select an option to proceed:'''


DESCRIPTION_BLOCK_SPLIT_BY_DURATION = '''
<b>✂️ Select Duration for Splitting</b> (in minutes):

Please choose a duration to continue:'''


DESCRIPTION_BLOCK_BITRATE = '''
<b>🎸 Select Your Preferred Bitrate</b> (in kbps):

<b>• 48 kbps:</b> Very low quality, smallest file size.
<b>• 64 kbps:</b> Low quality, suitable for voice.
<b>• 96 kbps:</b> Medium quality, smaller size.
<b>• 128 kbps:</b> Standard quality, balanced size.
<b>• 196 kbps:</b> High quality, great for music.
<b>• 256 kbps:</b> Very high quality, larger size.
<b>• 320 kbps:</b> Best quality, largest file size.

Please choose a bitrate to continue:'''


DESCRIPTION_BLOCK_SUBTITLES = '''
<b>✏️ Subtitles Options:</b>

<b>• 🔮 Retrieve All:</b> Get the complete subtitles for the video.
<b>• 🔍 Search by Word:</b> Find specific words or phrases in the subtitles.

Please select an option to proceed:'''

DESCRIPTION_BLOCK_SLICE_PART_ONE = '''
<b>🍰 Step 1/2: Enter the START time for your slice.</b>

<b>⏱️ Accepted formats:</b>
• hh:mm:ss (e.g., 01:02:03)
• mm:ss (e.g., 02:02)
• Seconds only (e.g., 78)

Please provide the start time to continue:'''


DESCRIPTION_BLOCK_SLICE_PART_TWO = '''
<b>🍰 Step 2/2: Enter the END time for your slice.</b>

<b>⏱️ Accepted formats:</b>
• hh:mm:ss (e.g., 01:02:03)
• mm:ss (e.g., 02:02)
• Seconds only (e.g., 78)

Please provide the end time to complete the process:'''


DESCRIPTION_BLOCK_CLI = f'''
<b>📟 CLI options</b>

 - one
 - two'''


DESCRIPTION_BLOCK_SEND_YOUTUBE_LINK_TEXT = '''
<b>🔗 Please provide your YouTube link:</b>

Paste the URL below to proceed:'''


DESCRIPTION_BLOCK_REFERENCES = f'''
<b>References</b>
- https://t.me/ytb2audiostartbot (LTS)
- https://t.me/ytb2audiobetabot (BETA) #todo-all-logs-info

- https://andrewalevin.github.io/ytb2audiobot/
- https://github.com/andrewalevin/ytb2audiobot
- https://pypi.org/project/ytb2audiobot/
- https://hub.docker.com/r/andrewlevin/ytb2audiobot'''


DESCRIPTION_BLOCK_OKAY_AFTER_EXIT = f'''
<b>👋 Okay!</b>

You can provide a YouTube link anytime to download its audio, or select one of the following commands:

{DESCRIPTION_BLOCK_COMMANDS}
'''


BITRATE_VALUES_ROW_ONE = ['48k', '64k', '96k', '128k']
BITRATE_VALUES_ROW_TWO = ['196k', '256k', '320k']
BITRATE_VALUES_ALL = BITRATE_VALUES_ROW_ONE + BITRATE_VALUES_ROW_TWO

SPLIT_DURATION_VALUES_ROW_1 = ['2', '3', '5', '7', '11', '13', '17', '19']
SPLIT_DURATION_VALUES_ROW_2 = ['23', '29', '31', '37', '41', '43']
SPLIT_DURATION_VALUES_ROW_3 = ['47', '53', '59', '61', '67']
SPLIT_DURATION_VALUES_ROW_4 = ['73', '79', '83', '89']
SPLIT_DURATION_VALUES_ALL = SPLIT_DURATION_VALUES_ROW_1 + SPLIT_DURATION_VALUES_ROW_2 + SPLIT_DURATION_VALUES_ROW_3 + SPLIT_DURATION_VALUES_ROW_4


CAPTION_HEAD_TEMPLATE = Template('''$partition $title
<a href=\"youtu.be/$movieid\">youtu.be/$movieid</a> [$duration]
$author $additional

$content
''')

CAPTION_TRIMMED_END_TEXT = '…\n…\n⚔️ [Text truncated to fit Telegram’s caption limit]'


COMMANDS_SPLIT = [
    {'name': 'split', 'alias': 'split'},
    {'name': 'split', 'alias': 'spl'},
    {'name': 'split', 'alias': 'sp'},
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
    {'name': 'bitrate', 'alias': 'bit'}
]

COMMANDS_SUBTITLES = [
    {'name': 'subtitles', 'alias': 'subtitles'},
    {'name': 'subtitles', 'alias': 'subtitle'},
    {'name': 'subtitles', 'alias': 'subt'},
    {'name': 'subtitles', 'alias': 'subs'},
    {'name': 'subtitles', 'alias': 'sub'},
    {'name': 'subtitles', 'alias': 'su'}
]

COMMANDS_FORCE_DOWNLOAD = [
    {'name': 'download', 'alias': 'download'},
    {'name': 'download', 'alias': 'down'},
    {'name': 'download', 'alias': 'dow'},
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

BITRATE_VALUES = ['48k', '64k', '96k', '128k'] + ['196k', '256k', '320k']

ACTION_MUSIC_HIGH_BITRATE = BITRATE_VALUES[-1]

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
ACTION_NAME_FORCE_REDOWNLOAD = 'force'
ACTION_NAME_SUMMARIZE = 'summarize'

DESCRIPTION_BLOCK_WELCOME = f'''
<b>🪩 Welcome!</b>
(version:  {version(PACKAGE_NAME)})

I’m here 🎄🎄 🦍☘️  to help you download audio and explore additional features!
'''

START_AND_HELP_TEXT = f'''
{DESCRIPTION_BLOCK_WELCOME}

{DESCRIPTION_BLOCK_COMMANDS}

{DESCRIPTION_BLOCK_EXTRA_OPTIONS}

<b>📟 CLI options</b>

/cli

{DESCRIPTION_BLOCK_REFERENCES}
'''

TEXT_SAY_HELLO_BOT_OWNER_AT_STARTUP = f'''
🚀 Bot has started! 

📦 Package Version: {version(PACKAGE_NAME)}

{DESCRIPTION_BLOCK_COMMANDS}
'''


DELAY_LESSE_SECOND = 0.9