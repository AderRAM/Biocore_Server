import json
import queue
import time
import threading
from datetime import datetime
from flask import Blueprint, request, jsonify, Response
from models import leituras, comandos

esp32_bp = Blueprint("esp32", __name__)

_subscribers: list[queue.Queue] = []
_lock = threading.Lock()
_ultimo_envio = 0.0
_INTERVALO_MIN = 0.5  # segundos — throttle apenas para leituras de sensor


def _publicar(dados: dict, throttle: bool = True):
    """Envia dados para todos os browsers via SSE."""
    global _ultimo_envio
    if throttle:
        agora = time.monotonic()
        if agora - _ultimo_envio < _INTERVALO_MIN:
            return
        _ultimo_envio = agora
    with _lock:
        mortos = []
        for q in _subscribers:
            try:
                q.put_nowait(dados)
            except queue.Full:
                mortos.append(q)
        for q in mortos:
            _subscribers.remove(q)


def publicar_evento(tipo: str, mensagem: str):
    """Publica evento de sistema no log do painel (sem throttle)."""
    _publicar({"_evento": tipo, "mensagem": mensagem}, throttle=False)


@esp32_bp.get("/api/stream")
def stream():
    q: queue.Queue = queue.Queue(maxsize=10)
    with _lock:
        _subscribers.append(q)

    def gerar():
        try:
            while True:
                try:
                    dados = q.get(timeout=25)
                    yield f"data: {json.dumps(dados)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with _lock:
                if q in _subscribers:
                    _subscribers.remove(q)

    return Response(gerar(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@esp32_bp.post("/api/leitura")
def receber_leitura():
    dados = request.get_json(silent=True)
    if not dados or "dispositivo_id" not in dados:
        return jsonify({"erro": "payload invalido"}), 400

    campos = {
        "dispositivo_id":       dados.get("dispositivo_id"),
        "umidade_solo_bruto":   dados.get("umidade_solo_bruto"),
        "umidade_solo_percent": dados.get("umidade_solo_percent"),
        "temperatura":          dados.get("temperatura"),
        "umidade_ar":           dados.get("umidade_ar"),
        "luminosidade_bruto":   dados.get("luminosidade_bruto"),
        "luminosidade_percent": dados.get("luminosidade_percent"),
        "bomba":                int(bool(dados.get("bomba", False))),
    }
    leituras.salvar(campos)
    campos["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _publicar(campos)
    print(f"[ESP32] Leitura recebida | "
          f"solo={campos['umidade_solo_percent']:.1f}% "
          f"temp={campos['temperatura']}°C "
          f"bomba={'ON' if campos['bomba'] else 'OFF'}")
    return jsonify({"ok": True}), 201


@esp32_bp.get("/api/comando")
def fornecer_comando():
    dispositivo_id = request.args.get("dispositivo_id", "")
    if not dispositivo_id:
        return jsonify({"erro": "dispositivo_id obrigatorio"}), 400
    return jsonify(comandos.consumir(dispositivo_id)), 200
