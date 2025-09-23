import pytest

from aioasuswrt.asuswrt import AsusWrt

from .test_data import (
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
    WAKE_DEVICES_NO_IP,
    WL_DATA,
    WL_DEVICES,
)


def mock_run_cmd(mocker, values) -> None:
    iter = 0

    async def patch_func(command, *args, **kwargs):
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
        "aioasuswrt.connection.SshConnection.async_run_command",
        side_effect=patch_func,
    )


@pytest.mark.asyncio
async def test_get_wl(mocker) -> None:
    """Testing wl."""
    mock_run_cmd(mocker, [WL_DATA])
    scanner = AsusWrt(host="localhost", port=22)
    devices = {}
    await scanner.async_get_wl(devices)
    assert WL_DEVICES.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in WL_DEVICES.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_wl_empty(mocker) -> None:
    """Testing wl."""
    mock_run_cmd(mocker, [""])
    scanner = AsusWrt(host="localhost", port=22)
    devices = {}
    await scanner.async_get_wl(devices)
    assert {} == devices


@pytest.mark.asyncio
async def test_async_get_leases(mocker) -> None:
    """Testing leases."""
    mock_run_cmd(mocker, [LEASES_DATA])
    scanner = AsusWrt(host="localhost", port=22)
    devices = NEIGH_DEVICES.copy()
    await scanner.async_get_leases(devices)
    assert LEASES_DEVICES.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in LEASES_DEVICES.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_arp(mocker) -> None:
    """Testing arp."""
    mock_run_cmd(mocker, [ARP_DATA])
    scanner = AsusWrt(host="localhost", port=22)
    devices = {}
    await scanner.async_get_arp(devices)
    assert ARP_DEVICES.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in ARP_DEVICES.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_neigh(mocker) -> None:
    """Testing neigh."""
    mock_run_cmd(mocker, [NEIGH_DATA])
    scanner = AsusWrt(host="localhost", port=22)
    devices = NEIGH_DEVICES.copy()
    await scanner.async_get_neigh(devices)
    assert NEIGH_DEVICES == devices


@pytest.mark.asyncio
async def test_get_connected_devices_ap(mocker) -> None:
    """Test for get asuswrt_data in ap mode."""
    # Note, unfortunately the order of data is important and should be the
    # same as in the `async_get_connected_devices` function.
    mock_run_cmd(mocker, [WL_DATA, ARP_DATA, NEIGH_DATA, LEASES_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=True)
    devices = await scanner.async_get_connected_devices()
    assert WAKE_DEVICES_AP.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [value.to_tuple() for value in WAKE_DEVICES_AP.values()]
    assert values == compare_values


@pytest.mark.asyncio
async def test_get_connected_devices_no_ip(mocker):
    """Test for get asuswrt_data and not requiring ip."""
    mock_run_cmd(mocker, [WL_DATA, ARP_DATA, NEIGH_DATA, LEASES_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    devices = await scanner.async_get_connected_devices()
    assert WAKE_DEVICES_NO_IP.keys() == devices.keys()
    values = [value.to_tuple() for value in devices.values()]
    compare_values = [
        value.to_tuple() for value in WAKE_DEVICES_NO_IP.values()
    ]
    assert values == compare_values


@pytest.mark.asyncio
async def test_async_get_temperature(mocker):
    """Test getting temperature."""
    mock_run_cmd(mocker, TEMP_DATA)
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_temperature()
    assert data == {"2.4GHz": 49.5, "5.0GHz": 54.5, "CPU": 77.0}

    mock_run_cmd(mocker, TEMP_DATA_2ND)
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_temperature()
    assert data == {"2.4GHz": 0.0, "5.0GHz": 0.0, "CPU": 81.3}


@pytest.mark.asyncio
async def test_async_get_loadavg(mocker):
    """Test getting loadavg."""
    mock_run_cmd(mocker, [LOADAVG_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_loadavg()
    assert data == [0.23, 0.5, 0.68]


@pytest.mark.asyncio
async def test_async_get_interfaces_counts(mocker):
    """Test getting loadavg."""
    mock_run_cmd(mocker, [NETDEV_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_interfaces_counts()
    assert data == INTERFACES_COUNT


# @pytest.mark.asyncio
# async def test_async_get_meminfo():
#     """Test getting meminfo."""
#     mocker.patch(
#         'aioasuswrt.connection.SshConnection.async_run_command',
#         side_effect=cmd_mock)
#     scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=False)
#     data = await scanner.async_get_meminfo()
#     assert data == []
