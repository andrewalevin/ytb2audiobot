import os
import random
import string
import pickle
from pathlib import Path
from typing import Union
from ytb2audiobot.utils import get_hash

# todo add check pkl with hash of bot name


class AutodownloadChatManager:
    def __init__(self, data_dir: Union[str, Path]):
        self.hashed_chat_ids = set()
        self.data_dir = Path(data_dir)  # Accept data_dir as either str or Path
        self.storage_file = self.data_dir / 'autodownload-hashed_chat_ids.pkl'  # Use pathlib to create the file path

        # Ensure the data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Read HASH_SALT from environment variable or generate a random one
        self.salt = os.environ.get('HASH_SALT')
        if not self.salt:
            self.salt = self._generate_random_salt()
            os.environ['HASH_SALT'] = self.salt  # Set the generated salt in the environment

        # Restore hashed_chat_ids from file if it exists
        self.restore_hashed_chat_ids()

    def _generate_random_salt(self, length: int = 32) -> str:
        """Generate a random salt of a given length."""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def _get_hash_salted(self, chat_id: str) -> str:
        """Generate a salted hash for the given chat_id."""
        return get_hash(chat_id) + self.salt

    def is_chat_id_inside(self, chat_id: Union[str, int]) -> bool:
        """Check if the salted hash of the chat_id exists in the storage."""
        chat_id = str(chat_id)
        return self._get_hash_salted(chat_id) in self.hashed_chat_ids

    def add_chat_id(self, chat_id: str) -> None:
        """Add the salted hash of the chat_id to the storage."""
        salted_hash = self._get_hash_salted(chat_id)
        self.hashed_chat_ids.add(salted_hash)
        self.save_hashed_chat_ids()  # Save changes after adding

    def remove_chat_id(self, chat_id: str) -> None:
        """Remove the salted hash of the chat_id from the storage if it exists."""
        salted_hash = self._get_hash_salted(chat_id)
        self.hashed_chat_ids.discard(salted_hash)
        self.save_hashed_chat_ids()  # Save changes after removing

    def toggle_chat_state(self, chat_id: Union[str, int]) -> bool:
        """Toggle the presence of the chat_id in the storage."""
        chat_id = str(chat_id)
        if self.is_chat_id_inside(chat_id):
            self.remove_chat_id(chat_id)
            return False
        else:
            self.add_chat_id(chat_id)
            return True

    def restore_hashed_chat_ids(self) -> None:
        """Restore hashed_chat_ids from a file if it exists."""
        if self.storage_file.exists():
            with open(self.storage_file, 'rb') as f:
                self.hashed_chat_ids = pickle.load(f)

    async def save_hashed_chat_ids(self, params=None) -> None:
        """Save hashed_chat_ids to a file."""
        with open(self.storage_file, 'wb') as f:
            pickle.dump(self.hashed_chat_ids, f)