"""Parser module"""

from json import loads

from structure import Device, InterfaceJson, new_device


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
