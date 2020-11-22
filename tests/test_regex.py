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
    RX,
    RX_DATA,
    TEMP_DATA,
    TX,
    TX_DATA,
    WAKE_DEVICES_AP,
    WAKE_DEVICES_NO_IP,
    WL_DATA,
    WL_DEVICES,
)


def mock_run_cmd(mocker, values):
    iter = 0

    async def patch_func(command, *args, **kwargs):
        nonlocal iter
        iter = iter + 1
        try:
            return values[iter - 1]
        except IndexError:
            print(
                f"Not enough elements in return list! Iteration {iter} while list is {len(values)}."
            )
            assert False

    mocker.patch(
        "aioasuswrt.connection.SshConnection.async_run_command",
        side_effect=patch_func,
    )


@pytest.mark.asyncio
async def test_get_wl(event_loop, mocker):
    """Testing wl."""
    mock_run_cmd(mocker, [WL_DATA])
    scanner = AsusWrt(host="localhost", port=22)
    devices = await scanner.async_get_wl()
    assert WL_DEVICES == devices


@pytest.mark.asyncio
async def test_get_wl_empty(event_loop, mocker):
    """Testing wl."""
    mock_run_cmd(mocker, [""])
    scanner = AsusWrt(host="localhost", port=22)
    devices = await scanner.async_get_wl()
    assert {} == devices


@pytest.mark.asyncio
async def test_async_get_leases(event_loop, mocker):
    """Testing leases."""
    mock_run_cmd(mocker, [LEASES_DATA])
    scanner = AsusWrt(host="localhost", port=22)
    data = await scanner.async_get_leases(NEIGH_DEVICES.copy())
    print(f"{data=}")
    assert LEASES_DEVICES == data


@pytest.mark.asyncio
async def test_get_arp(event_loop, mocker):
    """Testing arp."""
    mock_run_cmd(mocker, [ARP_DATA])
    scanner = AsusWrt(host="localhost", port=22)
    data = await scanner.async_get_arp()
    assert ARP_DEVICES == data


@pytest.mark.asyncio
async def test_get_neigh(event_loop, mocker):
    """Testing neigh."""
    mock_run_cmd(mocker, [NEIGH_DATA])
    scanner = AsusWrt(host="localhost", port=22)
    data = await scanner.async_get_neigh(NEIGH_DEVICES.copy())
    assert NEIGH_DEVICES == data


@pytest.mark.asyncio
async def test_get_connected_devices_ap(event_loop, mocker):
    """Test for get asuswrt_data in ap mode."""
    # Note, unfortunately the order of data is important and should be the
    # same as in the `async_get_connected_devices` function.
    mock_run_cmd(mocker, [WL_DATA, ARP_DATA, NEIGH_DATA, LEASES_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=True)
    data = await scanner.async_get_connected_devices()
    assert WAKE_DEVICES_AP == data


@pytest.mark.asyncio
async def test_get_connected_devices_no_ip(event_loop, mocker):
    """Test for get asuswrt_data and not requiring ip."""
    mock_run_cmd(mocker, [WL_DATA, ARP_DATA, NEIGH_DATA, LEASES_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_connected_devices()
    assert WAKE_DEVICES_NO_IP == data


@pytest.mark.asyncio
async def test_get_packets_total(event_loop, mocker):
    """Test getting packet totals."""
    mock_run_cmd(mocker, [TX_DATA, RX_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_tx()
    assert TX == data
    data = await scanner.async_get_rx()
    assert RX == data


@pytest.mark.asyncio
async def test_async_get_temperature(event_loop, mocker):
    """Test getting temperature."""
    mock_run_cmd(mocker, [TEMP_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_temperature()
    assert data == {"2.4GHz": 49.5, "5.0GHz": 54.5, "CPU": 77.0}


@pytest.mark.asyncio
async def test_async_get_loadavg(event_loop, mocker):
    """Test getting loadavg."""
    mock_run_cmd(mocker, [LOADAVG_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_loadavg()
    assert data == [0.23, 0.5, 0.68]


@pytest.mark.asyncio
async def test_async_get_interfaces_counts(event_loop, mocker):
    """Test getting loadavg."""
    mock_run_cmd(mocker, [NETDEV_DATA])
    scanner = AsusWrt(host="localhost", port=22, mode="ap", require_ip=False)
    data = await scanner.async_get_interfaces_counts()
    assert data == INTERFACES_COUNT


# @pytest.mark.asyncio
# async def test_async_get_meminfo(event_loop, mocker):
#     """Test getting meminfo."""
#     mocker.patch(
#         'aioasuswrt.connection.SshConnection.async_run_command',
#         side_effect=cmd_mock)
#     scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=False)
#     data = await scanner.async_get_meminfo()
#     assert data == []
