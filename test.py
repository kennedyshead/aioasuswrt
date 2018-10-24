from aioasuswrt.asuswrt import *
import asyncio

conn = AsusWrt('192.168.1.1', 22, username='knutas', password='Freakdays123')

asyncio.run(conn.async_get_packets_total())
