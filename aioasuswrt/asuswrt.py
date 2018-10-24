"""Moddule for Asuswrt."""
import logging
import re
from collections import namedtuple

from aioasuswrt.connection import SshConnection, TelnetConnection

_LOGGER = logging.getLogger(__name__)

_LEASES_CMD = 'cat /var/lib/misc/dnsmasq.leases'
_LEASES_REGEX = re.compile(
    r'\w+\s' +
    r'(?P<mac>(([0-9a-f]{2}[:-]){5}([0-9a-f]{2})))\s' +
    r'(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\s' +
    r'(?P<host>([^\s]+))')

# Command to get both 5GHz and 2.4GHz clients
_WL_CMD = 'for dev in `nvram get wl_ifnames`; do wl -i $dev assoclist; done'
_WL_REGEX = re.compile(
    r'\w+\s' +
    r'(?P<mac>(([0-9A-F]{2}[:-]){5}([0-9A-F]{2})))')

_IP_NEIGH_CMD = 'ip neigh'
_IP_NEIGH_REGEX = re.compile(
    r'(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3}|'
    r'([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{1,4}){1,7})\s'
    r'\w+\s'
    r'\w+\s'
    r'(\w+\s(?P<mac>(([0-9a-f]{2}[:-]){5}([0-9a-f]{2}))))?\s'
    r'\s?(router)?'
    r'\s?(nud)?'
    r'(?P<status>(\w+))')

_ARP_CMD = 'arp -n'
_ARP_REGEX = re.compile(
    r'.+\s' +
    r'\((?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\)\s' +
    r'.+\s' +
    r'(?P<mac>(([0-9a-f]{2}[:-]){5}([0-9a-f]{2})))' +
    r'\s' +
    r'.*')

_IFCONFIG_CMD = 'ifconfig eth0 |grep bytes'
_IFCONFIG_REGEX = re.compile(
    r'(?P<data>[\d]{4,})')
Device = namedtuple('Device', ['mac', 'ip', 'name'])


def _parse_lines(lines, regex):
    """Parse the lines using the given regular expression.

    If a line can't be parsed it is logged and skipped in the output.
    """
    results = []
    for line in lines:
        match = regex.search(line)
        if not match:
            _LOGGER.debug("Could not parse row: %s", line)
            continue
        results.append(match.groupdict())
    return results


class AsusWrt:
    """This is the interface class."""

    def __init__(self, host, port, use_telnet=False, username=None,
                 password=None, ssh_key=None, mode='router', require_ip=False):
        """Init function."""
        self.require_ip = require_ip
        self.mode = mode
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
        result = _parse_lines(lines, _WL_REGEX)
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
        result = _parse_lines(lines, _LEASES_REGEX)
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
        result = _parse_lines(lines, _IP_NEIGH_REGEX)
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
        result = _parse_lines(lines, _ARP_REGEX)
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
        devices.update(await self.async_get_wl())
        devices.update(await self.async_get_arp())
        devices.update(await self.async_get_neigh(devices))
        if not self.mode == 'ap':
            devices.update(await self.async_get_leases(devices))

        ret_devices = {}
        for key in devices:
            if not self.require_ip or devices[key].ip is not None:
                ret_devices[key] = devices[key]
        return ret_devices

    async def async_get_packets_total(self):
        """Retrieve total packets from ASUSWRT."""
        data = await self.connection.async_run_command(_IFCONFIG_CMD)
        result = _IFCONFIG_REGEX.findall(data[0])
        return result
