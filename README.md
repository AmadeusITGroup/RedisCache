# RedisCache

## Presentation

There are already quite a few Python decorators to cache functions in a Redis database:

- [redis-cache](https://pypi.org/project/redis-cache/)
- [redis_cache_decorator](https://pypi.org/project/redis_cache_decorator/)
- [redis-simple-cache](https://pypi.org/project/redis-simple-cache/)
- [python-redis-cache](https://pypi.org/project/python-redis-cache/)
- [redis-simple-cache-3k](https://pypi.org/project/redis-simple-cache-3k/)
- [redis-simple-cache-py3](https://pypi.org/project/redis-simple-cache-py3/)
- and more ...

But none I could find allows to set two expiration times as we do it here. The first given time is how long before we should update the value stored in the cache. The second given time, longer of course, is how long the data stored in the cache is still good enough to be sent back to the caller. The refreshing of the cache is only done when the function is called. And by default it is done asynchronously, so the caller doesn't have to wait. When the data in the cache becomes too old, it disapear automatically.

This is a great caching mechanism for functions that will give a consistent output according to their parameters and at a given time. A purelly random function should not be cached. And a function that is independent of the time should be cached with a different mechanism like the LRU cache in the [functools](https://docs.python.org/3/library/functools.html) standard module.

## Installation

Simply install the PyPi package:

```bash
pip install rediscache
```

## Requirements

Of course you need a Redis server installed. By default, the decorator will connect to `localhost:6379` with no password, using the database number `0`. This can be changed with parameters given to the `RedisCache` object.

## Usage of the RedisCache class

### RedisCache class

To avoid having too many connections to the Redis server, it is best to create only one instance of this class.

```python
rediscache = RedisCache()
```

All the parameters for the `RedisCache` constructor are optional. Their default value are in `[]`.

- host: IP or host name of the Redis server. [`'localhost'`]
- port: Port number of the Redis server. [`6379`]
- db: Database number in the Redis server. [`0`]
- password: Password required to read and write on the Redis server. [`None`]
- decode: Decode the data stored in the cache as byte string. For example, it should not be done if you actually want to cache byte strings. [`True`]
- enabled: When False it allows to programatically disable the cache. It can be usefull for unit tests. [`True`]

### Environment variables

In the case of a cloud deployment, for example, it might be easier to use environment variables to set the Redis server details:

- REDIS_SERVICE_HOST: IP or host name of the Redis server.
- REDIS_SERVICE_PORT: Port number of the Redis server.
- REDIS_SERVICE_DB: Database number in the Redis server.
- REDIS_SERVICE_PASSWORD: Password required to read and write on the Redis server.

The order of priority is the natural _parameter_ > _environment variable_ > _default value_.

### `cache` decorator

This is the main decorator. All the parameters are available. The mandatory ones do not have a default value:

- refresh: The amount of seconds before it would be a good idea to refresh the cached value.
- expire: How many seconds that the value in the cache is still considered good enough to be sent back to the caller.
- retry: While a value is being refreshed, we want to avoid to refresh it in parallel. But if it is taking too long, after the number of seconds provided here, we may want to try our luck again. If not specified, we will take the `refresh` value.
- default: If we do not have the value in the cache and we do not want to wait, what shall we send back to the caller? It has to be serializable because it will also be stored in the cache. [`''`]
- wait: If the value is not in the cache, do we wait for the return of the function? [`False`]
- serializer: The only type of data that can be stored directly in the Redis database are `byte`, `str`, `int` and `float`. Any other will have to be serialized with the function provided here. [`None`]
- deserializer: If the value was serialized to be stored in the cache, it needs to deserialized when it is retrieved. [`None`]
- use_args: This is the list of positional parameters (a list of integers) to be taken into account to generate the key that will be used in Redis. If `None`, they will all be used. [`None`]
- use_kwargs: This is the list of named paramters (a list of names) to be taken into account to generate the key that will be used in Redis. If `None`, they will all be used. [`None`]

Example:

```python
from rediscache import RedisCache
REDISCACHE = RedisCache()
@REDISCACHE.cache(10, 60) # Keep the value up to 1mn but ready to be refreshed every 10s.
def my_function(...) {
    ...
}
```

See `test_rediscache.py` for more examples.

Note: when you choose to wait for the value, you do not have an absolute guarantee that you will not get the default value. For example if it takes more than the retry time to get an answer from the function, the decorator will give up.

### `cache_raw` decorator helper

No serializer or deserializer. This will only work if the cached function only returns `byte`, `str`, `int` or `float` types. Even `None` will fail.

### `cache_raw_wait` decorator helper

Same as above but waits for the value if not in the cache.

### `cache_json` decorator helper

Serialize the value with `json.dumps()` and desiralize the value with `json.loads()`.

### `cache_json_wait` decorator helper

Same as above but waits for the value if not in the cache.

### `get_stats(delete=False)`

This will get the stats stored when using the cache. The `delete` option is to reset the counters after read.
The output is a dictionary with the following keys and values:

- **Refresh**: Number of times the cached function was actually called.
- **Wait**: Number of times we waited for the result when executing the function.
- **Failed**: Number of times the cached function raised an exception when called.
- **Missed**: Number of times the functions result was not found in the cache.
- **Success**: Number of times the function's result was found in the cache.
- **Default**: Number of times the default value was used because nothing is in the cache or the function failed.

### The `function` property

The decorator and its aliases add a new property to the decorated function to be able to bypass the cache as it may be required
in some cases.

```python
from rediscache import RedisCache
REDISCACHE = RedisCache()
@REDISCACHE.cache(2, 10)
def myfunc():
    return "Hello"
# Invoke the function without caching it.
print(myfunc.function())
```

## Development

### Poetry

My development environment is handled by Poetry. I use `Python 3.11.7`.

### Testing

To make sure we use Redis properly, we do not mock it in the unit tess. So you will need a localhost default instance of Redis server without a password. This means that the unit tests are more like integrtion tests.

The execution of the tests including coverage result can be done with `test.sh`. You can also run just `pytest`:

```bash
./test.sh
```

## CI/CD

### Workflow

We use the GitHub workflow to check each new commit. See `.github/workflows/python-package.yaml`.

We get help from re-usable actions. Here is the [Marketplace](https://github.com/marketplace?type=actions).

- [Checkout](https://github.com/marketplace/actions/checkout)
- [Install Poery Action](https://github.com/marketplace/actions/install-poetry-action)
- [Setup Python](https://github.com/marketplace/actions/setup-python)

### Publish to PyPI

For the moment the publish to PyPI is done manually with the `publish.sh` script. You will need a PyPI API token in `PYPI_API_TOKEN`, stored in a `secrets.sh`.
