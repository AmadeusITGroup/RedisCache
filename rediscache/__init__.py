#!/usr/bin/env python
"""
 .+"+.+"+.+"+.+"+.
(                 )
 ) rediscache.py (
(                 )
 "+.+"+.+"+.+"+.+"

rediscache is a function decorator that will cache its result in a Redis database.

Parameters:
- refresh: the number of seconds after which the cached data will be refreshed using the decorated function.
- expire: the number of seconds after which the cached data will altogether disapear from the Redis database.
- default: the value that will be returned if the data is not found in the cache. It cannot be None.
It can be bytes, string, int or float.
- enabled: This is True by default but enables to programmatically disable the cach if required.

It also reads from the environment:
- REDIS_SERVICE_HOST: the redis server host name or IP. Default is 'localhost'.
- REDIS_SERVICE_PORT: the port that the redis server listen to. Default is 6379.
- REDIS_SERVICE_DATABASE: the database number to use. Default is 0.
- REDIS_SERVICE_PASSWORD: the password to use to connect to the redis server. Default is None.

Note:
A key associated to the decorated function is created using the function name and its parameters. This is based
on the value returned by the repr() function (ie: the __repr__() member) of each paramter. user defined objects
will have this function return by default a string like this:
"<amadeusbook.services.EmployeesService object at 0x7f41dedd7128>"
This will not do as each instance of the object will have a different representation no matter what. The direct
consequence will be that each key in the cache will be different, so values in cache will never be reused.
So you need to make sure that your parameters return a meaningful representation value.

TODO:
- Check what happens if redis database is getting full
"""

from functools import wraps
from json import dumps, loads
import logging
import os
import threading
from time import sleep
from typing import Any, Callable, Dict, List, Optional, ParamSpec, TypeVar

import redis
from executiontime import printexecutiontime, YELLOW, RED

PREFIX = "."
REFRESH = "Refresh"  # Number of times the cached function was actually called.
WAIT = "Wait"  # Number of times that we executed the function in the current thread.
SLEEP = "Sleep"  # Number of time that we had to wait 1s for the data to be found in the cache.
FAILED = "Failed"  # Number of times the cached function raised an exception when called.
MISSED = "Missed"  # Number of times the functions result was not found in the cache.
SUCCESS = "Success"  # Number of times the function's result was found in the cache.
DEFAULT = "Default"  # Number of times the default value was used because nothing is in the cache or the function failed.
STATS = [REFRESH, WAIT, SLEEP, FAILED, MISSED, SUCCESS, DEFAULT]

P = ParamSpec("P")
T = TypeVar("T")


