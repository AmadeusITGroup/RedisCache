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
from threading import Thread
from time import sleep
from typing import Callable, Dict, Generator, TypeVar

import pytest
from redis import Redis, StrictRedis

from rediscache import RedisCache

T = TypeVar("T")


@pytest.fixture(name="flushdb", autouse=True)
def fixture_flushdb() -> Generator[Redis, None, None]:
    """
    Create an instance of RedisCache for each test.
    Make sue the Redis database is flushed before each test.
    """
    server = StrictRedis(decode_responses=True)
    server.flushdb()
    yield server


def test_create_key() -> None:
    """
    Test the internal function to create the key.
    """
    rediscache = RedisCache()

    # pylint: disable=protected-access

    key = rediscache._create_key(name="my_function", args=("toto",))
    assert key == "my_function('toto')"

    key = rediscache._create_key(name="my_function", args=("toto", "titi"), use_args=[1])
    assert key == "my_function('titi')"

    key = rediscache._create_key(name="my_function", args=("toto", "titi"), use_args=[1], kwargs={"riri": 1, "fifi": 2})
    assert key == "my_function('titi','1','2')"

    key = rediscache._create_key(name="my_function", args=("toto", "titi"), use_args=[1], use_kwargs=["riri"], kwargs={"riri": 1, "fifi": 2})
    assert key == "my_function('titi','1')"


def test_key_in_redis(flushdb: Callable[[], Generator[StrictRedis, None, None]]) -> None:
    """
    This can be tested alone with:
    pytest -k test_key_in_redis
    """
    server = flushdb
    rediscache = RedisCache()

    @rediscache.cache(10, 20, wait=True)
    def func_with_args(arg: str) -> str:
        return arg

    @rediscache.cache(10, 20, wait=True)
    def func_with_args_kwargs(arg: str, kwarg: str = "") -> str:
        return str(arg) + str(kwarg)

    func_with_args("tata")
    func_with_args_kwargs("toto", kwarg="titi")
    keys = server.keys("*")  # type: ignore
    assert "func_with_args('tata')" in keys
    assert "func_with_args_kwargs('toto','titi')" in keys


def test_normal_cache(flushdb: Callable[[], Generator[StrictRedis, None, None]]) -> None:
    """
    This can be tested alone with:
    pytest -k test_normal_cache
    """
    server = flushdb
    rediscache = RedisCache()

    @rediscache.cache_raw(1, 2)
    def my_slow_hello(name: str) -> str:
        server.incr("my_slow_hello")  # type: ignore
        sleep(0.3)
        return f"Hello {name}!"

    # Ask value to go in cache
    name = "toto"
    hello = my_slow_hello(name)
    # Make sure the Thread was started
    sleep(0.1)
    # The function was called
    assert server.get("my_slow_hello") == "1"  # type: ignore
    # But we do not have the result yet?
    assert hello == ""
    # Make sure the value is in the cache
    sleep(0.5)
    # Get value from cache
    hello = my_slow_hello(name)
    assert hello == f"Hello {name}!"
    # Still the function has only been called once
    assert server.get("my_slow_hello") == "1"  # type: ignore


def test_refresh() -> None:
    """
    This can be tested alone with:
    pytest -k test_refresh
    """
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
    hello = my_slow_hello("tata")
    # Make sure we have not got it yet
    assert hello == ""
    # Wait for it to arrive in cache
    sleep(0.5)
    # Retrieve value from cache
    hello1 = my_slow_hello("tata")
    # Wait for expiration of value
    sleep(1)
    # Retrieve value from cache again. Should be the same. But an update is on-going.
    hello2 = my_slow_hello("tata")
    assert hello1 == hello2
    # Wait for cache to be updated
    sleep(0.5)
    # Retrieve value from cache again. This time it was updated.
    hello3 = my_slow_hello("tata")
    assert hello2 != hello3


def test_default() -> None:
    """
    This can be tested alone with:
    pytest -k test_default
    """
    rediscache = RedisCache()
    default = "Default"

    @rediscache.cache_raw(1, 2, default=default)
    def my_fast_hello(name: str) -> str:
        return f"Hello {name}!"

    # First time storing value in cache
    hello = my_fast_hello("fifi")
    # Value is default the first time
    assert hello == default


