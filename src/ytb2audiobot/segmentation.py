
def segments_verification(segments: list, max_segment_duration: int) -> list:
    # Calculate maximum allowed duration for each segment based on source file size and total duration

    for idx, segment in enumerate(segments):
        start = segment.get('start')  # Segment start time
        end = segment.get('end')  # Segment end time
        segment_duration = end - start  # Duration of the current segment

        # If the segment's duration exceeds the allowed max duration, split it
        if segment_duration > max_segment_duration:
            # Calculate how many parts the segment needs to be divided into
            partition_count = segment_duration / max_segment_duration

            # Round partition count up if close to the next integer, otherwise round down
            partition_count = int(partition_count) + 1 if partition_count % 1 > 0.91 else int(partition_count)

            # Calculate the duration for each part, ensuring it slightly exceeds even division
            part_duration = 1 + segment_duration // partition_count

            # Split the segment into multiple parts, each with duration <= part_duration
            segment_parts = [{'start': i, 'end': min(i + part_duration, end)} for i in range(start, end, part_duration)]

            # Replace the original segment with its divided parts in the list
            segments[idx:idx + 1] = segment_parts

    return segments


def get_segments_by_timecodes(timecodes: list, total_duration: int) -> list:
    # If no timecodes provided, return a single segment covering the entire duration
    if not timecodes:
        return [{'start': 0, 'end': total_duration, 'title': ''}]

    # Ensure the list starts with a timecode at 0 seconds
    if timecodes[0].get('time', -2) != 0:
        timecodes.insert(0, {'time': 0, 'title': 'STARTTIME'})

    # Generate segments from consecutive timecodes
    segments = [
        {
            'start': timecodes[i]['time'],
            'end': timecodes[i + 1]['time'] if i < len(timecodes) - 1 else total_duration,
            'title': timecodes[i].get('title', '')
        }
        for i in range(len(timecodes))]

    return segments


def get_segments_by_timecodes_from_dict(timecodes: dict, total_duration: int) -> list:
    # If no timecodes provided, return a single segment covering the entire duration
    if not timecodes:
        return [{'start': 0, 'end': total_duration, 'title': ''}]

    # Ensure the list starts with a timecode at 0 seconds
    if  0 not in timecodes:
        timecodes[0] = {'title': 'START_TIME', 'type': 'timecodes'}

    sorted_keys = sorted(timecodes.keys())

    segments = []

    for idx, key in enumerate(sorted_keys):
        segments.append({
            'start': key,
            'end': sorted_keys[idx + 1] if idx < len(timecodes) - 1 else total_duration,
            'title': timecodes[key].get('title', '')})

    return segments


def get_segments_by_duration(total_duration: int, segment_duration: int) -> list:
    segment_duration = 10 if segment_duration < 10 else segment_duration

    segments = [
        {
            'start': time,
            'end': min(time + segment_duration, total_duration),
            'title': ''
        }
        for time in range(0, total_duration, segment_duration)
    ]

    # Adjust the end time of the last segment
    if segments:
        segments[-1]['end'] = total_duration

    return segments


def add_paddings_to_segments(input_segments: list, padding_duration: int) -> list:
    MAX_PADDING_DURATION = 60 * 5
    padding_duration = max(0, min(padding_duration, MAX_PADDING_DURATION))

    first_start = input_segments[0].get('start')
    last_end = input_segments[-1].get('end')

    segments = [
        {
            'start': max(first_start, segment['start'] - padding_duration),
            'end': min(last_end, segment['end'] + padding_duration),
            'title': segment['title']
        }
        for segment in input_segments
    ]

    return segments


def make_magic_tail(segments: list, max_segment_duration: int) -> list:
    """Merges the last two segments if their duration ratio meets a certain threshold."""

    if len(segments) <= 1:
        return segments

    last_duration = segments[-1]['end'] - segments[-1]['start']
    second_last_duration = segments[-2]['end'] - segments[-2]['start']
    duration_ratio = second_last_duration / last_duration

    _GOLDEN_RATIO = 1.618
    if duration_ratio > _GOLDEN_RATIO and (second_last_duration + last_duration) < max_segment_duration:
        segments[-2]['end'] = segments[-1]['end']
        segments.pop()  # Remove the last segment after merging

    return segments
