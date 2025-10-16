"""Mappings of structures and typing."""

from enum import StrEnum
from re import Pattern
from re import compile as re_compile
from typing import Callable, NamedTuple, TypeAlias, TypedDict

_VPN_COUNT: int = 5  # Max allowed VPN setups


InterfaceJson: TypeAlias = dict[
    str, dict[str, dict[str, dict[str, str | int]]]
]


class AsyncSSHConnectKwargs(NamedTuple):
    """Kwargs mapping for the asyncssh.connect method."""

    username: str
    client_keys: list[str] | None
    port: int
    password: str | None
    passphrase: str | None
    known_host: list[str] | None = None
    server_host_key_algs: list[str] = [
        "ssh-rsa",
        "rsa-sha2-256",
        "rsa-sha2-512",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "ssh-ed25519",
        "ssh-ed448",
    ]


class Interface(TypedDict):
    """
    Interface representation.

    Attributes:
        id (str | None): id of the interface (for example eth0)
        name (str | None): Name of the interface (for example 5g)
        mac (str | None): MAC address for the interface
    """

    id: str | None
    name: str | None
    mac: str | None


class DeviceData(TypedDict):
    """
    Device status representation.

    Attributes:
        ip (str |None): The IP of the device
        name (str | None): The hostname of the device
        status (str | None): The status of the device
        rssi (int | None): Signal strength,
            in a mesh systems this is to closest node.
    """

    ip: str | None
    name: str | None
    status: str | None
    rssi: int | None


class Device(NamedTuple):
    """
    Representation of a connected device.

    Attributes:
        mac (str): The MAC adrress for the device
        device_data (DeviceData): The current status
        interface (Interface): Information about the
            Interface device is connected to
    """

    mac: str
    device_data: DeviceData
    interface: Interface


class TransferRates(NamedTuple):
    """
    Representation of transfer rates.

    Attributes:
        rx (int): Received bytes
        tx (int): Transferred bytes
    """

    rx: int = 0
    tx: int = 0


class ConnectionType(StrEnum):
    """Connection type definition."""

    SSH = "SSH"
    TELNET = "TELNET"


class AuthConfig(TypedDict):
    """
    Authentication configuration

    There are multiple ways to connect to the router,
    we recomend using ssh_key with a passphrase if possible

    Attributes:
        username (str | None): The username to use
        password (str | None): The password to use
            required if no ssh_key is set
        connection_type (ConnectionType | None):
            Defaults to ConnectionType.SSH
        ssh_key (str |None): An optional ssh_key
        passphrase (str |None): An optional passphrase, used for ssh_key
        port (int | None): Defaults to 22 for ssh and 110 for telnet
    """

    username: str | None
    password: str | None
    connection_type: ConnectionType | None
    ssh_key: str | None
    passphrase: str | None
    port: int


class Mode(StrEnum):
    """Router modes definition."""

    ROUTER = "router"
    AP = "ap"


class Settings(NamedTuple):
    """
    Settings for communicating with asuswrt router.

    Args:
        require_ip (bool | None): Defaults to False
            if set to True we will not fetch any device we cannot map ip for
        mode (Mode | None): Defaults to Mode.ROUTER
        dnsmasq (str | None): Defaults to "/var/lib/misc"
            Directory where dnsmasq.leases can be found
        wan_interface (str | None): Defaults to eth0
            The name of the WAN interface connection
            used to get external IP and transfer rates
    """

    require_ip: bool = False
    mode: Mode | None = Mode.ROUTER
    dnsmasq: str = "/var/lib/misc"
    wan_interface: str = "eth0"


class TempCommand(NamedTuple):
    """
    Representation of a temperature command.

    Attributes:
        cli_command (str): The actual cli-command to run
            example "cat /proc/version"
        result_location (int): We .split(" ") the result of the command
            this tells which index of the resulting list to use
        eval_function (Callable): Method we run on the retrieved value
    """

    cli_command: str
    result_location: int
    eval_function: Callable[..., float]


