"""Module for connections."""

import math
from abc import ABC, abstractmethod
from asyncio import (
    IncompleteReadError,
    LimitOverrunError,
    Lock,
    open_connection,
    wait_for,
)
from asyncio.streams import StreamReader, StreamWriter
from collections.abc import Iterable
from logging import getLogger
from math import floor
from typing import final, override

from asyncssh import (
    ChannelOpenError,
    KeyEncryptionError,
    KeyImportError,
    SSHClientConnection,
    connect,
    set_log_level,
)

from .constant import ALLOWED_KEY_HASHES
from .structure import AsyncSSHConnectKwargs, AuthConfig, ConnectionType

_LOGGER = getLogger(__name__)

_PATH_EXPORT_COMMAND: str = "PATH=$PATH:/bin:/usr/sbin:/sbin"
set_log_level("WARNING")


class BaseConnection(ABC):
    """Abstract class representation of a connection to the router."""

    def __init__(
        self,
        host: str,
        auth_config: AuthConfig,
    ):
        """
        Initiate the Connection object (not the connection).

        Args:
            host (str): IP or hostname for the router
            auth_config (AuthConfig): Authentication configuration
        """
        self._host: str = host
        self._port: int
        self._username: str = str(auth_config["username"])
        self._password: str | None = auth_config.get("password")

        self._io_lock: Lock = Lock()

    @property
    def description(self) -> str:
        """Description of the connection ({user}@{host}:{port})."""
        ret = f"{self._host}:{self._port}"
        if self._username:
            ret = f"{self._username}@{ret}"

        return ret

    async def run_command(self, command: str) -> Iterable[str] | None:
        """
        Call a command on the router and retreive the output.
        Will call the command wrapped in a asyncio.Lock()
        All exceptions are catched and logged with logging.exception(ex),
            and in that case an empty list is returned.

        Args:
            command (str): The actual command to run
        """
        if not self.is_connected:
            await self.connect()

        async with self._io_lock:
            try:
                return await self._call_command(command)
            except ConnectionError as ex:
                _LOGGER.exception(ex)
                raise

    async def connect(self) -> None:
        """
        Connect to the router.
        If a connection is already established we create a logging.warning.
        Wrapping the io in asyncio.Lock
        """
        if self.is_connected:
            _LOGGER.warning(
                "Connection already established to: %s", self.description
            )
            return

        async with self._io_lock:
            await self._connect()

    async def disconnect(self) -> None:
        """
        Disconnect from the client.
        Wrapping the io in a asyncio.Lock
        """
        await self._disconnect()

    @abstractmethod
    async def _call_command(self, command: str) -> Iterable[str] | None:
        """Abstract call the command."""

    @abstractmethod
    async def _connect(self) -> None:
        """Abstract establish a connection."""

    @abstractmethod
    async def _disconnect(self) -> None:
        """Abstract disconnect."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Abstract do we have a connection."""


def create_connection(
    host: str,
    auth_config: AuthConfig,
) -> BaseConnection:
    """
    Create a connection to the router.
    A convinience function to get a new connection to the router.
    Returns either a TelnetConnection or a SSHConnection.

    Args:
        auth_config (AuthConfig): The authentication configuration to use
    """
    if auth_config.get("connection_type") == ConnectionType.SSH:
        return SshConnection(host, auth_config)
    return TelnetConnection(host, auth_config)


@final
class SshConnection(BaseConnection):
    """SSH connection to an ASUS-WRT router."""

    def __init__(
        self,
        host: str,
        auth_config: AuthConfig,
    ):
        """
        Initialize the SSH connection.

        Sets the port to 22 if not provided

        Args:
            host (str): The IP or hostname to use
            auth_config (AuthConfig): The authentication configuration
        """
        self._port = auth_config.get("port") or 22
        super().__init__(host, auth_config)
        self._ssh_key = auth_config.get("ssh_key")
        self._client: SSHClientConnection | None = None
        self._passphrase = auth_config.get("passphrase")
        self._known_hosts: list[str] | None = None

    @override
    async def _call_command(self, command: str) -> Iterable[str] | None:
        """
        Run commands through an SSH connection.

        Args:
            command (str): The actual command to run
        """
        if not self._client:
            return None

        try:
            result = await wait_for(
                self._client.run(f"{_PATH_EXPORT_COMMAND} && {command}"),
                9,
            )
            _split = str(result.stdout).split("\n")
            return iter(_split)
        except ChannelOpenError:
            _LOGGER.info("Router disconnected, will try to connect again.")
            await self.disconnect()
        except TimeoutError:
            _LOGGER.info("Router timed out when running command")
            await self._disconnect()
        return None

    @property
    @override
    def is_connected(self) -> bool:
        """Do we have a connection."""
        return self._client is not None

    @override
    async def _connect(self) -> None:
        """Connects the ssh-client."""
        kwargs = AsyncSSHConnectKwargs(
            username=self._username,
            port=self._port,
            server_host_key_algs=ALLOWED_KEY_HASHES,
            password=self._password,
            passphrase=self._passphrase,
            known_hosts=self._known_hosts,
            client_keys=[self._ssh_key] if self._ssh_key else None,
        )
        err: (
            FileNotFoundError
            | KeyImportError
            | KeyEncryptionError
            | TimeoutError
            | None
        ) = None
        try:
            self._client = await connect(
                self._host, connect_timeout=9, **kwargs
            )
        except FileNotFoundError as exc:
            err = exc
            if self._ssh_key:
                _LOGGER.warning(
                    "The given ssh-key (%s) does not exist", self._ssh_key
                )
        except KeyImportError as exc:
            err = exc
            _LOGGER.warning(
                (
                    "There was an error using the given key (%s) "
                    "make sure its the private key, have the correct "
                    "permissions and that the passphrase is correct"
                ),
                self._ssh_key,
            )
        except KeyEncryptionError as exc:
            err = exc
            _LOGGER.warning(
                "The given key is not accepted with error (%s)", err
            )
        except TimeoutError as exc:
            err = exc
            _LOGGER.warning("Connection to server timed out")
        if err:
            await self._disconnect()
            raise ConnectionError("Unable to connect to router") from err

    @override
    async def _disconnect(self) -> None:
        """Disconnect and set self._client to None"""
        if self._client:
            self._client.close()
        self._client = None


