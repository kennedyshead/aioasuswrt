"""
Mock library for the Telnet connection, especially mocking the reader/writer of asyncio
"""
import textwrap
import typing

_READER = None
_WRITER = None
_RETURN_VAL = "".encode("ascii")
_PROMPT = "".encode("ascii")
_LINEBREAK = float("inf")

_NEXT_EXCEPTION = None


class MockWriter:
    """ Mock implementation of the writer of a asyncio telnet connection."""

    def __init__(self):
        pass

    def write(self, write_bytes: bytes):
        global _READER, _NEXT_EXCEPTION
        if _NEXT_EXCEPTION is not None:
            exception = _NEXT_EXCEPTION
            _NEXT_EXCEPTION = None
            raise exception

        if _READER is not None:
            _READER.set_cmd(write_bytes)

    def close(self):
        pass


class MockReader:
    """ Mock implementation of the reader of a asyncio telnet connection."""

    def __init__(self):
        self._cmd: bytes = "".encode("ascii")

    def set_linebreak(self, linebreak: int):
        self._linebreak = linebreak

    def set_cmd(self, new_cmd: bytes):
        # The asyncio telnet connection adds '\r\rn' commands for every
        # strings bigger than the linebreak. So let's add that here.
        self._cmd = "\r\r\n".join(
            textwrap.wrap(
                _PROMPT.decode("utf-8") + " " + new_cmd.decode("utf-8"),
                width=_LINEBREAK,
                drop_whitespace=False,
            )
        ).encode("ascii")

    async def readuntil(self, read_till: bytes) -> bytes:
        # Let's create the return string from the cmd and the return string
        ret_val = self._cmd + "\n".encode("ascii")
        ret_val = ret_val + _RETURN_VAL + "\n".encode("ascii") + _PROMPT
        return ret_val


def set_prompt(new_prompt):
    global _PROMPT
    _PROMPT = new_prompt.encode("ascii")


def set_return(new_return: str):
    global _RETURN_VAL
    _RETURN_VAL = new_return.encode("ascii")


def set_linebreak(linebreak):
    global _LINEBREAK
    _LINEBREAK = linebreak


def raise_exception_on_write(exception_type):
    global _NEXT_EXCEPTION
    _NEXT_EXCEPTION = exception_type


async def open_connection(*args, **kwargs) -> typing.Tuple[MockReader, MockWriter]:
    global _READER, _WRITER
    _READER = MockReader()
    _WRITER = MockWriter()
    # Clear previously configured variables.
    set_return("")
    raise_exception_on_write(None)
    return (_READER, _WRITER)
