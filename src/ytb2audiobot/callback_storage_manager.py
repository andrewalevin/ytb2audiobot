
class StorageCallbackManager:
    def __init__(self):
        self.storage_callback_waiting_keys = dict()

    def check_key_inside(self, key: str) -> bool:
        """Check if the key exists in the storage."""
        return key in self.storage_callback_waiting_keys

    def add_key(self, key: str):
        """Add a key to the storage."""
        self.storage_callback_waiting_keys[key] = ''

    def remove_key(self, key: str):
        """Remove a key from the storage if it exists."""
        if key in self.storage_callback_waiting_keys:
            del self.storage_callback_waiting_keys[key]
