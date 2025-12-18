"""Module for Asuswrt class."""

from collections.abc import Iterable
from logging import getLogger
from re import finditer, split
from time import time
from typing import cast, final

from .connection import BaseConnection, create_connection
from .constant import NETDEV_FIELDS, VPN_COUNT
from .helpers import empty_iter
from .parsers import (
    parse_arp,
    parse_clientjson,
    parse_leases,
    parse_neigh,
    parse_raw_lines,
    parse_wl,
)
from .structure import (
    REGEX,
    TEMP_COMMANDS,
    AuthConfig,
    Command,
    Device,
    DNSRecord,
    Mode,
    Nvram,
    Settings,
    TempCommand,
    TransferRates,
)

_LOGGER = getLogger(__name__)

_BIT_WRAP = 0xFFFFFFFF


async def _run_temp_command(
    api: BaseConnection, command: TempCommand
) -> float | None:
    command_result: list[str] | None = await api.run_command(
        str(command.cli_command)
    )

    if not command_result:
        return None
    try:
        result = command_result[0].split(" ")[int(command.result_location)]
    except IndexError:
        return None

    if not result or result and not result.isnumeric():
        return None

    return float(command.eval_function(float(result)))


async def _filter_dev_list(
    devices: dict[str, Device], reachable: bool, require_ip: bool
) -> dict[str, Device] | None:
    def _reachable(reachable: bool, dev: Device) -> bool:
        return (
            not reachable
            or reachable
            and dev.device_data.get("status") in ["REACHABLE", "STALE", None]
        )

    def _ip_check(dev: Device, require_ip: bool) -> bool:
        return (
            not require_ip
            or require_ip
            and dev.device_data.get("ip") is not None
        )

    return (
        {
            key: dev
            for key, dev in devices.items()
            if _reachable(reachable, dev) and _ip_check(dev, require_ip)
        }
        if len(devices) > 0
        else None
    )


async def _get_wl(
    connection: BaseConnection, devices: dict[str, Device]
) -> dict[str, Device]:
    """
    Add devices fount in wl.

    Args:
        devices (dict[str, Device]): Currently known device list
    """
    _LOGGER.info("get_wl")

    lines = await connection.run_command(Command.WL)
    if not lines:
        return devices

    parse_wl(await parse_raw_lines(lines, REGEX.WL), devices)
    _LOGGER.info("There are %s devices found in wl", len(devices))
    return devices


async def _get_arp(
    connection: BaseConnection, devices: dict[str, Device]
) -> dict[str, Device]:
    """
    Add devices found in arp.

    Args:
        devices (dict[str, Device]): Currently known device list
    """
    _LOGGER.info("get_arp")
    lines = await connection.run_command(Command.ARP)
    if not lines:
        return devices
    parse_arp(await parse_raw_lines(lines, REGEX.ARP), devices)
    _LOGGER.info("There are %s devices found in arp", len(devices))
    return devices


async def _get_leases(
    connection: BaseConnection, devices: dict[str, Device], dnsmasq: str
) -> dict[str, Device]:
    """
    Add devices found in leases.

    Args:
        devices (dict[str, Device]): Currently known device list
    """
    _LOGGER.info("get_leases")

    lines: Iterable[str] | None = await connection.run_command(
        Command.LEASES.format(dnsmasq)
    )
    if not lines:
        return devices

    lines = filter(lambda line: not line.startswith("duid "), lines)
    if empty_iter(lines):
        return devices

    parse_leases(await parse_raw_lines(lines, REGEX.LEASES), devices)
    _LOGGER.info("There are %s devices found after leases", len(devices))
    return devices


async def _get_neigh(
    connection: BaseConnection, devices: dict[str, Device]
) -> dict[str, Device]:
    """
    Add devices found in neigh.

    Args:
        devices (dict[str, Device]): Currently known device list
    """
    _LOGGER.info("get_neigh")

    lines = await connection.run_command(Command.IP_NEIGH)
    if not lines:
        return devices

    parse_neigh(await parse_raw_lines(lines, REGEX.IP_NEIGH), devices)
    _LOGGER.info("There are %s devices found in neigh", len(devices))
    return devices


