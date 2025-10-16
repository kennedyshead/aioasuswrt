"""AioAsusWrt helpers."""

from math import floor, log
from math import pow as mpow


def convert_size(size: int) -> str:
    """
    Convert bytes to a readable string with MB/GB and so on added as a suffix.

    Args:
        size (float): Size given in number of bytes

    """
    if size == 0:
        return "0 B"
    name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    index = int(floor(log(size, 1024)))
    power = mpow(1024, index)
    return f"{round(size / power, 2)} {name[index]}"
