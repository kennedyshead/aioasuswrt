"""Unit test connection."""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false, reportAssignmentType=false

from asyncio import Lock

from aioasuswrt.connection import (
    SshConnection,
    TelnetConnection,
)


def test_sets_ssh_default_values(mocked_ssh_connection: SshConnection) -> None:
    """Test that the SSH init method sets values."""
    assert mocked_ssh_connection._port == 22
    assert mocked_ssh_connection._host == "host"
    assert mocked_ssh_connection._username == "Test"
    assert mocked_ssh_connection._password == "Test"
    assert mocked_ssh_connection._passphrase == "test"
    assert mocked_ssh_connection._ssh_key == "test"
    assert mocked_ssh_connection._known_hosts is None
    assert mocked_ssh_connection._client is None
    assert isinstance(mocked_ssh_connection._io_lock, Lock)
    assert mocked_ssh_connection.description == "Test@host:22"
    assert not mocked_ssh_connection.is_connected


def test_sets_telnet_default_values(
    mocked_telnet_connection: TelnetConnection,
):
    """Test that the SSH init method sets values."""
    assert mocked_telnet_connection._port == 110
    assert mocked_telnet_connection._host == "host"
    assert mocked_telnet_connection._username == "Test"
    assert mocked_telnet_connection._password == "Test"
    assert mocked_telnet_connection._reader is None
    assert mocked_telnet_connection._writer is None
    assert mocked_telnet_connection._prompt_string == "".encode("ascii")
    assert mocked_telnet_connection._linebreak is None
    assert isinstance(mocked_telnet_connection._io_lock, Lock)
    assert mocked_telnet_connection.description == "Test@host:110"
    assert not mocked_telnet_connection.is_connected
