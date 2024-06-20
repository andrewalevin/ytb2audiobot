import datetime
import re

from ytb2audiobot.utils import capital2lower

TIMECODES_THRESHOLD_COUNT = 3

MOVIES_TEST_TIMCODES = '''
Как миграция убивает францию
https://www.youtube.com/watch?v=iR0ETOSis7Y

Ремизов
youtu.be/iI3qo1Bxi0o 

'''


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




SYMBOLS_TO_CLEAN = '— – − - = _ |'


def remove_started_symbols(text):
    text = text.strip()
    text = f'@@@{text}'
    for _ in range(5):
        for symb in SYMBOLS_TO_CLEAN.split(' '):
            text = text.replace(f'@@@{symb}', '@@@')
            text = text.strip()
    return text.strip().replace('@@@', '').strip()


def get_timestamps_group(text, scheme):
    timestamps_findall_results = re.findall(r'(\d*:?\d+:\d+)\s+(.+)', text)
    if not timestamps_findall_results:
        return ['' for _ in range(len(scheme))]

    timestamps_all = [{'time': time_to_seconds(stamp[0]), 'title': stamp[1]} for stamp in timestamps_findall_results]

    timestamps_group = []
    for idx, part in enumerate(scheme):
        output_rows = []
        for stamp in timestamps_all:
            if stamp.get('time') < part[0] or part[1] < stamp.get('time'):
                continue
            time = filter_timestamp_format(datetime.timedelta(seconds=stamp.get('time') - part[0]))
            title = capital2lower(stamp.get('title'))
            title = remove_started_symbols(title)
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
        matches = re.compile(r'(\d{1,2}:\d{2})').findall(part)
        if len(matches) > TIMECODES_THRESHOLD_COUNT:
            return clean_timecodes_text(part)


async def get_timecodes(scheme, text):
    timecodes = ['' for _ in range(len(scheme))]
    if timecodes_text := get_timecodes_text(text):
        timecodes = get_timestamps_group(timecodes_text, scheme)
    return timecodes, ''
