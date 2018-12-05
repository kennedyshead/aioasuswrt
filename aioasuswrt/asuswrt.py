"""Moddule for Asuswrt."""
import inspect
import logging
import math
import re
from collections import namedtuple
from datetime import datetime

from aioasuswrt.connection import SshConnection, TelnetConnection
from aioasuswrt.helpers import convert_size

_LOGGER = logging.getLogger(__name__)

CHANGE_TIME_CACHE_DEFAULT = 5  # Default 60s

_LEASES_CMD = 'cat /var/lib/misc/dnsmasq.leases'
_LEASES_REGEX = re.compile(
    r'\w+\s' +
    r'(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))\s' +
    r'(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\s' +
    r'(?P<host>([^\s]+))')

# Command to get both 5GHz and 2.4GHz clients
_WL_CMD = 'for dev in `nvram get wl1_vifs && nvram get wl0_vifs && ' \
          'nvram get wl_ifnames`; do ' \
          'if type wlanconfig > /dev/null; then ' \
          'wlanconfig $dev list | awk \'FNR > 1 {print substr($1, 0, 18)}\';' \
          ' else wl -i $dev assoclist; fi; done'
_WL_REGEX = re.compile(
    r'\w+\s' +
    r'(?P<mac>(([0-9A-F]{2}[:-]){5}([0-9A-F]{2})))')

_IP_NEIGH_CMD = 'ip neigh'
_IP_NEIGH_REGEX = re.compile(
    r'(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3}|'
    r'([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{1,4}){1,7})\s'
    r'\w+\s'
    r'\w+\s'
    r'(\w+\s(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2}))))?\s'
    r'\s?(router)?'
    r'\s?(nud)?'
    r'(?P<status>(\w+))')

_ARP_CMD = 'arp -n'
_ARP_REGEX = re.compile(
    r'.+\s' +
    r'\((?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\)\s' +
    r'.+\s' +
    r'(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))' +
    r'\s' +
    r'.*')

_IFCONFIG_CMD = 'ifconfig eth0 |grep bytes'
_IFCONFIG_REGEX = re.compile(
    r'(?P<data>[\d]{4,})')

_IP_LINK_CMD = "ip -rc 1024 -s link"
_RX_COMMAND = 'cat /sys/class/net/eth0/statistics/rx_bytes'
_TX_COMMAND = 'cat /sys/class/net/eth0/statistics/tx_bytes'

Device = namedtuple('Device', ['mac', 'ip', 'name'])


async def _parse_lines(lines, regex):
    """Parse the lines using the given regular expression.

    If a line can't be parsed it is logged and skipped in the output.
    """
    results = []
    if inspect.iscoroutinefunction(lines):
        lines = await lines
    for line in lines:
        if line:
            match = regex.search(line)
            if not match:
                _LOGGER.debug("Could not parse row: %s", line)
                continue
            results.append(match.groupdict())
    return results


