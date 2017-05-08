import redis


class RedisPersist:
    _redis_connection = None

    def __init__(self, host="localhost", port=6379, db=0):
        self._redis_connection = redis.StrictRedis(
            host=host,
            port=port,
            db=db
        )
        self._redis_connection.set('tmp_validate', 'tmp_validate')

    def save(self, key=None, jsonstr=None):
        if key is None:
            raise ValueError("Key must be present to persist game.")
        if jsonstr is None:
            raise ValueError("JSON is badly formed or not present")
        self._redis_connection.set(key, str(jsonstr))

    def load(self, key=None):
        if key is None:
            raise ValueError("Key must be present to load game")
        return_result = self._redis_connection.get(key)
        if return_result is not None:
            return_result = str(return_result)
        return return_result
