from database import _conn


def salvar(dados: dict):
    sql = """
        INSERT INTO leituras
            (dispositivo_id, umidade_solo_bruto, umidade_solo_percent,
             temperatura, umidade_ar, luminosidade_bruto, luminosidade_percent, bomba)
        VALUES
            (:dispositivo_id, :umidade_solo_bruto, :umidade_solo_percent,
             :temperatura, :umidade_ar, :luminosidade_bruto, :luminosidade_percent, :bomba)
    """
    with _conn() as conn:
        conn.execute(sql, dados)


def buscar(dispositivo_id: str = None, limite: int = 100):
    with _conn() as conn:
        if dispositivo_id:
            rows = conn.execute(
                "SELECT * FROM leituras WHERE dispositivo_id = ? ORDER BY id DESC LIMIT ?",
                (dispositivo_id, limite),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leituras ORDER BY id DESC LIMIT ?",
                (limite,),
            ).fetchall()
    return [dict(r) for r in rows]
