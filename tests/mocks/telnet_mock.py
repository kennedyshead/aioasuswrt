"""
Mock library for the Telnet connection.

Especially mocking the reader/writer of asyncio.
"""

# pylint: skip-file
import textwrap
from typing import Any, Optional, Tuple

_READER: Optional["MockReader"] = None
_WRITER: Optional["MockWriter"] = None
_RETURN_VAL = "".encode("ascii")
_PROMPT = "".encode("ascii")
_LINEBREAK = float("inf")

_NEXT_EXCEPTION: Optional[Exception] = None


class MockWriter:
    """Mock implementation of the writer of a asyncio telnet connection."""

    def __init__(self) -> None:
        """Mock the init method."""

    def write(self, write_bytes: bytes) -> None:
        """Write method."""
        global _NEXT_EXCEPTION
        if _NEXT_EXCEPTION is not None:
            exception = _NEXT_EXCEPTION
            _NEXT_EXCEPTION = None
            raise exception

        if _READER is not None:
            _READER.set_cmd(write_bytes)

    def close(self) -> None:
        """Close method."""


class MockReader:
    """Mock implementation of the reader of a asyncio telnet connection."""

    def __init__(self) -> None:
        """Init method."""
        self._cmd: bytes = "".encode("ascii")

    def set_linebreak(self, linebreak: int) -> None:
        """Set linebreak method."""
        self._linebreak = linebreak

    def set_cmd(self, new_cmd: bytes) -> None:
        r"""
        Set cmd method.

        The asyncio telnet connection adds '\r\rn' commands for every
        strings bigger than the linebreak. So let's add that here.
        """
        try:
            self._cmd = "\r\r\n".join(
                textwrap.wrap(
                    _PROMPT.decode("utf-8") + " " + new_cmd.decode("utf-8"),
                    width=int(_LINEBREAK),
                    drop_whitespace=False,
                )
            ).encode("ascii")
        except OverflowError:
            self._comd = new_cmd

    async def readuntil(self, read_till: bytes) -> bytes:
        """
        Read until method.

        Let's create the return string from the cmd and the return string
        """
        ret_val = self._cmd + "\n".encode("ascii")
        ret_val = ret_val + _RETURN_VAL + "\n".encode("ascii") + _PROMPT
        return ret_val


def set_prompt(new_prompt: str) -> None:
    """Set prompt method."""
    global _PROMPT
    _PROMPT = new_prompt.encode("ascii")


def set_return(new_return: str) -> None:
    """Set return method."""
    global _RETURN_VAL
    print(f"set reutrn: {new_return}")
    _RETURN_VAL = new_return.encode("ascii")


def set_linebreak(linebreak: float) -> None:
    """Set linebreak method."""
    global _LINEBREAK
    _LINEBREAK = linebreak


def raise_exception_on_write(exception_type: Optional[Exception]) -> None:
    """Raise exception on write."""
    global _NEXT_EXCEPTION
    _NEXT_EXCEPTION = exception_type


async def open_connection(
    *args: Any, **kwargs: Any
) -> Tuple[MockReader, MockWriter]:
    """Open connection method."""
    global _READER, _WRITER
    print("MOCKED OPEN")
    _READER = MockReader()
    _WRITER = MockWriter()
    # Clear previously configured variables.
    set_return("")
    raise_exception_on_write(None)
    return (_READER, _WRITER)
