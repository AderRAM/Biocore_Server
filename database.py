import sqlite3
import config


def _conn():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # permite leituras simultâneas à escrita
    return conn


def inicializar():
    """Cria as tabelas e aplica migracoes necessarias."""
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS leituras (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                dispositivo_id        TEXT    NOT NULL,
                timestamp             DATETIME DEFAULT (datetime('now')),
                umidade_solo_bruto    INTEGER,
                umidade_solo_percent  REAL,
                temperatura           REAL,
                umidade_ar            REAL,
                luminosidade_bruto    INTEGER,
                luminosidade_percent  REAL,
                bomba                 INTEGER
            );

            CREATE TABLE IF NOT EXISTS comandos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                dispositivo_id TEXT    NOT NULL,
                bomba          INTEGER,
                luz            INTEGER,
                criado_em      DATETIME DEFAULT (datetime('now')),
                executado      INTEGER  DEFAULT 0
            );
        """)

        # migracao: recria comandos se bomba ainda for NOT NULL (schema antigo)
        cols = {r[1]: r[3] for r in conn.execute("PRAGMA table_info(comandos)").fetchall()}
        if cols.get("bomba") == 1:
            conn.executescript("""
                DROP TABLE comandos;
                CREATE TABLE comandos (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    dispositivo_id TEXT    NOT NULL,
                    bomba          INTEGER,
                    luz            INTEGER,
                    criado_em      DATETIME DEFAULT (datetime('now')),
                    executado      INTEGER  DEFAULT 0
                );
            """)
        elif "luz" not in cols:
            conn.execute("ALTER TABLE comandos ADD COLUMN luz INTEGER")