class RedisCache:
    """
    Having the decorator provided by a class allows to have some context to improve performances.
    """

    # pylint: disable=too-many-arguments

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        decode: bool = True,
        enabled: bool = True,
    ):
        self.enabled = enabled
        if self.enabled:
            # If environment variables are set for redis server, they superseed the default values.
            # But if provided at the construction, it has priority.
            if not host:
                host = os.environ.get("REDIS_SERVICE_HOST", "localhost")
            if not port:
                port = int(os.environ.get("REDIS_SERVICE_PORT", 6379))
            if not db:
                db = int(os.environ.get("REDIS_SERVICE_DATABASE", 0))
            if not password:
                # If password is None, it is ignored.
                password = os.environ.get("REDIS_SERVICE_PASSWORD")
            self.server = redis.StrictRedis(host=host, port=port, db=db, password=password, decode_responses=decode)

    def _create_key(
        self,
        name: str,
        args: Optional[tuple[Any, ...]] = None,
        use_args: Optional[List[int]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        use_kwargs: Optional[List[str]] = None,
    ) -> str:
        """
        Create a key from the function's name and its parameters values
        """
        values = []
        if args:
            if use_args:
                for position, value in enumerate(args):
                    if position in use_args:
                        values.append(f"'{value}'")
            else:
                values.extend(f"'{value}'" for value in args)

        if kwargs:
            if use_kwargs:
                for key, value in kwargs.items():
                    if key in use_kwargs:
                        values.append(f"'{value}'")
            else:
                values.extend(f"'{value}'" for value in kwargs.values())

        return f"{name}({','.join(values)})"

    # pylint: disable=line-too-long
    def cache(
        self,
        refresh: int,
        expire: int,
        retry: Optional[int] = None,
        default: Any = "",
        wait: bool = False,
        serializer: Optional[Callable[..., Any]] = None,
        deserializer: Optional[Callable[..., Any]] = None,
        use_args: Optional[List[int]] = None,
        use_kwargs: Optional[List[str]] = None,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Full decorator will all possible parameters. Most of the time, you should use a specialzed decorator below.

        Specific examples when to use this decorator:
        - Raw storage of byte string that you do not want to be decoded: use the decode=False.
        - JSON dumps data that doesn't need to be loaded before it is sent by a REST API: use serializer=dumps but no deserializer.
        """

        logger = logging.getLogger(__name__)

        def decorator(function: Callable[P, T]) -> Callable[P, T]:
            """
            The decorator itself returns a wrapper function that will replace the original one.
            """

            @printexecutiontime(
                "[" + function.__name__ + "] Total execution time of Redis decorator: {0}",
                color=YELLOW,
                output=logger.info,
            )
            @wraps(function)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                """
                This wrapper calculates and displays the execution time of the function.
                """

                @printexecutiontime(
                    "[" + function.__name__ + "] Execution time of call to function and storage in Redis: {0}",
                    color=RED,
                    output=logger.info,
                )
                def refreshvalue(key: str) -> T:
                    """
                    This gets the value provided by the function and stores it in local Redis database
                    """
                    try:
                        # Get some stats
                        self.server.incr(REFRESH)
                        # Execute function to fetch value to cache
                        new_value = function(*args, **kwargs)
                    # pylint: disable=broad-except
                    # It is normal to catch all exception because we do not know what function is decorated.
                    except Exception as exception_in_thread:
                        # Get some stats
                        self.server.incr(FAILED)
                        # Log the error. It's not critical because maybe next time it will work.
                        logger.error(
                            "Error in Thread execution to update the Redis cache on key %s\n%s",
                            key,
                            exception_in_thread,
                        )
                        # Since we have no value, let's use the default
                        self.server.incr(DEFAULT)
                        new_value = default

                    # Serialize the value if requested
                    if serializer:
                        new_value = serializer(new_value)
                    # Store value in cache with expiration time
                    self.server.set(key, new_value, ex=expire)  # type: ignore
                    # Set refresh key with refresh time
                    self.server.set(PREFIX + key, 1, ex=refresh)
                    return new_value

                def refreshvalueinthread(key: str) -> None:
                    """
                    Run the refresh value in a separate thread
                    """
                    thread = threading.Thread(target=refreshvalue, args=(key,))
                    thread.start()

                # If the cache is disabled, directly call the function
                if not self.enabled:
                    direct_value = function(*args, **kwargs)
                    # If we have decided to serialize, we always do it to be consistent
                    if serializer:
                        direct_value = serializer(direct_value)
                    if deserializer:
                        direct_value = deserializer(direct_value)
                    return direct_value

                # Lets create a key from the function's name and its parameters values
                key = self._create_key(name=function.__name__, args=args, use_args=use_args, kwargs=kwargs, use_kwargs=use_kwargs)
                values = ",".join([str(value) for value in args])
                dict_values = ",".join([str(key) + "='" + str(value) + "'" for key, value in kwargs.items()])
                all_args = values
                if values and dict_values:
                    all_args += ","
                all_args += dict_values

                # Get the value from the cache.
                # If it is not there we will get None.
                cached_value = self.server.get(key)

                # Time to update stats counters
                if cached_value is None:
                    self.server.incr(MISSED)
                else:
                    self.server.incr(SUCCESS)

                # If the refresh key is gone, it is time to refresh the value.
                if self.server.set(PREFIX + key, 1, ex=retry if retry else refresh, nx=True):

                    # If we found a value in the cash, we will not wait for the refresh
                    if cached_value or not wait:
                        # We just update the cache in another thread.
                        refreshvalueinthread(key)
                    else:
                        # Here we will wait, let's count it
                        self.server.incr(WAIT)
                        # We update the cash and return the value.
                        cached_value = refreshvalue(key)

                # We may still have decided to wait but another process is already getting the cache updated.
                if cached_value is None and wait:
                    # Let's wait, but this is dangerous if we never get the value in the cache.
                    # We will stop if we lose the refresh key indicating that the refreshing timed out.
                    while cached_value is None and self.server.get(PREFIX + key):
                        # Let's count how many times we wait 1s
                        self.server.incr(SLEEP)
                        sleep(1)
                        cached_value = self.server.get(key)

                # If the cache was empty, we have None in the cached_value.
                if cached_value is None:
                    # We are going to return the default value
                    self.server.incr(DEFAULT)
                    cached_value = serializer(default) if serializer else default

                # Return whatever value we have at this point.
                return deserializer(cached_value) if deserializer else cached_value  # type: ignore

            return wrapper

        return decorator

    def cache_raw(self, refresh: int, expire: int, retry: Optional[int] = None, default: Any = "") -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Normal caching of values directly storable in redis: byte string, string, int, float.
        """
        return self.cache(refresh=refresh, expire=expire, retry=retry, default=default)

    def cache_raw_wait(self, refresh: int, expire: int, retry: Optional[int] = None, default: Any = "") -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Same as cache_raw() but will wait for the completion of the cached function if no value is found in redis.
        """
        return self.cache(refresh=refresh, expire=expire, retry=retry, default=default, wait=True)

    def cache_json(self, refresh: int, expire: int, retry: Optional[int] = None, default: Any = "") -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        JSON dumps the values to be stored in redis and loads them again when returning them to the caller.
        """
        return self.cache(
            refresh=refresh,
            expire=expire,
            retry=retry,
            default=default,
            serializer=dumps,
            deserializer=loads,
        )

    def cache_json_wait(self, refresh: int, expire: int, retry: Optional[int] = None, default: Any = "") -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Same as cache_json() but will wait for the completion of the cached function if no value is found in redis.
        """
        return self.cache(
            refresh=refresh,
            expire=expire,
            retry=retry,
            default=default,
            wait=True,
            serializer=dumps,
            deserializer=loads,
        )

    def get_stats(self, delete: bool = False) -> Dict[str, Any]:
        """
        Get the stats stored by RedisCache. See the list and definition at the top of this file.
        If delete is set to True we delete the stats from Redis after read.
        From Redis 6.2, it is possible to GETDEL, making sure that we do not lose some data between
        the 'get' and the 'delete'. But it is not available in the Redis (v3.5.3) python interface yet.
        """
        stats = {stat: self.server.get(stat) for stat in STATS}
        if delete:
            for stat in STATS:
                self.server.delete(stat)
        return stats
