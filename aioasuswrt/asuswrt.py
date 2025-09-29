"""Module for Asuswrt."""

import json
import logging
import re
from collections import namedtuple
from time import time
from typing import Any, Dict, Iterable, List, Optional, Pattern, Tuple, Union

from aioasuswrt.connection import _BaseConnection, create_connection
from aioasuswrt.helpers import convert_size

_LOGGER = logging.getLogger(__name__)

_LEASES_CMD: str = "cat {}/dnsmasq.leases"
_LEASES_REGEX: Pattern[str] = re.compile(
    r"\w+\s"
    r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))\s"
    r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\s"
    r"(?P<host>([^\s]+))"
)

# Command to get both 5GHz and 2.4GHz clients
_WL_CMD: str = (
    "for dev in `nvram get wl1_vifs && nvram get wl0_vifs && "
    "nvram get wl_ifnames`; do "
    "if type wlanconfig > /dev/null; then "
    "wlanconfig $dev list | awk 'FNR > 1 {print substr($1, 0, 18)}';"
    " else wl -i $dev assoclist; fi; done"
)
_WL_REGEX: Pattern[str] = re.compile(
    r"\w+\s" r"(?P<mac>(([0-9A-F]{2}[:-]){5}([0-9A-F]{2})))"
)

_CLIENTLIST_CMD: str = "cat /tmp/clientlist.json"

_NVRAM_CMD: str = "nvram show"

_IP_NEIGH_CMD: str = "ip neigh"
_IP_NEIGH_REGEX: Pattern[str] = re.compile(
    r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3}|"
    r"([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{1,4}){1,7})\s"
    r"\w+\s"
    r"\w+\s"
    r"(\w+\s(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2}))))?\s"
    r"\s?(router)?"
    r"\s?(nud)?"
    r"(?P<status>(\w+))"
)

_ARP_CMD: str = "arp -n"
_ARP_REGEX = re.compile(
    r".+\s"
    r"\((?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\)\s"
    r".+\s"
    r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))"
    r".+\s"
    r"(?P<interface>([\w+]+.$))"
)


_RX_COMMAND: str = "cat /sys/class/net/{}/statistics/rx_bytes"
_TX_COMMAND: str = "cat /sys/class/net/{}/statistics/tx_bytes"

_MEMINFO_CMD: str = "cat /proc/meminfo"
_LOADAVG_CMD: str = "cat /proc/loadavg"
_ADDHOST_CMD: str = (
    'cat /etc/hosts | grep -q "{ipaddress} {hostname}" || '
    '(echo "{ipaddress} {hostname}" >> /etc/hosts && '
    "kill -HUP `cat /var/run/dnsmasq.pid`)"
)

