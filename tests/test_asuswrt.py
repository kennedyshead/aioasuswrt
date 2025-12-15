"""Unit test asyswrt."""

# pylint: disable=protected-access

from unittest.mock import AsyncMock

import pytest

from aioasuswrt.asuswrt import AsusWrt

from .common import DHCP_DATA, NVRAM_DATA


@pytest.mark.asyncio
async def test_get_nvram_successfull(mocked_wrt: AsusWrt) -> None:
    """Test get_nvram with successful command"""
    mocked_wrt._connection.run_command = AsyncMock(return_value=NVRAM_DATA)
    assert DHCP_DATA == await mocked_wrt.get_nvram("DHCP")


@pytest.mark.asyncio
async def test_get_nvram_empty(mocked_wrt: AsusWrt) -> None:
    """Test get_nvram with successful command"""
    mocked_wrt._connection.run_command = AsyncMock(return_value=[])
    assert await mocked_wrt.get_nvram("DHCP") is None
