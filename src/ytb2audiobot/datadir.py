import pathlib
import tempfile
import zlib

from ytb2audiobot import config
import hashlib
from ytb2audiobot.logger import logger


def get_md5(data, length=999999999):
    md5_hash = hashlib.md5()
    md5_hash.update(data.encode('utf-8'))
    return md5_hash.hexdigest()[:length]


def get_hash_adler32(text):
    return zlib.adler32(text.encode('utf-8'))


def get_data_dir():
    _hash = hex(get_hash_adler32(pathlib.Path.cwd().as_posix()))[-8:]
    temp_dir = pathlib.Path(tempfile.gettempdir())

    if temp_dir.exists():
        data_dir = temp_dir.joinpath(f'{config.DIRNAME_IN_TEMPDIR}-{_hash}')
        data_dir.mkdir(parents=True, exist_ok=True)

        symlink = pathlib.Path(config.DIRNAME_DATA)
        if not symlink.exists():
            symlink.symlink_to(data_dir)

        return symlink
    else:
        data_dir = pathlib.Path(config.DIRNAME_DATA)
        if data_dir.is_symlink():
            try:
                data_dir.unlink()
            except Exception as e:
                logger.error(f'❌ Error symlink unlink: {e}')

        data_dir.mkdir(parents=True, exist_ok=True)

        return data_dir