async def _get_clientjson(
    connection: BaseConnection, devices: dict[str, Device]
) -> dict[str, Device]:
    """
    Filter devices list using 'clientlist.json' file if available.

    Args:
        devices (dict[str, Device]): Currently known device list
    """
    _LOGGER.info("filter_dev_list")
    lines = await connection.run_command(Command.CLIENTLIST)
    if not lines:
        return devices

    parse_clientjson(lines[0], devices)
    _LOGGER.debug(
        "There are %s devices found after clientlist.json",
        len(devices),
    )
    return devices


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
        self._temps_commands: dict[str, TempCommand] | None = None
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
        target: str = r"\|".join(Nvram.get(parameter_to_fetch, set()))
        cmd = Command.NVRAM.format(target)
        print(cmd)
        data = await self._connection.run_command(cmd)

        if not data:
            _LOGGER.warning("Cant fetch Nvram")
            return None

        values: Iterable[list[str]] = filter(
            lambda row: len(row) > 1 and row[1] not in ["", None],
            map(lambda string: string.split("="), data),
        )

        return dict(list(values))

    async def get_connected_devices(
        self,
        reachable: bool = False,
    ) -> dict[str, Device] | None:
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
        connection = self._connection
        devices: dict[str, Device] = await _get_wl(connection, {})
        _LOGGER.debug(devices)
        devices = await _get_arp(connection, devices)
        _LOGGER.debug(devices)
        devices = await _get_neigh(connection, devices)
        _LOGGER.debug(devices)
        if self._settings.mode != Mode.AP:
            devices = await _get_leases(
                connection, devices, self._settings.dnsmasq
            )
            _LOGGER.debug(devices)
        devices = await _get_clientjson(connection, devices)
        return await _filter_dev_list(
            devices, reachable, self._settings.require_ip
        )

    async def get_current_transfer_rates(
        self,
    ) -> dict[str, int] | None:
        """Get current transfer rates calculated in per second in bytes."""
        _now = time()
        delay = _now - self._last_transfer_rates_check
        self._last_transfer_rates_check = _now

        net_dev_lines = await self._connection.run_command(Command.NETDEV)
        if not net_dev_lines:
            _LOGGER.info("Cannot run netdev command (for transfer rates)")
            return None

        def handle32bitwrap(v: int) -> int:
            return v if v > 0 else v + _BIT_WRAP

        def _add_if_match(line: str) -> TransferRates | None:
            parts = split(r"[\s:]+", line.strip())
            if parts[0] in ["eth0", "vlan1"]:
                return TransferRates(
                    handle32bitwrap(int(parts[1])),
                    handle32bitwrap(int(parts[9])),
                )
            return None

        eth, vlan = list(filter(None, map(_add_if_match, net_dev_lines[2:])))

        inetrx = handle32bitwrap(eth.rx - vlan.rx)
        inettx = handle32bitwrap(eth.tx - vlan.tx)

        rx = tx = 0
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

    async def get_loadavg(self) -> dict[str, float] | None:
        """Get loadavg."""

        _loadavg = await self._connection.run_command(Command.LOADAVG)
        if not _loadavg:
            return None

        loadavg = list(
            map(
                float,
                filter(None, _loadavg[0].split(" ")[0:3]),
            )
        )
        if not len(loadavg) >= 3:
            return None

        return {
            "sensor_load_avg1": loadavg[0],
            "sensor_load_avg5": loadavg[1],
            "sensor_load_avg15": loadavg[2],
        }

    async def get_dns_records(self) -> dict[str, DNSRecord] | None:
        """Get a list of all dns records in hosts file."""
        ret: dict[str, DNSRecord] = {}

        lines = await self._connection.run_command(Command.LISTHOSTS)
        if not lines:
            return None

        def _to_record(row: dict[str, str]) -> None:
            ip = row["ip"]
            hosts = row["hosts"].split(" ")
            if ip in ret:
                ret[ip]["host_names"] += hosts
                return
            ret[ip] = DNSRecord(ip=row["ip"], host_names=hosts)

        data = await parse_raw_lines(lines, REGEX.HOSTS)
        _ = list(map(_to_record, data))
        return ret

    async def add_dns_record(
        self, hostname: str, ipaddress: str
    ) -> list[str] | None:
        """
        Add record to /etc/hosts and HUP dnsmask to catch this record.

        Args:
            hostname (str): Hostname to add
            ipaddress (str): IP address to add
        """
        _records = await self._connection.run_command(
            Command.ADDHOST.format(hostname=hostname, ipaddress=ipaddress)
        )
        if _records:
            return list(_records)
        return None

    async def get_interface_counters(
        self,
    ) -> Iterable[tuple[str, dict[str, int]]] | None:
        """
        Get counters for all network interfaces.

        Returns:
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
        if not net_dev_lines:
            return None

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

    async def _find_temperature_commands(self) -> dict[str, float]:
        """Find which temperature commands work with the router, if any."""
        ret: dict[str, float] = {}
        self._temps_commands = {}

        for interface, commands in TEMP_COMMANDS.items():
            temp_command: TempCommand
            ret[interface] = 0.0
            for temp_command in commands:
                result = await _run_temp_command(
                    self._connection, temp_command
                )
                if not result:
                    continue
                self._temps_commands[interface] = temp_command
                ret[interface] = result
                break
        return ret

    async def get_temperature(self) -> dict[str, float] | None:
        """Get temperature values we can find."""
        result: dict[str, float] = {}

        if self._temps_commands is None:
            result = await self._find_temperature_commands()

        if result == {} and self._temps_commands:
            for interface, command in self._temps_commands.items():
                temp = await _run_temp_command(self._connection, command)
                if temp:
                    result[interface] = temp
        if result not in [{"2.4GHz": 0.0, "5.0GHz": 0.0, "CPU": 0.0}, {}]:
            return result
        return None

    async def get_vpn_clients(self) -> list[dict[str, str]] | None:
        """Get current vpn clients."""
        data = await self.get_nvram("VPN")

        if not data:
            return None

        vpn_list = data.get("vpnc_clientlist")
        if not vpn_list:
            return None

        vpns: list[dict[str, str]] = []
        for m in finditer(REGEX.VPN_LIST, vpn_list):
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
