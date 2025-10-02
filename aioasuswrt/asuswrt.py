"""Module for Asuswrt."""

import json
import logging
import re
from collections import namedtuple
from dataclasses import dataclass
from time import time
from typing import Any, Dict, Iterable, List, Optional, Pattern, Tuple, Union

from aioasuswrt.commands import (
    NETDEV_FIELDS,
    TEMP_COMMANDS,
    VPN_COUNT,
    Command,
    Nvram,
    Regex,
    TempCommand,
)
from aioasuswrt.connection import _BaseConnection, create_connection
from aioasuswrt.helpers import convert_size

_LOGGER = logging.getLogger(__name__)


@dataclass
class Interface:
    """Interface representation."""

    interface: Optional[str] = None
    name: Optional[str] = None
    mac: Optional[str] = None


@dataclass
class DeviceData:
    """Device data representation."""

    ip: Optional[str] = None
    name: Optional[str] = None
    rssi: Optional[int] = None


class Device:
    """Device representation."""

    def __init__(
        self,
        mac: str,
        device_data: DeviceData = DeviceData(),
        interface: Interface = Interface(),
    ) -> None:
        """Class to map the devices."""
        self._mac: str = mac
        self._device_data: DeviceData = device_data
        self._interface: Interface = interface

    @property
    def mac(self) -> str:
        """The mac property."""
        return self._mac

    @property
    def device_data(self) -> DeviceData:
        """The device data collected from router."""
        return self._device_data

    @property
    def interface(self) -> Interface:
        """The device connected interface collected from router."""
        return self._interface

    def __repr__(self) -> str:
        """Representation of the device."""
        return str(
            {
                "mac": self._mac,
                "ip": self._device_data.ip,
                "name": self._device_data.name,
                "rssi": self._device_data.rssi,
                "interface": self._interface.interface,
                "interface_name": self._interface.name,
                "interface_mac": self._interface.mac,
            }
        )

    def to_tuple(self) -> Any:
        """Return Device as a named tuple."""
        DeviceT = namedtuple(
            "DeviceT",
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
        return DeviceT(
            self._mac,
            self._device_data.ip,
            self._device_data.name,
            self._device_data.rssi,
            self._interface.interface,
            self._interface.name,
            self._interface.mac,
        )


def merge_device(old: Device, new: Device) -> Device:
    """Merge 2 devices into one."""
    return Device(
        new.mac,
        DeviceData(
            new.device_data.ip or old.device_data.ip,
            new.device_data.name or old.device_data.name,
            new.device_data.rssi or old.device_data.rssi,
        ),
        Interface(
            new.interface.interface or old.interface.interface,
            new.interface.name or old.interface.name,
            new.interface.mac or old.interface.mac,
        ),
    )


async def _parse_lines(
    lines: Iterable[str], regex: Pattern[str]
) -> Iterable[Dict[str, Union[str, Any]]]:
    """
    Parse the lines using the given regular expression.

    If a line can't be parsed it is logged and skipped in the output.
    """

    def _match(line: str) -> Optional[Dict[str, Union[str, Any]]]:
        if not line:
            return None
        match = regex.search(line)
        if not match:
            _LOGGER.debug("Could not parse row: %s", line)
            return None
        return match.groupdict()

    return filter(None, map(_match, lines))


@dataclass
class TransferRates:
    """Representation of transfer rates."""

    rx: int = 0
    tx: int = 0
    last_check: float = time()


@dataclass
class AuthConfig:
    """Settings for how to authenticate."""

    port: int = 22
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    use_telnet: bool = False


@dataclass
class Settings:
    """Settings for the integration."""

    require_ip: bool = False
    mode: str = "router"
    dnsmasq: str = "/var/lib/misc"
    wan_interface: str = "eth0"


class AsusWrt:
    """This is the interface class."""

    def __init__(
        self,
        host: str,
        auth_config: AuthConfig,
        *,
        settings: Settings = Settings(),
    ) -> None:
        """Init function."""
        self._settings: Settings = settings
        self._transfer_rates: TransferRates = TransferRates()
        self._temps_commands: Dict[str, TempCommand] = {}
        self._connection: _BaseConnection = create_connection(
            host,
            auth_config.port,
            auth_config.username,
            auth_config.password,
            auth_config.ssh_key,
            auth_config.use_telnet,
        )

    @property
    def wan_interface(self) -> str:
        """Wan interface property."""
        return self._settings.wan_interface

    async def get_nvram(self, parameter_to_fetch: str) -> Dict[str, str]:
        """Get nvram."""
        data: Dict[str, str] = {}
        target: Optional[List[str]] = getattr(Nvram, parameter_to_fetch, None)
        if not isinstance(target, list):
            return data

        lines = await self._connection.run_command(Command.NVRAM)
        if not lines:
            _LOGGER.warning("No devices found in router")
            return data
        for item in target:
            regex = Regex.NVRAM.format(item)
            for line in lines:
                result = re.findall(regex, line)
                if result:
                    data[item] = result[0]
                    break
        return data

    async def _get_wl(self, devices: Dict[str, Device]) -> None:
        """Get wl."""
        _LOGGER.info("get_wl")
        lines = await self._connection.run_command(Command.WL)
        if not lines:
            return
        result = await _parse_lines(lines, Regex.WL)

        def _handle(device: Dict[str, str]) -> None:
            mac = device["mac"].upper()
            devices[mac] = Device(mac)

        list(map(_handle, result))
        _LOGGER.info("There are %s devices found in wl", len(devices))

    async def _get_arp(self, devices: Dict[str, Device]) -> None:
        """Get arp."""
        _LOGGER.info("get_arp")
        lines = await self._connection.run_command(Command.ARP)
        if not lines:
            return
        result = await _parse_lines(lines, Regex.ARP)

        def _handle(device: Dict[str, str]) -> None:
            if device["mac"] is not None:
                mac = device["mac"].upper()
                devices[mac] = merge_device(
                    devices[mac] if mac in devices else Device(mac),
                    Device(
                        mac,
                        DeviceData(device["ip"]),
                        Interface(device["interface"]),
                    ),
                )

        list(map(_handle, result))
        _LOGGER.info("There are %s devices found in arp", len(devices))

    async def _get_leases(self, devices: Dict[str, Device]) -> None:
        """Get leases."""
        _LOGGER.info("get_leases")
        lines: Iterable[str] = await self._connection.run_command(
            Command.LEASES.format(self._settings.dnsmasq)
        )
        if not lines:
            return
        lines = filter(lambda line: not line.startswith("duid "), lines)
        result = await _parse_lines(lines, Regex.LEASES)

        def _handle(device: Dict[str, str]) -> None:
            host = device["host"] if device["host"] != "*" else None
            mac = device["mac"].upper()
            if mac not in devices:
                _LOGGER.debug(
                    "Skipping %s its not in the device list, "
                    "meaning its not currently precent",
                    mac,
                )
                return
            devices[mac] = merge_device(
                devices[mac],
                Device(
                    mac,
                    DeviceData(
                        device["ip"],
                        host,
                    ),
                ),
            )

        list(map(_handle, result))
        _LOGGER.info("There are %s devices found after leases", len(devices))

    async def _get_neigh(self, devices: Dict[str, Device]) -> None:
        """Get neigh."""
        _LOGGER.info("get_neigh")
        lines = await self._connection.run_command(Command.IP_NEIGH)
        if not lines:
            return
        result = await _parse_lines(lines, Regex.IP_NEIGH)

        def _handle(device: Dict[str, str]) -> None:
            if not device.get("mac"):
                return
            status = device["status"]
            mac = device["mac"].upper()
            if status is None or status and status.upper() != "REACHABLE":
                return
            devices[mac] = merge_device(
                devices[mac],
                Device(
                    mac,
                    DeviceData(device["ip"]),
                ),
            )

        list(map(_handle, result))
        _LOGGER.info("There are %s devices found in neigh", len(devices))

    async def _filter_dev_list(self, devices: Dict[str, Device]) -> None:
        """Filter devices list using 'clientlist.json' files if available."""
        _LOGGER.info("filter_dev_list")
        lines = await self._connection.run_command(Command.CLIENTLIST)
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
                    devices[mac] = merge_device(
                        devices[mac] if mac in devices else Device(mac),
                        Device(
                            mac,
                            DeviceData(ip, None, rssi),
                            Interface(None, conn_type, interface_mac),
                        ),
                    )

        _LOGGER.debug(
            "There are %s devices found after clientlist.json", len(devices)
        )

    async def get_connected_devices(
        self,
    ) -> Dict[str, Device]:
        """
        Retrieve data from ASUSWRT.

        Calls various commands on the router and returns the superset of all
        responses. Some commands will not work on some routers.
        """
        devices: Dict[str, Device] = {}
        await self._get_wl(devices)
        _LOGGER.debug(devices)
        await self._get_arp(devices)
        _LOGGER.debug(devices)
        await self._get_neigh(devices)
        _LOGGER.debug(devices)
        if self._settings.mode != "ap":
            await self._get_leases(devices)
            _LOGGER.debug(devices)

        await self._filter_dev_list(devices)
        _LOGGER.debug(devices)
        if not self._settings.require_ip:
            return devices
        return {
            key: dev
            for key, dev in devices.items()
            if dev.device_data.ip is not None
        }

    async def get_bytes_total(
        self,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Retrieve total bytes (rx an tx) from ASUSWRT."""
        _LOGGER.warning(
            "get_bytes_total is deprecated, calculate this elsewhere"
        )
        return 0, 0

    @property
    async def rx(self) -> int:
        """Get current RX total given in bytes."""
        return self._transfer_rates.rx

    @property
    async def tx(self) -> int:
        """Get current RX total given in bytes."""
        return self._transfer_rates.tx

    async def get_current_transfer_rates(
        self,
    ) -> Tuple[float, float]:
        """Get current transfer rates calculated in per second in bytes."""
        _now = time()
        delay = _now - self._transfer_rates.last_check
        self._transfer_rates.last_check = _now
        eth0rx = eth0tx = 0
        vlanrx = vlantx = 0

        net_dev_lines = await self._connection.run_command(Command.NETDEV)
        if not net_dev_lines:
            _LOGGER.info("Unable to run %s", Command.NETDEV)
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

        rx = int(handle32bitwrap(inetrx - self._transfer_rates.rx) / delay)
        tx = int(handle32bitwrap(inettx - self._transfer_rates.tx) / delay)

        self._transfer_rates.rx = inetrx
        self._transfer_rates.tx = inettx

        return rx, tx

    async def current_transfer_human_readable(
        self,
    ) -> Optional[tuple[str, str]]:
        """Get current transfer rates in a human readable format."""
        rx, tx = await self.get_current_transfer_rates()

        if rx is not None and rx > 0 and tx is not None and tx > 0:
            return f"{convert_size(rx)}/s", f" {convert_size(tx)}/s"
        return "0/s", "0/s"

    async def get_loadavg(self) -> List[float]:
        """Get loadavg."""
        loadavg = list(
            map(
                float,
                (await self._connection.run_command(Command.LOADAVG))[0].split(
                    " "
                )[0:3],
            )
        )
        return loadavg

    async def add_dns_record(
        self, hostname: str, ipaddress: str
    ) -> Optional[List[str]]:
        """Add record to /etc/hosts and HUP dnsmask to catch this record."""
        return await self._connection.run_command(
            Command.ADDHOST.format(hostname=hostname, ipaddress=ipaddress)
        )

    async def get_interfaces_count(
        self,
    ) -> Dict[str, Any]:
        """Get counters for all network interfaces."""
        net_dev_lines = await self._connection.run_command(Command.NETDEV)
        lines = map(
            lambda i: list(filter(lambda j: j != "", i.split(" "))),
            net_dev_lines[2:-1],
        )
        interfaces: Iterable[Tuple[str, Any]] = map(
            lambda i: (
                i[0][0:-1],
                dict(zip(NETDEV_FIELDS, map(int, i[1:]))),
            ),
            lines,
        )
        return dict(interfaces)

    async def _find_temperature_commands(self) -> Dict[str, float]:
        """Find which temperature commands work with the router, if any."""
        ret: Dict[str, float] = {}

        for interface, commands in TEMP_COMMANDS.items():
            temp_command: TempCommand
            ret[interface] = 0.0
            for temp_command in commands:
                try:
                    result = await self._connection.run_command(
                        temp_command.cli_command
                    )
                    interface_temperature = result[0].split(" ")[
                        temp_command.result_location
                    ]
                    if interface_temperature.isnumeric():
                        self._temps_commands[interface] = temp_command
                        print(interface_temperature)
                        ret[interface] = temp_command.eval_function(
                            float(interface_temperature)
                        )
                        print(ret[interface])
                        break
                except (ValueError, IndexError, OSError):
                    continue
        return ret

    async def get_temperature(self) -> Dict[str, float]:
        """Get temperature for 2.4GHz/5.0GHz/CPU."""
        result = {}
        if not self._temps_commands:
            print("finding commands")
            return await self._find_temperature_commands()
        for interface, command in self._temps_commands.items():
            command_result: List[str] = (
                await self._connection.run_command(str(command.cli_command))
            )[0].split(" ")
            result[interface] = float(
                command_result[int(command.result_location)]
            )
            result[interface] = command.eval_function(float(result[interface]))
        return result

    async def get_vpn_clients(self) -> List[Dict[str, str]]:
        """Get current vpn clients."""
        data = await self.get_nvram("VPN")
        vpn_list = data["vpnc_clientlist"]

        vpns = []
        for m in re.finditer(Regex.VPN_LIST, vpn_list):
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

        return vpns

    async def start_vpn_client(self, vpn_id: int) -> List[str]:
        """Start a vpn client by id."""
        # stop all running vpn clients
        for no in range(VPN_COUNT):
            await self._connection.run_command(
                Command.VPN_STOP.format(id=no + 1)
            )

        # actually start vpn
        return await self._connection.run_command(
            Command.VPN_START.format(id=vpn_id)
        )

    async def stop_vpn_client(self, vpn_id: int) -> List[str]:
        """Stop a vpn client by id."""
        return await self._connection.run_command(
            Command.VPN_STOP.format(id=vpn_id)
        )

    @property
    def is_connected(self) -> bool:
        """Is connected property."""
        return self._connection.is_connected

    async def disconnect(self) -> None:
        """Disconnect from router."""
        await self._connection.disconnect()
