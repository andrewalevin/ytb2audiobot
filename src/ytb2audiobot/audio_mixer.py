import pathlib
from typing import Optional
from ytb2audiobot.logger import logger
from pydub import AudioSegment


async def mix_audio_m4a(
        original_path: pathlib.Path,
        translated_path: pathlib.Path,
        output_path: pathlib.Path,
        overlay_volume=0.4,
        bitrate='48k'
) -> Optional[pathlib.Path]:
    try:
        original_audio = AudioSegment.from_file(original_path, format="m4a")

        translated_audio = AudioSegment.from_file(translated_path, format="m4a")

        min_length = min(len(original_audio), len(translated_audio))

        original_audio = original_audio[:min_length]
        translated_audio = translated_audio[:min_length]

        def map_range(value, old_min, old_max, new_min, new_max):
            if old_min == old_max:
                return new_min
            return new_min + ((value - old_min) / (old_max - old_min)) * (new_max - new_min)

        vol = map_range(overlay_volume, 0.0, 1.0, -60.0, original_audio.dBFS)

        original_audio = original_audio - original_audio.dBFS + vol

        mixed_audio = original_audio.overlay(translated_audio)

        mixed_audio.export(output_path, format="mp4", bitrate=bitrate)
    except Exception as e:
        logger.error(f'🔴 Error: {e}')
        return

    return output_path
