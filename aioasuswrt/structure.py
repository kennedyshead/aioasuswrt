"""Mappings of structures and typing."""

from enum import StrEnum
from re import Pattern
from re import compile as re_compile
from typing import Callable, NamedTuple, TypeAlias, TypedDict

from .constant import DEFAULT_DNSMASQ, DEFAULT_WAN_INTERFACE

InterfaceJson: TypeAlias = dict[
    str, dict[str, dict[str, dict[str, str | int]]]
]


class AsyncSSHConnectKwargs(TypedDict):
    """Kwargs mapping for the asyncssh.connect method."""

    username: str
    port: int
    server_host_key_algs: list[str]
    password: str | None
    passphrase: str | None
    known_hosts: list[str] | None
    client_keys: list[str] | None


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


class DNSRecord(TypedDict):
    """DNS record representation."""

    ip: str
    host_names: list[str]


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
    port: int | None


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
    dnsmasq: str = DEFAULT_DNSMASQ
    wan_interface: str = DEFAULT_WAN_INTERFACE


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


class _Regex(NamedTuple):
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
    HOSTS: Pattern[str] = re_compile(
        r"(?P<ip>(.+[\d][\.][\d]))[\s](?P<hosts>([a-zA-Z].+))"
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


REGEX = _Regex()


class Command(StrEnum):
    """List of commands that we run."""

    GET_PID_OF = "pidof {name}"
    NETDEV = "cat /proc/net/dev"
    RX = "cat /sys/class/net/{}/statistics/rx_bytes"
    TX = "cat /sys/class/net/{}/statistics/tx_bytes"

    MEMINFO = "cat /proc/meminfo"
    LOADAVG = "cat /proc/loadavg"
    LISTHOSTS = "cat /etc/hosts"
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
    NVRAM = "nvram show |grep '{}'"
    IP_NEIGH = "ip neigh"
    ARP = "arp -n"
    VPN_START = "service start_vpnclient{id}"
    VPN_STOP = "service stop_vpnclient{id}"


class _Nvram(TypedDict):
    """Property mapping for the nvram info command."""

    DHCP: set[str]
    MODEL: set[str]
    QOS: set[str]
    REBOOT: set[str]
    WLAN: set[str]
    GUEST_2G_1: set[str]
    GUEST_2G_2: set[str]
    GUEST_2G_3: set[str]
    WIFI_2G: set[str]
    GUEST_5G_1: set[str]
    GUEST_5G_2: set[str]
    GUEST_5G_3: set[str]
    WIFI_5G: set[str]
    FIRMWARE: set[str]
    LABEL_MAC: set[str]
    VPN: set[str]


_DHCP = {"dhcp_", "_dhcp", "dhcp=", "dhcpd"}
_MODEL = {"model="}
_QOS = {"qos_"}
_REBOOT = {"^reboot_"}
_WLAN = {"wan_"}
_GUEST_2G_1 = {"wl0.1_"}
_GUEST_2G_2 = {"wl0.2_"}
_GUEST_2G_3 = {"wl0.3_"}
_WIFI_2G = {"wl0_"}
_GUEST_5G_1 = {"wl1.1_"}
_GUEST_5G_2 = {"wl1.2_"}
_GUEST_5G_3 = {"wl1.3_"}
_WIFI_5G = {"wl1_"}
_FIRMWARE = {
    "buildinfo",
    "buildno",
    "firmver",
    "firmware_",
    "webs_",
}
_LABEL_MAC = {"label_mac"}

_VPN = {"vpnc_clientlist", "vpn_client"}

Nvram = _Nvram(
    DHCP=_DHCP,
    MODEL=_MODEL,
    QOS=_QOS,
    REBOOT=_REBOOT,
    WLAN=_WLAN,
    GUEST_2G_1=_GUEST_2G_1,
    GUEST_2G_2=_GUEST_2G_2,
    GUEST_2G_3=_GUEST_2G_3,
    WIFI_2G=_WIFI_2G,
    GUEST_5G_1=_GUEST_5G_1,
    GUEST_5G_2=_GUEST_5G_2,
    GUEST_5G_3=_GUEST_5G_3,
    WIFI_5G=_WIFI_5G,
    FIRMWARE=_FIRMWARE,
    LABEL_MAC=_LABEL_MAC,
    VPN=_VPN,
)


def new_device(mac: str) -> Device:
    """
    Initialize a new device.

    Args:
        mac (str): The MAC address of the device
    """
    return Device(
        mac,
        DeviceData(ip=None, name=None, status=None, rssi=None),
        Interface(id=None, name=None, mac=None),
    )


def _eval_divide_two_plus_twenty(val: float) -> float:
    """
    A filter to use on the retrieved float

    val / 2 + 20

    Args:
        val (float): Raw value from router
    """
    return val / 2 + 20


def _eval_divide_one_thousand(val: float) -> float:
    """
    A filter to use on the retrieved float

    val / 1000

    Args:
        val (float): Raw value from router
    """
    if val < 1000:
        raise ValueError(f"Value for dividing with 1000 is to low {val}")
    return val / 1000


def _eval_no_change(val: float) -> float:
    """
    A filter to use on the retrieved float

    Dummy method just returns the val

    Args:
        val (float): Raw value from router
    """
    return val


_TEMP_24_CMDS: list[TempCommand] = [
    TempCommand(
        "wl -i eth1 phy_tempsense",
        0,
        _eval_divide_two_plus_twenty,
    ),
    TempCommand(
        "wl -i eth5 phy_tempsense",
        0,
        _eval_divide_two_plus_twenty,
    ),
]
_TEMP_5_CMDS: list[TempCommand] = [
    TempCommand(
        "wl -i eth2 phy_tempsense",
        0,
        _eval_divide_two_plus_twenty,
    ),
    TempCommand(
        "wl -i eth6 phy_tempsense",
        0,
        _eval_divide_two_plus_twenty,
    ),
]
_TEMP_CPU_CMDS: list[TempCommand] = [
    TempCommand("head -c20 /proc/dmu/temperature", 2, _eval_no_change),
    TempCommand(
        "head -c5 /sys/class/thermal/thermal_zone0/temp",
        0,
        _eval_divide_one_thousand,
    ),
]

TEMP_COMMANDS: dict[str, list[TempCommand]] = {
    "2.4GHz": _TEMP_24_CMDS,
    "5.0GHz": _TEMP_5_CMDS,
    "CPU": _TEMP_CPU_CMDS,
}
