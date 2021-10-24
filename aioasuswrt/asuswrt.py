"""Module for Asuswrt."""
import inspect
import json
import logging
import math
import re
from collections import namedtuple
from datetime import datetime

from aioasuswrt.connection import SshConnection, TelnetConnection
from aioasuswrt.helpers import convert_size

_LOGGER = logging.getLogger(__name__)

CHANGE_TIME_CACHE_DEFAULT = 5  # Default 5s

_LEASES_CMD = "cat {}/dnsmasq.leases"
_LEASES_REGEX = re.compile(
    r"\w+\s"
    r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))\s"
    r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\s"
    r"(?P<host>([^\s]+))"
)

# Command to get both 5GHz and 2.4GHz clients
_WL_CMD = (
    "for dev in `nvram get wl1_vifs && nvram get wl0_vifs && "
    "nvram get wl_ifnames`; do "
    "if type wlanconfig > /dev/null; then "
    "wlanconfig $dev list | awk 'FNR > 1 {print substr($1, 0, 18)}';"
    " else wl -i $dev assoclist; fi; done"
)
_WL_REGEX = re.compile(r"\w+\s" r"(?P<mac>(([0-9A-F]{2}[:-]){5}([0-9A-F]{2})))")

_CLIENTLIST_CMD = 'cat /tmp/clientlist.json'

_NVRAM_CMD = "nvram show"

_IP_NEIGH_CMD = "ip neigh"
_IP_NEIGH_REGEX = re.compile(
    r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3}|"
    r"([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{1,4}){1,7})\s"
    r"\w+\s"
    r"\w+\s"
    r"(\w+\s(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2}))))?\s"
    r"\s?(router)?"
    r"\s?(nud)?"
    r"(?P<status>(\w+))"
)

_ARP_CMD = "arp -n"
_ARP_REGEX = re.compile(
    r".+\s"
    r"\((?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\)\s"
    r".+\s"
    r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))"
    r"\s"
    r".*"
)

_RX_COMMAND = "cat /sys/class/net/{}/statistics/rx_bytes"
_TX_COMMAND = "cat /sys/class/net/{}/statistics/tx_bytes"

_MEMINFO_CMD = "cat /proc/meminfo"
_LOADAVG_CMD = "cat /proc/loadavg"
_ADDHOST_CMD = (
    'cat /etc/hosts | grep -q "{ipaddress} {hostname}" || '
    '(echo "{ipaddress} {hostname}" >> /etc/hosts && '
    "kill -HUP `cat /var/run/dnsmasq.pid`)"
)

_NETDEV_CMD = "cat /proc/net/dev"
_NETDEV_FIELDS = [
    "tx_bytes",
    "tx_packets",
    "tx_errs",
    "tx_drop",
    "tx_fifo",
    "tx_frame",
    "tx_compressed",
    "tx_multicast",
    "rx_bytes",
    "rx_packets",
    "rx_errs",
    "rx_drop",
    "rx_fifo",
    "rx_colls",
    "rx_carrier",
    "rx_compressed",
]

_TEMP_RADIO_EVAL = " / 2 + 20"
_TEMP_24_CMDS = [
    {"cmd": "wl -i eth1 phy_tempsense", "result_loc": 0, "eval": _TEMP_RADIO_EVAL},
    {"cmd": "wl -i eth5 phy_tempsense", "result_loc": 0, "eval": _TEMP_RADIO_EVAL}
]
_TEMP_5_CMDS = [
    {"cmd": "wl -i eth2 phy_tempsense", "result_loc": 0, "eval": _TEMP_RADIO_EVAL},
    {"cmd": "wl -i eth6 phy_tempsense", "result_loc": 0, "eval": _TEMP_RADIO_EVAL}
]
_TEMP_CPU_CMDS = [
    {"cmd": "head -c20 /proc/dmu/temperature", "result_loc": 2, "eval": ""},
    {"cmd": "head -c5 /sys/class/thermal/thermal_zone0/temp", "result_loc": 0, "eval": " / 1000"}
]
_TEMP_CMDS = [_TEMP_24_CMDS, _TEMP_5_CMDS, _TEMP_CPU_CMDS]

