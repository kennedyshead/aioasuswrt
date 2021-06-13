"""Module for connections."""
import asyncio
from asyncio import IncompleteReadError
import logging
from asyncio import LimitOverrunError, TimeoutError
from math import floor

import asyncssh

_LOGGER = logging.getLogger(__name__)

_PATH_EXPORT_COMMAND = "PATH=$PATH:/bin:/usr/sbin:/sbin"
asyncssh.set_log_level("WARNING")


class SshConnection:
    """Maintains an SSH connection to an ASUS-WRT router."""

    def __init__(self, host, port, username, password, ssh_key):
        """Initialize the SSH connection properties."""
        self._host = host
        self._port = port or 22
        self._username = username
        self._password = password
        self._ssh_key = ssh_key
        self._client = None

    async def async_run_command(self, command, retry=False):
        """Run commands through an SSH connection.
        Connect to the SSH server if not currently connected, otherwise
        use the existing connection.
        """
        if self._client is None and not retry:
            await self.async_connect()
            return await self.async_run_command(command, retry=True)
        else:
            if self._client is not None:
                try:
                    result = await asyncio.wait_for(
                        self._client.run("%s && %s" % (_PATH_EXPORT_COMMAND, command)),
                        9,
                    )
                except asyncssh.misc.ChannelOpenError:
                    if not retry:
                        await self.async_connect()
                        return await self.async_run_command(command, retry=True)
                    else:
                        _LOGGER.error("Cant connect to host, giving up!")
                        return []
                except TimeoutError:
                    self._client = None
                    _LOGGER.error("Host timeout.")
                    return []

                return result.stdout.split("\n")

            else:
                _LOGGER.error("Cant connect to host, giving up!")
                return []

    @property
    def is_connected(self):
        """Do we have a connection."""
        return self._client is not None

    async def async_connect(self):
        """Fetches the client or creates a new one."""

        kwargs = {
            "username": self._username if self._username else None,
            "client_keys": [self._ssh_key] if self._ssh_key else None,
            "port": self._port,
            "password": self._password if self._password else None,
            "known_hosts": None,
            'server_host_key_algs': ['ssh-rsa'],
        }

        self._client = await asyncssh.connect(self._host, **kwargs)


class TelnetConnection:
    """Maintains a Telnet connection to an ASUS-WRT router."""

    def __init__(self, host, port, username, password):
        """Initialize the Telnet connection properties."""
        self._reader = None
        self._writer = None
        self._host = host
        self._port = port or 23
        self._username = username
        self._password = password
        self._prompt_string = None
        self._io_lock = asyncio.Lock()
        self._linebreak = None

    async def async_run_command(self, command, first_try=True):
        """Run a command through a Telnet connection. If first_try is True a second
        attempt will be done if the first try fails."""

        need_retry = False

        async with self._io_lock:
            try:
                if not self.is_connected:
                    await self._async_connect()
                # Let's add the path and send the command
                full_cmd = f"{_PATH_EXPORT_COMMAND} && {command}"
                self._writer.write((full_cmd + "\n").encode("ascii"))
                # And read back the data till the prompt string
                data = await asyncio.wait_for(
                    self._reader.readuntil(self._prompt_string), 9
                )
            except (BrokenPipeError, LimitOverrunError, IncompleteReadError):
                # Writing has failed, Let's close and retry if necessary
                self.disconnect()
                if first_try:
                    need_retry = True
                else:
                    _LOGGER.warning("connection is lost to host.")
                    return []
            except TimeoutError:
                _LOGGER.error("Host timeout.")
                self.disconnect()
                if first_try:
                    need_retry = True
                else:
                    return []

        if need_retry:
            _LOGGER.debug("Trying one more time")
            return await self.async_run_command(command, False)

        # Let's process the received data
        data = data.split(b"\n")
        # Let's find the number of elements the cmd takes
        cmd_len = len(self._prompt_string) + len(full_cmd)
        # We have to do floor + 1 to handle the infinite case correct
        start_split = floor(cmd_len / self._linebreak) + 1
        data = data[start_split:-1]
        return [line.decode("utf-8", "ignore") for line in data]

    async def async_connect(self):
        """Connect to the ASUS-WRT Telnet server."""
        async with self._io_lock:
            await self._async_connect()

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
            self.disconnect()
        self._writer.write((self._username + "\n").encode("ascii"))

        # Enter the password
        await self._reader.readuntil(b"Password: ")
        self._writer.write((self._password + "\n").encode("ascii"))

        # Now we can determine the prompt string for the commands.
        self._prompt_string = (await self._reader.readuntil(b"#")).split(b"\n")[-1]

        # Let's determine if any linebreaks are added
        # Write some arbitrary long string.
        if self._linebreak is None:
            self._writer.write((" " * 200 + "\n").encode("ascii"))
            self._determine_linebreak(
                await self._reader.readuntil(self._prompt_string)
            )

    def _determine_linebreak(self, input_bytes: bytes):
        """Telnet or asyncio seems to be adding linebreaks due to terminal size,
        try to determine here what the column number is."""
        # Let's convert the data to the expected format
        data = input_bytes.decode("utf-8").replace("\r", "").split("\n")
        if len(data) == 1:
            # There was no split, so assume infinite
            self._linebreak = float("inf")
        else:
            # The linebreak is the length of the prompt string + the first line
            self._linebreak = len(self._prompt_string) + len(data[0])

            if len(data) > 2:
                # We can do a quick sanity check, as there are more linebreaks
                if len(data[1]) != self._linebreak:
                    _LOGGER.warning(
                        f"Inconsistent linebreaks {len(data[1])} != "
                        f"{self._linebreak}"
                    )

    @property
    def is_connected(self):
        """Do we have a connection."""
        return self._reader is not None and self._writer is not None

    def disconnect(self):
        """Disconnects the client"""
        self._writer = None
        self._reader = None
