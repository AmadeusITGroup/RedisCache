"""
Unit tests for the rediscache.tools module.
"""

from datetime import date
from functools import partial
from json import dumps, loads
from typing import Any, Dict

from rediscache.tools import decorate


def test_single_decorate() -> None:
    """
    Test using a single decorate decorator.
    This can be tested alone with:
    pytest -k test_single_decorate
    """

    @decorate(dumps)
    def simple() -> str:
        return "value"

    @decorate(dumps)
    def func_with_args(size: int) -> Dict[int, float]:
        return {x: (x * 11 / 10) for x in range(size)}

    @decorate(dumps)
    def func_with_args_kwargs(arg: str, kwarg: str = "") -> Dict[str, str]:
        return {arg: kwarg}

    value0 = simple()
    assert isinstance(value0, str)

    value1 = func_with_args(4)
    assert isinstance(value1, str)

    value2 = func_with_args_kwargs("a", kwarg="b")
    assert isinstance(value2, str)


def test_multiple_decorate() -> None:
    """
    Test using a stack of decorate decorator.
    This can be tested alone with:
    pytest -k test_multiple_decorate
    """

    @decorate(loads)
    @decorate(dumps)
    def func_with_args(size: int) -> Dict[int, float]:
        """My func_with_args"""
        return {x: (x * 11 / 10) for x in range(size)}

    @decorate(loads)
    @decorate(dumps)
    def func_with_args_kwargs(arg: str, kwarg: str = "") -> Dict[str, str]:
        """My func_with_args_kwargs"""
        return {arg: kwarg}

    value1 = func_with_args(4)
    assert isinstance(value1, dict)
    assert len(value1) == 4
    assert "1" in value1
    assert value1["1"] == 1.1
    assert func_with_args.__name__ == "func_with_args"
    assert func_with_args.__doc__ == "My func_with_args"

    value2 = func_with_args_kwargs("a", kwarg="b")
    assert isinstance(value2, dict)
    assert len(value2) == 1
    assert "a" in value2
    assert value2["a"] == "b"
    assert func_with_args_kwargs.__name__ == "func_with_args_kwargs"
    assert func_with_args_kwargs.__doc__ == "My func_with_args_kwargs"


def test_partial_decorate() -> None:
    """
    Test using a transformation function with extra parameters.
    This can be tested alone with:
    pytest -k test_partial_decorate
    """

    @decorate(partial(dumps, skipkeys=True))
    def func_with_id() -> Dict[Any, Any]:
        """My func_with_id"""
        return {"name": "Toto", "age": 25, date.today(): "today"}

    value = func_with_id()
    assert isinstance(value, str)
    assert value == '{"name": "Toto", "age": 25}'
