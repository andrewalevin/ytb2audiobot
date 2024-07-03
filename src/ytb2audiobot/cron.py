import asyncio
import datetime

from ytb2audiobot.datadir import get_data_dir
from ytb2audiobot.utils import delete_file_async


data_dir = get_data_dir()


async def empty_dir_by_cron(age_seconds):
    now = int(datetime.datetime.now().timestamp())
    for file in data_dir.iterdir():
        creation = int(file.stat().st_ctime)
        if now - creation > age_seconds:
            print('\t', '🔹🗑', '\t', file.name, '\t', f'DELTA: {now - creation}',
                  f'Creation: ', datetime.datetime.fromtimestamp(creation), f'({creation})', '\t'
                  f'Current: ', datetime.datetime.fromtimestamp(now), f'({now})',)
            await delete_file_async(file)


async def run_periodically(interval, age, func):
    while True:
        await func(age)
        await asyncio.sleep(interval)


async def run_cron():
    print('⏰  Running cron ... ')
    await run_periodically(60, 3600, empty_dir_by_cron)
