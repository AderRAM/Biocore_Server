from database import _conn


def salvar(dispositivo_id: str, bomba=None, luz=None, pulso=None):
    """Enfileira um comando. Pelo menos um dos campos deve ser fornecido."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO comandos (dispositivo_id, bomba, luz, pulso) VALUES (?, ?, ?, ?)",
            (dispositivo_id,
             int(bomba) if bomba is not None else None,
             int(luz)   if luz   is not None else None,
             int(pulso) if pulso is not None else None),
        )


def consumir(dispositivo_id: str) -> dict:
    """Retorna o comando mais recente nao executado e o marca como executado."""
    with _conn() as conn:
        row = conn.execute(
            """SELECT id, bomba, luz, pulso FROM comandos
               WHERE dispositivo_id = ? AND executado = 0
               ORDER BY id DESC LIMIT 1""",
            (dispositivo_id,),
        ).fetchone()
        if row:
            conn.execute("UPDATE comandos SET executado = 1 WHERE id = ?", (row["id"],))
            result = {}
            if row["bomba"] is not None:
                result["bomba"] = bool(row["bomba"])
            if row["luz"] is not None:
                result["luz"] = bool(row["luz"])
            if row["pulso"] is not None:
                result["pulso"] = int(row["pulso"])
            return result
    return {}
