"""Corte explícito por fecha (D-050): la fase A y la liga solo usan partidos ANTERIORES al inicio del torneo objetivo.

Sin el corte, los partidos ya jugados del torneo que se quiere simular entran a la estimación (fuga): en el Apertura 2026 eran 22 partidos que
generaban 11 celdas técnico × club × temporada, todas de la temporada vigente. El Elo ya se calculaba solo con partidos previos (`calibrar.py`).
La simulación sigue desde la jornada 1; condicionar en los partidos ya jugados queda para después.
"""

from __future__ import annotations

import pandas as pd

TABLAS_POR_PARTIDO = ("juego", "exposicion", "saques", "cambios", "panel")


def cortar_por_fecha(tablas: dict, fecha_corte) -> tuple[dict, dict]:
    """(tablas sin los partidos con fecha ≥ `fecha_corte`, informe). Cada tabla se filtra por los `match_id` que sobreviven."""
    corte = pd.Timestamp(fecha_corte)
    p = tablas["partidos"]
    quitar = p[pd.to_datetime(p["fecha"]) >= corte]
    ids = set(quitar["match_id"])
    out = {n: t for n, t in tablas.items()}
    out["partidos"] = p[~p["match_id"].isin(ids)].reset_index(drop=True)
    for n in TABLAS_POR_PARTIDO:
        if n in out:
            out[n] = out[n][~out[n]["match_id"].isin(ids)].reset_index(drop=True)
    info = {
        "fecha_corte": str(corte.date()),
        "partidos_antes": int(len(p)),
        "partidos_quitados": int(len(quitar)),
        "partidos_despues": int(len(out["partidos"])),
        "temporadas_quitadas": sorted(int(t) for t in quitar["temporada"].unique())
        if len(quitar)
        else [],
        "fechas_quitadas": [
            str(pd.to_datetime(quitar["fecha"]).min().date()),
            str(pd.to_datetime(quitar["fecha"]).max().date()),
        ]
        if len(quitar)
        else [],
    }
    return out, info
