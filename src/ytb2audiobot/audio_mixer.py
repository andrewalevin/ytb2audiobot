import pathlib
from typing import Optional
from ytb2audiobot.logger import logger
from ytb2audiobot.utils import run_command


async def mix_audio_m4a(
        original_path: pathlib.Path,
        translated_path: pathlib.Path,
        output_path: pathlib.Path,
        overlay_volume=0.4,
        bitrate='48k'
) -> Optional[pathlib.Path]:
    try:

        command = (
            f"ffmpeg -i {translated_path.as_posix()} -i {original_path.as_posix()} "
            f"-vn -filter_complex '[1:a]volume={overlay_volume}[a2];[0:a][a2]amix=inputs=2:duration=shortest' "
            f"-c:a aac -b:a {bitrate} -y {output_path.as_posix()}"
        )

        logger.debug(f'🔰COMAMND: {command}')

        await run_command(command)

    except Exception as e:
        logger.error(f'🔴 Error mixing audio: {e}')
        return

    return pathlib.Path(output_path)
