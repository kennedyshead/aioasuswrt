"""Unit test asyswrt."""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false

from unittest.mock import AsyncMock, patch

import pytest

from aioasuswrt.asuswrt import AsusWrt
from aioasuswrt.constant import TEMP_COMMANDS
from aioasuswrt.structure import TransferRates

from .common import DHCP_DATA, NETDEV_DATA, NVRAM_DATA, TEMP_DATA

_BIT_WRAP = 0xFFFFFFFF


@pytest.mark.asyncio
async def test_get_nvram_empty(mocked_wrt: AsusWrt) -> None:
    """Test get_nvram with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=[])
    assert await mocked_wrt.get_nvram("DHCP") is None


@pytest.mark.asyncio
async def test_get_nvram_successful(mocked_wrt: AsusWrt) -> None:
    """Test get_nvram with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=NVRAM_DATA)
    assert DHCP_DATA == await mocked_wrt.get_nvram("DHCP")


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


def _temp_commands_run(command: str) -> list[str] | None:
    if command == "wl -i eth1 phy_tempsense":
        return TEMP_DATA[0]
    if command == "wl -i eth2 phy_tempsense":
        return TEMP_DATA[1]
    if command == "head -c20 /proc/dmu/temperature":
        return TEMP_DATA[2]
    return None


@pytest.mark.asyncio
async def test_get_temperature_first_empty(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=[])
    assert await mocked_wrt.get_temperature() is None


@pytest.mark.asyncio
async def test_get_temperature_first_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with successful command."""

    mocked_wrt._connection.run_command = AsyncMock(
        side_effect=_temp_commands_run
    )
    assert await mocked_wrt.get_temperature() == {
        "2.4GHz": 49.5,
        "5.0GHz": 54.5,
        "CPU": 77.0,
    }


@pytest.mark.asyncio
async def test_get_temperature_second_empty(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=[])
    mocked_wrt._find_temperature_commands = AsyncMock()

    mocked_wrt._temps_commands = {
        "2.4GHz": TEMP_COMMANDS["2.4GHz"][0],
        "5.0GHz": TEMP_COMMANDS["5.0GHz"][0],
        "CPU": TEMP_COMMANDS["CPU"][0],
    }
    assert await mocked_wrt.get_temperature() is None
    mocked_wrt._find_temperature_commands.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_temperature_second_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(
        side_effect=_temp_commands_run
    )
    mocked_wrt._find_temperature_commands = AsyncMock()

    mocked_wrt._temps_commands = {
        "2.4GHz": TEMP_COMMANDS["2.4GHz"][0],
        "5.0GHz": TEMP_COMMANDS["5.0GHz"][0],
        "CPU": TEMP_COMMANDS["CPU"][0],
    }
    assert await mocked_wrt.get_temperature() == {
        "2.4GHz": 49.5,
        "5.0GHz": 54.5,
        "CPU": 77.0,
    }
    mocked_wrt._find_temperature_commands.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_vpn_clients_empty(mocked_wrt: AsusWrt) -> None:
    """Test get_nvram with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(return_value=[])
    assert await mocked_wrt.get_vpn_clients() is None
