import asyncio
from bleak import BleakScanner

async def scan():
    print("Escaneando 10 segundos...")
    devices = await BleakScanner.discover(timeout=10)
    for d in devices:
        print(f"  {d.name} — {d.address}")

asyncio.run(scan())
