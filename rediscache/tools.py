"""
Extra tools provided to help with the cache main purpose.
"""

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
InT = TypeVar("InT")
OutT = TypeVar("OutT")


def decorate(transform: Callable[[InT], OutT]) -> Callable[[Callable[P, InT]], Callable[P, OutT]]:
    """
    This decorator helps to transform the output of a function from type InT to type OuT providing the
    appropriate function.
    It is especially meant to be used to serialize the output of a function to be cached.
    It can also be used to deserialize the cached value, but this should be used with great caution
    since it could be worse than not caching the function at all.

    Args:
        transform: the function that will take the output of the decorated function and transform it,
            usually to a new type.
    """

    def decorator(function: Callable[P, InT]) -> Callable[P, OutT]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> OutT:
            value = function(*args, **kwargs)
            return transform(value)

        return wrapper

    return decorator
