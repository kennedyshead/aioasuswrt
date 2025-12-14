"""Module for Asuswrt class."""

from collections.abc import Iterable
from json import loads
from logging import getLogger
from re import Pattern, findall, finditer, split
from time import time
from typing import cast, final

from .connection import BaseConnection, create_connection
from .constant import NETDEV_FIELDS, TEMP_COMMANDS, VPN_COUNT
from .helpers import convert_size
from .structure import (
    AuthConfig,
    Command,
    Device,
    DeviceData,
    Interface,
    InterfaceJson,
    Mode,
    Nvram,
    Settings,
    TempCommand,
    TransferRates,
)
from .structure import (
    compiled_regex as Regex,
)

_LOGGER = getLogger(__name__)

_BIT_WRAP = 0xFFFFFFFF


async def _run_temp_command(
    api: BaseConnection, command: TempCommand
) -> float | None:
    command_result: list[str] | None = await api.run_command(
        str(command.cli_command)
    )
    if command_result:
        result = command_result[0].split(" ")[int(command.result_location)]
        if result.isnumeric():
            return float(command.eval_function(float(result)))
    return None


async def _parse_lines(
    lines: Iterable[str], regex: Pattern[str]
) -> Iterable[dict[str, str]]:
    """
    Parse the lines using the given regular expression.

    If a line can't be parsed it is logged and skipped in the output.
    We first map all the lines, and after this filter out any None rows.

    Args:
        lines (Iterable[str]): A list of lines to parse
        regex (Pattern[str]): The regex pattern to use on each line
    """

    def _match(line: str) -> dict[str, str] | None:
        """
        Match a single line, will return a None value if no match is made.

        Args:
            line (str): single line to process
        """
        if not line:
            return None
        match = regex.search(line)
        if not match:
            _LOGGER.debug("Could not parse row: %s", line)
            return None
        return match.groupdict()

    return list(filter(None, map(_match, lines)))


def _new_device(mac: str) -> Device:
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


