from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, render_template
from models import leituras, comandos
import state  # noqa: E402  (importado após routes para evitar circular import)

painel_bp = Blueprint("painel", __name__)


@painel_bp.get("/")
def index():
    return render_template("index.html")


@painel_bp.get("/api/leituras")
def listar_leituras():
    dispositivo_id = request.args.get("dispositivo_id")
    ip = request.remote_addr
    if ip != "127.0.0.1":
        print(f"[App] Conectado ({ip}) — solicitou leituras")
    try:
        limite = min(int(request.args.get("limite", 100)), 500)
    except ValueError:
        limite = 100
    return jsonify(leituras.buscar(dispositivo_id, limite)), 200


@painel_bp.post("/api/comando")
def enviar_comando():
    dados = request.get_json(silent=True)
    if not dados or "dispositivo_id" not in dados:
        return jsonify({"erro": "payload invalido"}), 400
    if "bomba" not in dados and "luz" not in dados and "pulso" not in dados and "auto" not in dados:
        return jsonify({"erro": "informe bomba, pulso, luz ou auto"}), 400

    ip = request.remote_addr
    fonte = "App" if ip != "127.0.0.1" else "Painel"
    if "bomba" in dados:
        print(f"[Comando] {fonte} → bomba={'ON' if dados['bomba'] else 'OFF'}")
    if "pulso" in dados:
        print(f"[Comando] {fonte} → pulso={dados['pulso']}s")
    if "auto" in dados:
        print(f"[Comando] {fonte} → auto={'ON' if dados['auto'] else 'OFF'}")

    comandos.salvar(
        dados["dispositivo_id"],
        bomba=bool(dados["bomba"]) if "bomba" in dados else None,
        luz=bool(dados["luz"])     if "luz"   in dados else None,
        pulso=int(dados["pulso"])  if "pulso" in dados else None,
    )
    return jsonify({"ok": True}), 201


@painel_bp.get("/api/status")
def status():
    ble = state.get_ble()
    rows = leituras.buscar(None, 1)

    ble_ativo = ble["status"] == "conectado"

    if not rows:
        return jsonify({
            "servidor": "online",
            "ble": ble,
            "esp32_conectado": False,
            "ultima_leitura": None,
            "segundos_desde_leitura": None,
            "bomba": None,
            "sensores": None,
        })

    r = rows[0]
    ts = datetime.fromisoformat(r["timestamp"]).replace(tzinfo=timezone.utc)
    delta = int((datetime.now(timezone.utc) - ts).total_seconds())

    # Considera conectado só se BLE está ativo E chegou leitura nos últimos 30s
    esp32_conectado = ble_ativo and delta < 30

    return jsonify({
        "servidor": "online",
        "ble": ble,
        "esp32_conectado": esp32_conectado,
        "ultima_leitura": r["timestamp"],
        "segundos_desde_leitura": delta,
        "bomba": bool(r["bomba"]),
        "sensores": {
            "umidade_solo": r["umidade_solo_percent"],
            "temperatura":  r["temperatura"],
            "umidade_ar":   r["umidade_ar"],
            "luminosidade": r["luminosidade_percent"],
        },
    })


@painel_bp.post("/api/ble/reconectar")
def ble_reconectar():
    """Força o loop BLE a desconectar e tentar uma nova conexão."""
    state.reconectar.set()
    return jsonify({"ok": True})
