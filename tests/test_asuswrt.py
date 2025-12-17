"""Unit test asyswrt."""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aioasuswrt.asuswrt import AsusWrt
from aioasuswrt.connection import BaseConnection
from aioasuswrt.structure import (
    TEMP_COMMANDS,
    Command,
    Mode,
    Settings,
    TransferRates,
)

from .common import (
    BAD_CLIENTLIST_DATA,
    DHCP_DATA,
    HOST_DATA,
    LOADAVG_DATA,
    NETDEV_DATA,
    NVRAM_DATA,
    TEMP_DATA,
    WAKE_DEVICES,
    WAKE_DEVICES_AP,
    WAKE_DEVICES_REACHABLE,
    WAKE_DEVICES_REACHABLE_AND_IP,
    WAKE_DEVICES_REQIRE_IP,
)
from .conftest import successful_get_devices_commands

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
async def test_get_temperature_not_numeric(
    mocked_wrt: AsusWrt,
) -> None:
    """Test get_current_transfer_rates with successful command."""
    mocked_wrt._connection.run_command = AsyncMock(
        return_value=["5s (0x3b)\r"]
    )
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


@pytest.mark.asyncio
async def test_get_connected_devices_router_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    mocked_wrt._settings = Settings(mode=Mode.ROUTER)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(side_effect=successful_get_devices_commands),
    )
    devices = await mocked_wrt.get_connected_devices()
    assert devices == WAKE_DEVICES


@pytest.mark.asyncio
async def test_get_connected_devices_require_ip_router_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    mocked_wrt._settings = Settings(mode=Mode.ROUTER, require_ip=True)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(side_effect=successful_get_devices_commands),
    )
    devices = await mocked_wrt.get_connected_devices()
    assert devices == WAKE_DEVICES_REQIRE_IP


@pytest.mark.asyncio
async def test_get_connected_devices_reachable_router_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    mocked_wrt._settings = Settings(mode=Mode.ROUTER)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(side_effect=successful_get_devices_commands),
    )
    devices = await mocked_wrt.get_connected_devices(True)
    assert devices == WAKE_DEVICES_REACHABLE


@pytest.mark.asyncio
async def test_get_connected_devices_reachable_and_ip_router_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in router mode filter reachable and ip."""
    mocked_wrt._settings = Settings(mode=Mode.ROUTER, require_ip=True)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(side_effect=successful_get_devices_commands),
    )
    devices = await mocked_wrt.get_connected_devices(True)
    assert devices == WAKE_DEVICES_REACHABLE_AND_IP


@pytest.mark.asyncio
async def test_get_connected_devices_null_values(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data with null values."""

    def _no_values(_) -> None:
        """Just a dummy"""

    mocked_wrt._settings = Settings(mode=Mode.ROUTER)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(side_effect=_no_values),
    )
    devices = await mocked_wrt.get_connected_devices(True)
    assert devices is None


@pytest.mark.asyncio
async def test_get_connected_devices_bad_clientlist_data(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data with null values."""

    def _bad_clientlist(command: str) -> list[str] | None:
        """Just a dummy"""
        if command == Command.CLIENTLIST:
            return BAD_CLIENTLIST_DATA
        return None

    mocked_wrt._settings = Settings(mode=Mode.ROUTER)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(side_effect=_bad_clientlist),
    )
    devices = await mocked_wrt.get_connected_devices(True)
    assert devices is None


@pytest.mark.asyncio
async def test_get_connected_devices_ap_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    mocked_wrt._settings = Settings(mode=Mode.AP)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(side_effect=successful_get_devices_commands),
    )
    devices = await mocked_wrt.get_connected_devices()
    assert devices == WAKE_DEVICES_AP


@pytest.mark.asyncio
async def test_get_loadavg_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(return_value=LOADAVG_DATA),
    )
    assert await mocked_wrt.get_loadavg() == {
        "sensor_load_avg1": 0.23,
        "sensor_load_avg15": 0.68,
        "sensor_load_avg5": 0.5,
    }


@pytest.mark.asyncio
async def test_get_loadavg_null(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(return_value=None),
    )
    assert await mocked_wrt.get_loadavg() is None


@pytest.mark.asyncio
async def test_get_dns_records_successful(mocked_wrt: AsusWrt) -> None:
    """Test start_vpn_client successfully called."""
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(return_value=HOST_DATA),
    )
    assert await mocked_wrt.get_dns_records() == {
        "127.0.0.1": {
            "host_names": [
                "localhost.localdomain",
                "localhost",
            ],
            "ip": "127.0.0.1",
        },
        "192.168.1.1": {
            "host_names": [
                "RT-AC88U-2780.",
                "RT-AC88U-2780",
                "RT-AC88U-2780.local",
            ],
            "ip": "192.168.1.1",
        },
    }


@pytest.mark.asyncio
async def test_get_dns_records_null(mocked_wrt: AsusWrt) -> None:
    """Test start_vpn_client successfully called."""
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=AsyncMock(return_value=None),
    )
    assert await mocked_wrt.get_dns_records() is None
