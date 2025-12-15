"""Conftest setup."""

from unittest.mock import patch

import pytest

from aioasuswrt.asuswrt import AsusWrt
from aioasuswrt.structure import AuthConfig, ConnectionType


@pytest.fixture
def mocked_wrt() -> AsusWrt:
    """Mocked connection."""
    with patch("aioasuswrt.asuswrt.create_connection") as _connection:
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
        )
        return router
