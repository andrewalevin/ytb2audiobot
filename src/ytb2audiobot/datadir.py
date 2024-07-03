import pathlib
import tempfile
from ytb2audiobot import config


def get_data_dir():
    temp_dir = pathlib.Path(tempfile.gettempdir())
    if temp_dir.exists():
        data_dir = temp_dir.joinpath(config.DIRNAME_IN_TEMPDIR)
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
                print(f'Error symlink unlink: {e}')

        data_dir.mkdir(parents=True, exist_ok=True)

        return data_dir
