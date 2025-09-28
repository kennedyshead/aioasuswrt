# AioAsusWRT

![Python package](https://github.com/kennedyshead/aioasuswrt/workflows/Python%20package/badge.svg) [![Upload Python Package](https://github.com/kennedyshead/aioasuswrt/actions/workflows/python-publish.yml/badge.svg)](https://github.com/kennedyshead/aioasuswrt/actions/workflows/python-publish.yml)

Small wrapper for asuswrt.

## Setup

```bash
pipenv install --dev
pre-commit install
```

## Run lint/tests

```bash
pre-commit run --all-files
pytest .
```

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
To test and give us the information needed you should run:
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
    dev = {}
    await component.async_get_wl(dev)
    await component.async_get_arp(dev)
    dev.update(await component.async_get_neigh(dev))
    dev.update(await component.async_get_leases(dev))
    dev.update(await component.async_filter_dev_list(dev))
    await component.async_get_connected_devices(dev)
    __import__("pprint").pprint(dev)

    i = 0
    while True:
        print(await component.async_current_transfer_human_readable())
        await asyncio.sleep(10)
        i += 1
        if i > 6:
            break



loop = asyncio.get_event_loop()

loop.run_until_complete(print_data())
loop.close()
```
