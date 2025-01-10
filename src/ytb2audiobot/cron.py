import asyncio
import datetime
import pathlib

from ytb2audiobot.utils import delete_file_async, get_data_dir, run_command
from ytb2audiobot.logger import logger


async def update_pip_package_ytdlp(params: dict):
    """

    :type params: object
    """
    stdout, stderr, return_code = await run_command('pip install --upgrade yt-dlp --root-user-action=ignore')

    sign = 'Success! ✅' if return_code == 0 else 'Failure! ❌'
    logger.info(f'🎃🔄 Upgrade yt-dlp package: {sign}')

    if stdout:
        logger.debug('\n' + '\n'.join(f'\t{line}' for line in stdout.splitlines()))
    if stderr:
        logger.error('\n' + '\n'.join(f'\t{line}' for line in stderr.splitlines()))


async def empty_data_dir_by_cron(params: dict):
    """
    Removes files from a directory if they exceed a specified age.

    Args:
        params (dict): A dictionary containing the following keys:
            - 'age' (int): The maximum age (in seconds) a file can have before being deleted.
            - 'keep_files' (bool): If True, files are not deleted.
            - 'folder' (str): The path to the folder to clean.
    """
    age = params.get('age')
    keep_files = params.get('keep_files')
    folder_path = params.get('folder')

    # Validate required parameters
    if not age or keep_files or not folder_path:
        return

    folder = pathlib.Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Invalid folder path: {folder_path}")

    # Get the current timestamp
    now = int(datetime.datetime.now().timestamp())

    # Iterate through files and delete if older than specified age
    for file in folder.iterdir():
        if not file.is_file():
            continue

        creation_time = int(file.stat().st_ctime)
        if now - creation_time > age:
            await delete_file_async(file)


async def run_periodically(interval, func, params=None):
    if params is None:
        params = {}
    while True:
        await func(params)
        await asyncio.sleep(interval)
