from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def trace_span(name: str) -> Callable[[F], F]:
    """Use a Langfuse span when the optional SDK is installed."""
    try:
        from langfuse import observe
    except ImportError:
        def passthrough(function: F) -> F:
            return function
        return passthrough

    def decorate(function: F) -> F:
        return cast(F, observe(name=name)(function))

    return decorate
