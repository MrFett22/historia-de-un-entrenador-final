"""Calibración: RPS del motor contra frecuencias base y contra el simulador vigente del repo;
error de xPts en toda la liga.

El "simulador vigente" (04_MODELO §13.8, no incluido en este entorno) se reimplementa como lo
describe 01_CONTEXTO: Poisson independiente con ataque y defensa log5 por equipo y torneo a partir
del xG por partido (D-032).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import poisson

from .comun import predecir_partidos, puntos, rps


def _xg_por_equipo_partido(tablas: dict) -> pd.DataFrame:
    a = tablas["juego"].groupby(["match_id", "equipo"]).xg.sum()
    b = tablas["saques"].groupby(["match_id", "equipo"]).xg.sum()
    return a.add(b, fill_value=0.0).rename("xg").reset_index()


def vigente(tablas: dict, partidos: pd.DataFrame, G: int = 10) -> np.ndarray:
    """Poisson + log5: λ_local = xgf_l · xgc_v / xg_liga · e^{h}, por torneo (dentro de muestra)."""
    xg = _xg_por_equipo_partido(tablas).merge(
        partidos[["match_id", "temporada", "local", "visitante"]], on="match_id"
    )
    xg["rival"] = np.where(xg.equipo == xg.local, xg.visitante, xg.local)
    xg["es_local"] = xg.equipo == xg.local
    f = xg.groupby(["temporada", "equipo"]).xg.mean().rename("xgf")
    c = xg.groupby(["temporada", "rival"]).xg.mean().rename("xgc")
    liga = xg.groupby("temporada").xg.mean().rename("xgl")
    hl = xg[xg.es_local].groupby("temporada").xg.mean() / liga
    hv = xg[~xg.es_local].groupby("temporada").xg.mean() / liga
    out = np.zeros((len(partidos), 3))
    g = np.arange(G + 1)
    for i, r in enumerate(partidos.itertuples()):
        t = r.temporada
        lam_l = f.get((t, r.local), liga[t]) * c.get((t, r.visitante), liga[t]) / liga[t] * hl[t]
        lam_v = f.get((t, r.visitante), liga[t]) * c.get((t, r.local), liga[t]) / liga[t] * hv[t]
        P = np.outer(poisson.pmf(g, lam_l), poisson.pmf(g, lam_v))
        P /= P.sum()
        d = g[:, None] - g[None, :]
        out[i] = [P[d > 0].sum(), P[d == 0].sum(), P[d < 0].sum()]
    return out


def evaluar(res, tablas: dict) -> dict:
    p = tablas["partidos"].dropna(subset=["goles_local", "goles_visitante"]).copy()
    pr = predecir_partidos(res, p)
    gl, gv = pr.goles_local.to_numpy(), pr.goles_visitante.to_numpy()
    resultado = np.where(gl > gv, 0, np.where(gl == gv, 1, 2))
    P_motor = pr[["p_local", "p_empate", "p_visita"]].to_numpy()
    base = np.bincount(resultado, minlength=3) / len(resultado)
    P_base = np.tile(base, (len(p), 1))
    P_vig = vigente(tablas, p)
    pl, pv = puntos(gl, gv)
    reales = pl.sum() + pv.sum()
    esperados = pr.xpts_local.sum() + pr.xpts_visita.sum()
    r_m, r_b, r_v = rps(P_motor, resultado), rps(P_base, resultado), rps(P_vig, resultado)
    rng = np.random.default_rng(0)
    B = 2000
    idx = rng.integers(0, len(p), (B, len(p)))
    dif_b = (r_m[idx] - r_b[idx]).mean(1)
    dif_v = (r_m[idx] - r_v[idx]).mean(1)
    return {
        "n_partidos": int(len(p)),
        "dentro_de_muestra": True,
        "rps_motor": float(r_m.mean()),
        "rps_base": float(r_b.mean()),
        "rps_vigente": float(r_v.mean()),
        "dif_motor_base_ic95": np.quantile(dif_b, [0.025, 0.975]).tolist(),
        "dif_motor_vigente_ic95": np.quantile(dif_v, [0.025, 0.975]).tolist(),
        "puntos_reales": int(reales),
        "xpts_motor": float(esperados),
        "error_xpts": float(esperados / reales - 1),
        "goles_reales": float(gl.sum() + gv.sum()),
        "goles_esperados": float(pr.eg_local.sum() + pr.eg_visita.sum()),
        "empates_reales": float((gl == gv).mean()),
        "empates_motor": float(pr.p_empate.mean()),
        "cumple_rps": bool(r_m.mean() <= r_b.mean() and r_m.mean() <= r_v.mean()),
        "cumple_xpts": bool(abs(esperados / reales - 1) <= 0.005),
    }, pr
