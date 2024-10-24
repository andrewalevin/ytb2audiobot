from huey import SqliteHuey
from src.ytb2audiobot.processing import download_processing

huey = SqliteHuey(filename='../dev/huey-table.db')


@huey.task()
async def heuy_processing_commands(command_context: dict):
    return await download_processing(command_context)

