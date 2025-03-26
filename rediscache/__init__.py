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
- expire: the number of seconds after which the cached data will altogether disappear from the Redis database.
- default: the value that will be returned if the data is not found in the cache. It cannot be None.
It can be bytes, string, int or float.
- enabled: This is True by default but enables to programmatically disable the cache if required.

It also reads from the environment:
- REDIS_SERVICE_HOST: the redis server host name or IP. Default is 'localhost'.
- REDIS_SERVICE_PORT: the port that the redis server listen to. Default is 6379.
- REDIS_SERVICE_DATABASE: the database number to use. Default is 0.
- REDIS_SERVICE_PASSWORD: the password to use to connect to the redis server. Default is None.

Note:
A key associated to the decorated function is created using the function name and its parameters. This is based
on the value returned by the repr() function (ie: the __repr__() member) of each parameter. User defined objects
will have this function return by default a string like this:
"<amadeusbook.services.EmployeesService object at 0x7f41dedd7128>"
This will not do as each instance of the object will have a different representation no matter what. The direct
consequence will be that each key in the cache will be different, so values in cache will never be reused.
So you need to make sure that your parameters return a meaningful representation value.

TODO:
- Check what happens if redis database is getting full
"""

from functools import wraps
import logging
import os
import threading
from time import sleep
from typing import Any, Callable, cast, Dict, List, Optional, ParamSpec, TypeVar

from executiontime import printexecutiontime, YELLOW, RED
import redis

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
T = TypeVar("T", str, bytes)


class RedisCache:
    """
    Having the decorator provided by a class allows to have some context to improve performances.
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        decode: bool = True,
        enabled: bool = True,
    ):
        """
        Provide configuration parameter to a RedisCache instance.

        Args:
            host: The host of the Redis server instance to be used.
            port: The port the Redis server listens to.
            db: The name of the database to be used if not default.
            decode: If true, decode the data stored in the cache as byte string.
            enabled: When False it allows to programmatically disable the cache.
        """
        self.enabled = enabled
        if self.enabled:
            # If environment variables are set for redis server, they supersede the default values.
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

    def _create_key(  # pylint: disable=too-many-positional-arguments
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

    def cache(  # pylint: disable=too-many-positional-arguments
        self,
        refresh: int,
        expire: int,
        default: T,
        retry: Optional[int] = None,
        wait: bool = False,
        use_args: Optional[List[int]] = None,
        use_kwargs: Optional[List[str]] = None,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Full decorator with all possible parameters.

        Args:
            refresh: The amount of seconds before it would be a good idea to refresh the cached value.
            expire: How many seconds that the value in the cache is still considered good enough to be sent back to the caller.
            default: If we do not have the value in the cache and we do not want to wait, what shall we send back to the caller?
                It has to be serializable because it will also be stored in the cache.
            retry: While a value is being refreshed, we want to avoid to refresh it in parallel.
                But if it is taking too long, after the number of seconds provided here, we may want to try our luck again.
                If not specified, we will take the `refresh` value.
            wait: If the value is not in the cache, do we wait for the return of the function?
            use_args: This is the list of positional parameters (a list of integers) to be taken into account to generate the key that will be used in Redis.
            use_kwargs: This is the list of named parameters (a list of names) to be taken into account to generate the key that will be used in Redis.
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
                def refresh_value(key: str) -> T:
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

                    # Store value in cache with expiration time
                    self.server.set(key, new_value, ex=expire)
                    # Set refresh key with refresh time
                    self.server.set(PREFIX + key, 1, ex=refresh)
                    return new_value

                def refresh_value_in_thread(key: str) -> None:
                    """
                    Run the refresh value in a separate thread
                    """
                    thread = threading.Thread(target=refresh_value, args=(key,))
                    thread.start()

                # If the cache is disabled, directly call the function
                if not self.enabled:
                    return function(*args, **kwargs)

                # Lets create a key from the function's name and its parameters values
                key = self._create_key(name=function.__name__, args=args, use_args=use_args, kwargs=kwargs, use_kwargs=use_kwargs)

                # Get the value from the cache.
                # If it is not there we will get None.
                cached_value = cast(T, self.server.get(key))

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
                        refresh_value_in_thread(key)
                    else:
                        # Here we will wait, let's count it
                        self.server.incr(WAIT)
                        # We update the cash and return the value.
                        cached_value = refresh_value(key)

                # We may still have decided to wait but another process is already getting the cache updated.
                if cached_value is None and wait:
                    # Let's wait, but this is dangerous if we never get the value in the cache.
                    # We will stop if we lose the refresh key indicating that the refreshing timed out.
                    while cached_value is None and self.server.get(PREFIX + key):
                        # Let's count how many times we wait 1s
                        self.server.incr(SLEEP)
                        sleep(1)
                        cached_value = cast(T, self.server.get(key))

                # If the cache was empty, we have None in the cached_value.
                if cached_value is None:
                    # We are going to return the default value
                    self.server.incr(DEFAULT)
                    cached_value = default

                # Return whatever value we have at this point.
                return cached_value

            # If we want to bypass the cache at runtime, we need a reference to the decorated function
            wrapper.function = function  # type: ignore

            return wrapper

        return decorator

    def get_stats(self, delete: bool = False) -> Dict[str, Any]:
        """
        Get the stats stored by RedisCache. See the list and definition at the top of this file.
        If delete is set to True we delete the stats from Redis after read.
        From Redis 6.2, it is possible to GETDEL, making sure that we do not lose some data between
        the 'get' and the 'delete'. But it is not available in the Redis (v3.5.3) python interface yet.

        Args:
            delete: Reset the counters after read.

        Returns:
            dict: Dictionary of all the counters and their value.
        """
        stats = {stat: self.server.get(stat) for stat in STATS}
        if delete:
            for stat in STATS:
                self.server.delete(stat)
        return stats
