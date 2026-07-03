# BioCore - Ponte BLE
# Conecta ao ESP32 via Bluetooth e repassa os dados ao servidor Flask.
#
# Como usar:
#   1. Inicie o servidor Flask:  python app.py
#   2. Em outro terminal:        python ponte.py

import asyncio
import json
import requests
from bleak import BleakClient, BleakScanner

# ─── UUIDs (devem ser iguais ao firmware do ESP32) ────────────────────────────
CHAR_LEITURA_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"  # ESP32 → Notebook
CHAR_COMANDO_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a9"  # Notebook → ESP32

NOME_DISPOSITIVO  = "BioCore"
SERVIDOR_URL      = "http://localhost:5001"
INTERVALO_RETRY   = 5  # segundos entre tentativas de scan/reconexão


# ─── Recebe notificação do ESP32 e repassa ao Flask ───────────────────────────
def ao_receber_leitura(sender, data: bytearray):
    texto = data.decode("utf-8")
    print(f"[BLE] Recebido: {texto}")

    try:
        payload = json.loads(texto)
    except json.JSONDecodeError:
        print("[BLE] JSON inválido, ignorando.")
        return

    try:
        res = requests.post(f"{SERVIDOR_URL}/api/leitura", json=payload, timeout=5)
        print(f"[Servidor] Resposta {res.status_code}: {res.json()}")
    except requests.exceptions.ConnectionError:
        print("[Servidor] Flask não está rodando ou não acessível.")


# ─── Busca comando pendente no Flask e envia ao ESP32 via BLE ────────────────
async def enviar_comando_pendente(client: BleakClient):
    try:
        res = requests.get(
            f"{SERVIDOR_URL}/api/comando",
            params={"dispositivo_id": "esp32-biocore-01"},
            timeout=3,
        )
        comando = res.json()
        if not comando:
            return
        payload = json.dumps(comando).encode("utf-8")
        await client.write_gatt_char(CHAR_COMANDO_UUID, payload, response=True)
        print(f"[Comando] Enviado ao ESP32: {comando}")
    except requests.exceptions.ConnectionError:
        pass
    except Exception as e:
        print(f"[Comando] Erro: {e}")


# ─── Escaneia, conecta e reconecta automaticamente ───────────────────────────
async def conectar_e_manter():
    while True:
        print(f"[BLE] Escaneando por '{NOME_DISPOSITIVO}'...")

        try:
            dispositivo = await BleakScanner.find_device_by_name(
                NOME_DISPOSITIVO, timeout=15
            )
        except Exception as e:
            print(f"[BLE] Erro no scan: {e}. Tentando novamente em {INTERVALO_RETRY}s...")
            await asyncio.sleep(INTERVALO_RETRY)
            continue

        if dispositivo is None:
            print(f"[BLE] '{NOME_DISPOSITIVO}' não encontrado. "
                  f"Tentando novamente em {INTERVALO_RETRY}s...")
            await asyncio.sleep(INTERVALO_RETRY)
            continue

        print(f"[BLE] Encontrado: {dispositivo.name} ({dispositivo.address})")
        print(f"[BLE] Conectando...")

        try:
            async with BleakClient(dispositivo) as client:
                print(f"[BLE] Conectado! Aguardando leituras...\n")

                await client.start_notify(CHAR_LEITURA_UUID, ao_receber_leitura)

                # Mantém a conexão aberta e verifica comandos pendentes a cada 3s
                while True:
                    await enviar_comando_pendente(client)
                    await asyncio.sleep(3)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[BLE] Conexão perdida: {e}. Reconectando em {INTERVALO_RETRY}s...")
            await asyncio.sleep(INTERVALO_RETRY)


# ─── Ponto de entrada ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(conectar_e_manter())
    except KeyboardInterrupt:
        print("\n[BLE] Encerrado pelo usuário.")
