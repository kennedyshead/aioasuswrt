"""Conftest setup."""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aioasuswrt.asuswrt import AsusWrt
from aioasuswrt.connection import BaseConnection
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
