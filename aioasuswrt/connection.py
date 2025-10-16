"""Module for connections."""

from abc import ABC, abstractmethod
from asyncio import (
    IncompleteReadError,
    LimitOverrunError,
    Lock,
    open_connection,
    wait_for,
)
from asyncio.streams import StreamReader, StreamWriter
from logging import getLogger
from math import floor
from typing import final, override

from asyncssh import SSHClientConnection, connect, set_log_level

from .structure import AsyncSSHConnectKwargs, AuthConfig, ConnectionType

_LOGGER = getLogger(__name__)

_PATH_EXPORT_COMMAND: str = "PATH=$PATH:/bin:/usr/sbin:/sbin"
set_log_level("WARNING")


class _CommandException(Exception):
    """Protected command exception."""


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
        """Description of the connection (user@192.168.1.1:22)."""
        ret = f"{self._host}:{self._port}"
        if self._username:
            ret = f"{self._username}@{ret}"

        return ret

    async def run_command(self, command: str) -> list[str]:
        """
        Call a command on the router and retreive the output.
        Will call the command wrapped in a asyncio.Lock()
        All exceptions are catched and logged with logging.exception(ex),
            and in that case an empty list is returned.

        Args:
            command (str): The actual command to run
        """
        async with self._io_lock:
            if not self.is_connected:
                await self.connect()

            try:
                return await self._call_command(command)
            except _CommandException as ex:
                _LOGGER.exception(ex)

        return []

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
        async with self._io_lock:
            self._disconnect()

    @abstractmethod
    async def _call_command(self, command: str) -> list[str]:
        """Abstract call the command."""

    @abstractmethod
    async def _connect(self) -> None:
        """Abstract establish a connection."""

    @abstractmethod
    def _disconnect(self) -> None:
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
    if auth_config.get("connection_type", ConnectionType.SSH):
        return TelnetConnection(host, auth_config)
    return SshConnection(host, auth_config)


@final
class SshConnection(BaseConnection):
    """Maintains an SSH connection to an ASUS-WRT router."""

    def __init__(
        self,
        host: str,
        auth_config: AuthConfig,
    ):
        """
        Initialize the SSH connection properties.

        Sets the port to 22 if not provided

        Args:
            host (str): The IP or hostname to use
            auth_config (AuthConfig): The authentication configuration
        """
        self._port = auth_config.get("port", 22)
        super().__init__(host, auth_config)
        self._ssh_key = auth_config.get("ssh_key")
        self._client: SSHClientConnection | None = None
        self._passphrase = auth_config.get("passphrase")

    @override
    async def _call_command(self, command: str) -> list[str]:
        """
        Run commands through an SSH connection.

        Args:
            command (str): The actual command to run
        """
        if not self._client:
            raise ConnectionError("Lost connection to router")

        result = await wait_for(
            self._client.run(f"{_PATH_EXPORT_COMMAND} && {command}"),
            9,
        )
        return list(str(result.stdout).split("\n"))

    @property
    @override
    def is_connected(self) -> bool:
        """Do we have a connection."""
        return self._client is not None

    @override
    async def _connect(self) -> None:
        """Connects the ssh-client."""
        if self._client:
            _LOGGER.debug(
                "reconnecting; old connection is disconnected",
            )
            self._disconnect()
        else:
            _LOGGER.debug("reconnecting; no old connection existed")

        kwargs = AsyncSSHConnectKwargs(
            username=self._username,
            client_keys=[self._ssh_key] if self._ssh_key else None,
            port=self._port,
            password=self._password,
            passphrase=self._passphrase,
        )
        self._client = await connect(self._host, *kwargs)
        _LOGGER.debug(
            "reconnected",
        )

    @override
    def _disconnect(self) -> None:
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
        self._port = auth_config.get("port", 110)
        super().__init__(host, auth_config)
        self._reader: StreamReader | None = None
        self._writer: StreamWriter | None = None
        self._prompt_string: bytes = "".encode("ascii")
        self._linebreak: float | None = None

    @override
    async def _call_command(self, command: str) -> list[str]:
        """Run a command through a Telnet connection."""
        try:
            if not self.is_connected:
                await self._connect()

            if self._linebreak is None:
                self._linebreak = await self.linebreak()

            if not self._writer or not self._reader:
                raise _CommandException

            # Let's add the path and send the command
            full_cmd = f"{_PATH_EXPORT_COMMAND} && {command}"
            self._writer.write((full_cmd + "\n").encode("ascii"))
            # And read back the data till the prompt string
            data = await wait_for(
                self._reader.readuntil(self._prompt_string), 9
            )
        except (BrokenPipeError, LimitOverrunError, IncompleteReadError) as ex:
            # Writing has failed, Let's close and retry if necessary
            _LOGGER.warning("connection is lost to host.")
            self._disconnect()
            raise _CommandException from ex
        except TimeoutError as ex:
            _LOGGER.error("Host timeout.")
            self._disconnect()
            raise _CommandException from ex

        # Let's process the received data
        data_list = data.split(b"\n")
        # Let's find the number of elements the cmd takes
        cmd_len = len(self._prompt_string) + len(full_cmd)
        # We have to do floor + 1 to handle the infinite case correct
        start_split = floor(cmd_len / self._linebreak) + 1
        return list(line.decode("utf-8") for line in data_list[start_split:-1])

    @override
    async def _connect(self) -> None:
        if self.is_connected:
            self._disconnect()

        self._reader, self._writer = await open_connection(
            self._host, self._port
        )

        # Process the login
        # Enter the Username
        try:
            _ = await wait_for(self._reader.readuntil(b"login: "), 9)
        except IncompleteReadError:
            _LOGGER.error(
                "Unable to read from router on %s:%s", self._host, self._port
            )
            return
        except TimeoutError:
            _LOGGER.error("Host timeout.")
            self._disconnect()

        self._writer.write((self._username or "" + "\n").encode("ascii"))

        # Enter the password
        _ = await self._reader.readuntil(b"Password: ")
        self._writer.write((self._password or "" + "\n").encode("ascii"))

        # Now we can determine the prompt string for the commands.
        self._prompt_string = (await self._reader.readuntil(b"#")).split(
            b"\n"
        )[-1]

    async def linebreak(self) -> float:
        """
        Get linebreak.

        Telnet or asyncio seems to be adding linebreaks due to terminal size.
        Try to determine here what the column number is.
        """
        # Let's determine if any linebreaks are added
        # Write some arbitrary long string.
        if not self._writer or not self._reader:
            raise _CommandException

        self._writer.write((" " * 200 + "\n").encode("ascii"))
        input_bytes = await self._reader.readuntil(self._prompt_string)

        return self._determine_linebreak(input_bytes)

    def _determine_linebreak(self, input_bytes: bytes) -> float:
        # Let's convert the data to the expected format
        data = input_bytes.decode("utf-8").replace("\r", "").split("\n")
        if len(data) == 1:
            # There was no split, so assume infinite
            linebreak = float("inf")
        else:
            # The linebreak is the length of the prompt string + the first line
            linebreak = len(self._prompt_string) + len(data[0])

            if len(data) > 2:
                # We can do a quick sanity check, as there are more linebreaks
                if len(data[1]) != linebreak:
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
    def _disconnect(self) -> None:
        """
        Disconnect the connection.

        Ensure that the caller holds the io_lock.
        """
        if self._writer:
            self._writer.close()
        self._writer = None
        self._reader = None
        self._linebreak = None
