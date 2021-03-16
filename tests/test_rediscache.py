#!/usr/bin/env python3
"""
This will test various scenario with the redis cache.

It requires the local redis server to be started:
sudo service redis.server start

Start with unittest
python -m unittest test_rediscache.py

Start with pytest
pytest -s

Start with coverage
coverage run --source=rediscache --module pytest
coverage report --show-missing
"""
from datetime import datetime
from logging import info, INFO, basicConfig
from threading import Thread
from time import sleep
from unittest import TestCase, main

from redis import StrictRedis

from rediscache import RedisCache

# pylint: disable=missing-class-docstring, missing-function-docstring
class TestRedisCache(TestCase):

    def __init__(self, method_name: str):
        self.server = StrictRedis(decode_responses=True)
        super().__init__(method_name)

    def setUp(self):
        retour = self.server.flushdb()
        info("Redis database flushed: %s", retour)

    def test_normal_cache(self):
        rediscache = RedisCache()
        @rediscache.cache_raw(1, 2)
        def my_slow_hello(name: str) -> str:
            self.server.incr('my_slow_hello')
            sleep(0.3)
            return f"Hello {name}!"

        # Ask value to go in cache
        name = 'toto'
        hello = my_slow_hello(name)
        # Make sure the Thread was started
        sleep(0.1)
        # The function was called
        self.assertEqual(self.server.get('my_slow_hello'), '1')
        # But we do not have the result yet?
        self.assertEqual(hello, '')
        # Make sure the value is in the cache
        sleep(0.5)
        # Get value from cache
        hello = my_slow_hello(name)
        self.assertEqual(hello, f"Hello {name}!")
        # Still the function has only been called once
        self.assertEqual(self.server.get('my_slow_hello'), '1')

    def test_refresh(self):
        rediscache = RedisCache()
        @rediscache.cache_raw(1, 2)
        def my_slow_hello(name: str) -> str:
            """
            A slow function to test the Redis cache.
            Each call will get a different result.
            """
            sleep(0.2)
            return f"Hello {name}! {datetime.utcnow()}"

        # Ask value to go in cache
        hello = my_slow_hello('tata')
        # Make sure we have not got it yet
        self.assertEqual(hello, '')
        # Wait for it to arrive in cache
        sleep(0.5)
        # Retrieve value from cache
        hello1 = my_slow_hello('tata')
        # Wait for expiration of value
        sleep(1)
        # Retrieve value from cache again. Should be the same. But an update is on-going.
        hello2 = my_slow_hello('tata')
        self.assertEqual(hello1, hello2)
        # Wait for cache to be updated
        sleep(0.5)
        # Retrieve value from cache again. This time it was updated.
        hello3 = my_slow_hello('tata')
        self.assertNotEqual(hello2, hello3)

    def test_default(self):
        default = 'Default'
        rediscache = RedisCache()
        @rediscache.cache_raw(1, 2, default=default)
        def my_fast_hello(name: str) -> str:
            return f"Hello {name}!"

        # First time storing value in cache
        hello = my_fast_hello('fifi')
        # Value is default the first time
        self.assertEqual(hello, default)

    def test_fail(self):
        default = 'Default'
        rediscache = RedisCache()
        @rediscache.cache_raw(1, 2, default=default)
        def my_failling_hello(name: str) -> str:
            if not name:
                raise ValueError('Invalid name')
            return f"Hello {name}!"

        # Store value in the cache
        hello = my_failling_hello('')
        # Make sure we have not got it yet
        self.assertEqual(hello, default)
        # Wait for value to be in the cache
        sleep(1.1)
        # Do we get a value from the cache?
        hello = my_failling_hello('')
        # Only the default value is in the cache because the function failed
        self.assertEqual(hello, default)

    def test_expire(self):
        default = 'Default'
        rediscache = RedisCache()
        @rediscache.cache_raw(1, 2, default=default)
        def my_fast_hello(name: str) -> str:
            return f"Hello {name}!"

        # Store value in the cache
        hello = my_fast_hello('loulou')
        # Make sure we have not got it yet
        self.assertEqual(hello, default)
        # Wait for the value to be totally expired in the cache
        sleep(3)
        # Let's try and get the value from the cache
        hello = my_fast_hello('loulou')
        # The value is not in the cache anymore
        self.assertEqual(hello, default)

    def test_empty(self):
        default = 'Default'
        rediscache = RedisCache()
        @rediscache.cache_raw(1, 2, default=default)
        def my_empty_hello(name: str) -> str:
            if name:
                return f"Hello {name}!"
            return ""

        # Store value in the cache
        hello = my_empty_hello('')
        # Make sure we have not got it yet
        self.assertEqual(hello, default)
        # Wait for the value to be stored in the cache
        sleep(0.5)
        # Let's try and get the value from the cache
        hello = my_empty_hello('')
        # We also store empty strings in the cache
        self.assertEqual(hello, '')

    def test_no_cache(self):
        rediscache = RedisCache(enabled=False)
        @rediscache.cache_raw(1, 2)
        def my_slow_hello(name: str) -> str:
            sleep(0.5)
            return f"Hello {name}!"

        # Get the value directly, no cache
        name = 'choux'
        hello = my_slow_hello(name)
        # We have the value after the first call
        self.assertEqual(hello, f"Hello {name}!")

    def test_no_cache_dumps(self):
        rediscache = RedisCache(enabled=False)
        @rediscache.cache_json(1, 2)
        def my_slow_hello(name: str) -> str:
            sleep(0.5)
            return f"Hello {name}!"

        # Get the value directly, no cache
        name = 'choux'
        hello = my_slow_hello(name)
        # We have the value after the first call
        self.assertEqual(hello, f'Hello {name}!')

    def test_very_long(self):
        rediscache = RedisCache()
        @rediscache.cache_raw(1, 10, retry=1)
        def my_very_slow_hello(name: str) -> str:
            # Count how many times the function was called
            self.server.incr('my_very_slow_hello')
            sleep(2)
            return f"Hello {name}!"

        # Stores the value in the cache
        my_very_slow_hello('hiboux')
        # Wait after the retry
        sleep(1.5)
        # Do we have it now?
        hello = my_very_slow_hello('hiboux')
        # No, we should not
        self.assertEqual(hello, '')
        # Let's see how many times the function was actually called
        sleep(0.1)
        self.assertEqual(self.server.get('my_very_slow_hello'), '2')

    def test_dict(self):
        rediscache = RedisCache()
        @rediscache.cache_json(1, 2)
        def return_dict(name: str):
            return {"hello": name}
        # Stores the value in the cache
        return_dict('you')
        # Make sure it is in the cache
        sleep(0.1)
        # Get the value from the cache
        hello = return_dict('you')
        self.assertEqual(hello, {'hello': 'you'})

    def test_dict_wait(self):
        rediscache = RedisCache()
        @rediscache.cache_json_wait(1, 2)
        def return_dict(name: str):
            sleep(0.1)
            return {"hello": name}
        # Stores the value in the cache and wait for the output
        hello = return_dict('me')
        self.assertEqual(hello, {'hello': 'me'})

    def test_wait(self):
        rediscache = RedisCache()
        @rediscache.cache_raw_wait(1, 2)
        def my_hello_wait(name: str) -> str:
            sleep(0.5)
            return f"hello {name}!"
        # Stores the value in the cache but wait for it as well
        name = 'chouchou'
        hello = my_hello_wait(name)
        self.assertEqual(hello, f"hello {name}!")

    def test_wait_thread(self):
        rediscache = RedisCache()
        @rediscache.cache_raw_wait(1, 2)
        def my_hello_wait(name: str) -> str:
            sleep(0.5)
            return f"hello {name}!"
        name = 'bob'
        # Store the value in the cache and wait in another thread
        thread = Thread(target=my_hello_wait, args=(name,))
        thread.start()
        # Make sure the thread is started but not enough that it would be completed
        sleep(0.2)
        # Now we still wait for the value
        hello = my_hello_wait(name)
        self.assertEqual(hello, f"hello {name}!")

    def test_no_decode(self):
        my_byte_string = b'This is a byte string'
        rediscache = RedisCache(decode=False)
        @rediscache.cache_raw_wait(1, 2)
        def my_bytes() -> bytes:
            sleep(0.1)
            return my_byte_string

        # Store the value in the cache and wait
        value = my_bytes()
        self.assertEqual(value, my_byte_string)
        # Wait for the value to reach the cache
        sleep(0.2)
        # Get the same value from the cache
        value = my_bytes()
        self.assertEqual(value, my_byte_string)

    def test_decorator(self):
        rediscache = RedisCache()
        @rediscache.cache(1, 2)
        def my_cached_hello(name: str) -> str:
            """This is my documentation"""
            sleep(0.1)
            return f"Hello {name}!"
        self.assertEqual(my_cached_hello.__name__, "my_cached_hello")
        self.assertEqual(my_cached_hello.__doc__, "This is my documentation")

    # This test should run first, so it needs the be the first alphabatically.
    def test_1_get_stats(self):
        rediscache = RedisCache()
        @rediscache.cache_raw_wait(1, 2)
        def function1() -> str:
            sleep(0.1)
            return "Hello function 1"
        @rediscache.cache(1, 2)
        def function2() -> str:
            sleep(0.1)
            return "Hello function 2"
        function1()
        function2()
        stats = rediscache.get_stats()
        self.assertEqual(stats["Refresh"], 2)
        self.assertEqual(stats["Wait"], 1)
        self.assertEqual(stats["Failed"], 0)
        self.assertEqual(stats["Missed"], 2)
        self.assertEqual(stats["Success"], 0)
        self.assertEqual(stats["Default"], 1)
        function1()
        function2()
        stats = rediscache.get_stats()
        self.assertEqual(stats["Refresh"], 2)
        self.assertEqual(stats["Wait"], 1)
        self.assertEqual(stats["Failed"], 0)
        self.assertEqual(stats["Missed"], 3)
        self.assertEqual(stats["Success"], 1)
        self.assertEqual(stats["Default"], 2)
        sleep(0.2)
        function1()
        function2()
        stats = rediscache.get_stats(delete=True)
        self.assertEqual(stats["Refresh"], 2)
        self.assertEqual(stats["Wait"], 1)
        self.assertEqual(stats["Failed"], 0)
        self.assertEqual(stats["Missed"], 3)
        self.assertEqual(stats["Success"], 3)
        self.assertEqual(stats["Default"], 2)
        stats = rediscache.get_stats()
        self.assertEqual(stats["Refresh"], 0)
        self.assertEqual(stats["Wait"], 0)
        self.assertEqual(stats["Failed"], 0)
        self.assertEqual(stats["Missed"], 0)
        self.assertEqual(stats["Success"], 0)
        self.assertEqual(stats["Default"], 0)

if __name__ == "__main__":
    basicConfig(level=INFO)
    main()
