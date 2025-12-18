"""Unit test connection."""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false, reportAssignmentType=false

from asyncio import Lock, StreamReader, StreamWriter
from unittest.mock import AsyncMock, MagicMock

import pytest
from asyncssh import SSHClientConnection

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


@pytest.mark.asyncio
async def test_ssh_connect_locks(mocked_ssh_connection: SshConnection) -> None:
    """Test that SshConnection locks while connecting."""
    mocked_ssh_connection._connect = AsyncMock()
    _mock_lock = AsyncMock()
    mocked_ssh_connection._io_lock = MagicMock(
        autospec=Lock, __aenter__=_mock_lock
    )
    assert await mocked_ssh_connection.connect() is None
    _mock_lock.assert_awaited_once()


@pytest.mark.asyncio
async def test_telnet_connect_locks(
    mocked_telnet_connection: TelnetConnection,
) -> None:
    """Test that SshConnection locks while connecting."""
    mocked_telnet_connection._connect = AsyncMock()
    _mock_lock = AsyncMock()
    mocked_telnet_connection._io_lock = MagicMock(
        autospec=Lock, __aenter__=_mock_lock
    )
    assert await mocked_telnet_connection.connect() is None
    _mock_lock.assert_awaited_once()


@pytest.mark.asyncio
async def test_ssh_already_connected(
    mocked_ssh_connection: SshConnection,
) -> None:
    """Test that SshConnection locks while connecting."""
    _mock_lock = AsyncMock()
    mocked_ssh_connection._client = MagicMock(autospec=SSHClientConnection)
    mocked_ssh_connection._io_lock = MagicMock(
        autospec=Lock, __aenter__=_mock_lock
    )
    assert await mocked_ssh_connection.connect() is None
    _mock_lock.assert_not_awaited()


@pytest.mark.asyncio
async def test_telnet_already_connected(
    mocked_telnet_connection: TelnetConnection,
) -> None:
    """Test that SshConnection locks while connecting."""
    _mock_lock = AsyncMock()
    mocked_telnet_connection._reader = MagicMock(autospec=StreamReader)
    mocked_telnet_connection._writer = MagicMock(autospec=StreamWriter)
    mocked_telnet_connection._io_lock = MagicMock(
        autospec=Lock, __aenter__=_mock_lock
    )
    assert await mocked_telnet_connection.connect() is None
    _mock_lock.assert_not_awaited()
