from urlextract import URLExtract
from ytb2audio.ytb2audio import get_youtube_move_id

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

ALL_COMMANDS = COMMANDS_SPLIT + COMMANDS_BITRATE + COMMANDS_SUBTITLES

YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be']

PARAMS_MAX_COUNT = 2


def is_youtube_url(text):

    for domain in YOUTUBE_DOMAINS:
        if domain in text:
            return True
    return False


def get_command_params_of_request(text):
    command_context = dict()
    command_context['id'] = ''
    command_context['url_started'] = False
    command_context['name'] = ''
    command_context['params'] = []
    command_context['force_download'] = False
    command_context['post_status_id'] = None

    text = text.strip()
    if not is_youtube_url(text):
        return command_context

    urls = URLExtract().find_urls(text)
    url = ''
    for url in urls:
        url = url.strip()
        if is_youtube_url(url):
            command_context['url'] = url
            break
    movie_id = get_youtube_move_id(command_context.get('url'))
    if not movie_id:
        return command_context

    command_context['id'] = movie_id

    if text.startswith(url):
        command_context['url_started'] = True

    text = text.replace(url, '')
    text = text.strip()
    text = text.replace('   ', ' ')
    text = text.replace('  ', ' ')
    parts = text.split(' ')

    print('🌈 Parts of Request: ', parts)
    print()

    if not len(parts):
        return command_context

    for idx, command in enumerate(COMMANDS_FORCE_DOWNLOAD):
        if command.get('alias') == parts[0]:
            print('🏺 Found bot')
            command_context['force_download'] = True
            parts = parts[1:]
            break

    if not parts:
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

    command_context['params'] = parts[1:PARAMS_MAX_COUNT+1]

    return command_context
