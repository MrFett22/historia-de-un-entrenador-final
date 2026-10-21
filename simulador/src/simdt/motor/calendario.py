"""Calendario del torneo: real (matches_*.json de StatsBomb) o todos contra todos (fallback)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ETAPAS_REGULARES = ("Apertura", "Clausura", "Regular Season")


def todos_contra_todos(n: int = 18) -> np.ndarray:
    """Método del círculo: n−1 jornadas, cada equipo con localía balanceada (±1)."""
    eq = list(range(n))
    out = []
    for j in range(n - 1):
        for i in range(n // 2):
            a, b = eq[i], eq[n - 1 - i]
            out.append((a, b) if (j + i) % 2 == 0 else (b, a))
        eq = [eq[0]] + [eq[-1]] + eq[1:-1]
    return np.array(out)


def calendario_real(ruta_json: str | Path, equipos: list[str] | None = None):
    """Devuelve (equipos, calendario (n, 2) índices local/visitante, jornada, info por partido)."""
    with open(ruta_json, encoding="utf-8") as f:
        d = json.load(f)
    reg = [m for m in d if m["competition_stage"]["name"] in ETAPAS_REGULARES]
    reg.sort(key=lambda m: (m.get("match_week") or 0, m["match_date"], m["match_id"]))
    nombres = sorted(
        {m["home_team"]["home_team_name"] for m in reg}
        | {m["away_team"]["away_team_name"] for m in reg}
    )
    equipos = equipos or nombres
    pos = {e: i for i, e in enumerate(equipos)}
    cal = np.array(
        [
            (pos[m["home_team"]["home_team_name"]], pos[m["away_team"]["away_team_name"]])
            for m in reg
        ]
    )
    jornada = np.array([m.get("match_week") or 0 for m in reg])
    info = [
        {
            "match_id": m["match_id"],
            "fecha": m["match_date"],
            "estado": m["match_status"],
            "goles_local": m["home_score"],
            "goles_visitante": m["away_score"],
        }
        for m in reg
    ]
    return equipos, cal, jornada, info
