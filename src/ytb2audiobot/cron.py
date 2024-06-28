import asyncio
import datetime
import pathlib

from ytb2audiobot.datadir import get_data_dir

data_dir = get_data_dir()


async def empty_dir_by_cron(age_seconds):
    for file in data_dir.iterdir():
        if datetime.datetime.now().timestamp() - file.stat().st_mtime > age_seconds:
            file.unlink()


async def run_periodically(interval, age, func):
    while True:
        await func(age)
        await asyncio.sleep(interval)


async def run_cron():
    print('⏰  Running cron ... ')
    await run_periodically(60, 3600, empty_dir_by_cron)
