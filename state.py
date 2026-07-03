import threading

_lock = threading.Lock()
_ble  = {"status": "iniciando", "dispositivo": None, "erro": None}

# Flask seta este evento para sinalizar reconexão ao loop BLE
reconectar = threading.Event()


def set_ble(**kw):
    with _lock:
        _ble.update(kw)


def get_ble() -> dict:
    with _lock:
        return dict(_ble)
