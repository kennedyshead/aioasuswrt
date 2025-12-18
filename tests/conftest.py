"""Conftest setup."""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false, reportAssignmentType=false

from asyncio import StreamReader, StreamWriter
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asyncssh import SSHClientConnection

from aioasuswrt.asuswrt import AsusWrt
from aioasuswrt.connection import (
    BaseConnection,
    SshConnection,
    TelnetConnection,
    create_connection,
)
from aioasuswrt.constant import DEFAULT_DNSMASQ
from aioasuswrt.structure import AuthConfig, Command, ConnectionType, Settings
from tests.common import (
    ARP_DATA,
    CLIENTLIST_DATA,
    LEASES_DATA,
    NEIGH_DATA,
    WL_DATA,
)


def successful_get_devices_commands(
    command: str,
) -> list[str | None] | list[str] | None:
    """Commands mapped to data for successful call."""
    if command == Command.WL:
        return WL_DATA
    if command == Command.ARP:
        return ARP_DATA
    if command == Command.IP_NEIGH:
        return NEIGH_DATA
    if command == Command.LEASES.format(DEFAULT_DNSMASQ):
        return LEASES_DATA
    if command == Command.CLIENTLIST:
        return CLIENTLIST_DATA
    return None


@pytest.fixture
def mocked_wrt() -> AsusWrt:
    """AsusWrt with mocked connection."""
    with patch(
        "aioasuswrt.asuswrt.create_connection",
        return_value=MagicMock(
            autospec=BaseConnection, run_command=AsyncMock(return_value=None)
        ),
    ):
        router = AsusWrt(
            "fake",
            AuthConfig(
                username="test",
                password="test",
                connection_type=ConnectionType.SSH,
                ssh_key=None,
                port=None,
                passphrase=None,
            ),
            settings=Settings(),
        )
        return router


@pytest.fixture
def mocked_ssh_connection() -> SshConnection:
    """Mocked SshConnection."""
    with patch("aioasuswrt.connection.connect", autospec=SSHClientConnection):
        _connection: SshConnection = create_connection(
            "host",
            AuthConfig(
                username="Test",
                password="Test",
                connection_type=ConnectionType.SSH,
                ssh_key="test",
                passphrase="test",
                port=None,
            ),
        )
        return _connection


@pytest.fixture
def mocked_telnet_connection() -> TelnetConnection:
    """Mocked SshConnection."""
    with patch(
        "aioasuswrt.connection.open_connection",
        return_value=(
            MagicMock(autospec=StreamReader),
            MagicMock(autospec=StreamWriter),
        ),
    ):
        _connection: TelnetConnection = create_connection(
            "host",
            AuthConfig(
                username="Test",
                password="Test",
                connection_type=ConnectionType.TELNET,
                ssh_key="test",
                passphrase="test",
                port=None,
            ),
        )
        return _connection
