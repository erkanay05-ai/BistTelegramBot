import time

class SimpleCache:
    def __init__(self):
        self._cache = {}

    def get(self, key):
        if key in self._cache:
            val, expiry = self._cache[key]
            if time.time() < expiry:
                return val
            else:
                del self._cache[key]
        return None

    def set(self, key, value, ttl=300):
        self._cache[key] = (value, time.time() + ttl)

    def clear(self):
        self._cache.clear()

cache_store = SimpleCache()
