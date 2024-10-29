import asyncio
import datetime
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


async def empty_dir_by_cron(params):
    if not params.get('age'):
        return

    data_dir = get_data_dir()

    now = int(datetime.datetime.now().timestamp())
    for file in data_dir.iterdir():
        creation = int(file.stat().st_ctime)
        if now - creation > params.get('age'):
            #print('\t', '🔹🗑', '\t', file.name, '\t', f'DELTA: {now - creation}',
            #      f'Creation: ', datetime.datetime.fromtimestamp(creation), f'({creation})', '\t'
            #                                                                                 f'Current: ',
            #      datetime.datetime.fromtimestamp(now), f'({now})', )
            await delete_file_async(file)


async def run_periodically(interval, func, params=None):
    if params is None:
        params = {}
    while True:
        await func(params)
        await asyncio.sleep(interval)
