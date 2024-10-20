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


async def get_timecodes(scheme, description):
    #print('🛍 get_timecodes: ')
    #print('description: ', description)
    #print()

    if not isinstance(description, str):
        if isinstance(description, list):
            description = description[0]
        else:
            return [], ''

    try:
        timestamps = get_all_timecodes(description)
    except Exception as e:
        return ['' for _ in range(len(scheme))], ''

    #print('timestamps: ')
    #print(timestamps)
    #print()

    timecodes = []
    for idx, part in enumerate(scheme):
        output_rows = []
        for stamp in timestamps:
            if int(stamp.get('timecode')) < int(part[0]) or int(part[1]) < int(stamp.get('timecode')):
                continue
            time = filter_timestamp_format(datetime.timedelta(seconds=stamp.get('timecode') - part[0]))
            title = capital2lower(stamp.get('title'))

            output_rows.append(f'{time} - {title}')
        timecodes.append('\n'.join(output_rows))

    return timecodes, ''
