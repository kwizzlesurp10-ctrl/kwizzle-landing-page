from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    error: E


Result = Union[Ok[T], Err[E]]


def is_ok(result: Result[T, E]) -> bool:
    return isinstance(result, Ok)


def unwrap_ok(result: Ok[T]) -> T:
    return result.value
