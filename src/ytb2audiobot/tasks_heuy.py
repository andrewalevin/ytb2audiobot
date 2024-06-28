from huey import SqliteHuey
from ytb2audiobot.processing import processing_commands

huey = SqliteHuey(filename='../../huey-table.db')


@huey.task()
async def heuy_processing_commands(command_context: dict):
    return await processing_commands(command_context)