class AsusWrt:
    """This is the interface class."""

    def __init__(self, host, port, use_telnet=False, username=None,
                 password=None, ssh_key=None, mode='router', require_ip=False,
                 time_cache=CHANGE_TIME_CACHE_DEFAULT):
        """Init function."""
        self.require_ip = require_ip
        self.mode = mode
        self._rx_latest = None
        self._tx_latest = None
        self._latest_transfer_check = None
        self._cache_time = time_cache
        self._trans_cache_timer = None
        self._transfer_rates_cache = None
        self._latest_transfer_data = 0, 0

        if use_telnet:
            self.connection = TelnetConnection(
                host, port, username, password)
        else:
            self.connection = SshConnection(
                host, port, username, password, ssh_key)

    async def async_get_wl(self):
        lines = await self.connection.async_run_command(_WL_CMD)
        if not lines:
            return {}
        result = await _parse_lines(lines, _WL_REGEX)
        devices = {}
        for device in result:
            mac = device['mac'].upper()
            devices[mac] = Device(mac, None, None)
        return devices

    async def async_get_leases(self, cur_devices):
        lines = await self.connection.async_run_command(_LEASES_CMD)
        if not lines:
            return {}
        lines = [line for line in lines if not line.startswith('duid ')]
        result = await _parse_lines(lines, _LEASES_REGEX)
        devices = {}
        for device in result:
            # For leases where the client doesn't set a hostname, ensure it
            # is blank and not '*', which breaks entity_id down the line.
            host = device['host']
            if host == '*':
                host = ''
            mac = device['mac'].upper()
            if mac in cur_devices:
                devices[mac] = Device(mac, device['ip'], host)
        return devices

    async def async_get_neigh(self, cur_devices):
        lines = await self.connection.async_run_command(_IP_NEIGH_CMD)
        if not lines:
            return {}
        result = await _parse_lines(lines, _IP_NEIGH_REGEX)
        devices = {}
        for device in result:
            status = device['status']
            if status is None or status.upper() != 'REACHABLE':
                continue
            if device['mac'] is not None:
                mac = device['mac'].upper()
                old_device = cur_devices.get(mac)
                old_ip = old_device.ip if old_device else None
                devices[mac] = Device(mac, device.get('ip', old_ip), None)
        return devices

    async def async_get_arp(self):
        lines = await self.connection.async_run_command(_ARP_CMD)
        if not lines:
            return {}
        result = await _parse_lines(lines, _ARP_REGEX)
        devices = {}
        for device in result:
            if device['mac'] is not None:
                mac = device['mac'].upper()
                devices[mac] = Device(mac, device['ip'], None)
        return devices

    async def async_get_connected_devices(self):
        """Retrieve data from ASUSWRT.

        Calls various commands on the router and returns the superset of all
        responses. Some commands will not work on some routers.
        """
        devices = {}
        dev = await self.async_get_wl()
        devices.update(dev)
        dev = await self.async_get_arp()
        devices.update(dev)
        dev = await self.async_get_neigh(devices)
        devices.update(dev)
        if not self.mode == 'ap':
            dev = await self.async_get_leases(devices)
            devices.update(dev)

        ret_devices = {}
        for key in devices:
            if not self.require_ip or devices[key].ip is not None:
                ret_devices[key] = devices[key]
        return ret_devices

    async def async_get_packets_total(self, use_cache=True):
        """Retrieve total packets from ASUSWRT."""
        now = datetime.utcnow()
        if use_cache and self._trans_cache_timer and self._cache_time > \
                (now - self._trans_cache_timer).total_seconds():
            return self._transfer_rates_cache

        data = await self.connection.async_run_command(_IP_LINK_CMD)
        _LOGGER.debug(data)
        i = 0
        rx = 0
        tx = 0
        for line in data:
            if 'eth0' in line:
                rx = data[i+3].split(' ')[4]
                tx = data[i+5].split(' ')[4]
                break
            i += 1
        return int(rx), int(tx)

    async def async_get_rx(self, use_cache=True):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(_RX_COMMAND)
        return data

    async def async_get_tx(self, use_cache=True):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(_TX_COMMAND)
        return data

    async def async_get_current_transfer_rates(self, use_cache=True):
        """Gets current transfer rates calculated in per second in bytes."""
        now = datetime.utcnow()
        data = await self.async_get_packets_total(use_cache)
        if self._rx_latest is None or self._tx_latest is None:
            self._latest_transfer_check = now
            self._rx_latest = data[0]
            self._tx_latest = data[1]
            return self._latest_transfer_data

        time_diff = now - self._latest_transfer_check
        if time_diff.total_seconds() < 30:
            return self._latest_transfer_data

        if data[0] < self._rx_latest:
            rx = data[0]
        else:
            rx = data[0] - self._rx_latest
        if data[1] < self._tx_latest:
            tx = data[1]
        else:
            tx = data[1] - self._tx_latest
        self._latest_transfer_check = now

        self._rx_latest = data[0]
        self._tx_latest = data[1]

        self._latest_transfer_data = (
            math.ceil(rx / time_diff.total_seconds()) if rx > 0 else 0,
            math.ceil(tx / time_diff.total_seconds()) if tx > 0 else 0)
        return self._latest_transfer_data

    async def async_current_transfer_human_readable(
            self, use_cache=True):
        """Gets current transfer rates in a human readable format."""
        rx, tx = await self.async_get_current_transfer_rates(use_cache)

        return "%s/s" % convert_size(rx), "%s/s" % convert_size(tx)

    @property
    def is_connected(self):
        return self.connection.is_connected