GET_LIST = {
    "DHCP": [
        "dhcp_dns1_x",
        "dhcp_dns2_x",
        "dhcp_enable_x",
        "dhcp_start",
        "dhcp_end",
        "dhcp_lease",
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
        "qos_type",
    ],
    "REBOOT": ["reboot_schedule", "reboot_schedule_enable", "reboot_time"],
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
        "wan_realip_state",
    ],
    "2G_GUEST_1": [
        "wl0.1_bss_enabled",
        "wl0.1_lanaccess",
        "wl0.1_ssid",
        "wl0.1_wpa_psk",
    ],
    "2G_GUEST_2": [
        "wl0.2_bss_enabled",
        "wl0.2_lanaccess",
        "wl0.2_ssid",
        "wl0.2_wpa_psk",
    ],
    "2G_GUEST_3": [
        "wl0.3_bss_enabled",
        "wl0.3_lanaccess",
        "wl0.3_ssid",
        "wl0.3_wpa_psk",
    ],
    "2G_WIFI": ["wl0_bss_enabled", "wl0_chanspec", "wl0_ssid", "wl0_wpa_psk"],
    "5G_GUEST_1": [
        "wl1.1_bss_enabled",
        "wl1.1_lanaccess",
        "wl1.1_ssid",
        "wl1.1_wpa_psk",
    ],
    "5G_GUEST_2": [
        "wl1.2_bss_enabled",
        "wl1.2_lanaccess",
        "wl1.2_ssid",
        "wl1.2_wpa_psk",
    ],
    "5G_GUEST_3": [
        "wl1.3_bss_enabled",
        "wl1.3_lanaccess",
        "wl1.3_ssid",
        "wl1.3_wpa_psk",
    ],
    "5G_WIFI": ["wl1_bss_enabled", "wl1_chanspec", "wl1_ssid", "wl1_wpa_psk"],
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
        "webs_state_url",
    ],
    "LABEL_MAC": ["label_mac"],
}

