from typing import Optional


def time_hhmmss_check_and_convert(start_time: str) -> Optional[int]:
    """Convert a time string in hh:mm:ss, mm:ss, or ss format to total seconds.

    Args:
        start_time (str): Time string in the format hh:mm:ss, mm:ss, or ss.

    Returns:
        Optional[int]: The total time in seconds if valid, otherwise None.
    """

    # Case 1: Plain seconds as an integer string
    if start_time.isdigit():
        seconds = int(start_time)
        return seconds if seconds >= 0 else None

    # Split the input string by colons and validate
    parts = start_time.split(":")
    if len(parts) > 3 or not all(part.isdigit() for part in parts):
        return None

    hours, minutes, seconds = 0, 0, 0
    # Parse time parts into hours, minutes, and seconds based on the format
    try:
        parts = [int(part) for part in parts]
        if len(parts) == 3:  # hh:mm:ss
            hours, minutes, seconds = parts
        elif len(parts) == 2:  # mm:ss
            hours, minutes, seconds = 0, parts[0], parts[1]
        elif len(parts) == 1:  # ss
            hours, minutes, seconds = 0, 0, parts[0]
    except ValueError:
        return None

    # Validate minutes and seconds ranges
    if not (0 <= minutes < 60 and 0 <= seconds < 60):
        return None

    # Calculate total seconds
    return hours * 3600 + minutes * 60 + seconds
