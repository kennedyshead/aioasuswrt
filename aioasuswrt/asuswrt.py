"""Module for Asuswrt."""

import json
import logging
import re
from collections import namedtuple
from typing import Any, Dict, Iterable, List, Optional, Pattern, Tuple, Union

from aioasuswrt.connection import create_connection
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
_ARP_REGEX: Pattern[str] = re.compile(
    r".+\s"
    r"\((?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\)\s"
    r".+\s"
    r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))"
    r"\s"
    r".*"
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

Device = namedtuple("Device", ["mac", "ip", "name"])


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
        self._rx_latest: Optional[float] = None
        self._tx_latest: Optional[float] = None
        self._temps_commands: List[Optional[Dict[str, Union[str, int]]]] = [
            None,
            None,
            None,
        ]
        self.interface = interface
        self.dnsmasq = dnsmasq

        self.connection = create_connection(
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

    async def async_get_wl(self) -> Dict[str, Device]:
        """Get wl."""
        lines = await self.connection.async_run_command(_WL_CMD)
        if not lines:
            return {}
        result = await _parse_lines(lines, _WL_REGEX)
        devices = {}
        for device in result:
            mac = device["mac"].upper()
            devices[mac] = Device(mac, None, None)
        _LOGGER.debug("There are %s devices found in wl", len(devices))
        return devices

    async def async_get_leases(
        self, cur_devices: Dict[str, Device]
    ) -> Dict[str, Device]:
        """Get leases."""
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
        _LOGGER.debug("There are %s devices found in leases", len(devices))
        return devices

    async def async_get_neigh(
        self, cur_devices: Dict[str, Device]
    ) -> Dict[str, Device]:
        """Get neigh."""
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
        _LOGGER.debug("There are %s devices found in neigh", len(devices))
        return devices

    async def async_get_arp(self) -> Dict[str, Device]:
        """Get arp."""
        lines = await self.connection.async_run_command(_ARP_CMD)
        if not lines:
            return {}
        result = await _parse_lines(lines, _ARP_REGEX)
        devices = {}
        for device in result:
            if device["mac"] is not None:
                mac = device["mac"].upper()
                devices[mac] = Device(mac, device["ip"], None)
        _LOGGER.debug("There are %s devices found in arp", len(devices))
        return devices

    async def async_filter_dev_list(
        self, cur_devices: Dict[str, Device]
    ) -> Dict[str, Device]:
        """Filter devices list using 'clientlist.json' files if available."""
        lines = await self.connection.async_run_command(_CLIENTLIST_CMD)
        if not lines:
            return cur_devices

        try:
            dev_list = json.loads(lines[0])
        except (TypeError, ValueError):
            _LOGGER.info("Unable to parse clientlist.json")
            _LOGGER.debug(lines[0])
            return cur_devices

        devices = {}
        list_wired = {}

        # parse client list
        for interface_mac in dev_list.values():
            for conn_type, conn_items in interface_mac.items():
                if conn_type == "wired_mac":
                    _LOGGER.debug("Found these wired devices: %s", conn_items)
                    list_wired.update(conn_items)
                    continue
                for dev_mac in conn_items:
                    mac = dev_mac.upper()
                    if mac in cur_devices:
                        devices[mac] = cur_devices[mac]

        _LOGGER.debug(
            "There are %s devices found in clientlist.json", len(devices)
        )
        return devices

    async def async_get_connected_devices(
        self,
    ) -> Dict[str, Device]:
        """
        Retrieve data from ASUSWRT.

        Calls various commands on the router and returns the superset of all
        responses. Some commands will not work on some routers.
        """
        devices: Dict[str, Device] = {}
        dev = await self.async_get_wl()
        merge_devices(devices, dev)
        dev = await self.async_get_arp()
        merge_devices(devices, dev)
        dev = await self.async_get_neigh(devices)
        merge_devices(devices, dev)
        if not self.mode == "ap":
            dev = await self.async_get_leases(devices)
            merge_devices(devices, dev)

        filter_devices = await self.async_filter_dev_list(devices)
        ret_devices = {
            key: dev
            for key, dev in filter_devices.items()
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

    async def async_get_rx(self) -> Optional[float]:
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(
            _RX_COMMAND.format(self.interface)
        )
        return float(data[0]) if data[0] != "" else None

    async def async_get_tx(self) -> Optional[float]:
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(
            _TX_COMMAND.format(self.interface)
        )
        return float(data[0]) if data[0] != "" else None

    async def async_get_current_transfer_rates(
        self,
    ) -> Tuple[float, float]:
        """Get current transfer rates calculated in per second in bytes."""
        _LOGGER.warning(
            "async_get_currenttransfer_rates is deprecated, "
            "calculate this elsewhere"
        )
        return 0, 0

    async def async_current_transfer_human_readable(
        self,
    ) -> Optional[tuple[str, str]]:
        """Get current transfer rates in a human readable format."""
        rx, tx = await self.async_get_current_transfer_rates()

        if rx is not None and tx is not None:
            return "%s/s" % convert_size(rx), "%s/s" % convert_size(tx)

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


def merge_devices(
    devices: Dict[str, Device], new_devices: Dict[str, Device]
) -> None:
    """
    Merge a new list of devices into an existing list.

    This merge fills in any null values in the base list if the device
    in the new list has values for them."""
    for mac, device in new_devices.items():
        if mac not in devices:
            devices[mac] = device
        elif any(val is None for val in devices[mac]):
            mismatches = [
                f"{Device._fields[field]}({val1} != {val2})"
                for field, (val1, val2) in enumerate(zip(devices[mac], device))
                if val1 and val2 and val1 != val2
            ]
            if mismatches:
                # if filled values do not match between
                # devices from found from different sources
                # then something is wrong. Log a warning and carry on.
                _LOGGER.warning(
                    "Mismatched values for device {}: {}".format(
                        mac, ", ".join(mismatches)
                    )
                )
            else:
                devices[mac] = Device(
                    *(val1 or val2 for val1, val2 in zip(devices[mac], device))
                )
