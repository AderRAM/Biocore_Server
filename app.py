# BioCore — Servidor + Ponte BLE integrados
#
# Inicie com:
#   python app.py

import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bleak import BleakClient, BleakScanner
from flask import Flask

import config
import database
import state
from routes.esp32 import esp32_bp, publicar_evento
from routes.painel import painel_bp

# ─── Configuração BLE ─────────────────────────────────────────────────────────
CHAR_LEITURA_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
CHAR_COMANDO_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a9"
NOME_DISPOSITIVO  = "BioCore"
SERVIDOR_URL      = f"http://localhost:{config.PORT}"
INTERVALO_RETRY   = 5

# Pool dedicado para as chamadas HTTP bloqueantes — não bloqueia o event loop
_http_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="BLE-HTTP")


# ─── Ponte BLE ────────────────────────────────────────────────────────────────
def _postar_leitura(payload: dict):
    """Executa em thread separada — não toca no event loop asyncio."""
    try:
        requests.post(f"{SERVIDOR_URL}/api/leitura", json=payload, timeout=5)
    except Exception:
        pass


def ao_receber_leitura(sender, data: bytearray):
    try:
        payload = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    # Despacha para thread — mantém o event loop asyncio livre
    _http_pool.submit(_postar_leitura, payload)


async def enviar_comando_pendente(client: BleakClient):
    loop = asyncio.get_event_loop()
    try:
        # HTTP bloqueante roda no pool, não trava o event loop
        res = await loop.run_in_executor(
            _http_pool,
            lambda: requests.get(
                f"{SERVIDOR_URL}/api/comando",
                params={"dispositivo_id": "esp32-biocore-01"},
                timeout=3,
            ),
        )
        comando = res.json()
        if not comando:
            return
        await client.write_gatt_char(
            CHAR_COMANDO_UUID, json.dumps(comando).encode(), response=True
        )
        print(f"[BLE] Comando enviado: {comando}")
    except requests.exceptions.ConnectionError:
        pass
    except Exception as e:
        print(f"[BLE] Erro ao enviar comando: {e}")


async def conectar_e_manter():
    while True:
        state.reconectar.clear()
        state.set_ble(status="escaneando", dispositivo=None, erro=None)
        publicar_evento("ble", f"Escaneando por '{NOME_DISPOSITIVO}'...")
        print(f"[BLE] Escaneando por '{NOME_DISPOSITIVO}'...")

        try:
            disp = await BleakScanner.find_device_by_name(NOME_DISPOSITIVO, timeout=15)
        except Exception as e:
            state.set_ble(status="erro", erro=str(e))
            publicar_evento("ble_erro", f"Erro no scan: {e}")
            print(f"[BLE] Erro no scan: {e}")
            await asyncio.sleep(INTERVALO_RETRY)
            continue

        if disp is None:
            msg = f"'{NOME_DISPOSITIVO}' não encontrado. Tentando em {INTERVALO_RETRY}s..."
            publicar_evento("ble", msg)
            print(f"[BLE] {msg}")
            await asyncio.sleep(INTERVALO_RETRY)
            continue

        state.set_ble(status="conectando", dispositivo=disp.name)
        publicar_evento("ble_ok", f"ESP32 encontrado ({disp.address}). Conectando...")
        print(f"[BLE] Encontrado: {disp.name} ({disp.address}). Conectando...")

        try:
            async with BleakClient(disp) as client:
                state.set_ble(status="conectado", dispositivo=disp.name)
                publicar_evento("ble_ok", "BLE conectado! Aguardando leituras do ESP32...")
                print("[BLE] Conectado!\n")

                await client.start_notify(CHAR_LEITURA_UUID, ao_receber_leitura)

                while True:
                    if state.reconectar.is_set():
                        publicar_evento("ble", "Reconexão solicitada pelo usuário.")
                        print("[BLE] Reconexão forçada.")
                        break
                    await enviar_comando_pendente(client)
                    await asyncio.sleep(3)

        except Exception as e:
            msg = str(e) or type(e).__name__
            print(f"[BLE] Conexão perdida: {msg}. Reconectando em {INTERVALO_RETRY}s...")
        finally:
            # Garante que o estado nunca fica preso em "conectado" após queda
            if state.get_ble()["status"] in ("conectado", "conectando"):
                state.set_ble(status="desconectado", erro=None)
                publicar_evento("ble_erro", f"ESP32 desconectado. Reconectando em {INTERVALO_RETRY}s...")

        await asyncio.sleep(INTERVALO_RETRY)


def _ble_thread():
    time.sleep(1.5)
    while True:
        try:
            asyncio.run(conectar_e_manter())
        except KeyboardInterrupt:
            raise
        except BaseException as e:
            # BaseException captura CancelledError (que não é Exception no Python 3.8+)
            # — ocorre quando o BlueZ cancela tasks internas ao perder conexão
            print(f"[BLE] Loop caiu inesperadamente: {e!r}. Reiniciando em 5s...")
            state.set_ble(status="erro", erro=str(e) or type(e).__name__)
            publicar_evento("ble_erro", "Bridge BLE caiu. Reiniciando...")
            time.sleep(5)


# ─── Flask ────────────────────────────────────────────────────────────────────
def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(esp32_bp)
    app.register_blueprint(painel_bp)
    return app


if __name__ == "__main__":
    database.inicializar()
    app = create_app()

    t = threading.Thread(target=_ble_thread, daemon=True, name="BLE-Bridge")
    t.start()

    print(f"\n{'═' * 48}")
    print(f"  BioCore — Servidor + Ponte BLE")
    print(f"{'═' * 48}")
    print(f"  Painel  → http://localhost:{config.PORT}")
    print(f"  BLE     → buscando '{NOME_DISPOSITIVO}'...")
    print(f"  Banco   → {config.DB_PATH}")
    print(f"{'═' * 48}\n")

    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