def test_fail() -> None:
    """
    This can be tested alone with:
    pytest -k test_fail
    """
    rediscache = RedisCache()
    default = "Default"

    @rediscache.cache_raw(1, 2, default=default)
    def my_failling_hello(name: str) -> str:
        if not name:
            raise ValueError("Invalid name")
        return f"Hello {name}!"

    # Store value in the cache
    hello = my_failling_hello("")
    # Make sure we have not got it yet
    assert hello == default
    # Wait for value to be in the cache
    sleep(1.1)
    # Do we get a value from the cache?
    hello = my_failling_hello("")
    # Only the default value is in the cache because the function failed
    assert hello == default


def test_expire() -> None:
    """
    This can be tested alone with:
    pytest -k test_expire
    """
    rediscache = RedisCache()
    default = "Default"

    @rediscache.cache_raw(1, 2, default=default)
    def my_fast_hello(name: str) -> str:
        return f"Hello {name}!"

    # Store value in the cache
    hello = my_fast_hello("loulou")
    # Make sure we have not got it yet
    assert hello == default
    # Wait for the value to be totally expired in the cache
    sleep(3)
    # Let's try and get the value from the cache
    hello = my_fast_hello("loulou")
    # The value is not in the cache anymore
    assert hello == default


def test_empty() -> None:
    """
    This can be tested alone with:
    pytest -k test_empty
    """
    rediscache = RedisCache()
    default = "Default"

    @rediscache.cache_raw(1, 2, default=default)
    def my_empty_hello(name: str) -> str:
        if name:
            return f"Hello {name}!"
        return ""

    # Store value in the cache
    hello = my_empty_hello("")
    # Make sure we have not got it yet
    assert hello == default
    # Wait for the value to be stored in the cache
    sleep(0.5)
    # Let's try and get the value from the cache
    hello = my_empty_hello("")
    # We also store empty strings in the cache
    assert hello == ""


def test_no_cache() -> None:
    """
    This can be tested alone with:
    pytest -k test_no_cache
    """
    rediscache = RedisCache(enabled=False)

    @rediscache.cache_raw(1, 2)
    def my_slow_hello(name: str) -> str:
        sleep(0.5)
        return f"Hello {name}!"

    # Get the value directly, no cache
    name = "choux"
    hello = my_slow_hello(name)
    # We have the value after the first call
    assert hello == f"Hello {name}!"


def test_no_cache_dumps() -> None:
    """
    This can be tested alone with:
    pytest -k test_no_cache_dumps
    """
    rediscache = RedisCache(enabled=False)

    @rediscache.cache_json(1, 2)
    def my_slow_hello(name: str) -> str:
        sleep(0.5)
        return f"Hello {name}!"

    # Get the value directly, no cache
    name = "choux"
    hello = my_slow_hello(name)
    # We have the value after the first call
    assert hello == f"Hello {name}!"


def test_very_long(flushdb: Callable[[], Generator[StrictRedis, None, None]]) -> None:
    """
    This can be tested alone with:
    pytest -k test_very_long
    """
    server = flushdb
    rediscache = RedisCache()

    @rediscache.cache_raw(1, 10, retry=1)
    def my_very_slow_hello(name: str) -> str:
        # Count how many times the function was called
        server.incr("my_very_slow_hello")  # type: ignore
        sleep(2)
        return f"Hello {name}!"

    # Stores the value in the cache
    my_very_slow_hello("hiboux")
    # Wait after the retry
    sleep(1.5)
    # Do we have it now?
    hello = my_very_slow_hello("hiboux")
    # No, we should not
    assert hello == ""
    # Let's see how many times the function was actually called
    sleep(0.1)
    assert server.get("my_very_slow_hello") == "2"  # type: ignore


