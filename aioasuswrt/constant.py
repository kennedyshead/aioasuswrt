"""Constant decleration."""

from .structure import TempCommand

NETDEV_FIELDS: list[str] = [
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