Device = namedtuple("Device", ["mac", "ip", "name"])


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

    def __init__(
        self,
        host,
        port=None,
        use_telnet=False,
        username=None,
        password=None,
        ssh_key=None,
        mode="router",
        require_ip=False,
        time_cache=CHANGE_TIME_CACHE_DEFAULT,
        interface="eth0",
        dnsmasq="/var/lib/misc",
    ):
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
        self._nvram_cache_timer = None
        self._nvram_cache = None
        self._temps_commands = [None, None, None]
        self._list_wired = {}
        self.interface = interface
        self.dnsmasq = dnsmasq

        if use_telnet:
            self.connection = TelnetConnection(host, port, username, password)
        else:
            self.connection = SshConnection(host, port, username, password, ssh_key)

    async def async_get_nvram(self, to_get, use_cache=True):
        """Gets nvram"""
        data = {}
        if not (to_get in GET_LIST):
            return data

        now = datetime.utcnow()
        if (
            use_cache
            and self._nvram_cache_timer
            and self._cache_time > (now - self._nvram_cache_timer).total_seconds()
        ):
            lines = self._nvram_cache
        else:
            lines = await self.connection.async_run_command(_NVRAM_CMD)
            self._nvram_cache = lines
            self._nvram_cache_timer = now

        for item in GET_LIST[to_get]:
            regex = rf"^{item}=([\w.\-/: ]+)"
            for line in lines:
                result = re.findall(regex, line)
                if result:
                    data[item] = result[0]
                    break
        return data

    async def async_get_wl(self):
        """gets wl"""
        lines = await self.connection.async_run_command(_WL_CMD)
        if not lines:
            return {}
        result = await _parse_lines(lines, _WL_REGEX)
        devices = {}
        for device in result:
            mac = device["mac"].upper()
            devices[mac] = Device(mac, None, None)
        return devices

    async def async_get_leases(self, cur_devices):
        """Gets leases"""
        lines = await self.connection.async_run_command(
            _LEASES_CMD.format(self.dnsmasq)
        )
        if not lines:
            return {}
        lines = [line for line in lines if not line.startswith("duid ")]
        result = await _parse_lines(lines, _LEASES_REGEX)
        devices = {}
        for device in result:
            # For leases where the client doesn't set a hostname, ensure it
            # is blank and not '*', which breaks entity_id down the line.
            host = device["host"]
            if host == "*":
                host = ""
            mac = device["mac"].upper()
            if mac in cur_devices:
                devices[mac] = Device(mac, device["ip"], host)
        return devices

    async def async_get_neigh(self, cur_devices):
        """Gets neigh"""
        lines = await self.connection.async_run_command(_IP_NEIGH_CMD)
        if not lines:
            return {}
        result = await _parse_lines(lines, _IP_NEIGH_REGEX)
        devices = {}
        for device in result:
            status = device["status"]
            if status is None or status.upper() != "REACHABLE":
                continue
            if device["mac"] is not None:
                mac = device["mac"].upper()
                old_device = cur_devices.get(mac)
                old_ip = old_device.ip if old_device else None
                devices[mac] = Device(mac, device.get("ip", old_ip), None)
        return devices

    async def async_get_arp(self):
        """Gets arp"""
        lines = await self.connection.async_run_command(_ARP_CMD)
        if not lines:
            return {}
        result = await _parse_lines(lines, _ARP_REGEX)
        devices = {}
        for device in result:
            if device["mac"] is not None:
                mac = device["mac"].upper()
                devices[mac] = Device(mac, device["ip"], None)
        return devices

    async def async_filter_dev_list(self, cur_devices):
        """Filter devices list using 'clientlist.json' files if available"""
        lines = await self.connection.async_run_command(_CLIENTLIST_CMD)
        if not lines:
            return cur_devices

        try:
            dev_list = json.loads(lines[0])
        except (TypeError, ValueError):
            return cur_devices

        devices = {}
        list_wired = {}
        # parse client list
        for if_mac in dev_list.values():
            for conn_type, conn_items in if_mac.items():
                if conn_type == "wired_mac":
                    list_wired.update(conn_items)
                    continue
                for dev_mac in conn_items:
                    mac = dev_mac.upper()
                    if mac in cur_devices:
                        devices[mac] = cur_devices[mac]

        # Delay 180 seconds removal of previously detected wired devices.
        # This is to avoid continuous add and remove in some circumstance
        # with devices connected via additional hub.
        cur_time = datetime.utcnow()
        for dev_mac, dev_data in list_wired.items():
            if dev_data.get("ip"):
                mac = dev_mac.upper()
                self._list_wired[mac] = cur_time

        pop_list = []
        for dev_mac, last_seen in self._list_wired.items():
            if (cur_time - last_seen).total_seconds() <= 180:
                if dev_mac in cur_devices:
                    devices[dev_mac] = cur_devices[dev_mac]
            else:
                pop_list.append(dev_mac)

        for mac in pop_list:
            self._list_wired.pop(mac)

        return devices

    async def async_get_connected_devices(self, use_cache=True):
        """Retrieve data from ASUSWRT.

        Calls various commands on the router and returns the superset of all
        responses. Some commands will not work on some routers.
        """
        now = datetime.utcnow()
        if (
            use_cache
            and self._dev_cache_timer
            and self._cache_time > (now - self._dev_cache_timer).total_seconds()
        ):
            return self._devices_cache

        devices = {}
        dev = await self.async_get_wl()
        devices.update(dev)
        dev = await self.async_get_arp()
        devices.update(dev)
        dev = await self.async_get_neigh(devices)
        devices.update(dev)
        if not self.mode == "ap":
            dev = await self.async_get_leases(devices)
            devices.update(dev)

        filter_devices = await self.async_filter_dev_list(devices)
        ret_devices = {
            key: dev
            for key, dev in filter_devices.items()
            if not self.require_ip or dev.ip is not None
        }

        self._devices_cache = ret_devices
        self._dev_cache_timer = now
        return ret_devices

    async def async_get_bytes_total(self, use_cache=True):
        """Retrieve total bytes (rx an tx) from ASUSWRT."""
        now = datetime.utcnow()
        if (
            use_cache
            and self._trans_cache_timer
            and self._cache_time > (now - self._trans_cache_timer).total_seconds()
        ):
            return self._transfer_rates_cache

        rx = await self.async_get_rx()
        tx = await self.async_get_tx()
        return rx, tx

    async def async_get_rx(self):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(
            _RX_COMMAND.format(self.interface)
        )
        return float(data[0]) if data[0] != "" else None

    async def async_get_tx(self):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(
            _TX_COMMAND.format(self.interface)
        )
        return float(data[0]) if data[0] != "" else None

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
            math.ceil(tx / time_diff.total_seconds()) if tx > 0 else 0,
        )
        return self._latest_transfer_data

    async def async_current_transfer_human_readable(self, use_cache=True):
        """Gets current transfer rates in a human readable format."""
        rx, tx = await self.async_get_current_transfer_rates(use_cache)

        return "%s/s" % convert_size(rx), "%s/s" % convert_size(tx)

    async def async_get_loadavg(self):
        """Get loadavg."""
        loadavg = list(
            map(
                lambda avg: float(avg),
                (await self.connection.async_run_command(_LOADAVG_CMD))[0].split(" ")[
                    0:3
                ],
            )
        )
        return loadavg

    #    async def async_get_meminfo(self):
    #        """Get Memory information."""
    #        memory_info = await self.connection.async_run_command(_MEMINFO_CMD)
    #        memory_info = filter(lambda s: s != '', memory_info)
    #        ret = {}
    #        for item in list(map(lambda i: i.split(' '), memory_info)):
    #            name = re.sub(r'(?<!^)(?=[A-Z])', '_', item[0]).lower()
    #            ret[name] = list(filter(lambda i: i != '', item[1].split(' ')))
    #            ret[name][0] = int(ret[name][0])
    #
    #        return ret

    async def async_add_dns_record(self, hostname, ipaddress):
        """Add record to /etc/hosts and HUP dnsmask to catch this record."""
        return await self.connection.async_run_command(
            _ADDHOST_CMD.format(hostname=hostname, ipaddress=ipaddress)
        )

    async def async_get_interfaces_counts(self):
        """Get counters for all network interfaces."""
        lines = await self.connection.async_run_command(_NETDEV_CMD)
        lines = list(
            map(lambda i: list(filter(lambda j: j != "", i.split(" "))), lines[2:-1])
        )
        interfaces = map(
            lambda i: [
                i[0][0:-1],
                dict(zip(_NETDEV_FIELDS, map(lambda j: int(j), i[1:]))),
            ],
            lines,
        )
        return dict(interfaces)

    async def async_find_temperature_commands(self):
        """Find which temperature commands work with the router, if any."""
        for i in range(3):
            for cmd in _TEMP_CMDS[i]:
                try:
                    result = await self.connection.async_run_command(cmd["cmd"])
                    if result[0].split(" ")[cmd["result_loc"]].isnumeric():
                        self._temps_commands[i] = cmd
                        break
                except (ValueError, IndexError, OSError):
                    continue
        return [self._temps_commands[i] is not None for i in range(3)]

    async def async_get_temperature(self):
        """Get temperature for 2.4GHz/5.0GHz/CPU."""
        result = [0.0, 0.0, 0.0]
        if self._temps_commands == [None, None, None]:
            await self.async_find_temperature_commands()
        for i in range(3):
            if self._temps_commands[i] is None:
                continue
            cmd_result = await self.connection.async_run_command(self._temps_commands[i]["cmd"])
            result[i] = cmd_result[0].split(" ")[self._temps_commands[i]["result_loc"]]
            result[i] = eval("float(" + result[i] + ")" + self._temps_commands[i]["eval"])
        return dict(zip(["2.4GHz", "5.0GHz", "CPU"], result))

    @property
    def is_connected(self):
        return self.connection.is_connected
