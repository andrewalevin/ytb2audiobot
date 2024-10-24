import dramatiq
from dramatiq.brokers.redis import RedisBroker
from src.ytb2audiobot.processing import download_processing

redis_broker = RedisBroker()
dramatiq.set_broker(redis_broker)


@dramatiq.actor
async def dramatiq_processing_commands(command_context: dict):
    return await download_processing(command_context)

