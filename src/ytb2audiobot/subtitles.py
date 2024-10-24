import time
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from src.ytb2audiobot import config


def get_answer_text(subtitles, selected_index=None):
    if selected_index is None:
        selected_index = []
    if not selected_index:
        selected_index = list(range(len(subtitles)))
    output_text = ''
    index_last = None
    for index_item in selected_index:
        if index_last and index_item - index_last > 1:
            output_text += '...\n'

        subtitle_time = time.strftime('%H:%M:%S', time.gmtime(int(subtitles[index_item]['start'])))
        subtitle_text = subtitles[index_item]['text']

        output_text += f'{subtitle_time} {subtitle_text}\n'

        index_last = index_item

    return output_text


def get_discovered_subtitles_index(subtitles, discovered_word):
    discovered_rows = set()
    for idx, sub in enumerate(subtitles):
        text = sub['text'].lower()
        text = f' {text} '
        res_find = text.find(discovered_word)
        if res_find > 0:
            discovered_rows.add(idx)

    return discovered_rows


def extend_discovered_index(discovered_index, max_length, count_addition_index=1):
    for row in discovered_index.copy():
        for row_add in list(range(row-count_addition_index, row+count_addition_index+1)):
            if 0 <= row_add <= max_length-1:
                discovered_index.add(row_add)

    return sorted(discovered_index)


def format_text(text, target):
    if config.IS_TEXT_FORMATTED:
        text = text.replace(target, config.FORMAT_TEMPLATE.substitute(text=target))
        text = text.replace(target.capitalize(), config.FORMAT_TEMPLATE.substitute(text=target.capitalize()))
        text = text.replace(target.upper(), config.FORMAT_TEMPLATE.substitute(text=target.upper()))
        text = text.replace(target.lower(), config.FORMAT_TEMPLATE.substitute(text=target.lower()))
    return text


async def get_subtitles(movie_id: str, discovered_word: str = ''):
    try:
        subtitles = YouTubeTranscriptApi.get_transcript(movie_id, languages=['ru'])
    except TranscriptsDisabled:
        return '', '⛔️ YouTubeTranscriptApi: TranscriptsDisabled'
    except (ValueError, Exception):
        return '', '⛔️ Undefined problem in YouTubeTranscriptApi'

    if not discovered_word:
        text = get_answer_text(subtitles)
        return text, ''

    if not (discovered_index := get_discovered_subtitles_index(subtitles, discovered_word)):
        return '🔦 Nothing Found! 😉', ''

    discovered_index = extend_discovered_index(discovered_index, len(subtitles), config.ADDITION_ROWS_NUMBER)

    text = get_answer_text(subtitles, discovered_index)

    text = format_text(text, discovered_word)

    return text, ''
