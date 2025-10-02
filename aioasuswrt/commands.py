"""Command mapping, and regex handling."""

import re
from collections import namedtuple
from enum import StrEnum
from typing import Dict, List, Pattern

NETDEV_FIELDS: List[str] = [
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

VPN_COUNT: int = 5  # Max allowed VPN setups

_NVRAM_VPN_LIST: List[str] = ["vpnc_clientlist"]
_NVRAM_VPN_LIST.extend([f"vpn_client{i + 1}_state" for i in range(VPN_COUNT)])


TempCommand: namedtuple = namedtuple(
    "TempCommand", ["cli_command", "result_location", "eval_function"]
)
__TEMP_24_CMDS: List[TempCommand] = [
    TempCommand(
        "wl -i eth1 phy_tempsense",
        0,
        lambda val: val / 2 + 20,
    ),
    TempCommand(
        "wl -i eth5 phy_tempsense",
        0,
        lambda val: val / 2 + 20,
    ),
]
__TEMP_5_CMDS: List[TempCommand] = [
    TempCommand(
        "wl -i eth2 phy_tempsense",
        0,
        lambda val: val / 2 + 20,
    ),
    TempCommand(
        "wl -i eth6 phy_tempsense",
        0,
        lambda val: val / 2 + 20,
    ),
]
__TEMP_CPU_CMDS: List[TempCommand] = [
    TempCommand("head -c20 /proc/dmu/temperature", 2, lambda val: val),
    TempCommand(
        "head -c5 /sys/class/thermal/thermal_zone0/temp",
        0,
        lambda val: val / 1000,
    ),
]
TEMP_COMMANDS: Dict[str, List[TempCommand]] = {
    "2.4GHz": __TEMP_24_CMDS,
    "5.0GHz": __TEMP_5_CMDS,
    "CPU": __TEMP_CPU_CMDS,
}


class Regex:  # pylint: disable=too-few-public-methods
    """Regex mapping."""

    VPN_LIST: Pattern[str] = re.compile(
        r"(?P<description>.+?)>"
        r"(?P<type>.+?)>"
        r"(?P<id>.+?)>"
        r"(?P<username>.*?)>"
        r"(?P<password>.*?)(?:<|$)"
    )
    LEASES: Pattern[str] = re.compile(
        r"\w+\s"
        r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))\s"
        r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\s"
        r"(?P<host>([^\s]+))"
    )

    WL: Pattern[str] = re.compile(
        r"\w+\s"
        r"(?P<mac>(([0-9A-F]{2}[:-]){5}([0-9A-F]{2})))"
    )
    NVRAM: str = "^{}=([\\w.\\-/: <>]+)"
    IP_NEIGH: Pattern[str] = re.compile(
        r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3}|"
        r"([0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{1,4}){1,7})\s"
        r"\w+\s"
        r"\w+.+\s"
        r"(\w+\s(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2}))))?\s"
        r"\s?(router)?"
        r"\s?(nud)?"
        r"(?P<status>(\w+))"
    )
    ARP: Pattern[str] = re.compile(
        r".+\s"
        r"\((?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\)\s"
        r".+\s"
        r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))"
        r".+\s"
        r"(?P<interface>([\w.-]+))"
    )


class Command(StrEnum):
    """Available commands."""

    GET_PID_OF = "pidof {name}"
    NETDEV = "cat /proc/net/dev"
    RX = "cat /sys/class/net/{}/statistics/rx_bytes"
    TX = "cat /sys/class/net/{}/statistics/tx_bytes"

    MEMINFO = "cat /proc/meminfo"
    LOADAVG = "cat /proc/loadavg"
    ADDHOST = (
        'cat /etc/hosts | grep -q "{ipaddress} {hostname}" || '
        '(echo "{ipaddress} {hostname}" >> /etc/hosts && '
        "kill -HUP `cat /var/run/dnsmasq.pid`)"
    )
    LEASES = "cat {}/dnsmasq.leases"
    WL = (
        "for dev in `nvram get wl1_vifs && nvram get wl0_vifs && "
        "nvram get wl_ifnames`; do "
        "if type wlanconfig > /dev/null; then "
        "wlanconfig $dev list | awk 'FNR > 1 {print substr($1, 0, 18)}';"
        " else wl -i $dev assoclist; fi; done"
    )
    CLIENTLIST = "cat /tmp/clientlist.json"
    NVRAM = "nvram show"
    IP_NEIGH = "ip neigh"
    ARP = "arp -n"
    VPN_START = "service start_vpnclient{id}"
    VPN_STOP = "service stop_vpnclient{id}"


class Nvram:  # pylint: disable=too-few-public-methods
    """Property mapping for nvram info."""

    DHCP: List[str] = [
        "dhcp_dns1_x",
        "dhcp_dns2_x",
        "dhcp_enable_x",
        "dhcp_start",
        "dhcp_end",
        "dhcp_lease",
    ]
    MODEL: List[str] = ["model"]
    QOS: List[str] = [
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
    ]
    REBOOT: List[str] = [
        "reboot_schedule",
        "reboot_schedule_enable",
        "reboot_time",
    ]
    WLAN: List[str] = [
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
    ]
    GUEST_2G_1: List[str] = [
        "wl0.1_bss_enabled",
        "wl0.1_lanaccess",
        "wl0.1_ssid",
        "wl0.1_wpa_psk",
    ]
    GUEST_2G_2: List[str] = [
        "wl0.2_bss_enabled",
        "wl0.2_lanaccess",
        "wl0.2_ssid",
        "wl0.2_wpa_psk",
    ]
    GUEST_2G_3: List[str] = [
        "wl0.3_bss_enabled",
        "wl0.3_lanaccess",
        "wl0.3_ssid",
        "wl0.3_wpa_psk",
    ]
    WIFI_2G: List[str] = [
        "wl0_bss_enabled",
        "wl0_chanspec",
        "wl0_ssid",
        "wl0_wpa_psk",
    ]
    GUEST_5G_1: List[str] = [
        "wl1.1_bss_enabled",
        "wl1.1_lanaccess",
        "wl1.1_ssid",
        "wl1.1_wpa_psk",
    ]
    GUEST_5G_2: List[str] = [
        "wl1.2_bss_enabled",
        "wl1.2_lanaccess",
        "wl1.2_ssid",
        "wl1.2_wpa_psk",
    ]
    GUEST_5G_3: List[str] = [
        "wl1.3_bss_enabled",
        "wl1.3_lanaccess",
        "wl1.3_ssid",
        "wl1.3_wpa_psk",
    ]
    WIFI_5G: List[str] = [
        "wl1_bss_enabled",
        "wl1_chanspec",
        "wl1_ssid",
        "wl1_wpa_psk",
    ]
    FIRMWARE: List[str] = [
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
    ]
    LABEL_MAC: List[str] = ["label_mac"]
    VPN: List[str] = _NVRAM_VPN_LIST
