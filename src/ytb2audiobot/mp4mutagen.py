import pathlib

from mutagen.mp4 import MP4


async def get_mp4object(path: pathlib.Path):
    path = pathlib.Path(path)
    try:
        mp4object = MP4(path.as_posix())
    except Exception as e:
        return {}
    return mp4object