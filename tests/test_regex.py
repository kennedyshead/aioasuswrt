import asyncio
import pytest
from aioasuswrt.asuswrt import (AsusWrt, _LEASES_CMD, _WL_CMD, _IP_NEIGH_CMD,
                                _ARP_CMD, Device, _RX_COMMAND, _TX_COMMAND,
                                _TEMP_CMD, _LOADAVG_CMD, _MEMINFO_CMD,
                                _NETDEV_CMD)

RX_DATA = ["2703926881", ""]
TX_DATA = ["648110137", ""]

RX = 2703926881
TX = 648110137

TEMP_DATA = [
    '59 (0x3b)\r',
    '69 (0x45)\r',
    'CPU temperature	: 77'
]

NETDEV_DATA = [
    'nter-|   Receive                                                |  Transmit',
    ' face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed',
    '    lo: 129406077  639166    0    0    0     0          0         0 129406077  639166    0    0    0     0       0          0',
    '  ifb0:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0',
    '  ifb1:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0',
    '  fwd0:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0',
    '  fwd1:       0 32991574    0    0    0     0          0         0 2758131447 21323444    0    0    0     0       0          0',
    '   agg:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0',
    '  eth0: 1376394855 180111514    0    0    0     0          0         0 896208608 161258260    0    0    0     0       0          0',
    ' dpsta:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0',
    '  eth1: 240050447 1451957    0    0    0     0          0     47377 2112087504 43036729    0 26277918    0     0       0          0',
    '  eth2:       0       0    0    0    0     0          0         0 3283428721 33007901    0    2    0     0       0          0',
    ' vlan1: 35966691832 80394316    0    0    0     0          0     91875 29563557562 53006688    0    0    0     0       0          0',
    ' vlan2:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0',
    '   br0: 4643330713 15198823    0    0    0     0          0         0 5699827990 13109400    0    0    0     0       0          0',
    ' wl0.1: 72308780  385338    0    0    0     0          0      7706 311596615 4150488    0 199907    0     0       0          0',
    'ds0.1:       0       0    0    0    0     0          0         0 102404809  805208    0    0    0     0       0          0',
    ' tun21:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0'
]

INTERFACES_COUNT = {
    'lo': {'tx_bytes': 129406077, 'tx_packets': 639166, 'tx_errs': 0,
           'tx_drop': 0, 'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
           'tx_multicast': 0, 'rx_bytes': 129406077, 'rx_packets': 639166,
           'rx_errs': 0, 'rx_drop': 0, 'rx_fifo': 0, 'rx_colls': 0,
           'rx_carrier': 0, 'rx_compressed': 0},
    'ifb0': {'tx_bytes': 0, 'tx_packets': 0, 'tx_errs': 0, 'tx_drop': 0,
             'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
             'tx_multicast': 0,
             'rx_bytes': 0, 'rx_packets': 0, 'rx_errs': 0, 'rx_drop': 0,
             'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
             'rx_compressed': 0},
    'ifb1': {'tx_bytes': 0, 'tx_packets': 0, 'tx_errs': 0, 'tx_drop': 0,
             'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
             'tx_multicast': 0,
             'rx_bytes': 0, 'rx_packets': 0, 'rx_errs': 0, 'rx_drop': 0,
             'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
             'rx_compressed': 0},
    'fwd0': {'tx_bytes': 0, 'tx_packets': 0, 'tx_errs': 0, 'tx_drop': 0,
             'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
             'tx_multicast': 0,
             'rx_bytes': 0, 'rx_packets': 0, 'rx_errs': 0, 'rx_drop': 0,
             'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
             'rx_compressed': 0},
    'fwd1': {'tx_bytes': 0, 'tx_packets': 32991574, 'tx_errs': 0,
             'tx_drop': 0,
             'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
             'tx_multicast': 0,
             'rx_bytes': 2758131447, 'rx_packets': 21323444, 'rx_errs': 0,
             'rx_drop': 0, 'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
             'rx_compressed': 0},
    'agg': {'tx_bytes': 0, 'tx_packets': 0, 'tx_errs': 0, 'tx_drop': 0,
            'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
            'tx_multicast': 0,
            'rx_bytes': 0, 'rx_packets': 0, 'rx_errs': 0, 'rx_drop': 0,
            'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
            'rx_compressed': 0},
    'eth0': {'tx_bytes': 1376394855, 'tx_packets': 180111514, 'tx_errs': 0,
             'tx_drop': 0, 'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
             'tx_multicast': 0, 'rx_bytes': 896208608,
             'rx_packets': 161258260,
             'rx_errs': 0, 'rx_drop': 0, 'rx_fifo': 0, 'rx_colls': 0,
             'rx_carrier': 0, 'rx_compressed': 0},
    'dpsta': {'tx_bytes': 0, 'tx_packets': 0, 'tx_errs': 0, 'tx_drop': 0,
              'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
              'tx_multicast': 0,
              'rx_bytes': 0, 'rx_packets': 0, 'rx_errs': 0, 'rx_drop': 0,
              'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
              'rx_compressed': 0},
    'eth1': {'tx_bytes': 240050447, 'tx_packets': 1451957, 'tx_errs': 0,
             'tx_drop': 0, 'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
             'tx_multicast': 47377, 'rx_bytes': 2112087504,
             'rx_packets': 43036729, 'rx_errs': 0, 'rx_drop': 26277918,
             'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
             'rx_compressed': 0},
    'eth2': {'tx_bytes': 0, 'tx_packets': 0, 'tx_errs': 0, 'tx_drop': 0,
             'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
             'tx_multicast': 0,
             'rx_bytes': 3283428721, 'rx_packets': 33007901, 'rx_errs': 0,
             'rx_drop': 2, 'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
             'rx_compressed': 0},
    'vlan1': {'tx_bytes': 35966691832, 'tx_packets': 80394316,
              'tx_errs': 0,
              'tx_drop': 0, 'tx_fifo': 0, 'tx_frame': 0,
              'tx_compressed': 0,
              'tx_multicast': 91875, 'rx_bytes': 29563557562,
              'rx_packets': 53006688, 'rx_errs': 0, 'rx_drop': 0,
              'rx_fifo': 0,
              'rx_colls': 0, 'rx_carrier': 0, 'rx_compressed': 0},
    'vlan2': {'tx_bytes': 0, 'tx_packets': 0, 'tx_errs': 0, 'tx_drop': 0,
              'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
              'tx_multicast': 0,
              'rx_bytes': 0, 'rx_packets': 0, 'rx_errs': 0, 'rx_drop': 0,
              'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
              'rx_compressed': 0},
    'br0': {'tx_bytes': 4643330713, 'tx_packets': 15198823, 'tx_errs': 0,
            'tx_drop': 0, 'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
            'tx_multicast': 0, 'rx_bytes': 5699827990,
            'rx_packets': 13109400,
            'rx_errs': 0, 'rx_drop': 0, 'rx_fifo': 0, 'rx_colls': 0,
            'rx_carrier': 0, 'rx_compressed': 0},
    'wl0.1': {'tx_bytes': 72308780, 'tx_packets': 385338, 'tx_errs': 0,
              'tx_drop': 0, 'tx_fifo': 0, 'tx_frame': 0,
              'tx_compressed': 0,
              'tx_multicast': 7706, 'rx_bytes': 311596615,
              'rx_packets': 4150488,
              'rx_errs': 0, 'rx_drop': 199907, 'rx_fifo': 0, 'rx_colls': 0,
              'rx_carrier': 0, 'rx_compressed': 0},
    'ds0.1': {'tx_bytes': 0, 'tx_packets': 0, 'tx_errs': 0, 'tx_drop': 0,
              'tx_fifo': 0, 'tx_frame': 0, 'tx_compressed': 0,
              'tx_multicast': 0,
              'rx_bytes': 102404809, 'rx_packets': 805208, 'rx_errs': 0,
              'rx_drop': 0, 'rx_fifo': 0, 'rx_colls': 0, 'rx_carrier': 0,
              'rx_compressed': 0}
}

