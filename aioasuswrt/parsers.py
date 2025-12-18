"""Parser module"""

from collections.abc import Iterable
from json import JSONDecodeError, loads
from logging import getLogger
from re import Pattern

from .structure import Device, InterfaceJson, new_device

_LOGGER = getLogger(__name__)


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


def _parse_neigh_row(
    device: dict[str, str], devices: dict[str, Device]
) -> None:
    if not device.get("mac"):
        return
    status = device["status"]
    mac = device["mac"].upper()
    if mac not in devices:
        devices[mac] = new_device(mac)
    devices[mac].device_data["status"] = status
    devices[mac].device_data["ip"] = device.get(
        "ip", devices[mac].device_data["ip"]
    )


def parse_neigh(
    data: Iterable[dict[str, str]], devices: dict[str, Device]
) -> None:
    """Parse neigh data."""
    _ = list(map(lambda row: _parse_neigh_row(row, devices), data))


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
    try:
        device_list = InterfaceJson(loads(data))
    except JSONDecodeError:
        _LOGGER.info("clientlist.json is corrupt.")
        return
    _ = list(
        map(
            lambda interface_mac: _handle_clientjson(
                interface_mac, device_list[interface_mac], devices
            ),
            device_list,
        )
    )
