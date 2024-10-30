import pathlib
import tempfile
import hashlib
import config  # Assuming config has DATA_DIR_DIRNAME_IN_TEMPDIR and DATA_DIR_NAME


class DataDirManager(pathlib.Path):
    _flavour = pathlib._windows_flavour if pathlib.Path().drive else pathlib._posix_flavour

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    @staticmethod
    def remove_all_in_dir(data_dir: pathlib.Path, except_list=None):
        """
        Remove all files and subdirectories in a directory except specified in except_list.
        """
        except_list = except_list or []
        for item in data_dir.iterdir():
            if item.name in except_list:
                continue
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                for subitem in item.rglob('*'):
                    if subitem.name in except_list:
                        continue
                    if subitem.is_file():
                        subitem.unlink()
                    elif subitem.is_dir():
                        subitem.rmdir()
                item.rmdir()

    @staticmethod
    def get_data_dir():
        """
        Creates or retrieves the data directory, with a unique suffix based on the current working directory's hash.
        """
        # Generate unique hash based on current working directory
        hash_value = hashlib.adler32(pathlib.Path.cwd().as_posix().encode())
        _hash = hex(hash_value)[-8:]
        temp_dir = pathlib.Path(tempfile.gettempdir())

        # Create or retrieve directory within temporary directory
        if temp_dir.exists():
            data_dir = temp_dir.joinpath(f'{config.DATA_DIR_DIRNAME_IN_TEMPDIR}-{_hash}')
            data_dir.mkdir(parents=True, exist_ok=True)

            # Create symlink if it doesn't exist
            symlink = pathlib.Path(config.DATA_DIR_NAME)
            if not symlink.exists():
                symlink.symlink_to(data_dir)
            return symlink

        # Fallback: create directory in the current directory
        else:
            data_dir = pathlib.Path(config.DATA_DIR_NAME)
            if data_dir.is_symlink():
                try:
                    data_dir.unlink()
                except Exception as e:
                    print(f'❌ Error symlink unlink: {e}')
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir

    @staticmethod
    def remove_files_with_pattern(data_dir: pathlib.Path, pattern="-parts-"):
        """
        Remove all files within the directory that contain the specified pattern in their filenames.
        """
        for file in data_dir.rglob(f"*{pattern}*"):
            if file.is_file():
                file.unlink()