@final
class TelnetConnection(BaseConnection):
    """Maintains a Telnet connection to an ASUS-WRT router."""

    def __init__(
        self,
        host: str,
        auth_config: AuthConfig,
    ):
        """
        Initialize the Telnet connection properties.

        Sets the port to 110 if not provided.

        Args:
            host (str): IP or hostname for the connection
            auth_config (AuthConfig): The authentication configuration to use
        """
        self._port = auth_config.get("port") or 110
        super().__init__(host, auth_config)
        self._reader: StreamReader | None = None
        self._writer: StreamWriter | None = None
        self._prompt_string: bytes = "".encode("ascii")
        self._linebreak: float | None = None

    @override
    async def _call_command(self, command: str) -> Iterable[str] | None:
        """Run a command through a Telnet connection."""
        if not self.is_connected:
            try:
                await self._connect()
            except ConnectionError:
                _LOGGER.warning("Unable to connect to router, retrying")
                return None

        full_cmd = f"{_PATH_EXPORT_COMMAND} && {command}"
        await self._write((full_cmd + "\n").encode("ascii"))
        data = await self._readuntil(self._prompt_string)
        if not data:
            _LOGGER.warning("Got empty respnse for %s", command)
            return None
        data_list = data.split(b"\n")

        cmd_len = len(self._prompt_string) + len(full_cmd)
        start_split: int = floor(cmd_len / self.linebreak) + 1
        return map(
            lambda line: line.decode("utf-8"), data_list[start_split:-1]
        )

    @property
    def linebreak(self) -> float:
        """Get linelength"""
        if not self._linebreak:
            raise ConnectionError("No linebreak found")
        return self._linebreak

    @override
    async def _connect(self) -> None:
        err: (
            IncompleteReadError | TimeoutError | ConnectionRefusedError | None
        ) = None
        try:
            self._reader, self._writer = await wait_for(
                open_connection(self._host, self._port), 9
            )
        except TimeoutError as exc:
            err = exc
            _LOGGER.error("Host timeout")
        except ConnectionRefusedError as exc:
            err = exc
            _LOGGER.error("Connection refused")

        if err:
            raise ConnectionError("Unable to connect to router") from err

        _ = await self._readuntil(b"login: ", _raise=True)
        await self._write((self._username or "" + "\n").encode("ascii"))
        _ = await self._readuntil(b"Password: ", _raise=True)
        await self._write((self._password or "" + "\n").encode("ascii"))
        self._linebreak = await self._get_linebreak()
        await self._set_promptstring()

    async def _set_promptstring(self) -> None:
        _read = await self._readuntil(b"#", _raise=True)
        if not _read:
            raise ConnectionError("Unable to get prompt string")
        self._prompt_string = _read.split(b"\n")[-1]

    async def _write(self, value: bytes, _raise: bool = False) -> None:
        if self._writer is None:
            raise ConnectionError("Unable to write to router")

        self._writer.write(value)
        err: TimeoutError | None = None
        try:
            await wait_for(self._writer.drain(), 9)
        except TimeoutError as exc:
            err = exc
            _LOGGER.error("Tiemout while writing")
        if _raise and err:
            raise ConnectionError("Error while writing") from err

    async def _readuntil(
        self, value: bytes, _raise: bool = False
    ) -> bytes | None:
        if self._reader is None:
            raise ConnectionError("Unable to read from router")
        err: IncompleteReadError | TimeoutError | LimitOverrunError | None = (
            None
        )
        try:
            return await wait_for(self._reader.readuntil(value), 9)
        except IncompleteReadError as exc:
            err = exc
            _LOGGER.error("Unable to read from router")
        except TimeoutError as exc:
            err = exc
            _LOGGER.error("Router times out in read")
        except LimitOverrunError as exc:
            err = exc
            _LOGGER.error("Limit overrun error occured")
        if _raise and err:
            raise ConnectionError("Error while reading") from err
        return None

    async def _get_linebreak(self) -> float | None:
        """
        Get linebreak.

        Telnet or asyncio seems to be adding linebreaks due to terminal size.
        Try to determine here what the column number is.
        """
        if not self._writer or not self._reader:
            _LOGGER.warning("Not connected while getting linebreak")
            return None

        await self._write((" " * 200 + "\n").encode("ascii"))
        input_bytes = await self._readuntil(self._prompt_string)
        if not input_bytes:
            _LOGGER.error("Unable to get linebreak")
            return None
        return self._determine_linebreak(input_bytes.decode("utf-8"))

    def _determine_linebreak(self, _input: str) -> float:
        data = _input.replace("\r", "").split("\n")
        if len(data) == 1:
            return math.inf

        linebreak = len(self._prompt_string) + len(data[0])
        if len(data) > 2 and len(data[1]) != linebreak:
            _LOGGER.warning(
                "Inconsistent linebreaks %s != %s",
                len(data[1]),
                linebreak,
            )

        return linebreak

    @property
    @override
    def is_connected(self) -> bool:
        """Do we have a connection."""
        return self._reader is not None and self._writer is not None

    @override
    async def _disconnect(self) -> None:
        """
        Disconnect the connection.
        """
        if self._writer:
            self._writer.close()
        self._writer = None
        self._reader = None
        self._linebreak = None
