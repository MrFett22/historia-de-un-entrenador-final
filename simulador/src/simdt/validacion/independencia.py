"""H1 (partidos independientes): autocorrelación de residuos y días de descanso.

residuo = puntos − xPts por equipo y partido (fichas de su celda). Se reporta
(1) la autocorrelación de lag 1 dentro de cada equipo-torneo, agrupada, con IC bootstrap por equipo;
(2) la pendiente de la regresión del residuo sobre la diferencia de días de descanso
    (propios − rival), con IC bootstrap por equipo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .comun import puntos


def residuos(pr: pd.DataFrame) -> pd.DataFrame:
    pl, pv = puntos(pr.goles_local, pr.goles_visitante)
    a = pd.DataFrame(
        {
            "equipo": pr.local,
            "rival": pr.visitante,
            "fecha": pr.fecha,
            "temporada": pr.temporada,
            "match_id": pr.match_id,
            "res": pl - pr.xpts_local,
        }
    )
    b = pd.DataFrame(
        {
            "equipo": pr.visitante,
            "rival": pr.local,
            "fecha": pr.fecha,
            "temporada": pr.temporada,
            "match_id": pr.match_id,
            "res": pv - pr.xpts_visita,
        }
    )
    x = pd.concat([a, b]).sort_values(["equipo", "fecha", "match_id"])
    x["descanso"] = x.groupby("equipo").fecha.diff().dt.days
    d = x[["match_id", "equipo", "descanso"]].rename(
        columns={"equipo": "rival", "descanso": "descanso_rival"}
    )
    x = x.merge(d, on=["match_id", "rival"], how="left")
    x["dif_descanso"] = (x.descanso - x.descanso_rival).clip(-10, 10)
    x["res_prev"] = x.groupby(["equipo", "temporada"]).res.shift(1)
    return x


def evaluar(pr: pd.DataFrame, B: int = 2000, semilla: int = 0) -> dict:
    x = residuos(pr)
    a = x.dropna(subset=["res_prev"])
    eqs = a.equipo.unique()
    g = {e: a[a.equipo == e] for e in eqs}
    rng = np.random.default_rng(semilla)

    def rho(df):
        return float(np.corrcoef(df.res, df.res_prev)[0, 1])

    r0 = rho(a)
    bs = [rho(pd.concat([g[e] for e in rng.choice(eqs, len(eqs))])) for _ in range(B)]
    b = x.dropna(subset=["dif_descanso"])
    gb = {e: b[b.equipo == e] for e in b.equipo.unique()}

    def pend(df):
        X = np.column_stack([np.ones(len(df)), df.dif_descanso])
        return float(np.linalg.lstsq(X, df.res, rcond=None)[0][1])

    p0 = pend(b)
    bp = [pend(pd.concat([gb[e] for e in rng.choice(list(gb), len(gb))])) for _ in range(B)]
    return {
        "autocorrelacion_lag1": r0,
        "autocorrelacion_ic95": np.quantile(bs, [0.025, 0.975]).tolist(),
        "pendiente_descanso_por_dia": p0,
        "pendiente_ic95": np.quantile(bp, [0.025, 0.975]).tolist(),
        "n_pares": int(len(a)),
        "n_descanso": int(len(b)),
    }
