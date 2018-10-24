from aioasuswrt.asuswrt import *
import asyncio

conn = AsusWrt('192.168.1.1', 22, username='knutas', password='Freakdays123')

loop = asyncio.get_event_loop()


async def printer(cmd):
    data = await cmd()
    print(data)

loop.run_until_complete(printer(conn.async_get_packets_total))
loop.run_until_complete(printer(conn.async_get_rx))
loop.run_until_complete(printer(conn.async_get_tx))
loop.run_until_complete(printer(conn.async_get_current_transfer_rates))
loop.run_until_complete(printer(conn.async_get_current_transfer_rates))
loop.run_until_complete(printer(conn.async_get_current_transfer_rates))