@final
class AsusWrt:
    """This is the main interface class."""

    def __init__(
        self,
        host: str,
        auth_config: AuthConfig,
        settings: Settings | None = None,
    ) -> None:
        """
        Initiate the AsusWrt class, and the connection interface.

        Args:
            host (str): IP or hostname for the router
            auth_config (AuthConfig): The authentication configuration
            settings (Settings | None): Optional aioasuswrt settings
        """
        self._settings = settings or Settings()
        self._transfer_rates: TransferRates | None = None
        self._total_bytes = TransferRates()
        self._last_transfer_rates_check = time()
        self._temps_commands: dict[str, TempCommand] = {}
        self._connection = create_connection(
            host,
            auth_config,
        )

    async def connect(self) -> None:
        """Connect to router."""
        await self._connection.connect()

    @property
    def wan_interface(self) -> str:
        """Wan interface property."""
        return str(self._settings.wan_interface)

    async def get_nvram(
        self, parameter_to_fetch: str
    ) -> dict[str, str] | None:
        """
        Get nvram value.

        Args:
            parameter_to_fetch (str): The parameter we are targeting to fetch.
        """
        data: dict[str, str] = {}
        target: list[str] | None = getattr(Nvram, parameter_to_fetch, None)
        if not isinstance(target, list):
            return None

        lines = await self._connection.run_command(Command.NVRAM)
        if not lines:
            _LOGGER.warning("No devices found in router")
            return None

        for item in target:
            regex = Regex.NVRAM.format(item)
            for line in lines:
                result = findall(regex, line)
                if result:
                    data[item] = result[0]
                    break
        return data

    async def _get_wl(self, devices: dict[str, Device]) -> dict[str, Device]:
        """
        Add devices fount in wl.

        Args:
            devices (dict[str, Device]): Currently known device list
        """
        _LOGGER.info("get_wl")
        lines = await self._connection.run_command(Command.WL)
        if not lines:
            return devices
        result = await _parse_lines(lines, Regex.WL)

        def _handle(device: dict[str, str]) -> None:
            mac = device["mac"].upper()
            devices[mac] = _new_device(mac)

        _ = list(map(_handle, result))
        _LOGGER.info("There are %s devices found in wl", len(devices))
        return devices

    async def _get_arp(self, devices: dict[str, Device]) -> dict[str, Device]:
        """
        Add devices found in arp.

        Args:
            devices (dict[str, Device]): Currently known device list
        """
        _LOGGER.info("get_arp")
        lines = await self._connection.run_command(Command.ARP)
        if not lines:
            return devices
        result = await _parse_lines(lines, Regex.ARP)

        def _handle(device: dict[str, str]) -> None:
            mac = device["mac"].upper()
            if mac not in devices:
                devices[mac] = _new_device(mac)
            devices[mac].device_data["ip"] = device["ip"]
            devices[mac].interface["id"] = device["interface"]

        _ = list(map(_handle, result))
        _LOGGER.info("There are %s devices found in arp", len(devices))
        return devices

    async def _get_leases(
        self, devices: dict[str, Device]
    ) -> dict[str, Device]:
        """
        Add devices found in leases.

        Args:
            devices (dict[str, Device]): Currently known device list
        """
        _LOGGER.info("get_leases")
        lines: Iterable[str] | None = await self._connection.run_command(
            Command.LEASES.format(self._settings.dnsmasq)
        )
        if not lines:
            return devices
        lines = filter(lambda line: not line.startswith("duid "), lines)
        result = await _parse_lines(lines, Regex.LEASES)

        def _handle(device: dict[str, str]) -> None:
            mac = device["mac"].upper()
            if mac not in devices:
                devices[mac] = _new_device(mac)
            host = device.get("host")
            if host is not None and host != "*":
                devices[mac].device_data["name"] = host

            devices[mac].device_data["ip"] = device["ip"]

        _ = list(map(_handle, result))
        _LOGGER.info("There are %s devices found after leases", len(devices))
        return devices

    async def _get_neigh(
        self, devices: dict[str, Device]
    ) -> dict[str, Device]:
        """
        Add devices found in neigh.

        Args:
            devices (dict[str, Device]): Currently known device list
        """
        _LOGGER.info("get_neigh")
        lines = await self._connection.run_command(Command.IP_NEIGH)
        if not lines:
            return devices
        result = await _parse_lines(lines, Regex.IP_NEIGH)

        def _handle(device: dict[str, str]) -> None:
            if device.get("mac"):
                status = device["status"]
                mac = device["mac"].upper()
                if mac not in devices:
                    devices[mac] = _new_device(mac)
                devices[mac].device_data["status"] = status
                devices[mac].device_data["ip"] = device.get(
                    "ip", devices[mac].device_data["ip"]
                )

        _ = list(map(_handle, result))
        _LOGGER.info("There are %s devices found in neigh", len(devices))
        return devices

    async def _filter_dev_list(
        self, devices: dict[str, Device]
    ) -> dict[str, Device]:
        """
        Filter devices list using 'clientlist.json' file if available.

        Args:
            devices (dict[str, Device]): Currently known device list
        """
        _LOGGER.info("filter_dev_list")
        lines = await self._connection.run_command(Command.CLIENTLIST)
        if not lines:
            return devices

        def _parse_client_json(data: str) -> None:
            device_list = InterfaceJson(loads(data))
            for interface_mac, interface in device_list.items():
                for conn_type, conn_items in interface.items():
                    for dev_mac in conn_items:
                        mac = dev_mac.upper()
                        device = conn_items[mac]
                        ip = device.get("ip")
                        if not isinstance(ip, str):
                            ip = None
                        rssi = device.get("rssi", None)
                        if mac not in devices:
                            devices[mac] = _new_device(mac)
                        devices[mac].device_data["ip"] = ip
                        devices[mac].device_data["rssi"] = (
                            int(rssi) if rssi else None
                        )
                        devices[mac].interface["name"] = conn_type
                        devices[mac].interface["mac"] = interface_mac

        try:
            _parse_client_json(lines[0])
            _LOGGER.debug(
                "There are %s devices found after clientlist.json",
                len(devices),
            )
        except (TypeError, ValueError, AssertionError) as ex:
            _LOGGER.warning("Unable to parse clientlist.json")
            print(lines[0])
            print(ex)
        return devices

    async def get_connected_devices(
        self,
        reachable: bool = False,
    ) -> dict[str, Device]:
        """
        Retrieve devices and as much info as possible.

        If Settings.require_ip is `True,
            we filter out all devices that do not have ip mapped

        Calls various commands on the router and returns the superset of all
        responses. Some commands will not work on some routers.

        Args:
            reachable (bool): If true,
                filter out all devices that have not REACHABLE as status

        """
        devices: dict[str, Device] = await self._get_wl({})
        _LOGGER.debug(devices)
        devices = await self._get_arp(devices)
        _LOGGER.debug(devices)
        devices = await self._get_neigh(devices)
        _LOGGER.debug(devices)
        if self._settings.mode != Mode.AP:
            devices = await self._get_leases(devices)
            _LOGGER.debug(devices)

        devices = await self._filter_dev_list(devices)
        _LOGGER.debug(devices)
        if reachable:
            devices = {
                key: dev
                for key, dev in devices.items()
                if dev.device_data.get("status") not in ["FAILED", "STALE"]
            }
        if not self._settings.require_ip:
            return devices
        return {
            key: dev
            for key, dev in devices.items()
            if dev.device_data.get("ip") is not None
        }

    @property
    async def rx(self) -> int:
        """Get current RX given in bytes."""
        return int(self._transfer_rates.rx) if self._transfer_rates else 0

    @property
    async def tx(self) -> int:
        """Get current RX given in bytes."""
        return int(self._transfer_rates.tx) if self._transfer_rates else 0

    async def get_current_transfer_rates(
        self,
    ) -> dict[str, int] | None:
        """Get current transfer rates calculated in per second in bytes."""
        _now = time()
        delay = _now - self._last_transfer_rates_check
        self._last_transfer_rates_check = _now
        eth0rx = eth0tx = 0
        vlanrx = vlantx = 0

        net_dev_lines = await self._connection.run_command(Command.NETDEV)
        if not net_dev_lines:
            _LOGGER.info("Cannot calculate transfer speeds")
            return None

        def handle32bitwrap(v: int) -> int:
            return v if v > 0 else v + _BIT_WRAP

        for line in net_dev_lines[2:]:
            parts = split(r"[\s:]+", line.strip())
            # NOTES:
            #  * assuming eth0 always comes before vlan1 in dev file
            #  * counted bytes wrap around at 0xFFFFFFFF
            if parts[0] == "eth0":
                eth0rx = handle32bitwrap(int(parts[1]))  # received bytes
                eth0tx = handle32bitwrap(int(parts[9]))  # transmitted bytes
            elif parts[0] == "vlan1":
                vlanrx = handle32bitwrap(int(parts[1]))  # received bytes
                vlantx = handle32bitwrap(int(parts[9]))  # transmitted bytes

        # the true amount of Internet related data equals eth0 - vlan1
        inetrx = handle32bitwrap(eth0rx - vlanrx)
        inettx = handle32bitwrap(eth0tx - vlantx)

        rx = 0
        tx = 0

        if self._transfer_rates:
            rx = int(handle32bitwrap(inetrx - self._transfer_rates.rx) / delay)
            tx = int(handle32bitwrap(inettx - self._transfer_rates.tx) / delay)
            self._total_bytes = TransferRates(
                handle32bitwrap(
                    self._total_bytes.rx + inetrx - self._transfer_rates.rx
                ),
                handle32bitwrap(
                    self._total_bytes.tx + inettx - self._transfer_rates.tx
                ),
            )

        self._transfer_rates = TransferRates(inetrx, inettx)
        return cast(
            dict[str, int],
            TransferRates(rx, tx)._asdict(),
        )

    async def total_transfer(self) -> dict[str, int]:
        """Total transfer."""
        return cast(dict[str, int], self._total_bytes._asdict())

    async def current_transfer_human_readable(
        self,
    ) -> tuple[str, str] | None:
        """Get current transfer rates in a human readable format."""
        _rates = await self.get_current_transfer_rates()
        if not _rates:
            return None
        rx = _rates.get("rx")
        tx = _rates.get("tx")
        if rx and rx > 0 and tx and tx > 0:
            return f"{convert_size(rx)}/s", f" {convert_size(tx)}/s"
        return "0/s", "0/s"

    async def get_loadavg(self) -> dict[str, float] | None:
        """Get loadavg."""
        _loadavg = await self._connection.run_command(Command.LOADAVG)
        if _loadavg:
            loadavg = list(
                map(
                    float,
                    _loadavg[0].split(" ")[0:3],
                )
            )
            _keys = [
                "sensor_load_avg1",
                "sensor_load_avg5",
                "sensor_load_avg15",
            ]
            return {
                f"{_keys[index]}": loadavg[index]
                for index in range(len(loadavg))
            }
        return None

    async def add_dns_record(
        self, hostname: str, ipaddress: str
    ) -> list[str] | None:
        """
        Add record to /etc/hosts and HUP dnsmask to catch this record.

        Args:
            hostname (str): Hostname to add
            ipaddress (str): IP address to add
        """
        _records: list[str] | None = await self._connection.run_command(
            Command.ADDHOST.format(hostname=hostname, ipaddress=ipaddress)
        )
        if _records:
            return _records
        return None

    async def get_interface_counters(
        self,
    ) -> Iterable[tuple[str, dict[str, int]]] | None:
        """
        Get counters for all network interfaces.

        Return value (needs unwrap with a list as its a Iterable):
            [('lo', # Interface name
                {'rx_bytes': 537171783, # Received
                   'rx_carrier': 0,
                   'rx_colls': 0,
                   'rx_compressed': 0,
                   'rx_drop': 0,
                   'rx_errs': 0,
                   'rx_fifo': 0,
                   'rx_packets': 2834938,
                   'tx_bytes': 537171783, # Transferred
                   'tx_compressed': 0,
                   'tx_drop': 0,
                   'tx_errs': 0,
                   'tx_fifo': 0,
                   'tx_frame': 0,
                   'tx_multicast': 0,
                   'tx_packets': 2834938
                })
            ]
        """
        net_dev_lines = await self._connection.run_command(Command.NETDEV)
        if net_dev_lines:
            lines = map(
                lambda i: list(filter(lambda j: j != "", i.split(" "))),
                net_dev_lines[2:-1],
            )
            interfaces: Iterable[tuple[str, dict[str, int]]] = map(
                lambda i: (
                    i[0][0:-1],
                    dict(zip(NETDEV_FIELDS, map(int, i[1:]))),
                ),
                lines,
            )
            return interfaces
        return None

    async def _find_temperature_commands(self) -> dict[str, float] | None:
        """Find which temperature commands work with the router, if any."""
        ret: dict[str, float] = {}

        for interface, commands in TEMP_COMMANDS.items():
            temp_command: TempCommand
            ret[interface] = 0.0
            for temp_command in commands:
                try:
                    result = await _run_temp_command(
                        self._connection, temp_command
                    )
                    if result:
                        self._temps_commands[interface] = temp_command
                        ret[interface] = result
                        break
                except (ValueError, IndexError, OSError):
                    continue
        if len(ret) > 0:
            return ret
        return None

    async def get_temperature(self) -> dict[str, float] | None:
        """Get temperature values we can find."""
        result: dict[str, float] = {}
        if not self._temps_commands:
            return await self._find_temperature_commands()
        for interface, command in self._temps_commands.items():
            temp = await _run_temp_command(self._connection, command)
            if temp:
                result[interface] = temp
        if len(result) > 0:
            return result
        return None

    async def get_vpn_clients(self) -> list[dict[str, str]] | None:
        """Get current vpn clients."""
        data = await self.get_nvram("VPN")
        if not data:
            return None

        vpn_list = data["vpnc_clientlist"]

        vpns: list[dict[str, str]] = []
        for m in finditer(Regex.VPN_LIST, vpn_list):
            vpn_id = m.group("id")
            pid = await self._connection.run_command(
                Command.GET_PID_OF.format(name=f"vpnclient{vpn_id}")
            )

            vpn = {k: v for k, v in m.groupdict().items() if v}
            vpn_state_key = f"vpn_client{vpn_id}_state"
            vpn_state = int(data.get(vpn_state_key, 0))

            if vpn_state == 0 or not pid:
                vpn["state"] = "off"
            elif vpn_state == 1:
                vpn["state"] = "starting"
            elif vpn_state == 2:
                vpn["state"] = "on"

            vpns.append(vpn)
        if len(vpns) > 0:
            return vpns
        return None

    async def start_vpn_client(self, vpn_id: int) -> list[str] | None:
        """
        Start a vpn client by id.

        Args:
            vpn_id (int): The id of the VPN service to start
        """
        for no in range(VPN_COUNT):
            _ = await self._connection.run_command(
                Command.VPN_STOP.format(id=no + 1)
            )
        ret: list[str] | None = await self._connection.run_command(
            Command.VPN_START.format(id=vpn_id)
        )
        return ret

    async def stop_vpn_client(self, vpn_id: int) -> list[str] | None:
        """
        Stop a vpn client by id.

        Args:
            vpn_id (int): The id of the VPN service to stop
        """
        ret: list[str] | None = await self._connection.run_command(
            Command.VPN_STOP.format(id=vpn_id)
        )
        return ret

    @property
    def is_connected(self) -> bool:
        """Is connected property."""
        return bool(self._connection.is_connected)

    async def disconnect(self) -> None:
        """Disconnect from router."""
        await self._connection.disconnect()
