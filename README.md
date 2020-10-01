Small wrapper for asuswrt. ![Python package](https://github.com/kennedyshead/aioasuswrt/workflows/Python%20package/badge.svg)

### How to run tests

`python setup.py test`

## Credits:
[@mvn23](https://github.com/mvn23)
[@halkeye](https://github.com/halkeye)
[@maweki](https://github.com/maweki)
[@quarcko](https://github.com/quarcko)
[@wdullaer](https://github.com/wdullaer)

## Info
There are many different versions of asuswrt and sometimes they just dont work in current implementation.
If you have a problem with your specific router open an issue, but please add as much info as you can and atleast:

* Version of router
* Version of Asuswrt

## Known issues

## Bugs
You can always create an issue in this tracker.
To test and give us the information needed you could run:
```python
#!/usr/bin/env python
import asyncio
import logging

import sys

from aioasuswrt.asuswrt import AsusWrt

component = AsusWrt('192.168.1.1', 22, username='****', password='****')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def print_data():
    logger.debug("wl")
    logger.debug(await component.connection.async_run_command('for dev in `nvram get wl_ifnames`; do wl -i $dev assoclist; done'))
    dev = await component.async_get_wl()
    logger.debug(dev)
    logger.debug("arp")
    logger.debug(await component.connection.async_run_command('arp -n'))
    dev.update(await component.async_get_arp())
    logger.debug(dev)
    logger.debug("neigh")
    logger.debug(await component.connection.async_run_command('ip neigh'))
    dev.update(await component.async_get_neigh(dev))
    logger.debug(dev)
    logger.debug("leases")
    logger.debug(await component.connection.async_run_command('cat /var/lib/misc/dnsmasq.leases'))
    dev.update(await component.async_get_leases(dev))
    logger.debug(dev)


loop = asyncio.get_event_loop()

loop.run_until_complete(print_data())
loop.close()

```
Coffeefund: 1Huz6vNN6drX3Fq1sU98wPqNSdMPvkMBJG
