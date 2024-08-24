import datetime
import re

from ytb2audiobot.utils import capital2lower
from ytb2audiobot import config

SYMBOLS_TO_CLEAN = '— – − - = _ |'
TIMECODES_THRESHOLD_COUNT = 3


def clean_timecodes_text(text):
    text = (text
            .replace('---', '')
            .replace('--', '')
            .replace('===', '')
            .replace('==', '')
            .replace(' =', '')
            .replace('___', '')
            .replace('__', '')
            .replace('_ _ _', '')
            .replace('_ _', '')
            .replace(' _', '')
            .replace('\n-', '')
            .replace('\n=', '')
            .replace('\n_', '')
            .replace('\n -', '')
            .replace('\n =', '')
            .replace('\n _', '')
            .strip()
            .lstrip()
            .rstrip()
            )
    return text


def time_to_seconds(time_str):
    if time_str.count(':') == 1:
        format_str = '%M:%S'
        time_obj = datetime.datetime.strptime(time_str, format_str)
        total_seconds = time_obj.minute * 60 + time_obj.second
    elif time_str.count(':') == 2:
        format_str = '%H:%M:%S'
        time_obj = datetime.datetime.strptime(time_str, format_str)
        total_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
    else:
        raise ValueError("Time format not recognized")
    return total_seconds


def filter_timestamp_format(_time):
    _time = str(_time)
    if _time == '0:00':
        return '0:00'

    if _time == '00:00':
        return '0:00'

    if _time == '0:00:00':
        return '0:00'

    if _time == '00:00:00':
        return '0:00'

    if _time.startswith('00:00:0'):
        return _time.replace('00:00:0', '0:0')

    if _time.startswith('0:00:0'):
        return _time.replace('0:00:0', '0:0')

    if _time.startswith('00:00:'):
        return _time.replace('00:00:', '0:')

    if _time.startswith('0:00:'):
        return _time.replace('0:00:', '0:')

    _time = f'@@{_time}##'
    _time = _time.replace('@@00:00:0', '@@0:0')
    _time = _time.replace('@@0:0', '@@')
    _time = _time.replace('@@0:', '@@')

    return _time.replace('@@', '').replace('##', '')


TIMECODE_PATTERN = r'(\d?:?\d+:\d+)'
TIMECODE_PATTERN = r'(\d*:*\d+:+\d+)'


STRIP_CHARS = ' #$%&@()*+[\\]^_`{|}~--−–—'
DOTS_CHARS = '.,;:?!'


def get_matched(text):
    print('🍷 Text: ', text)
    matched = re.findall(TIMECODE_PATTERN, text)
    print('🍷🍷 Matched: ', matched)

    return matched


def get_timestamps_group(text, scheme):
    print('🍕 get_timestamps_group : ', text)
    print()

    timestamps_findall_results = []
    for row in text.split('\n'):
        if not (matched := re.findall(TIMECODE_PATTERN, row)):
            continue

        title = row.replace(matched[0], '')
        title = title.strip(STRIP_CHARS).lstrip(DOTS_CHARS)
        timestamps_findall_results.append([matched[0], title])

    if not timestamps_findall_results:
        return ['' for _ in range(len(scheme))]

    timestamps_all = [{'time': time_to_seconds(stamp[0]), 'title': stamp[1]} for stamp in timestamps_findall_results]

    timestamps_group = []
    for idx, part in enumerate(scheme):
        output_rows = []
        for stamp in timestamps_all:
            if int(stamp.get('time')) < int(part[0]) or int(part[1]) < int(stamp.get('time')):
                continue
            time = filter_timestamp_format(datetime.timedelta(seconds=stamp.get('time') - part[0]))
            title = capital2lower(stamp.get('title'))

            output_rows.append(f'{time} - {title}')
        timestamps_group.append('\n'.join(output_rows))

    return timestamps_group


def get_timecodes_text(description):
    if not description:
        return
    if type(description) is not list:
        return
    if len(description) < 1:
        return ''

    for part in description[0].split('\n\n'):
        matches = re.findall(TIMECODE_PATTERN, part)
        if len(matches) > TIMECODES_THRESHOLD_COUNT:
            return clean_timecodes_text(part)


async def get_timecodes(scheme, text):
    timecodes = ['' for _ in range(len(scheme))]
    if timecodes_text := get_timecodes_text(text):
        timecodes = get_timestamps_group(timecodes_text, scheme)
    return timecodes, ''
