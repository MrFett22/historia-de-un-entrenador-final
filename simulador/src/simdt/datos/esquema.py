"""Esquema común de las tablas (sintéticas y reales). Ambas fuentes deben cumplirlo."""

from __future__ import annotations

import pandas as pd

ESQUEMA = {
    "partidos": [
        "match_id",
        "temporada",
        "jornada",
        "fecha",
        "local",
        "visitante",
        "goles_local",
        "goles_visitante",
        "tecnico_local",
        "tecnico_visitante",
        "elo_local",
        "elo_visitante",
        "etapa",
    ],
    "juego": [
        "match_id",
        "equipo",
        "rival",
        "local",
        "tramo",
        "m",
        "k",
        "n",
        "remates",
        "xg",
        "goles",
    ],
    "exposicion": ["match_id", "equipo", "tramo", "m", "minutos"],
    "saques": [
        "match_id",
        "equipo",
        "rival",
        "local",
        "tramo",
        "m",
        "u",
        "n",
        "remates",
        "xg",
        "goles",
    ],
    "cambios": ["match_id", "equipo", "minuto", "m", "tipo"],
    "panel": ["match_id", "equipo", "minuto", "m", "cambio"],
}


def validar(tablas: dict[str, pd.DataFrame]) -> list[str]:
    errores = []
    for nombre, cols in ESQUEMA.items():
        if nombre not in tablas:
            errores.append(f"falta la tabla {nombre}")
            continue
        faltan = [c for c in cols if c not in tablas[nombre].columns]
        if faltan:
            errores.append(f"{nombre}: faltan columnas {faltan}")
    if not errores:
        j, e = tablas["juego"], tablas["exposicion"]
        if not j["tramo"].between(0, 5).all() or not j["m"].between(0, 2).all():
            errores.append("juego: tramo o m fuera de rango")
        if (e["minutos"] < 0).any():
            errores.append("exposicion: minutos negativos")
    return errores
