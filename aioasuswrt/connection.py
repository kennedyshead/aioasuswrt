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

_PATH_EXPORT_COMMAND = "PATH=$PATH:/bin:/usr/sbin:/sbin"
asyncssh.set_log_level("WARNING")


class _CommandException(Exception):
    pass


class _BaseConnection(abc.ABC):
    def __init__(
        self, host: str, port: int, username: Optional[str], password: Optional[str]
    ):
        self._host = host
        self._port = port
        self._username = username if username else None
        self._password = password if password else None

        self._io_lock = asyncio.Lock()

    @property
    def description(self) -> str:
        """ Description of the connection."""
        ret = f"{self._host}:{self._port}"
        if self._username:
            ret = f"{self._username}@{ret}"

        return ret

    async def async_run_command(self, command: str, retry=True) -> List[str]:
        """ Call a command using the connection."""
        async with self._io_lock:
            if not self.is_connected:
                await self.async_connect()

            try:
                return await self._async_call_command(command)
            except _CommandException:
                pass

        # The command failed
        if retry:
            _LOGGER.debug(f"Retrying command: {command}")
            return await self._async_call_command(command)
        return []

    async def async_connect(self):
        if self.is_connected:
            _LOGGER.debug(f"Connection already established to: {self.description}")
            return

        await self._async_connect()

    async def async_disconnect(self):
        """Disconnects the client"""
        async with self._io_lock:
            self._disconnect()

    @abc.abstractmethod
    async def _async_call_command(self, command: str) -> List[str]:
        """ Call the command."""
        pass

    @abc.abstractmethod
    async def _async_connect(self):
        """ Establish a connection."""
        pass

    @abc.abstractmethod
    def _disconnect(self):
        """ Disconnect."""
        pass

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

    if use_telnet:
        return TelnetConnection(
            host=host, port=port, username=username, password=password
        )
    else:
        return SshConnection(
            host=host, port=port, username=username, password=password, ssh_key=ssh_key
        )


class SshConnection(_BaseConnection):
    """Maintains an SSH connection to an ASUS-WRT router."""

    def __init__(
        self,
        host: str,
        port: Optional[int],
        username: Optional[str],
        password: Optional[str],
        ssh_key: Optional[str],
    ):
        """Initialize the SSH connection properties."""
        super().__init__(host, port or 22, username, password)
        self._ssh_key = ssh_key
        self._client = None

    async def _async_call_command(self, command: str) -> List[str]:
        """Run commands through an SSH connection.
        Connect to the SSH server if not currently connected, otherwise
        use the existing connection.
        """
        try:
            if not self.is_connected:
                await self._async_connect()
            if not self._client:
                raise _CommandException

            result = await asyncio.wait_for(
                self._client.run(f"{_PATH_EXPORT_COMMAND} && {command}"),
                9,
            )
        except asyncssh.misc.ChannelOpenError as ex:
            self._disconnect()
            _LOGGER.warning("Not connected to host")
            raise _CommandException from ex
        except TimeoutError as ex:
            self._disconnect()
            _LOGGER.error("Host timeout.")
            raise _CommandException from ex

        return result.stdout.split("\n")

    @property
    def is_connected(self) -> bool:
        """Do we have a connection."""
        return self._client is not None

    async def _async_connect(self):
        """Fetches the client or creates a new one."""
        kwargs = {
            "username": self._username if self._username else None,
            "client_keys": [self._ssh_key] if self._ssh_key else None,
            "port": self._port,
            "password": self._password if self._password else None,
            "known_hosts": None,
        }

        self._client = await asyncssh.connect(self._host, **kwargs)

    def _disconnect(self):
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

    async def _async_call_command(self, command):
        """Run a command through a Telnet connection. If first_try is True a second
        attempt will be done if the first try fails."""
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
        return [line.decode("utf-8") for line in data_list[start_split:-1]]

    async def _async_connect(self):
        self._reader, self._writer = await asyncio.open_connection(
            self._host, self._port
        )

        # Process the login
        # Enter the Username
        try:
            await asyncio.wait_for(self._reader.readuntil(b"login: "), 9)
        except asyncio.IncompleteReadError:
            _LOGGER.error(
                "Unable to read from router on %s:%s" % (self._host, self._port)
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
        self._prompt_string = (await self._reader.readuntil(b"#")).split(b"\n")[-1]

    async def _async_linebreak(self) -> float:
        """Telnet or asyncio seems to be adding linebreaks due to terminal size,
        try to determine here what the column number is."""
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
                        f"Inconsistent linebreaks {len(data[1])} != " f"{linebreak}"
                    )

        return linebreak

    @property
    def is_connected(self) -> bool:
        """Do we have a connection."""
        return self._reader is not None and self._writer is not None

    def _disconnect(self):
        """ Disconnect the connection, ensure that the caller holds the io_lock."""
        self._writer = None
        self._reader = None
        self._linebreak = None
