#!/usr/bin/env python3
# Teste direto da bomba via BLE — sem precisar do servidor Flask.
# Uso: python testar_bomba.py

import asyncio
import json
from bleak import BleakClient, BleakScanner

NOME_DISPOSITIVO  = "BioCore"
CHAR_LEITURA_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
CHAR_COMANDO_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a9"

TEMPO_BOMBA_LIGADA = 5  # segundos com a bomba ligada


def ao_receber_leitura(sender, data: bytearray):
    try:
        payload = json.loads(data.decode("utf-8"))
        print(f"  ESP32 | umidade_solo={payload.get('umidade_solo_percent')}%  "
              f"temp={payload.get('temperatura')}°C  "
              f"bomba={'LIGADA' if payload.get('bomba') else 'desligada'}")
    except Exception:
        pass


async def enviar(client: BleakClient, comando: dict):
    payload = json.dumps(comando).encode("utf-8")
    await client.write_gatt_char(CHAR_COMANDO_UUID, payload, response=False)
    print(f"[→ ESP32] {comando}")


async def testar():
    print(f"[BLE] Procurando '{NOME_DISPOSITIVO}' (timeout 15s)...")
    dispositivo = await BleakScanner.find_device_by_name(NOME_DISPOSITIVO, timeout=15)

    if dispositivo is None:
        print("[ERRO] ESP32 não encontrado. Verifique se está ligado e com firmware gravado.")
        return

    print(f"[BLE] Encontrado: {dispositivo.name}  {dispositivo.address}")

    async with BleakClient(dispositivo) as client:
        print("[BLE] Conectado!\n")
        await client.start_notify(CHAR_LEITURA_UUID, ao_receber_leitura)

        print("─── LIGANDO BOMBA ───────────────────────────────")
        await enviar(client, {"bomba": True})
        await asyncio.sleep(TEMPO_BOMBA_LIGADA)

        print("─── DESLIGANDO BOMBA ────────────────────────────")
        await enviar(client, {"bomba": False})
        await asyncio.sleep(2)

        await client.stop_notify(CHAR_LEITURA_UUID)
        print("\n[OK] Teste concluído.")


if __name__ == "__main__":
    try:
        asyncio.run(testar())
    except KeyboardInterrupt:
        print("\n[BLE] Interrompido pelo usuário.")