LOADAVG_DATA = [
    '0.23 0.50 0.68 2/167 13095'
]

MEMINFO_DATA = [
    '0.46 0.75 0.77 1/165 2609'
]

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
    print(command, *args, **kwargs)
    f = asyncio.Future()
    if command == _WL_CMD:
        f.set_result(WL_DATA)
        return f
    if command == _LEASES_CMD.format('/var/lib/misc'):
        f.set_result(LEASES_DATA)
        return f
    if command == _IP_NEIGH_CMD:
        f.set_result(NEIGH_DATA)
        return f
    if command == _ARP_CMD:
        f.set_result(ARP_DATA)
        return f
    if command == _RX_COMMAND.format('eth0'):
        f.set_result(RX_DATA)
        return f
    if command == _TX_COMMAND.format('eth0'):
        f.set_result(TX_DATA)
        return f
    if command == _TEMP_CMD:
        f.set_result(TEMP_DATA)
        return f
    if command == _LOADAVG_CMD:
        f.set_result(LOADAVG_DATA)
        return f
    if command == _MEMINFO_CMD:
        f.set_result(MEMINFO_DATA)
        return f
    if command == _NETDEV_CMD:
        f.set_result(NETDEV_DATA)
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


@pytest.mark.asyncio
async def test_async_get_temperature(event_loop, mocker):
    """Test getting temperature."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=False)
    data = await scanner.async_get_temperature()
    assert data == {'2.4GHz': 49.5, '5.0GHz': 54.5, 'CPU': 77.0}


@pytest.mark.asyncio
async def test_async_get_loadavg(event_loop, mocker):
    """Test getting loadavg."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=False)
    data = await scanner.async_get_loadavg()
    assert data == [0.23, 0.5, 0.68]


@pytest.mark.asyncio
async def test_async_get_interfaces_counts(event_loop, mocker):
    """Test getting loadavg."""
    mocker.patch(
        'aioasuswrt.connection.SshConnection.async_run_command',
        side_effect=RunCommandMock)
    scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=False)
    data = await scanner.async_get_interfaces_counts()
    assert data == INTERFACES_COUNT

# @pytest.mark.asyncio
# async def test_async_get_meminfo(event_loop, mocker):
#     """Test getting meminfo."""
#     mocker.patch(
#         'aioasuswrt.connection.SshConnection.async_run_command',
#         side_effect=RunCommandMock)
#     scanner = AsusWrt(host="localhost", port=22, mode='ap', require_ip=False)
#     data = await scanner.async_get_meminfo()
#     assert data == []
