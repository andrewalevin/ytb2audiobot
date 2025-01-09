import os
import pprint
import sys

from ytb2audiobot import config
from ytb2audiobot.download import filter_timecodes_within_bounds, get_timecodes_formatted_text
from ytb2audiobot.logger import logger
DEBUG = False if os.getenv(config.ENV_NAME_DEBUG_MODE, 'false').lower() != 'true' else True


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

    # todo
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


def rebalance_segments_long_timecodes(
        segments: list,
        available_caption_size: int,
        timecodes_dict: dict,
        max_audio_len_sec: int = sys.maxsize,
) -> list:
    """
    Rebalance segments based on timecodes and available caption size.
    """

    # todo
    logger.debug('🎆 Rebalance process started:')
    logger.debug(f'🎆 Segments: {pprint.pformat(segments)}')
    logger.debug(f'🎆 Timecodes dictionary: {pprint.pformat(timecodes_dict)}')

    # Extract start and end times of the original segments
    full_start = segments[0].get('start')
    full_end = segments[-1].get('end')

    # Check if rebalance is needed
    for segment in segments:
        timecodes_text = get_timecodes_formatted_text(
            filter_timecodes_within_bounds(
                timecodes=timecodes_dict,
                start_time=segment.get('start') + config.SEGMENT_DUARITION_PADDING_SEC,
                end_time=segment.get('end') - config.SEGMENT_DUARITION_PADDING_SEC - 1),
            full_start)

        if available_caption_size - len(timecodes_text) < 0:
            logger.debug('🎆 Starting Rebalance process:')
            break
    else:
        return segments

    # Initialize variables for grouping timecodes
    timecode_groups = []
    current_group = []
    current_group_len = 0

    # Group timecodes
    for time, timecode in timecodes_dict.items():
        timecode_text = f"00:00:00 - {timecode.get('title')}"
        proposed_len = current_group_len + len(timecode_text)

        if available_caption_size - proposed_len < 0:
            timecode_groups.append(current_group)
            current_group = [time]
            current_group_len = len(timecode_text)
            continue

        if current_group and time - current_group[0] > max_audio_len_sec:
            timecode_groups.append(current_group)
            current_group = [time]
            current_group_len = len(timecode_text)
            continue

        current_group.append(time)
        current_group_len = proposed_len

    # Add the last group if it exists
    if current_group:
        timecode_groups.append(current_group)


    # Create new segments from groups
    new_segments = []
    for i, group in enumerate(timecode_groups):
        start_time = group[0]
        end_time = (
            timecode_groups[i + 1][0] - 1
            if i < len(timecode_groups) - 1
            else full_end
        )

        new_segments.append({
            "start": start_time,
            "end": end_time,
            "title": ""  # Title can be added dynamically if needed
        })

        # Check if the last segment can be unified with the second-to-last segment
    if len(new_segments) > 1:
        last_segment = new_segments[-1]
        second_last_segment = new_segments[-2]

        # Get timecodes within the last two segments
        last_timecodes = filter_timecodes_within_bounds(
            timecodes=timecodes_dict,
            start_time=last_segment['start'],
            end_time=last_segment['end']
        )
        second_last_timecodes = filter_timecodes_within_bounds(
            timecodes=timecodes_dict,
            start_time=second_last_segment['start'],
            end_time=second_last_segment['end']
        )

        # Combine their text lengths
        combined_text_length = len(get_timecodes_formatted_text(last_timecodes, last_segment['start'])) + \
                               len(get_timecodes_formatted_text(second_last_timecodes, second_last_segment['start']))

        if combined_text_length <= available_caption_size:
            # Merge the segments
            second_last_segment['end'] = last_segment['end']
            new_segments.pop()  # Remove the last segment

    return new_segments


