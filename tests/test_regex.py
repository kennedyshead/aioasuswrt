"""Test for regex patterns."""

# pylint: disable=W0212
from copy import deepcopy
from typing import Any

import pytest

from aioasuswrt import (
    AsusWrt,
    AuthConfig,
    ConnectionType,
    Device,
    Mode,
    Settings,
)
from tests.test_data import (
    ARP_DATA,
    ARP_DEVICES,
    CLIENTLIST_DATA,
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
    """Mocking the run_command method in AsusWrt."""
    count = 0

    async def patch_func(command: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal count
        print(f"Command: {command}\nwith args={args} and kwargs={kwargs}")
        try:
            count += 1
            print(count)
            return values[count - 1]
        except IndexError:
            print(
                f"Not enough elements in return list! Iteration {
                    count
                } while list is {len(values)}."
            )
            assert False

    mocker.patch(
        "aioasuswrt.connection.BaseConnection.run_command",
        side_effect=patch_func,
    )


@pytest.mark.asyncio
async def test_parse_with_empty_line(mocker: Any) -> None:
    """Testing _parse_lines where we get an empty line."""
    mock_run_cmd(mocker, [WL_MIISING_LINE])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    devices: dict[str, Device] = {}
    await scanner._get_wl(devices)
    assert devices == WL_DEVICES


@pytest.mark.asyncio
async def test_get_wl(mocker: Any) -> None:
    """Testing wl."""
    mock_run_cmd(mocker, [WL_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    devices: dict[str, Device] = {}
    await scanner._get_wl(devices)
    assert devices == WL_DEVICES


@pytest.mark.asyncio
async def test_get_wl_empty(mocker: Any) -> None:
    """Testing wl."""
    mock_run_cmd(mocker, [""])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    devices: dict[str, Device] = {}
    devices = await scanner._get_wl(devices)
    assert not devices


@pytest.mark.asyncio
async def test_get_leases(mocker: Any) -> None:
    """Testing leases."""
    mock_run_cmd(mocker, [LEASES_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    devices: dict[str, Device] = deepcopy(NEIGH_DEVICES)
    result = await scanner._get_leases(devices)
    assert result == LEASES_DEVICES


@pytest.mark.asyncio
async def test_get_arp(mocker: Any) -> None:
    """Testing arp."""
    mock_run_cmd(mocker, [ARP_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    devices: dict[str, Device] = deepcopy(WL_DEVICES)
    await scanner._get_arp(devices)
    assert devices == ARP_DEVICES


@pytest.mark.asyncio
async def test_get_neigh(mocker: Any) -> None:
    """Testing neigh."""
    mock_run_cmd(mocker, [NEIGH_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    devices: dict[str, Device] = deepcopy(ARP_DEVICES)
    await scanner._get_neigh(devices)
    assert devices == NEIGH_DEVICES


@pytest.mark.asyncio
async def test_get_connected_devices_ap(mocker: Any) -> None:
    """Test for get asuswrt_data in ap mode."""
    mock_run_cmd(mocker, [WL_DATA, ARP_DATA, NEIGH_DATA, CLIENTLIST_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
        settings=Settings(mode=Mode.AP, require_ip=False),
    )
    devices = await scanner.get_connected_devices()
    assert devices == WAKE_DEVICES_AP


@pytest.mark.asyncio
async def test_get_connected_devices_ap_no_ip(mocker: Any) -> None:
    """Test for get asuswrt_data and not requiring ip."""
    mock_run_cmd(mocker, [WL_DATA, ARP_DATA, NEIGH_DATA, CLIENTLIST_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
        settings=Settings(mode=Mode.AP, require_ip=False),
    )
    devices = await scanner.get_connected_devices()
    assert devices == WAKE_DEVICES_AP_NO_IP


@pytest.mark.asyncio
async def test_get_temperature(mocker: Any) -> None:
    """Test getting temperature."""
    mock_run_cmd(mocker, TEMP_DATA)
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
        settings=Settings(mode=Mode.AP),
    )
    data = await scanner.get_temperature()
    assert data == {"2.4GHz": 49.5, "5.0GHz": 54.5, "CPU": 77.0}

    mock_run_cmd(mocker, TEMP_DATA_2ND)
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    data = await scanner.get_temperature()
    assert data == {"2.4GHz": 0.0, "5.0GHz": 0.0, "CPU": 81.3}


@pytest.mark.asyncio
async def test_get_loadavg(mocker: Any) -> None:
    """Test getting loadavg."""
    mock_run_cmd(mocker, [LOADAVG_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    data = await scanner.get_loadavg()
    assert data == [0.23, 0.5, 0.68]


@pytest.mark.asyncio
async def test_get_interfaces_counts(mocker: Any) -> None:
    """Test getting loadavg."""
    mock_run_cmd(mocker, [NETDEV_DATA])
    scanner = AsusWrt(
        host="localhost",
        auth_config=AuthConfig(
            username="test",
            password="test",
            connection_type=ConnectionType.SSH,
            ssh_key=None,
            passphrase=None,
            port=2,
        ),
    )
    data = await scanner.get_interfaces_count()
    assert data == INTERFACES_COUNT
