from asyncio import IncompleteReadError
from unittest import TestCase, mock

import pytest

from aioasuswrt.connection import TelnetConnection
from tests.mocks import telnet_mock


class TestTelnetConnection(TestCase):
    """Testing TelnetConnection."""

    def setUp(self):
        """Set up test env."""
        self.connection = TelnetConnection("fake", 2, "fake", "fake")
        # self.connection._connected = True
        self.connection._prompt_string = "".encode("ascii")

    def test_determine_linelength_inf(self):
        """Test input for infinite breakline length."""
        # An input without newlines results in infinite linebreak
        # The input string is shorter than the limit
        for i in (15, 50):
            input_bytes = (" " * i).encode("ascii")
            linebreak = self.connection._determine_linebreak(input_bytes)
            self.assertEqual(linebreak, float("inf"))

    def test_determine_linelength(self):
        for i in (15, 50):
            input_bytes = (" " * i + "\n" + " " * 5).encode("ascii")
            linebreak = self.connection._determine_linebreak(input_bytes)
            self.assertEqual(linebreak, i)

            # And now with some more lines
            input_bytes = ((" " * i + "\n") * 3 + " " * 5).encode("ascii")
            linebreak = self.connection._determine_linebreak(input_bytes)
            self.assertEqual(linebreak, i)

            # And with a prompt string
            prompt = "test_string"
            input_bytes = ("a" * (i - len(prompt)) + "\n" + "a" * 5).encode(
                "ascii"
            )
            self.connection._prompt_string = prompt.encode("ascii")
            linebreak = self.connection._determine_linebreak(input_bytes)
            self.assertEqual(linebreak, i)
            self.connection._prompt_string = "".encode("ascii")


@pytest.mark.asyncio
async def test_sending_cmds():
    with mock.patch(
        "asyncio.open_connection", new=telnet_mock.open_connection
    ):
        # Let's set a short linebreak of 10
        telnet_mock.set_linebreak(22)

        connection = TelnetConnection("fake", 2, "fake", "fake")
        print("Doing connection")
        await connection.async_connect()
        print("Fin connection")

        # Now let's send some arbitrary short command
        exp_ret_val = "Some arbitrary long return string." + "." * 100
        telnet_mock.set_return(exp_ret_val)
        new_return = await connection.async_run_command("run command\n")
        print(new_return)
        assert new_return[0] == exp_ret_val


@pytest.mark.asyncio
async def test_reconnect():
    with mock.patch(
        "asyncio.open_connection", new=telnet_mock.open_connection
    ):
        connection = TelnetConnection("fake", 2, "fake", "fake")
        await connection.async_connect()

        telnet_mock.raise_exception_on_write(
            IncompleteReadError("".encode("ascii"), 42)
        )

        new_return = await connection.async_run_command("run command\n")
        assert new_return == [""]
