"""Module for connections."""
import asyncio
import logging

import asyncssh

_LOGGER = logging.getLogger(__name__)

_PATH_EXPORT_COMMAND = "PATH=$PATH:/bin:/usr/sbin:/sbin"


class SshConnection:
    """Maintains an SSH connection to an ASUS-WRT router."""

    def __init__(self, host, port, username, password, ssh_key):
        """Initialize the SSH connection properties."""

        self._connected = False
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ssh_key = ssh_key
        self._client = None

    async def async_run_command(self, command, retry=False):
        """Run commands through an SSH connection.

        Connect to the SSH server if not currently connected, otherwise
        use the existing connection.
        """
        if not self.is_connected:
            await self.async_connect()
        try:
            result = await self._client.run(
                "%s && %s" % (_PATH_EXPORT_COMMAND, command))
        except asyncssh.misc.ChannelOpenError:
            if not retry:
                await self.async_connect()
                return self.async_run_command(command, retry=True)
            else:
                self._connected = False
                _LOGGER.error("No connection to host")
                return []

        self._connected = True
        return result.stdout.split('\n')

    @property
    def is_connected(self):
        """Do we have a connection."""
        return self._connected

    async def async_connect(self):
        """Fetches the client or creates a new one."""

        kwargs = {
            'username': self._username if self._username else None,
            'client_keys': [self._ssh_key] if self._ssh_key else None,
            'port': self._port,
            'password': self._password if self._password else None,
            'known_hosts': None
        }

        self._client = await asyncssh.connect(self._host, **kwargs)
        self._connected = True


class TelnetConnection:
    """Maintains a Telnet connection to an ASUS-WRT router."""

    def __init__(self, host, port, username, password):
        """Initialize the Telnet connection properties."""

        self._reader = None
        self._writer = None
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._prompt_string = None
        self._connected = False

    async def async_run_command(self, command, first_try=True):
        """Run a command through a Telnet connection.
        Connect to the Telnet server if not currently connected, otherwise
        use the existing connection.
        """
        if not self._connected:
            await self.async_connect()
        self._writer.write('{}\n'.format(
                "%s && %s" % (_PATH_EXPORT_COMMAND, command)).encode('ascii'))
        try:
            data = ((await self._reader.readuntil(self._prompt_string)).
                split(b'\n')[1:-1])
        except BrokenPipeError:
            if first_try:
                self._connected = False
                return await self.async_run_command(command, False)
            else:
                _LOGGER.warning("connection is lost for router")
                return[]
        return [line.decode('utf-8') for line in data]

    async def async_connect(self):
        """Connect to the ASUS-WRT Telnet server."""
        self._reader, self._writer = await asyncio.open_connection(
            self._host, self._port)
        await self._reader.readuntil(b'login: ')
        self._writer.write((self._username + '\n').encode('ascii'))
        await self._reader.readuntil(b'Password: ')
        self._writer.write((self._password + '\n').encode('ascii'))
        self._prompt_string = (await self._reader.readuntil(
            b'#')).split(b'\n')[-1]
        self._connected = True

    @property
    def is_connected(self):
        """Do we have a connection."""
        return self._connected
