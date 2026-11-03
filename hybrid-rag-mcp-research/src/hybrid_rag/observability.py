from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def trace_span(name: str, as_type: str = "span") -> Callable[[F], F]:
    """Create an optional Langfuse observation without capturing arguments or results."""
    try:
        from langfuse import observe
    except ImportError:
        def passthrough(function: F) -> F:
            return function
        return passthrough

    def decorate(function: F) -> F:
        return cast(
            F,
            observe(
                name=name,
                as_type=as_type,
                capture_input=False,
                capture_output=False,
            )(function),
        )

    return decorate
