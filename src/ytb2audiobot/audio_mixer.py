import pathlib
from typing import Optional
from ytb2audiobot.logger import logger
from ytb2audiobot.utils import run_command


async def mix_audio_m4a(
        original_path: pathlib.Path,
        translated_path: pathlib.Path,
        output_path: pathlib.Path,
        overlay_volume: float = 0.4,
        bitrate: str = '48k'
) -> Optional[pathlib.Path]:
    """
    Mixes two audio files (original and translated) into one output file with a specified overlay volume and bitrate.

    Args:
        original_path (pathlib.Path): Path to the original audio file.
        translated_path (pathlib.Path): Path to the translated audio file.
        output_path (pathlib.Path): Path where the mixed audio file will be saved.
        overlay_volume (float, optional): Volume of the overlay audio. Default is 0.4.
        bitrate (str, optional): Audio bitrate for the output file. Default is '48k'.

    Returns:
        Optional[pathlib.Path]: The path to the output mixed audio file, or None if an error occurred.
    """
    try:
        # Build the ffmpeg command to mix the audio files
        command = (
            f"ffmpeg -i {translated_path.as_posix()} -i {original_path.as_posix()} "
            f"-vn -filter_complex '[1:a]volume={overlay_volume}[a2];[0:a][a2]amix=inputs=2:duration=shortest' "
            f"-c:a aac -b:a {bitrate} -y {output_path.as_posix()}"
        )

        # Run the command asynchronously
        await run_command(command)

    except Exception as e:
        # Log the error with the exception message
        logger.error(f'❌ Error occurred while mixing audio: {e}')
        return None

    # Return the path to the output file
    return output_path