from src.ytb2audiobot import config


def read_autodownload_chat_ids_hashed():
    if not config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH.exists():
        return {}

    with config.AUTODOWNLOAD_CHAT_IDS_HASHED_PATH.open(mode='r') as file:
        data = file.read()
        return {row: None for row in data.split('\n')}

