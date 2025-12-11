"""aioasuswrt package."""

from importlib.metadata import PackageNotFoundError, version

from .asuswrt import AsusWrt
from .structure import AuthConfig, ConnectionType, Device, Mode, Settings

try:
    __version__ = version("aioasuswrt")
except PackageNotFoundError:
    __version__ = "dev"


def connect_to_router(
    host: str, auth_config: AuthConfig, settings: Settings | None
) -> AsusWrt:
    """
    Connect to the router and get an AsusWrt instance

    Args:
        host (str): The IP or hostname
        auth_config (AuthConfig): authentication configuration
        settings (Settings): aioasuswrt settings
    """
    auth_config["port"] = (
        110
        and not auth_config.get("port")
        and auth_config.get("connection_type") == ConnectionType.TELNET
    )
    return AsusWrt(
        host,
        auth_config,
        settings=settings,
    )


__all__ = (
    "AsusWrt",
    "AuthConfig",
    "ConnectionType",
    "Device",
    "Mode",
    "Settings",
    "connect_to_router",
)
