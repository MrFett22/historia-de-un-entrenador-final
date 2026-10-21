"""Retroprueba con llegadas de técnico (sin mirar el futuro).

Para cada torneo de corte T: la fase A se reajusta SOLO con los torneos < T (φ[club, T] queda
como pronóstico de la caminata aleatoria). Una llegada = técnico X que dirige ≥ 5 partidos al
club c en T sin haberlo dirigido en T − 1. Predicción de los puntos por partido de X en c:
media de los xPts exactos de esos partidos con
  ζ_c = b0 + φ[c, T] + θ[X] (si X se observó antes de T) + ε[X, c] (si el par se observó),
  ζ_rival = b0 + φ[r, T] + θ[técnico del rival] + ε[par rival]  (medias posteriores),
y el Elo previo a cada partido. Inercia = puntos por partido del club en T − 1.
Diebold-Mariano (pérdida cuadrática; corrección de Harvey, Leybourne y Newbold) y cobertura
conforme del 80 % (residuos absolutos, dejando uno fuera).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import t as student

from ..estimacion import fase_a
from ..motor.partido import partido_lote
from .comun import ficha_media, puntos

MCMC_LIGERO = {"chains": 2, "tune": 600, "draws": 600, "ess_min": 200}


def _filtrar(tablas: dict, ids: set) -> dict:
    return {k: (v[v.match_id.isin(ids)] if "match_id" in v else v) for k, v in tablas.items()}


def _ppm_por_club(p: pd.DataFrame) -> pd.Series:
    pl, pv = puntos(p.goles_local, p.goles_visitante)
    x = pd.concat(
        [pd.DataFrame({"club": p.local, "pts": pl}), pd.DataFrame({"club": p.visitante, "pts": pv})]
    )
    return x.groupby("club").pts.mean()


def llegadas(p: pd.DataFrame, T: int, minimo: int = 5) -> list[tuple[str, str]]:
    def dirigio(temp):
        q = p[p.temporada == temp]
        a = set(zip(q.tecnico_local, q.local)) | set(zip(q.tecnico_visitante, q.visitante))
        n = pd.concat(
            [
                q[["tecnico_local", "local"]].set_axis(["t", "c"], axis=1),
                q[["tecnico_visitante", "visitante"]].set_axis(["t", "c"], axis=1),
            ]
        ).value_counts()
        return a, n

    previos, _ = dirigio(T - 1)
    _, n = dirigio(T)
    return [(t, c) for (t, c), k in n.items() if k >= minimo and (t, c) not in previos]


def correr(tablas: dict, cortes: list[int], verbose: bool = True) -> dict:
    p = tablas["partidos"].dropna(subset=["goles_local", "goles_visitante"])
    filas = []
    for T in cortes:
        ids = set(p[p.temporada < T].match_id)
        res = fase_a.correr(
            _filtrar(tablas, ids),
            cache=f"fase_a_retro_{T}.pkl",
            n_temp=T + 1,
            verbose=verbose,
            mcmc=MCMC_LIGERO,
            P_cadenas=None,
            mu_cadenas=None,
        )
        inercia = _ppm_por_club(p[(p.temporada == T - 1) & (p.etapa == "regular")])
        for tec, club in llegadas(p, T):
            sub = p[
                (p.temporada == T)
                & (
                    ((p.local == club) & (p.tecnico_local == tec))
                    | ((p.visitante == club) & (p.tecnico_visitante == tec))
                )
            ]
            es_local = (sub.local == club).to_numpy()
            rival = np.where(es_local, sub.visitante, sub.local)
            tec_r = np.where(es_local, sub.tecnico_visitante, sub.tecnico_local)
            zi = np.array([ficha_media(res, club, T, tec)] * len(sub))
            zj = np.array([ficha_media(res, r, T, tr) for r, tr in zip(rival, tec_r)])
            de = np.where(
                es_local, sub.elo_local - sub.elo_visitante, sub.elo_visitante - sub.elo_local
            )
            d = partido_lote(res.liga, zi, zj, es_local.astype(float), de)
            pl, pv = puntos(sub.goles_local, sub.goles_visitante)
            real = np.where(es_local, pl, pv).mean()
            filas.append(
                {
                    "corte": T,
                    "tecnico": tec,
                    "club": club,
                    "partidos": int(len(sub)),
                    "observado_antes": tec in res.ix.tecnicos,
                    "prediccion": float(d.xpts_i.mean()),
                    "inercia": float(inercia.get(club, np.nan)),
                    "real": float(real),
                }
            )
    df = pd.DataFrame(filas).dropna()
    return {"tabla": df, **resumen(df)}


def resumen(df: pd.DataFrame, nivel: float = 0.80) -> dict:
    n = len(df)
    if n < 3:
        return {"n": n, "dm_p": float("nan"), "etiqueta": "descriptivo"}
    e_s = df.real - df.prediccion
    e_i = df.real - df.inercia
    d = (e_i**2 - e_s**2).to_numpy()
    dm = d.mean() / (d.std(ddof=1) / np.sqrt(n))
    dm_hln = dm * np.sqrt((n - 1) / n)  # Harvey, Leybourne y Newbold (h = 1)
    p = float(1 - student.cdf(dm_hln, n - 1))  # H1: el simulador tiene menor pérdida
    r = np.abs(e_s.to_numpy())
    cubre = []
    for i in range(n):
        otros = np.delete(r, i)
        k = int(np.ceil(nivel * (len(otros) + 1))) - 1
        q = np.sort(otros)[min(k, len(otros) - 1)]
        cubre.append(r[i] <= q)
    return {
        "n": n,
        "mae_simulador": float(np.abs(e_s).mean()),
        "mae_inercia": float(np.abs(e_i).mean()),
        "rmse_simulador": float(np.sqrt((e_s**2).mean())),
        "rmse_inercia": float(np.sqrt((e_i**2).mean())),
        "dm_estadistico": float(dm_hln),
        "dm_p": p,
        "cobertura_conforme80": float(np.mean(cubre)),
        "etiqueta": "predictivo" if p < 0.05 else "descriptivo",
    }
