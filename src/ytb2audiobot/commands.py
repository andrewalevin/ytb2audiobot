from urlextract import URLExtract

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

YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be']

PARAMS_MAX_COUNT = 2


def is_youtube_url(text):

    for domain in YOUTUBE_DOMAINS:
        if domain in text:
            return True
    return False


def get_command_params_of_request(text):
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

    command_context['params'] = parts[1:PARAMS_MAX_COUNT+1]

    return command_context
