"""Unit test asyswrt."""

# pylint: disable=protected-access
# pyright: reportPrivateUsage=false

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from aioasuswrt.asuswrt import AsusWrt
from aioasuswrt.connection import BaseConnection
from aioasuswrt.constant import DEFAULT_DNSMASQ
from aioasuswrt.structure import (
    TEMP_COMMANDS,
    Command,
    Mode,
    Settings,
    TransferRates,
)

from .common import (
    BAD_CLIENTLIST_DATA,
    HOST_DATA,
    LOADAVG_DATA,
    NETDEV_DATA,
    NVRAM_DHCP_DATA,
    NVRAM_DHCP_VALUES,
    NVRAM_FIRMWARE_DATA,
    NVRAM_FIRMWARE_VALUES,
    NVRAM_LABEL_MAC_DATA,
    NVRAM_LABEL_MAC_VALUES,
    NVRAM_MODEL_DATA,
    NVRAM_MODEL_VALUES,
    NVRAM_QOS_DATA,
    NVRAM_QOS_VALUES,
    NVRAM_REBOOT_DATA,
    NVRAM_REBOOT_VALUES,
    NVRAM_WLAN_DATA,
    NVRAM_WLAN_VALUES,
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
@pytest.mark.parametrize(
    "command,return_data,result",
    [
        ("DHCP", NVRAM_DHCP_DATA, NVRAM_DHCP_VALUES),
        ("MODEL", NVRAM_MODEL_DATA, NVRAM_MODEL_VALUES),
        ("QOS", NVRAM_QOS_DATA, NVRAM_QOS_VALUES),
        ("REBOOT", NVRAM_REBOOT_DATA, NVRAM_REBOOT_VALUES),
        ("WLAN", NVRAM_WLAN_DATA, NVRAM_WLAN_VALUES),
        ("FIRMWARE", NVRAM_FIRMWARE_DATA, NVRAM_FIRMWARE_VALUES),
        ("LABEL_MAC", NVRAM_LABEL_MAC_DATA, NVRAM_LABEL_MAC_VALUES),
    ],
)
async def test_get_nvram_successful(
    command: str, return_data: str, result: dict[str, str], mocked_wrt: AsusWrt
) -> None:
    """Test get_nvram with successful command."""
    print(command, return_data)
    mocked_wrt._connection.run_command = AsyncMock(return_value=return_data)
    assert result == await mocked_wrt.get_nvram(command)


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

    _cmd_mock = AsyncMock(side_effect=_no_values)
    mocked_wrt._settings = Settings(mode=Mode.ROUTER)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=_cmd_mock,
    )
    devices = await mocked_wrt.get_connected_devices(True)
    assert devices is None
    _cmd_mock.assert_has_calls(
        (
            call(Command.WL),
            call(Command.ARP),
            call(Command.IP_NEIGH),
            call(Command.LEASES.format(DEFAULT_DNSMASQ)),
            call(Command.CLIENTLIST),
        )
    )


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

    _cmd_mock = AsyncMock(side_effect=_bad_clientlist)
    mocked_wrt._settings = Settings(mode=Mode.ROUTER)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=_cmd_mock,
    )
    devices = await mocked_wrt.get_connected_devices(True)
    assert devices is None
    _cmd_mock.assert_has_calls(
        (
            call(Command.WL),
            call(Command.ARP),
            call(Command.IP_NEIGH),
            call(Command.LEASES.format(DEFAULT_DNSMASQ)),
            call(Command.CLIENTLIST),
        )
    )


@pytest.mark.asyncio
async def test_get_connected_devices_ap_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    _cmd_mock = AsyncMock(side_effect=successful_get_devices_commands)
    mocked_wrt._settings = Settings(mode=Mode.AP)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=_cmd_mock,
    )
    devices = await mocked_wrt.get_connected_devices()
    assert devices == WAKE_DEVICES_AP
    _not_called = False
    try:
        _cmd_mock.assert_any_await(Command.LEASES.format(DEFAULT_DNSMASQ))
    except AssertionError:
        _not_called = True
    assert _not_called


@pytest.mark.asyncio
async def test_get_loadavg_successful(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    _cmd_mock = AsyncMock(return_value=LOADAVG_DATA)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=_cmd_mock,
    )
    assert await mocked_wrt.get_loadavg() == {
        "sensor_load_avg1": 0.23,
        "sensor_load_avg15": 0.68,
        "sensor_load_avg5": 0.5,
    }
    _cmd_mock.assert_awaited_once_with(Command.LOADAVG)


@pytest.mark.asyncio
async def test_get_loadavg_null(
    mocked_wrt: AsusWrt,
) -> None:
    """Test for get asuswrt_data in ap mode."""
    _cmd_mock = AsyncMock(return_value=None)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=_cmd_mock,
    )
    assert await mocked_wrt.get_loadavg() is None
    _cmd_mock.assert_awaited_once_with(Command.LOADAVG)


@pytest.mark.asyncio
async def test_get_dns_records_successful(mocked_wrt: AsusWrt) -> None:
    """Test start_vpn_client successfully called."""
    _cmd_mock = AsyncMock(return_value=HOST_DATA)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=_cmd_mock,
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
    _cmd_mock.assert_awaited_once_with(Command.LISTHOSTS)


@pytest.mark.asyncio
async def test_get_dns_records_null(mocked_wrt: AsusWrt) -> None:
    """Test start_vpn_client successfully called."""
    _cmd_mock = AsyncMock(return_value=None)
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=_cmd_mock,
    )
    assert await mocked_wrt.get_dns_records() is None
    _cmd_mock.assert_awaited_once_with(Command.LISTHOSTS)


@pytest.mark.asyncio
async def test_total_transfer(mocked_wrt: AsusWrt) -> None:
    """Test start_vpn_client successfully called."""
    _cmd_mock = AsyncMock()
    mocked_wrt._connection = MagicMock(
        autospec=BaseConnection,
        run_command=_cmd_mock,
    )
    mocked_wrt._total_bytes = TransferRates(10, 10)
    assert await mocked_wrt.total_transfer() == {"rx": 10, "tx": 10}
    _cmd_mock.assert_not_awaited()
