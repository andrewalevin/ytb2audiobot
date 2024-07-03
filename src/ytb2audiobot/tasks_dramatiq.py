import dramatiq
from dramatiq.brokers.redis import RedisBroker
from ytb2audiobot.processing import processing_commands

redis_broker = RedisBroker()
dramatiq.set_broker(redis_broker)


@dramatiq.actor
async def dramatiq_processing_commands(command_context: dict):
    return await processing_commands(command_context)

