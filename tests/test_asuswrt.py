"""Unit test asyswrt."""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false

from unittest.mock import AsyncMock, patch

import pytest
from structure import TransferRates

from aioasuswrt.asuswrt import AsusWrt

from .common import DHCP_DATA, NETDEV_DATA, NVRAM_DATA

_BIT_WRAP = 0xFFFFFFFF


@pytest.mark.asyncio
async def test_get_nvram_successful(mocked_wrt: AsusWrt) -> None:
    """Test get_nvram with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=NVRAM_DATA)
    assert DHCP_DATA == await mocked_wrt.get_nvram("DHCP")


@pytest.mark.asyncio
async def test_get_nvram_empty(mocked_wrt: AsusWrt) -> None:
    """Test get_nvram with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=[])
    assert await mocked_wrt.get_nvram("DHCP") is None


@pytest.mark.asyncio
async def test_get_current_transfer_first_empty(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=[])
    assert await mocked_wrt.get_current_transfer_rates() is None


@pytest.mark.asyncio
async def test_get_current_transfer_first_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with first successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=NETDEV_DATA)
    assert await mocked_wrt.get_current_transfer_rates() == {"rx": 0, "tx": 0}


@pytest.mark.asyncio
async def test_get_current_transfer_second_empty(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=[])
    with patch("aioasuswrt.asuswrt.time", return_value=120) as mocked_time:
        mocked_wrt._last_transfer_rates_check = 60
        mocked_wrt._transfer_rates = TransferRates(
            -1 + _BIT_WRAP, -1 + _BIT_WRAP
        )
        assert await mocked_wrt.get_current_transfer_rates() is None
        mocked_time.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_transfer_second_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with second successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=NETDEV_DATA)
    with patch("aioasuswrt.asuswrt.time", return_value=120) as mocked_time:
        mocked_wrt._last_transfer_rates_check = 60
        mocked_wrt._transfer_rates = TransferRates(
            -1 + _BIT_WRAP, -1 + _BIT_WRAP
        )
        assert await mocked_wrt.get_current_transfer_rates() == {
            "rx": 21734767,
            "tx": 13230063,
        }
        mocked_time.assert_called_once()
