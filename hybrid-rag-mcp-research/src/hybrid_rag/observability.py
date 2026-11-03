from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def trace_span(name: str) -> Callable[[F], F]:
    """Trace a named span without capturing function arguments or return values."""
    try:
        from langfuse import observe
    except ImportError:
        def passthrough(function: F) -> F:
            return function
        return passthrough

    def decorate(function: F) -> F:
        return cast(
            F,
            observe(name=name, capture_input=False, capture_output=False)(function),
        )

    return decorate
