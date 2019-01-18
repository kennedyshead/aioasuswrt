import asyncio
import pytest
from aioasuswrt.asuswrt import (AsusWrt, _LEASES_CMD, _WL_CMD, _IP_NEIGH_CMD,
                                _ARP_CMD, Device, _RX_COMMAND, _TX_COMMAND)

RX_DATA = ["2703926881", ""]
TX_DATA = ["648110137", ""]

RX = 2703926881
TX = 648110137

WL_DATA = [
    'assoclist 01:02:03:04:06:08\r',
    'assoclist 08:09:10:11:12:14\r',
    'assoclist 08:09:10:11:12:15\r',
    'assoclist AB:CD:DE:AB:CD:EF\r'
]

WL_DEVICES = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip=None, name=None),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip=None, name=None),
    '08:09:10:11:12:15': Device(
        mac='08:09:10:11:12:15', ip=None, name=None),
    'AB:CD:DE:AB:CD:EF': Device(
        mac='AB:CD:DE:AB:CD:EF', ip=None, name=None)
}

ARP_DATA = [
    '? (123.123.123.125) at 01:02:03:04:06:08 [ether]  on eth0\r',
    '? (123.123.123.126) at 08:09:10:11:12:14 [ether]  on br0\r',
    '? (123.123.123.128) at AB:CD:DE:AB:CD:EF [ether]  on br0\r',
    '? (123.123.123.127) at <incomplete>  on br0\r',
    '? (172.16.10.2) at 00:25:90:12:2D:90 [ether]  on br0\r',
]

ARP_DEVICES = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name=None),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=None),
    'AB:CD:DE:AB:CD:EF': Device(
        mac='AB:CD:DE:AB:CD:EF', ip='123.123.123.128', name=None),
    '00:25:90:12:2D:90': Device(
        mac='00:25:90:12:2D:90', ip='172.16.10.2', name=None)
}

NEIGH_DATA = [
    '123.123.123.125 dev eth0 lladdr 01:02:03:04:06:08 REACHABLE\r',
    '123.123.123.126 dev br0 lladdr 08:09:10:11:12:14 REACHABLE\r',
    '123.123.123.128 dev br0 lladdr ab:cd:de:ab:cd:ef REACHABLE\r',
    '123.123.123.127 dev br0  FAILED\r',
    '123.123.123.129 dev br0 lladdr 08:09:15:15:15:15 DELAY\r',
    'fe80::feff:a6ff:feff:12ff dev br0 lladdr fc:ff:a6:ff:12:ff STALE\r',
]

NEIGH_DEVICES = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name=None),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=None),
    'AB:CD:DE:AB:CD:EF': Device(
        mac='AB:CD:DE:AB:CD:EF', ip='123.123.123.128', name=None)
}

LEASES_DATA = [
    '51910 01:02:03:04:06:08 123.123.123.125 TV 01:02:03:04:06:08\r',
    '79986 01:02:03:04:06:10 123.123.123.127 android 01:02:03:04:06:15\r',
    '23523 08:09:10:11:12:14 123.123.123.126 * 08:09:10:11:12:14\r',
]

LEASES_DEVICES = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name='TV'),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name='')
}

WAKE_DEVICES = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name='TV'),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=''),
    '00:25:90:12:2D:90': Device(
        mac='00:25:90:12:2D:90', ip='172.16.10.2', name=None)
}

WAKE_DEVICES_AP = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name=None),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=None),
    'AB:CD:DE:AB:CD:EF': Device(
        mac='AB:CD:DE:AB:CD:EF', ip='123.123.123.128', name=None),
    '00:25:90:12:2D:90': Device(
        mac='00:25:90:12:2D:90', ip='172.16.10.2', name=None)
}

WAKE_DEVICES_NO_IP = {
    '01:02:03:04:06:08': Device(
        mac='01:02:03:04:06:08', ip='123.123.123.125', name=None),
    '08:09:10:11:12:14': Device(
        mac='08:09:10:11:12:14', ip='123.123.123.126', name=None),
    '08:09:10:11:12:15': Device(
        mac='08:09:10:11:12:15', ip=None, name=None),
    'AB:CD:DE:AB:CD:EF': Device(
        mac='AB:CD:DE:AB:CD:EF', ip='123.123.123.128', name=None),
    '00:25:90:12:2D:90': Device(
        mac='00:25:90:12:2D:90', ip='172.16.10.2', name=None)
}


def RunCommandMock(command, *args, **kwargs):
    f = asyncio.Future()
    if command == _WL_CMD:
        f.set_result(WL_DATA)
        return f
    if command == _LEASES_CMD:
        f.set_result(LEASES_DATA)
        return f
    if command == _IP_NEIGH_CMD:
        f.set_result(NEIGH_DATA)
        return f
    if command == _ARP_CMD:
        f.set_result(ARP_DATA)
        return f
    if command == _RX_COMMAND:
        f.set_result(RX_DATA)
        return f
    if command == _TX_COMMAND:
        f.set_result(TX_DATA)
        return f
    raise Exception("Unhandled command: %s" % command)


def RunCommandEmptyMock(command, *args, **kwargs):
    f = asyncio.Future()
    f.set_result("")
    return f


@pytest.mark.asyncio
async def test_get_wl(event_loop, mocker):
    """Testing wl."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22)
    devices = await scanner.async_get_wl()
    assert WL_DEVICES == devices


@pytest.mark.asyncio
async def test_get_wl_empty(event_loop, mocker):
    """Testing wl."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandEmptyMock)
    scanner = AsusWrt(host="localhost", port=22)
    devices = await scanner.async_get_wl()
    assert {} == devices


@pytest.mark.asyncio
async def test_async_get_leases(event_loop, mocker):
    """Testing leases."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22)
    data = await scanner.async_get_leases(NEIGH_DEVICES.copy())
    assert LEASES_DEVICES == data


@pytest.mark.asyncio
async def test_get_arp(event_loop, mocker):
    """Testing arp."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22)
    data = await scanner.async_get_arp()
    assert ARP_DEVICES == data


@pytest.mark.asyncio
async def test_get_neigh(event_loop, mocker):
    """Testing neigh."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22)
    data = await scanner.async_get_neigh(NEIGH_DEVICES.copy())
    assert NEIGH_DEVICES == data


@pytest.mark.asyncio
async def test_get_connected_devices_ap(event_loop, mocker):
    """Test for get asuswrt_data in ap mode."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=True)
    data = await scanner.async_get_connected_devices()
    assert WAKE_DEVICES_AP == data


@pytest.mark.asyncio
async def test_get_connected_devices_no_ip(event_loop, mocker):
    """Test for get asuswrt_data and not requiring ip."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=False)
    data = await scanner.async_get_connected_devices()
    assert WAKE_DEVICES_NO_IP == data


@pytest.mark.asyncio
async def test_get_packets_total(event_loop, mocker):
    """Test getting packet totals."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=False)
    data = await scanner.async_get_tx()
    assert TX == data
    data = await scanner.async_get_rx()
    assert RX == data
