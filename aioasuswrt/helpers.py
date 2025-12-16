"""AioAsusWrt helpers."""

from collections.abc import Iterable
from copy import deepcopy


def empty_iter(iterable: Iterable[str]) -> bool:
    """Checks if an iterator is empty, without consuming."""
    try:
        _ = next(iter(deepcopy(iterable)))
        return False
    except StopIteration:
        return True
