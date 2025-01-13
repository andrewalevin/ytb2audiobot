import hashlib
import pathlib
import random
import string
from pathlib import Path
from typing import Any, Union
import aiofiles
import yaml


def get_hash(data: Any, limit_digits: int = None) -> str:
    """Generate SHA-256 hash for the given data.

    Args:
        data (Any): The input data to hash. It will be converted to a string if not already.
        limit_digits (int, optional): The number of digits to return from the hash. Defaults to None, which returns the full hash.

    Returns:
        str: The SHA-256 hash of the input data, truncated to `limit_digits` if provided.
    """
    _hash = hashlib.sha256(str(data).encode('utf-8')).hexdigest()
    if limit_digits:
        return _hash[:limit_digits]  # Return the truncated hash
    return _hash  # Return the full hash if no limit is specified

def generate_random_salt(length: int = 32) -> str:
    """Generate a random salt of a given length."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


DEFAULT_PATH_NAME = 'autodownload-hashed-chat-ids.yaml'

class AutodownloadChatManager:
    """Manages a collection of hashed chat IDs with salted hashing and persistent storage."""

    def __init__(self, path: Union[Path, str] = DEFAULT_PATH_NAME):
        """
        Initialize the manager with a storage file.

        Args:
            path (Union[Path, str]): The directory to store the YAML file.
        """
        self.hashed_chat_ids = set()
        self.path = Path(path)

        if not self.path.parent.exists():
            self.path = pathlib.Path(DEFAULT_PATH_NAME)

        self.salt = ""

        if self.path.exists():
            try:
                self.restore()
            except Exception as e:
                print(f"Error restoring data from {self.path}: {e}")

        if not self.salt:
            self.salt = generate_random_salt()

    def _get_hash_salted(self, chat_id: str) -> str:
        """Generate a salted hash for the given chat_id."""
        return get_hash(chat_id + self.salt, 16)

    def is_chat_id_inside(self, chat_id: Union[str, int]) -> bool:
        """Check if the salted hash of the chat_id exists in the storage."""
        return self._get_hash_salted(str(chat_id)) in self.hashed_chat_ids

    async def add_chat_id(self, chat_id: Union[str, int]) -> None:
        """Add the salted hash of the chat_id to the storage."""
        self.hashed_chat_ids.add(self._get_hash_salted(str(chat_id)))
        await self.save_hashed_chat_ids()

    async def remove_chat_id(self, chat_id: Union[str, int]) -> None:
        """Remove the salted hash of the chat_id from the storage."""
        self.hashed_chat_ids.discard(self._get_hash_salted(str(chat_id)))
        await self.save_hashed_chat_ids()

    async def toggle_chat_state(self, chat_id: Union[str, int]) -> bool:
        """Toggle the presence of the chat_id in the storage."""
        if self.is_chat_id_inside(chat_id):
            await self.remove_chat_id(chat_id)
            await self.save_hashed_chat_ids()
            return False
        else:
            await self.add_chat_id(chat_id)
            await self.save_hashed_chat_ids()
            return True

    def restore(self) -> None:
        """Restore data synchronously from the storage file."""
        with self.path.open('r') as file:
            data = yaml.safe_load(file)
            self.salt = data.get('salt', '')
            self.hashed_chat_ids = set(data.get('chat_ids', []))

    async def save_hashed_chat_ids(self, _params=None) -> None:
        """Save data asynchronously to the storage file."""
        data = {
            'salt': self.salt,
            'chat_ids': list(self.hashed_chat_ids),
        }
        async with aiofiles.open(self.path, 'w') as file:
            await file.write(yaml.dump(data, default_flow_style=False, sort_keys=False))
