from typing import Any, Dict

import pytest

from aioasuswrt.asuswrt import AsusWrt, AuthConfig, Device, Settings
from tests.test_data import (
    ARP_DATA,
    ARP_DEVICES,
    INTERFACES_COUNT,
    LEASES_DATA,
    LEASES_DEVICES,
    LOADAVG_DATA,
    NEIGH_DATA,
    NEIGH_DEVICES,
    NETDEV_DATA,
    TEMP_DATA,
    TEMP_DATA_2ND,
    WAKE_DEVICES_AP,
    WAKE_DEVICES_AP_NO_IP,
    WL_DATA,
    WL_DEVICES,
    WL_MIISING_LINE,
)


def mock_run_cmd(mocker: Any, values: Any) -> None:
    iter = 0

    async def patch_func(command: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal iter
        print(f"Command: {command}\nwith args={args} and kwargs={kwargs}")
        iter = iter + 1
        try:
            return values[iter - 1]
        except IndexError:
            print(
                f"Not enough elements in return list! Iteration {
                    iter
                } while list is {len(values)}."
            )
            assert False

    mocker.patch(
        "aioasuswrt.connection.SshConnection.run_command",
        side_effect=patch_func,
    )


@pytest.mark.asyncio
async def test_parse_with_empty_line(mocker: Any) -> None:
    """Testing _parse_lines where we get an empty line."""
    mock_run_cmd(mocker, [WL_MIISING_LINE])
    scanner = AsusWrt(host="localhost", auth_config=AuthConfig())
    devices: Dict[str, Device] = {}
    await scanner._get_wl(devices)
    assert WL_DEVICES.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in WL_DEVICES.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_wl(mocker: Any) -> None:
    """Testing wl."""
    mock_run_cmd(mocker, [WL_DATA])
    scanner = AsusWrt(host="localhost", auth_config=AuthConfig())
    devices: Dict[str, Device] = {}
    await scanner._get_wl(devices)
    assert WL_DEVICES.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in WL_DEVICES.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_wl_empty(mocker: Any) -> None:
    """Testing wl."""
    mock_run_cmd(mocker, [""])
    scanner = AsusWrt(host="localhost", auth_config=AuthConfig())
    devices: Dict[str, Device] = {}
    await scanner._get_wl(devices)
    assert {} == devices


@pytest.mark.asyncio
async def test_get_leases(mocker: Any) -> None:
    """Testing leases."""
    mock_run_cmd(mocker, [LEASES_DATA])
    scanner = AsusWrt(host="localhost", auth_config=AuthConfig())
    devices: Dict[str, Device] = NEIGH_DEVICES.copy()
    await scanner._get_leases(devices)
    assert LEASES_DEVICES.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in LEASES_DEVICES.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_arp(mocker: Any) -> None:
    """Testing arp."""
    mock_run_cmd(mocker, [ARP_DATA])
    scanner = AsusWrt(host="localhost", auth_config=AuthConfig())
    devices: Dict[str, Device] = WL_DEVICES.copy()
    await scanner._get_arp(devices)
    assert ARP_DEVICES.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in ARP_DEVICES.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_neigh(mocker: Any) -> None:
    """Testing neigh."""
    mock_run_cmd(mocker, [NEIGH_DATA])
    scanner = AsusWrt(host="localhost", auth_config=AuthConfig())
    devices: Dict[str, Device] = ARP_DEVICES.copy()
    await scanner._get_neigh(devices)
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in NEIGH_DEVICES.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_connected_devices_ap(mocker: Any) -> None:
    """Test for get asuswrt_data in ap mode."""
    mock_run_cmd(mocker, [WL_DATA, ARP_DATA, NEIGH_DATA, LEASES_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(),
        settings=Settings(mode="ap", require_ip=True),
    )
    devices = await scanner.get_connected_devices()
    assert WAKE_DEVICES_AP.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in WAKE_DEVICES_AP.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_connected_devices_ap_no_ip(mocker: Any) -> None:
    """Test for get asuswrt_data and not requiring ip."""
    mock_run_cmd(mocker, [WL_DATA, ARP_DATA, NEIGH_DATA, LEASES_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(),
        settings=Settings(mode="ap", require_ip=False),
    )
    devices = await scanner.get_connected_devices()
    assert WAKE_DEVICES_AP_NO_IP.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [
        value.to_tuple() for value in WAKE_DEVICES_AP_NO_IP.values()
    ]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_temperature(mocker: Any) -> None:
    """Test getting temperature."""
    mock_run_cmd(mocker, TEMP_DATA)
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(),
        settings=Settings(mode="ap", require_ip=False),
    )
    data = await scanner.get_temperature()
    assert data == {"2.4GHz": 49.5, "5.0GHz": 54.5, "CPU": 77.0}

    mock_run_cmd(mocker, TEMP_DATA_2ND)
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(),
        settings=Settings(mode="ap", require_ip=False),
    )
    data = await scanner.get_temperature()
    assert data == {"2.4GHz": 0.0, "5.0GHz": 0.0, "CPU": 81.3}


@pytest.mark.asyncio
async def test_get_loadavg(mocker: Any) -> None:
    """Test getting loadavg."""
    mock_run_cmd(mocker, [LOADAVG_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(),
        settings=Settings(mode="ap", require_ip=False),
    )
    data = await scanner.get_loadavg()
    assert data == [0.23, 0.5, 0.68]


@pytest.mark.asyncio
async def test_get_interfaces_counts(mocker: Any) -> None:
    """Test getting loadavg."""
    mock_run_cmd(mocker, [NETDEV_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(),
        settings=Settings(mode="ap", require_ip=False),
    )
    data = await scanner.get_interfaces_count()
    assert data == INTERFACES_COUNT