_NETDEV_CMD: str = "cat /proc/net/dev"
_NETDEV_FIELDS: List[str] = [
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

_TEMP_RADIO_EVAL: str = " / 2 + 20"
_TEMP_24_CMDS: List[Dict[str, Union[str, int]]] = [
    {
        "cmd": "wl -i eth1 phy_tempsense",
        "result_loc": 0,
        "eval": _TEMP_RADIO_EVAL,
    },
    {
        "cmd": "wl -i eth5 phy_tempsense",
        "result_loc": 0,
        "eval": _TEMP_RADIO_EVAL,
    },
]
_TEMP_5_CMDS: List[Dict[str, Union[str, int]]] = [
    {
        "cmd": "wl -i eth2 phy_tempsense",
        "result_loc": 0,
        "eval": _TEMP_RADIO_EVAL,
    },
    {
        "cmd": "wl -i eth6 phy_tempsense",
        "result_loc": 0,
        "eval": _TEMP_RADIO_EVAL,
    },
]
_TEMP_CPU_CMDS: List[Dict[str, Union[str, int]]] = [
    {"cmd": "head -c20 /proc/dmu/temperature", "result_loc": 2, "eval": ""},
    {
        "cmd": "head -c5 /sys/class/thermal/thermal_zone0/temp",
        "result_loc": 0,
        "eval": " / 1000",
    },
]
_TEMP_CMDS: List[List[Dict[str, Union[str, int]]]] = [
    _TEMP_24_CMDS,
    _TEMP_5_CMDS,
    _TEMP_CPU_CMDS,
]

_VPN_LIST_REGEX: Pattern[str] = re.compile(
    r"(?P<description>.+?)>"
    r"(?P<type>.+?)>"
    r"(?P<id>.+?)>"
    r"(?P<username>.*?)>"
    r"(?P<password>.*?)(?:<|$)"
)
_VPN_AMOUNT: int = 5

_VPN_START_CMD: str = "service start_vpnclient{id}"
_VPN_STOP_CMD: str = "service stop_vpnclient{id}"

_GET_PID_OF: str = "pidof {name}"

GET_LIST: Dict[str, List[str]] = {
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
    "VPN": [
        "vpnc_clientlist",
    ]
    + [f"vpn_client{i + 1}_state" for i in range(_VPN_AMOUNT)],
}


class Device:
    def __init__(
        self,
        mac: str,
        ip: Optional[str] = None,
        name: Optional[str] = None,
        rssi: Optional[int] = None,
        interface: Optional[str] = None,
        interface_name: Optional[str] = None,
        interface_mac: Optional[str] = None,
    ) -> None:
        """Class to map the devices."""
        self._mac: str = mac
        self._ip: Optional[str] = ip
        self._name: Optional[str] = name
        self._rssi: Optional[int] = rssi
        self._interface: Optional[str] = interface
        self._interface_name: Optional[str] = interface_name
        self._interface_mac: Optional[str] = interface_mac

    @property
    def mac(self) -> str:
        """mac property."""
        return self._mac

    @property
    def ip(self) -> Optional[str]:
        """ip property."""
        return self._ip

    @ip.setter
    def ip(self, ip: str) -> None:
        """ip setter."""
        self._ip = ip

    @property
    def interface(self) -> Optional[str]:
        """ip property."""
        return self._interface

    @interface.setter
    def interface(self, interface: str) -> None:
        """ip setter."""
        self._interface = interface.strip("\r\n")

    @property
    def name(self) -> Optional[str]:
        """ip property."""
        return self._name

    @name.setter
    def name(self, host: str) -> None:
        """ip setter."""
        self._name = host

    @property
    def rssi(self) -> Optional[int]:
        """rssi property."""
        return self._rssi

    @rssi.setter
    def rssi(self, rssi: int) -> None:
        """rssi setter."""
        self._rssi = rssi

    @property
    def interface_name(self) -> Optional[str]:
        """rssi property."""
        return self._interface_name

    @interface_name.setter
    def interface_name(self, interface_name: str) -> None:
        """rssi setter."""
        self._interface_name = interface_name

    @property
    def interface_mac(self) -> Optional[str]:
        """rssi property."""
        return self._interface_mac

    @interface_mac.setter
    def interface_mac(self, interface_mac: str) -> None:
        """rssi setter."""
        self._interface_mac = interface_mac

    def __repr__(self) -> str:
        """Representation of the device"""

        return str(
            {
                "mac": self.mac,
                "ip": self.ip,
                "name": self.name,
                "rssi": self.rssi,
                "interface": self.interface,
                "interface_name": self.interface_name,
                "interface_mac": self.interface_mac,
            }
        )

    def to_tuple(self) -> Any:
        """Returns Device as a named tuple."""
        Device = namedtuple(
            "Device",
            (
                "mac",
                "ip",
                "name",
                "rssi",
                "interface",
                "interface_name",
                "interface_mac",
            ),
        )
        return Device(
            self.mac,
            self.ip,
            self.name,
            self.rssi,
            self.interface,
            self.interface_name,
            self.interface_mac,
        )


async def _parse_lines(
    lines: List[str], regex: Pattern[str]
) -> List[Dict[str, Union[str, Any]]]:
    """
    Parse the lines using the given regular expression.

    If a line can't be parsed it is logged and skipped in the output.
    """
    results = []
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
        host: str,
        port: Optional[int] = None,
        use_telnet: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssh_key: Optional[str] = None,
        mode: str = "router",
        require_ip: bool = False,
        interface: str = "eth0",
        dnsmasq: str = "/var/lib/misc",
    ) -> None:
        """Init function."""
        self.require_ip = require_ip
        self.mode = mode
        self._temps_commands: List[Optional[Dict[str, Union[str, int]]]] = [
            None,
            None,
            None,
        ]
        self.dnsmasq: str = dnsmasq
        self._previous_rx: int = 0
        self._previous_tx: int = 0
        self._last_transaction_run: float = time()
        self.connection: _BaseConnection = create_connection(
            use_telnet, host, port, username, password, ssh_key
        )

    async def async_get_nvram(self, to_get: str) -> Dict[str, str]:
        """Get nvram."""
        data: Dict[str, str] = {}
        if to_get not in GET_LIST:
            return data

        lines = await self.connection.async_run_command(_NVRAM_CMD)
        if not lines:
            _LOGGER.warning("No devices found in router")
            return data

        for item in GET_LIST[to_get]:
            regex = rf"^{item}=([\w.\-/: <>]+)"
            for line in lines:
                result = re.findall(regex, line)
                if result:
                    data[item] = result[0]
                    break
        return data

    async def async_get_wl(self, devices: Dict[str, Device]) -> None:
        """Get wl."""
        _LOGGER.info("async_get_wl")
        lines = await self.connection.async_run_command(_WL_CMD)
        if not lines:
            return
        result = await _parse_lines(lines, _WL_REGEX)
        for device in result:
            mac = device["mac"].upper()
            devices[mac] = Device(mac)
        _LOGGER.info("There are %s devices found in wl", len(devices))

    async def async_get_arp(self, devices: Dict[str, Device]) -> None:
        """Get arp."""
        _LOGGER.info("async_get_arp")
        lines = await self.connection.async_run_command(_ARP_CMD)
        if not lines:
            return
        result = await _parse_lines(lines, _ARP_REGEX)
        for device in result:
            if device["mac"] is not None:
                mac = device["mac"].upper()
                if mac not in devices:
                    devices[mac] = Device(mac)
                devices[mac].ip = device["ip"]
                devices[mac].interface = device["interface"]

        _LOGGER.info("There are %s devices found in arp", len(devices))

    async def async_get_leases(self, devices: Dict[str, Device]) -> None:
        """Get leases."""
        _LOGGER.info("async_get_leases")
        lines = await self.connection.async_run_command(
            _LEASES_CMD.format(self.dnsmasq)
        )
        if not lines:
            return
        lines = [line for line in lines if not line.startswith("duid ")]
        result = await _parse_lines(lines, _LEASES_REGEX)
        for device in result:
            host = device["host"] if device["host"] != "*" else None
            mac = device["mac"].upper()
            if mac not in devices:
                # There can be values that are not connected here IIRC
                _LOGGER.debug(
                    "Skipping %s its not already in the device list, "
                    "meaning its not currently precent",
                    mac,
                )
                continue
            devices[mac].ip = device["ip"]
            if host:
                devices[mac].name = host

        _LOGGER.info("There are %s devices found in leases", len(devices))

    async def async_get_neigh(self, devices: Dict[str, Device]) -> None:
        """Get neigh."""
        _LOGGER.info("async_get_neigh")
        lines = await self.connection.async_run_command(_IP_NEIGH_CMD)
        if not lines:
            return
        result = await _parse_lines(lines, _IP_NEIGH_REGEX)

        for device in result:
            status = device["status"]
            if status is None or status.upper() != "REACHABLE":
                continue
            if device["mac"] is not None:
                mac = device["mac"].upper()
                if mac not in devices:
                    devices[mac] = Device(mac)
                ip = device.get("ip")
                if ip:
                    devices[mac].ip = ip
        _LOGGER.info("There are %s devices found in neigh", len(devices))

    async def async_filter_dev_list(self, devices: Dict[str, Device]) -> None:
        """Filter devices list using 'clientlist.json' files if available."""
        _LOGGER.info("async_filter_dev_list")
        lines = await self.connection.async_run_command(_CLIENTLIST_CMD)
        if not lines:
            return

        try:
            dev_list = json.loads(lines[0])
        except (TypeError, ValueError):
            _LOGGER.info("Unable to parse clientlist.json")
            _LOGGER.debug(lines[0])
            return

        # parse client list
        for interface_mac, interface in dev_list.items():
            for conn_type, conn_items in interface.items():
                for dev_mac in conn_items:
                    mac = dev_mac.upper()
                    device = conn_items[mac]
                    ip = device.get("ip")
                    rssi = device.get("rssi")
                    if mac not in devices:
                        devices[mac] = Device(mac)
                    if ip:
                        devices[mac].ip = ip
                    if rssi:
                        devices[mac].rssi = rssi
                    devices[mac].interface_name = conn_type
                    devices[mac].interface_mac = interface_mac

        _LOGGER.debug(
            "There are %s devices found after clientlist.json", len(devices)
        )

    async def async_get_connected_devices(
        self,
    ) -> Dict[str, Device]:
        """
        Retrieve data from ASUSWRT.

        Calls various commands on the router and returns the superset of all
        responses. Some commands will not work on some routers.
        """
        devices: Dict[str, Device] = {}
        await self.async_get_wl(devices)
        _LOGGER.debug(devices)
        await self.async_get_arp(devices)
        _LOGGER.debug(devices)
        await self.async_get_neigh(devices)
        _LOGGER.debug(devices)
        if not self.mode == "ap":
            await self.async_get_leases(devices)
            _LOGGER.debug(devices)

        await self.async_filter_dev_list(devices)
        _LOGGER.debug(devices)
        ret_devices = {
            key: dev
            for key, dev in devices.items()
            if not self.require_ip or dev.ip is not None
        }

        return ret_devices

    async def async_get_bytes_total(
        self,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Retrieve total bytes (rx an tx) from ASUSWRT."""
        _LOGGER.warning(
            "async_get_bytes_total is deprecated, calculate this elsewhere"
        )
        return 0, 0

    async def async_get_rx(self) -> int:
        """Get current RX total given in bytes."""
        return self._previous_rx

    async def async_get_tx(self) -> int:
        """Get current RX total given in bytes."""
        return self._previous_tx

    async def async_get_current_transfer_rates(
        self,
    ) -> Tuple[float, float]:
        """Get current transfer rates calculated in per second in bytes."""
        _now = time()
        delay = _now - self._last_transaction_run
        self._last_transaction_run = _now
        eth0rx = eth0tx = 0
        vlanrx = vlantx = 0

        net_dev_lines = await self.connection.async_run_command(_NETDEV_CMD)
        if not net_dev_lines:
            _LOGGER.info("Unable to run %s", _NETDEV_CMD)
            return 0, 0

        for line in net_dev_lines[2:]:
            parts = re.split(r"[\s:]+", line.strip())
            # NOTES:
            #  * assuming eth0 always comes before vlan1 in dev file
            #  * counted bytes wrap around at 0xFFFFFFFF
            if parts[0] == "eth0":
                eth0rx = int(parts[1])  # received bytes
                eth0tx = int(parts[9])  # transmitted bytes
            elif parts[0] == "vlan1":
                vlanrx = int(parts[1])  # received bytes
                vlantx = int(parts[9])  # transmitted bytes

        def handle32bitwrap(v: int) -> int:
            return v if v > 0 else v + 0xFFFFFFFF

        # the true amount of Internet related data equals eth0 - vlan1
        inetrx = handle32bitwrap(eth0rx - vlanrx)
        inettx = handle32bitwrap(eth0tx - vlantx)

        rx = int(handle32bitwrap(inetrx - self._previous_rx) / delay)
        tx = int(handle32bitwrap(inettx - self._previous_tx) / delay)

        self._previous_rx = inetrx
        self._previous_tx = inettx

        return rx, tx

    async def async_current_transfer_human_readable(
        self,
    ) -> Optional[tuple[str, str]]:
        """Get current transfer rates in a human readable format."""
        rx, tx = await self.async_get_current_transfer_rates()

        if rx is not None and rx > 0 and tx is not None and tx > 0:
            return "%s/s" % convert_size(rx), "%s/s" % convert_size(tx)
        return "0/s", "0/s"

    async def async_get_loadavg(self) -> List[float]:
        """Get loadavg."""
        loadavg = list(
            map(
                lambda avg: float(avg),
                (await self.connection.async_run_command(_LOADAVG_CMD))[
                    0
                ].split(" ")[0:3],
            )
        )
        return loadavg

    async def async_add_dns_record(
        self, hostname: str, ipaddress: str
    ) -> Optional[List[str]]:
        """Add record to /etc/hosts and HUP dnsmask to catch this record."""
        return await self.connection.async_run_command(
            _ADDHOST_CMD.format(hostname=hostname, ipaddress=ipaddress)
        )

    async def async_get_interfaces_counts(
        self,
    ) -> Dict[str, Any]:
        """Get counters for all network interfaces."""
        net_dev_lines = await self.connection.async_run_command(_NETDEV_CMD)
        lines = map(
            lambda i: list(filter(lambda j: j != "", i.split(" "))),
            net_dev_lines[2:-1],
        )
        interfaces: Iterable[Tuple[str, Any]] = map(
            lambda i: (
                i[0][0:-1],
                dict(zip(_NETDEV_FIELDS, map(lambda j: int(j), i[1:]))),
            ),
            lines,
        )
        return dict(interfaces)

    async def async_find_temperature_commands(self) -> List[float]:
        """Find which temperature commands work with the router, if any."""
        for i in range(3):
            cmd: Dict[str, Union[str, int]]
            for cmd in _TEMP_CMDS[i]:
                try:
                    result = await self.connection.async_run_command(
                        str(cmd["cmd"])
                    )
                    if (
                        result[0]
                        .split(" ")[int(cmd["result_loc"])]
                        .isnumeric()
                    ):
                        self._temps_commands[i] = cmd
                        break
                except (ValueError, IndexError, OSError):
                    continue
        return [self._temps_commands[i] is not None for i in range(3)]

    async def async_get_temperature(self) -> Dict[str, float]:
        """Get temperature for 2.4GHz/5.0GHz/CPU."""
        result = [0.0, 0.0, 0.0]
        if self._temps_commands == [None, None, None]:
            await self.async_find_temperature_commands()
        for i in range(3):
            cmd: Optional[Dict[str, Union[str, int]]] = self._temps_commands[i]
            if not isinstance(cmd, dict):
                continue
            cmd_result: List[str] = (
                await self.connection.async_run_command(str(cmd["cmd"]))
            )[0].split(" ")
            result.insert(i, float(cmd_result[int(cmd["result_loc"])]))
            result[i] = eval(  # nosec
                "float(" + str(result[i]) + ")" + str(cmd["eval"])
            )
        return dict(zip(["2.4GHz", "5.0GHz", "CPU"], result))

    async def async_get_vpn_clients(self) -> List[Dict[str, str]]:
        """Get current vpn clients"""
        data = await self.async_get_nvram("VPN")
        vpn_list = data["vpnc_clientlist"]

        vpns = []
        for m in re.finditer(_VPN_LIST_REGEX, vpn_list):
            id = m.group("id")
            pid = await self.connection.async_run_command(
                _GET_PID_OF.format(name=f"vpnclient{id}")
            )

            vpn = {k: v for k, v in m.groupdict().items() if v}
            vpn_state_key = f"vpn_client{id}_state"
            vpn_state = int(data.get(vpn_state_key, 0))

            if vpn_state == 0 or not pid:
                vpn["state"] = "off"
            elif vpn_state == 1:
                vpn["state"] = "starting"
            elif vpn_state == 2:
                vpn["state"] = "on"

            vpns.append(vpn)

        return vpns

    async def async_start_vpn_client(self, id: int) -> List[str]:
        """Start a vpn client by id."""
        # stop all running vpn clients
        for i in range(_VPN_AMOUNT):
            await self.connection.async_run_command(
                _VPN_STOP_CMD.format(id=(i + 1))
            )

        # actually start vpn
        return await self.connection.async_run_command(
            _VPN_START_CMD.format(id=id)
        )

    async def async_stop_vpn_client(self, id: int) -> List[str]:
        """Stop a vpn client by id."""
        return await self.connection.async_run_command(
            _VPN_STOP_CMD.format(id=id)
        )

    @property
    def is_connected(self) -> bool:
        """Is connected property."""
        return self.connection.is_connected

    async def async_disconnect(self) -> None:
        """Disconnect from router."""
        await self.connection.async_disconnect()
