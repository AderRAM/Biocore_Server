# BioCore - Servidor central de irrigacao
#
# Inicie com:
#   source venv/bin/activate
#   python app.py

from flask import Flask
import config
import database
from routes.esp32 import esp32_bp
from routes.painel import painel_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(esp32_bp)
    app.register_blueprint(painel_bp)
    return app


if __name__ == "__main__":
    database.inicializar()
    app = create_app()
    print(f"BioCore servidor iniciado em http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=True, threaded=True)
