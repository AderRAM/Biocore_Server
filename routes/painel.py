from flask import Blueprint, request, jsonify, render_template
from models import leituras, comandos

painel_bp = Blueprint("painel", __name__)


@painel_bp.get("/")
def index():
    return render_template("index.html")


@painel_bp.get("/api/leituras")
def listar_leituras():
    """Retorna as ultimas leituras (painel web ou app movel).

    Query params:
        dispositivo_id  — filtra por dispositivo (opcional)
        limite          — quantidade de registros (padrao 100, max 500)
    """
    dispositivo_id = request.args.get("dispositivo_id")
    try:
        limite = min(int(request.args.get("limite", 100)), 500)
    except ValueError:
        limite = 100

    return jsonify(leituras.buscar(dispositivo_id, limite)), 200


@painel_bp.post("/api/comando")
def enviar_comando():
    """Painel ou app movel envia comando para um dispositivo.

    Body JSON:
        {"dispositivo_id": "...", "bomba": true}
        {"dispositivo_id": "...", "luz": false}
        {"dispositivo_id": "...", "bomba": true, "luz": false}
    """
    dados = request.get_json(silent=True)
    if not dados or "dispositivo_id" not in dados:
        return jsonify({"erro": "payload invalido"}), 400
    if "bomba" not in dados and "luz" not in dados:
        return jsonify({"erro": "informe bomba e/ou luz"}), 400

    comandos.salvar(
        dados["dispositivo_id"],
        bomba=bool(dados["bomba"]) if "bomba" in dados else None,
        luz=bool(dados["luz"])     if "luz"   in dados else None,
    )
    return jsonify({"ok": True}), 201
