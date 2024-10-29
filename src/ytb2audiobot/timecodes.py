import datetime

from ytb2audiobot.utils import capital2lower
from ytbtimecodes.timecodes import get_all_timecodes


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


def get_boundaries_timecodes(timecodes, start, end):
    outputs = []
    for timecode in timecodes:
        if int(timecode.get('timecode')) < int(start) or int(end) < int(timecode.get('timecode')):
            continue
        outputs.append(timecode)
    return outputs


def get_timecodes_formatted_text(timecodes: list):
    if not timecodes:
        return ''

    rows = []
    for stamp in timecodes:
        _time = filter_timestamp_format(datetime.timedelta(seconds=stamp.get('timecode')))
        _title = capital2lower(stamp.get('title'))
        rows.append(f'{_time} - {_title}')
    return '\n'.join(rows)


async def get_timecodes(scheme, description):
    if not isinstance(description, str):
        if isinstance(description, list):
            description = description[0]
        else:
            return [], ''

    try:
        timestamps = get_all_timecodes(description)
    except Exception as e:
        return ['' for _ in range(len(scheme))], ''

    print('♏️ Timestamps: ', timestamps)
    print()

    timecodes = []
    for idx, part in enumerate(scheme):
        start = part[0]
        end = part[1]

        boundaries_timecodes = get_boundaries_timecodes(timestamps, start, end)
        _text = get_timecodes_formatted_text(boundaries_timecodes)
        timecodes.append(_text)

    return timecodes
