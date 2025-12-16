"""Parser module"""

from collections.abc import Iterable
from json import loads
from logging import getLogger
from re import Pattern, findall

from .structure import REGEX, Device, InterfaceJson, new_device

_LOGGER = getLogger(__name__)


def _add_nvram_to_data(
    target_row: str, row: str, result: dict[str, str]
) -> None:
    regex = REGEX.NVRAM.format(target_row)
    _parsed_result = findall(regex, row)
    if _parsed_result:
        result[target_row] = _parsed_result[0]


def _parse_nvram_target_row(
    target_row: str, data: list[str], result: dict[str, str]
) -> None:
    _ = list(
        map(
            lambda row: _add_nvram_to_data(target_row, row, result),
            filter(lambda row: target_row in row, data),
        )
    )


def parse_nvram(
    data: list[str], target: list[str], result: dict[str, str]
) -> None:
    """Parse Nvram data."""
    _ = list(
        map(
            lambda target_row: _parse_nvram_target_row(
                target_row, data, result
            ),
            target,
        )
    )


async def parse_raw_lines(
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

    return filter(None, map(_match, lines))


def _parse_wl_row(row: dict[str, str], devices: dict[str, Device]) -> None:
    mac = row["mac"].upper()
    devices[mac] = new_device(mac)


def parse_wl(
    data: Iterable[dict[str, str]], devices: dict[str, Device]
) -> None:
    """Parse wl data."""
    _ = list(map(lambda row: _parse_wl_row(row, devices), data))


def _parse_arp_row(row: dict[str, str], devices: dict[str, Device]) -> None:
    mac = row["mac"].upper()
    if mac not in devices:
        devices[mac] = new_device(mac)
    devices[mac].device_data["ip"] = row["ip"]
    devices[mac].interface["id"] = row["interface"]


def _parse_leases(device: dict[str, str], devices: dict[str, Device]) -> None:
    mac = device["mac"].upper()
    host = device.get("host")
    if host is not None and host != "*":
        devices[mac].device_data["name"] = host

    devices[mac].device_data["ip"] = device["ip"]


def _lease_in_devices(
    device: dict[str, str], devices: dict[str, Device]
) -> bool:
    return device["mac"].upper() in devices


def parse_leases(
    data: Iterable[dict[str, str]], devices: dict[str, Device]
) -> None:
    """Parse leases data."""
    _ = list(
        map(
            lambda row: _parse_leases(row, devices),
            filter(lambda row: _lease_in_devices(row, devices), data),
        )
    )


def parse_arp(
    data: Iterable[dict[str, str]], devices: dict[str, Device]
) -> None:
    """Parse arp data."""
    _ = list(map(lambda row: _parse_arp_row(row, devices), data))


def _parse_device_clientjson(
    interface_mac: str,
    conn_type: str,
    conn_items: dict[str, dict[str, str | int]],
    dev_mac: str,
    devices: dict[str, Device],
) -> None:
    mac = dev_mac.upper()
    device = conn_items[mac]
    ip = device.get("ip")
    if not isinstance(ip, str):
        ip = None
    rssi = device.get("rssi", None)
    if mac not in devices:
        devices[mac] = new_device(mac)
    devices[mac].device_data["ip"] = ip
    devices[mac].device_data["rssi"] = int(rssi) if rssi else None
    devices[mac].interface["name"] = conn_type
    devices[mac].interface["mac"] = interface_mac


def _map_device_clientjson(
    interface_mac: str,
    conn_type: str,
    conn_items: dict[str, dict[str, str | int]],
    devices: dict[str, Device],
) -> None:
    _ = list(
        map(
            lambda item: _parse_device_clientjson(
                interface_mac,
                conn_type,
                conn_items,
                item,
                devices,
            ),
            conn_items,
        )
    )


def _handle_clientjson(
    interface_mac: str,
    interface: dict[str, dict[str, dict[str, str | int]]],
    devices: dict[str, Device],
) -> None:
    _ = list(
        map(
            lambda conn_type: _map_device_clientjson(
                interface_mac, conn_type, interface[conn_type], devices
            ),
            interface,
        )
    )


def parse_clientjson(data: str, devices: dict[str, Device]) -> None:
    """Parse clientlist.json file"""
    device_list = InterfaceJson(loads(data))
    _ = list(
        map(
            lambda interface_mac: _handle_clientjson(
                interface_mac, device_list[interface_mac], devices
            ),
            device_list,
        )
    )
