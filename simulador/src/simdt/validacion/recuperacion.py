"""Recuperación: técnicos con ≥ 50 partidos en un club. Su mezcla simulada en ese club (motor con
las fichas de sus celdas contra sus rivales reales, ocupación del marcador incluida) debe caer
dentro del rango observado (bootstrap por partido, 95 %)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..motor.partido import partido_lote
from .comun import ficha_media


def evaluar(res, tablas: dict, minimo: int = 50, B: int = 1000, semilla: int = 0) -> dict:
    p = tablas["partidos"]
    a = p[
        [
            "match_id",
            "temporada",
            "local",
            "visitante",
            "tecnico_local",
            "elo_local",
            "elo_visitante",
            "tecnico_visitante",
        ]
    ]
    filas = []
    for lado in ("local", "visitante"):
        o = "visitante" if lado == "local" else "local"
        filas.append(
            pd.DataFrame(
                {
                    "match_id": a.match_id,
                    "temporada": a.temporada,
                    "club": a[lado],
                    "rival": a[o],
                    "tecnico": a[f"tecnico_{lado}"],
                    "tec_rival": a[f"tecnico_{o}"],
                    "local": float(lado == "local"),
                    "elo_dif": (a.elo_local - a.elo_visitante) * (1 if lado == "local" else -1),
                }
            )
        )
    x = pd.concat(filas)
    n = x.groupby(["tecnico", "club"]).match_id.nunique()
    j = (
        tablas["juego"]
        .pivot_table(index=["match_id", "equipo"], columns="k", values="n", aggfunc="sum")
        .fillna(0)
    )
    rng = np.random.default_rng(semilla)
    out = []
    for (tec, club), nn in n[n >= minimo].items():
        sub = x[(x.tecnico == tec) & (x.club == club)]
        zi = np.array([ficha_media(res, club, t, tec) for t in sub.temporada])
        zj = np.array(
            [
                ficha_media(res, r, t, tr)
                for r, t, tr in zip(sub.rival, sub.temporada, sub.tec_rival)
            ]
        )
        d = partido_lote(
            res.liga, zi, zj, sub.local.to_numpy(), sub.elo_dif.to_numpy(), con_detalle=True
        )
        Nk = d.extra["N_k_i"].sum(0)
        sim = Nk / Nk.sum()
        obs_m = j.loc[[(m, club) for m in sub.match_id if (m, club) in j.index]].to_numpy()
        obs = obs_m.sum(0) / obs_m.sum()
        bs = obs_m[rng.integers(0, len(obs_m), (B, len(obs_m)))].sum(1)
        bs = bs / bs.sum(1, keepdims=True)
        lo, hi = np.quantile(bs, [0.025, 0.975], axis=0)
        dentro = bool(np.all((sim >= lo) & (sim <= hi)))
        out.append(
            {
                "tecnico": tec,
                "club": club,
                "partidos": int(nn),
                "simulada": sim.round(4).tolist(),
                "observada": obs.round(4).tolist(),
                "rango95": [lo.round(4).tolist(), hi.round(4).tolist()],
                "dentro": dentro,
            }
        )
    frac = float(np.mean([o["dentro"] for o in out])) if out else float("nan")
    return {"n_pares": len(out), "fraccion_dentro": frac, "detalle": out}
