"""Module for Asuswrt."""
import asyncio
import inspect
import logging
import math
import re
from collections import namedtuple
from datetime import datetime

from aioasuswrt.connection import SshConnection, TelnetConnection
from aioasuswrt.helpers import convert_size

_LOGGER = logging.getLogger(__name__)

CHANGE_TIME_CACHE_DEFAULT = 5  # Default 5s

_LEASES_CMD = 'cat {}/dnsmasq.leases'
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

_RX_COMMAND = 'cat /sys/class/net/{}/statistics/rx_bytes'
_TX_COMMAND = 'cat /sys/class/net/{}/statistics/tx_bytes'

GET_LIST = {
    "DHCP": [
        "dhcp_dns1_x",
        "dhcp_dns2_x",
        "dhcp_enable_x",
        "dhcp_start",
        "dhcp_end",
        "dhcp_lease"
    ],
    "MODEL": ["model"],
    "QOS": [
        "qos_ack",
        "qos_atm",
        "qos_burst0",
        "qos_burst1",
        "qos_default",
        "qos_enable",
        "qos_fin",
        "qos_ibw",
        "qos_ibw1",
        "qos_icmp",
        "qos_irates",
        "qos_method",
        "qos_obw",
        "qos_obw1",
        "qos_orules",
        "qos_overhead",
        "qos_reset",
        "qos_rst",
        "qos_sched",
        "qos_sticky",
        "qos_syn",
        "qos_type"
    ],
    "REBOOT": [
        "reboot_schedule",
        "reboot_schedule_enable",
        "reboot_time"
    ],
    "WANS": [
        "link_internet",
        "wan_unit",
        "wans_cap",
        "wans_dualwan",
        "wans_lanport",
        "wans_lb_ratio",
        "wans_mode",
        "wans_routing_enable",
        "wans_standby",
    ],
    "WAN0": [
        "wan0_auxstate_t",
        "wan0_dns",
        "wan0_dns1_x",
        "wan0_dns2_x",
        "wan0_dnsenable_x",
        "wan0_enable",
        "wan0_gateway",
        "wan0_ipaddr",
        "wan0_is_usb_modem_ready",
        "wan0_primary",
        "wan0_sbstate_t",
        "wan0_state_t",
        "wan0_unit",
    ],
    "WAN1": [
        "wan1_auxstate_t",
        "wan1_dns",
        "wan1_dns1_x",
        "wan1_dns2_x",
        "wan1_dnsenable_x",
        "wan1_enable",
        "wan1_gateway",
        "wan1_ipaddr",
        "wan1_is_usb_modem_ready",
        "wan1_primary",
        "wan1_sbstate_t",
        "wan1_state_t",
        "wan1_unit",
    ],
    "WLAN": [
        "wan_dns",
        "wan_domain",
        "wan_enable",
        "wan_expires",
        "wan_gateway",
        "wan_ipaddr",
        "wan_lease",
        "wan_mtu",
        "wan_realip_ip",
        "wan_realip_state"
    ],
    "2G_GUEST_1": [
        "wl0.1_bss_enabled",
        "wl0.1_lanaccess",
        "wl0.1_ssid",
        "wl0.1_wpa_psk"
    ],
    "2G_GUEST_2": [
        "wl0.2_bss_enabled",
        "wl0.2_lanaccess",
        "wl0.2_ssid",
        "wl0.2_wpa_psk"
    ],
    "2G_GUEST_3": [
        "wl0.3_bss_enabled",
        "wl0.3_lanaccess",
        "wl0.3_ssid",
        "wl0.3_wpa_psk"
    ],
    "2G_WIFI": [
        "wl0_bss_enabled",
        "wl0_chanspec",
        "wl0_ssid",
        "wl0_wpa_psk"
    ],
    "5G_GUEST_1": [
        "wl1.1_bss_enabled",
        "wl1.1_lanaccess",
        "wl1.1_ssid",
        "wl1.1_wpa_psk"
    ],
    "5G_GUEST_2": [
        "wl1.2_bss_enabled",
        "wl1.2_lanaccess",
        "wl1.2_ssid",
        "wl1.2_wpa_psk"
    ],
    "5G_GUEST_3": [
        "wl1.3_bss_enabled",
        "wl1.3_lanaccess",
        "wl1.3_ssid",
        "wl1.3_wpa_psk"
    ],
    "5G_WIFI": [
        "wl1_bss_enabled",
        "wl1_chanspec",
        "wl1_ssid",
        "wl1_wpa_psk"
    ],
    "FIRMWARE": [
        "buildinfo",
        "buildno",
        "buildno_org",
        "firmver",
        "firmware_check",
        "firmware_check_enable",
        "firmware_path",
        "firmware_server",
        "webs_last_info",
        "webs_notif_flag",
        "webs_state_REQinfo",
        "webs_state_error",
        "webs_state_flag",
        "webs_state_odm",
        "webs_state_update",
        "webs_state_upgrade",
        "webs_state_url"
    ]
}

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

    def __init__(self, host, port=None, use_telnet=False, username=None,
                 password=None, ssh_key=None, mode='router', require_ip=False,
                 time_cache=CHANGE_TIME_CACHE_DEFAULT, interface='eth0',
                 dnsmasq='/var/lib/misc'):
        """Init function."""
        self.require_ip = require_ip
        self.mode = mode
        self._rx_latest = None
        self._tx_latest = None
        self._latest_transfer_check = None
        self._cache_time = time_cache
        self._trans_cache_timer = None
        self._dev_cache_timer = None
        self._devices_cache = None
        self._transfer_rates_cache = None
        self._latest_transfer_data = 0, 0
        self.interface = interface
        self.dnsmasq = dnsmasq

        if use_telnet:
            self.connection = TelnetConnection(
                host, port, username, password)
        else:
            self.connection = SshConnection(
                host, port, username, password, ssh_key)

    async def async_get_nvram(self, toGet):
        data = {}
        if toGet in GET_LIST:
            lines = await self.connection.async_run_command('nvram show')
            for item in GET_LIST[toGet]:
                regex = rf"{item}=([\w.\-/: ]+)"
                for line in lines:
                    result = re.findall(regex, line)
                    if result:
                        data[item] = result[0]
                        break
        return data

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
        lines = await self.connection.async_run_command(
            _LEASES_CMD.format(self.dnsmasq))
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

    async def async_get_connected_devices(self, use_cache=True):
        """Retrieve data from ASUSWRT.

        Calls various commands on the router and returns the superset of all
        responses. Some commands will not work on some routers.
        """
        now = datetime.utcnow()
        if use_cache and self._dev_cache_timer and self._cache_time > \
                (now - self._dev_cache_timer).total_seconds():
            return self._devices_cache

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

        self._devices_cache = ret_devices
        self._dev_cache_timer = now
        return ret_devices

    async def async_get_bytes_total(self, use_cache=True):
        """Retrieve total bytes (rx an tx) from ASUSWRT."""
        now = datetime.utcnow()
        if use_cache and self._trans_cache_timer and self._cache_time > \
                (now - self._trans_cache_timer).total_seconds():
            return self._transfer_rates_cache

        rx = await self.async_get_rx()
        tx = await self.async_get_tx()
        return rx, tx

    async def async_get_rx(self):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(
            _RX_COMMAND.format(self.interface))
        return float(data[0]) if data[0] != '' else None

    async def async_get_tx(self):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(
            _TX_COMMAND.format(self.interface))
        return float(data[0]) if data[0] != '' else None

    async def async_get_current_transfer_rates(self, use_cache=True):
        """Gets current transfer rates calculated in per second in bytes."""
        now = datetime.utcnow()
        data = await self.async_get_bytes_total(use_cache)
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
    
    async def async_get_wan(self):
        """Gets status parameters relating to WAN"""
        values = await asyncio.gather(
            self.async_get_nvram("WANS"),
            self.async_get_nvram("WAN0"),
            self.async_get_nvram("WAN1"),
        )
        return {
            "wans": values[0],
            "wan0": values[1],
            "wan1": values[2],
        }

    async def async_get_supported_functions(self):
        """Gets comma seperated list of router supported functions"""
        fn = await self.async_get_nvram("SUPPORT")
        return fn.get("rc_support", "").split()

    @property
    def is_connected(self):
        return self.connection.is_connected
