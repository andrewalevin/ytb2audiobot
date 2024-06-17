import time
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

import config


def parse_input(input_text: str) -> (str, str):
    input_parts = input_text.split(' ')
    url = input_parts[0]
    discovered_word = ''
    if len(input_parts) > 1:
        discovered_word = input_parts[1]

    return url, discovered_word


def get_movie_id(url: str) -> [str, None]:
    purl = urlparse(url)
    if not purl:
        return
    query_dict = parse_qs(purl.query)

    if 'youtube.com' in url:
        if 'v' not in query_dict:
            return
        if not (id_video := query_dict.get('v')[0]):
            return
        return id_video

    if 'youtu.be' in url:
        path_parts = purl.path.split('/')
        if len(path_parts) < 2:
            return
        return path_parts[1]

    if len(purl.netloc) < 2:
        # It is relative link
        if '/watch' in purl.path:
            if 'v' in query_dict:
                return query_dict.get('v')[0]

    return


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


def get_answer_text(subtitles, selected_index=[]):
    if not selected_index:
        selected_index = list(range(len(subtitles)))
    output_text = ''
    index_last = None
    for index_item in selected_index:
        if index_last and index_item - index_last > 1:
            output_text += '...\n\n'

        subtitle_time = time.strftime('%H:%M:%S', time.gmtime(int(subtitles[index_item]['start'])))
        subtitle_text = subtitles[index_item]['text']

        output_text += f'{subtitle_time} {subtitle_text}\n'

        index_last = index_item

    return output_text


from urllib.parse import urlparse



def main_subtitles(input_text: str) -> str:
    if not urlparse(input_text).netloc:
        return '⛔️ No URL in your request!'

    url, discovered_word = parse_input(input_text)
    if not url:
        return '⛔️ Bad input URL. Check it!'

    if not (movie_id := get_movie_id(url)):
        return '⛔️ Couldnt parse movie id from your URL. Check it!'

    try:
        subtitles = YouTubeTranscriptApi.get_transcript(movie_id, languages=['ru'])
    except TranscriptsDisabled:
        return '⛔️ YouTubeTranscriptApi: TranscriptsDisabled'
    except (ValueError, Exception):
        return '⛔️ Undefined problem in YouTubeTranscriptApi'

    if not discovered_word:
        return get_answer_text(subtitles)

    if not (discovered_index := get_discovered_subtitles_index(subtitles, discovered_word)):
        return 'Nothing Found :)'

    discovered_index = extend_discovered_index(discovered_index, len(subtitles), ADDITION_ROWS_NUMBER)

    output_text = get_answer_text(subtitles, discovered_index)

    output_text = format_text(output_text, discovered_word)

    return output_text