class Regex(NamedTuple):
    """Regex Mapped to a key."""

    VPN_LIST: Pattern[str] = re_compile(
        (
            r"(?P<description>.+?)>"
            r"(?P<type>.+?)>"
            r"(?P<id>.+?)>"
            r"(?P<username>.*?)>"
            r"(?P<password>.*?)(?:<|$)"
        )
    )
    LEASES: Pattern[str] = re_compile(
        (
            r"\w+\s"
            r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))\s"
            r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\s"
            r"(?P<host>([^\s]+))"
        )
    )

    WL: Pattern[str] = re_compile(
        (
            r"\w+\s"
            r"(?P<mac>(([0-9A-F]{2}[:-]){5}([0-9A-F]{2})))"
        )
    )
    NVRAM: str = "^{}=([\\w.\\-/: <>]+)"
    IP_NEIGH: Pattern[str] = re_compile(
        (
            r"(?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3}|"
            r"([0-9a-fA-F]{1,4}:){1,7}"
            r"[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{1,4}){1,7})\s"
            r"\w+\s"
            r"\w+.+\s"
            r"(\w+\s(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2}))))?\s"
            r"\s?(router)?"
            r"\s?(nud)?"
            r"(?P<status>(\w+))"
        )
    )
    ARP: Pattern[str] = re_compile(
        (
            r".+\s"
            r"\((?P<ip>([0-9]{1,3}[\.]){3}[0-9]{1,3})\)\s"
            r".+\s"
            r"(?P<mac>(([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})))"
            r".+\s"
            r"(?P<interface>([\w.-]+))"
        )
    )


compiled_regex = Regex()


class Command(StrEnum):
    """List of commands that we run."""

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


_NVRAM_VPN_LIST: list[str] = ["vpnc_clientlist"]
_NVRAM_VPN_LIST.extend([f"vpn_client{i + 1}_state" for i in range(_VPN_COUNT)])


class Nvram(NamedTuple):
    """Property mapping for the nvram info command."""

    DHCP: list[str] = [
        "dhcp_dns1_x",
        "dhcp_dns2_x",
        "dhcp_enable_x",
        "dhcp_start",
        "dhcp_end",
        "dhcp_lease",
    ]
    MODEL: list[str] = ["model"]
    QOS: list[str] = [
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
    REBOOT: list[str] = [
        "reboot_schedule",
        "reboot_schedule_enable",
        "reboot_time",
    ]
    WLAN: list[str] = [
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
    GUEST_2G_1: list[str] = [
        "wl0.1_bss_enabled",
        "wl0.1_lanaccess",
        "wl0.1_ssid",
        "wl0.1_wpa_psk",
    ]
    GUEST_2G_2: list[str] = [
        "wl0.2_bss_enabled",
        "wl0.2_lanaccess",
        "wl0.2_ssid",
        "wl0.2_wpa_psk",
    ]
    GUEST_2G_3: list[str] = [
        "wl0.3_bss_enabled",
        "wl0.3_lanaccess",
        "wl0.3_ssid",
        "wl0.3_wpa_psk",
    ]
    WIFI_2G: list[str] = [
        "wl0_bss_enabled",
        "wl0_chanspec",
        "wl0_ssid",
        "wl0_wpa_psk",
    ]
    GUEST_5G_1: list[str] = [
        "wl1.1_bss_enabled",
        "wl1.1_lanaccess",
        "wl1.1_ssid",
        "wl1.1_wpa_psk",
    ]
    GUEST_5G_2: list[str] = [
        "wl1.2_bss_enabled",
        "wl1.2_lanaccess",
        "wl1.2_ssid",
        "wl1.2_wpa_psk",
    ]
    GUEST_5G_3: list[str] = [
        "wl1.3_bss_enabled",
        "wl1.3_lanaccess",
        "wl1.3_ssid",
        "wl1.3_wpa_psk",
    ]
    WIFI_5G: list[str] = [
        "wl1_bss_enabled",
        "wl1_chanspec",
        "wl1_ssid",
        "wl1_wpa_psk",
    ]
    FIRMWARE: list[str] = [
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
    LABEL_MAC: list[str] = ["label_mac"]
    VPN: list[str] = _NVRAM_VPN_LIST
