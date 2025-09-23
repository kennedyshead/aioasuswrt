"""Module for connections."""

import abc
import asyncio
import logging
from asyncio import IncompleteReadError, LimitOverrunError, TimeoutError
from asyncio.streams import StreamReader, StreamWriter
from math import floor
from typing import List, Optional

import asyncssh

_LOGGER = logging.getLogger(__name__)

_PATH_EXPORT_COMMAND: str = "PATH=$PATH:/bin:/usr/sbin:/sbin"
asyncssh.set_log_level("WARNING")


class _CommandException(Exception):
    """Protected command exception."""


class _BaseConnection(abc.ABC):
    def __init__(
        self,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._host: str = host
        self._port: int = port
        self._username: Optional[str] = username
        self._password: Optional[str] = password

        self._io_lock = asyncio.Lock()

    @property
    def description(self) -> str:
        """Description of the connection."""
        ret = f"{self._host}:{self._port}"
        if self._username:
            ret = f"{self._username}@{ret}"

        return ret

    async def async_run_command(
        self, command: str, retry: bool = True
    ) -> List[str]:
        """Call a command using the connection."""
        async with self._io_lock:
            if not self.is_connected:
                await self.async_connect()

            try:
                return await self._async_call_command(command)
            except _CommandException as ex:
                _LOGGER.exception(ex)

        # The command failed
        if retry:
            _LOGGER.debug(f"Retrying command: {command}")
            return await self._async_call_command(command)
        return []

    async def async_connect(self) -> None:
        if self.is_connected:
            _LOGGER.debug(
                f"Connection already established to: {self.description}"
            )
            return

        await self._async_connect()

    async def async_disconnect(self) -> None:
        """Disconnect the client."""
        async with self._io_lock:
            self._disconnect()

    @abc.abstractmethod
    async def _async_call_command(self, command: str) -> List[str]:
        """Call the command."""

    @abc.abstractmethod
    async def _async_connect(self) -> None:
        """Establish a connection."""

    @abc.abstractmethod
    def _disconnect(self) -> None:
        """Disconnect."""

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Do we have a connection."""
        pass


def create_connection(
    use_telnet: bool,
    host: str,
    port: Optional[int],
    username: Optional[str],
    password: Optional[str],
    ssh_key: Optional[str],
) -> _BaseConnection:
    """Create a connection to the router."""
    if use_telnet:
        return TelnetConnection(
            host=host, port=port, username=username, password=password
        )
    else:
        return SshConnection(
            host=host,
            port=port,
            username=username,
            password=password,
            ssh_key=ssh_key,
        )


class SshConnection(_BaseConnection):
    """Maintains an SSH connection to an ASUS-WRT router."""

    def __init__(
        self,
        host: str,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssh_key: Optional[str] = None,
        passphrase: Optional[str] = None,
    ):
        """Initialize the SSH connection properties."""
        super().__init__(host, port or 22, username, password)
        self._ssh_key = ssh_key
        self._client: Optional[asyncssh] = None
        self._lock = asyncio.Lock()
        self._passphrase: Optional[str] = passphrase

    async def _async_call_command(self, command: str) -> List[str]:
        """
        Run commands through an SSH connection.

        Connect to the SSH server if not currently connected, otherwise
        use the existing connection.
        """
        if not self._client:
            raise ConnectionError("Lost connection to router")

        async with self._lock:
            result = await asyncio.wait_for(
                self._client.run("%s && %s" % (_PATH_EXPORT_COMMAND, command)),
                9,
            )
        return list(result.stdout.split("\n"))

    @property
    def is_connected(self) -> bool:
        """Do we have a connection."""
        return self._client is not None

    async def _async_connect(self) -> None:
        """Fetch the client or creates a new one."""
        kwargs = {
            "username": self._username,
            "client_keys": [self._ssh_key] if self._ssh_key else None,
            "port": self._port,
            "password": self._password,
            "passphrase": self._passphrase,
            "known_hosts": None,
            "server_host_key_algs": [
                "ssh-rsa",
                "rsa-sha2-256",
                "rsa-sha2-512",
                "ecdsa-sha2-nistp256",
                "ecdsa-sha2-nistp384",
                "ecdsa-sha2-nistp521",
                "ssh-ed25519",
                "ssh-ed448",
            ],
        }
        async with self._lock:
            if self._client:
                _LOGGER.debug(
                    "reconnecting; old connection had local port %d",
                    self._client._local_port if self._client else "Unknown",
                )
                self._disconnect()
            else:
                _LOGGER.debug("reconnecting; no old connection existed")
            self._client = await asyncssh.connect(self._host, **kwargs)
            _LOGGER.debug(
                "reconnected; new connection has local port %d",
                self._client._local_port if self._client else "Unknown",
            )

    def _disconnect(self) -> None:
        if self._client:
            self._client.close()
        self._client = None


class TelnetConnection(_BaseConnection):
    """Maintains a Telnet connection to an ASUS-WRT router."""

    def __init__(
        self,
        host: str,
        port: Optional[int],
        username: Optional[str],
        password: Optional[str],
    ):
        """Initialize the Telnet connection properties."""
        super().__init__(host, port or 23, username, password)
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None
        self._prompt_string = "".encode("ascii")
        self._linebreak: Optional[float] = None

    async def _async_call_command(self, command: str) -> List[str]:
        """Run a command through a Telnet connection."""
        try:
            if not self.is_connected:
                await self._async_connect()

            if self._linebreak is None:
                self._linebreak = await self._async_linebreak()

            if not self._writer or not self._reader:
                raise _CommandException

            # Let's add the path and send the command
            full_cmd = f"{_PATH_EXPORT_COMMAND} && {command}"
            self._writer.write((full_cmd + "\n").encode("ascii"))
            # And read back the data till the prompt string
            data = await asyncio.wait_for(
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

    async def async_connect(self) -> None:
        """Connect to the ASUS-WRT Telnet server."""
        async with self._io_lock:
            await self._async_connect()

    async def _async_connect(self) -> None:
        if self.is_connected:
            self._disconnect()

        self._reader, self._writer = await asyncio.open_connection(
            self._host, self._port
        )

        # Process the login
        # Enter the Username
        try:
            await asyncio.wait_for(self._reader.readuntil(b"login: "), 9)
        except asyncio.IncompleteReadError:
            _LOGGER.error(
                "Unable to read from router on %s:%s"
                % (self._host, self._port)
            )
            return
        except TimeoutError:
            _LOGGER.error("Host timeout.")
            self._disconnect()

        self._writer.write((self._username or "" + "\n").encode("ascii"))

        # Enter the password
        await self._reader.readuntil(b"Password: ")
        self._writer.write((self._password or "" + "\n").encode("ascii"))

        # Now we can determine the prompt string for the commands.
        self._prompt_string = (await self._reader.readuntil(b"#")).split(
            b"\n"
        )[-1]

    async def _async_linebreak(self) -> float:
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
                        f"Inconsistent linebreaks {len(data[1])} != "
                        f"{linebreak}"
                    )

        return linebreak

    @property
    def is_connected(self) -> bool:
        """Do we have a connection."""
        return self._reader is not None and self._writer is not None

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
