"""Module for connections."""
import asyncio
import logging
from asyncio import LimitOverrunError, TimeoutError

import asyncssh

_LOGGER = logging.getLogger(__name__)

_PATH_EXPORT_COMMAND = "PATH=$PATH:/bin:/usr/sbin:/sbin"
asyncssh.set_log_level('WARNING')


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
                    result = await asyncio.wait_for(self._client.run(
                        "%s && %s" % (_PATH_EXPORT_COMMAND, command)), 9)
                except asyncssh.misc.ChannelOpenError:
                    if not retry:
                        await self.async_connect()
                        return await self.async_run_command(
                            command, retry=True)
                    else:
                        _LOGGER.error("Cant connect to host, giving up!")
                        return []
                except TimeoutError:
                    self._client = None
                    _LOGGER.error("Host timeout.")
                    return []

                return result.stdout.split('\n')

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
            'username': self._username if self._username else None,
            'client_keys': [self._ssh_key] if self._ssh_key else None,
            'port': self._port,
            'password': self._password if self._password else None,
            'known_hosts': None,
            'server_host_key_algs': ['ssh-rsa']
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
        self._connected = False
        self._io_lock = asyncio.Lock()

    async def async_run_command(self, command, first_try=True):
        """Run a command through a Telnet connection.
        Connect to the Telnet server if not currently connected, otherwise
        use the existing connection.
        """
        await self.async_connect()
        try:
            with (await self._io_lock):
                self._writer.write('{}\n'.format(
                    "%s && %s" % (
                        _PATH_EXPORT_COMMAND, command)).encode('ascii'))
                data = ((await asyncio.wait_for(self._reader.readuntil(
                    self._prompt_string), 9)).split(b'\n')[1:-1])

        except (BrokenPipeError, LimitOverrunError):
            if first_try:
                return await self.async_run_command(command, False)
            else:
                _LOGGER.warning("connection is lost to host.")
                return[]
        except TimeoutError:
            _LOGGER.error("Host timeout.")
            return []
        finally:
            self._writer.close()

        return [line.decode('utf-8') for line in data]

    async def async_connect(self):
        """Connect to the ASUS-WRT Telnet server."""
        self._reader, self._writer = await asyncio.open_connection(
            self._host, self._port)

        with (await self._io_lock):
            try:
                await asyncio.wait_for(self._reader.readuntil(b'login: '), 9)
            except asyncio.streams.IncompleteReadError:
                _LOGGER.error(
                    "Unable to read from router on %s:%s" % (
                        self._host, self._port))
                return
            except TimeoutError:
                _LOGGER.error("Host timeout.")
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

    async def disconnect(self):
        """Disconnects the client"""
        self._writer.close()