def test_dict() -> None:
    """
    This can be tested alone with:
    pytest -k test_dict
    """
    rediscache = RedisCache()

    @rediscache.cache_json(1, 2)
    def return_dict(name: str) -> Dict[str, str]:
        return {"hello": name}

    # Stores the value in the cache
    return_dict("you")
    # Make sure it is in the cache
    sleep(0.1)
    # Get the value from the cache
    hello = return_dict("you")
    assert hello == {"hello": "you"}


def test_dict_wait() -> None:
    """
    This can be tested alone with:
    pytest -k test_dict_wait
    """
    rediscache = RedisCache()

    @rediscache.cache_json_wait(1, 2)
    def return_dict(name: str) -> Dict[str, str]:
        sleep(0.1)
        return {"hello": name}

    # Stores the value in the cache and wait for the output
    hello = return_dict("me")
    assert hello == {"hello": "me"}


def test_wait() -> None:
    """
    This can be tested alone with:
    pytest -k test_wait
    """
    rediscache = RedisCache()

    @rediscache.cache_raw_wait(1, 2)
    def my_hello_wait(name: str) -> str:
        sleep(0.5)
        return f"hello {name}!"

    # Stores the value in the cache but wait for it as well
    name = "chouchou"
    hello = my_hello_wait(name)
    assert hello == f"hello {name}!"


def test_wait_thread() -> None:
    """
    This can be tested alone with:
    pytest -k test_wait_thread
    """
    rediscache = RedisCache()

    @rediscache.cache_raw_wait(1, 2)
    def my_hello_wait(name: str) -> str:
        sleep(0.5)
        return f"hello {name}!"

    name = "bob"
    # Store the value in the cache and wait in another thread
    thread = Thread(target=my_hello_wait, args=(name,))
    thread.start()
    # Make sure the thread is started but not enough that it would be completed
    sleep(0.2)
    # Now we still wait for the value
    hello = my_hello_wait(name)
    assert hello == f"hello {name}!"


def test_no_decode() -> None:
    """
    This can be tested alone with:
    pytest -k test_no_decode
    """
    my_byte_string = b"This is a byte string"
    rediscache = RedisCache(decode=False)

    @rediscache.cache_raw_wait(1, 2)
    def my_bytes() -> bytes:
        sleep(0.1)
        return my_byte_string

    # Store the value in the cache and wait
    value = my_bytes()
    assert value == my_byte_string
    # Wait for the value to reach the cache
    sleep(0.2)
    # Get the same value from the cache
    value = my_bytes()
    assert value == my_byte_string


def test_decorator() -> None:
    """
    This can be tested alone with:
    pytest -k test_decorator
    """
    rediscache = RedisCache()

    @rediscache.cache(1, 2)
    def my_cached_hello(name: str) -> str:
        """This is my documentation"""
        sleep(0.1)
        return f"Hello {name}!"

    assert my_cached_hello.__name__ == "my_cached_hello"
    assert my_cached_hello.__doc__ == "This is my documentation"


# This test should run first, so it needs the be the first alphabatically.
def test_get_stats() -> None:
    """
    This can be tested alone with:
    pytest -k test_get_stats
    """
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
    assert stats["Refresh"] == "2"
    assert stats["Wait"] == "1"
    assert stats["Failed"] is None
    assert stats["Missed"] == "2"
    assert stats["Success"] is None
    assert stats["Default"] == "1"
    function1()
    function2()
    stats = rediscache.get_stats()
    assert stats["Refresh"] == "2"
    assert stats["Wait"] == "1"
    assert stats["Failed"] is None
    assert stats["Missed"] == "3"
    assert stats["Success"] == "1"
    assert stats["Default"] == "2"
    sleep(0.2)
    function1()
    function2()
    stats = rediscache.get_stats(delete=True)
    assert stats["Refresh"] == "2"
    assert stats["Wait"] == "1"
    assert stats["Failed"] is None
    assert stats["Missed"] == "3"
    assert stats["Success"] == "3"
    assert stats["Default"] == "2"
    stats = rediscache.get_stats()
    assert stats["Refresh"] is None
    assert stats["Wait"] is None
    assert stats["Failed"] is None
    assert stats["Missed"] is None
    assert stats["Success"] is None
    assert stats["Default"] is None
