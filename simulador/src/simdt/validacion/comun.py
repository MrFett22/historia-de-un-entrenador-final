"""Utilidades de validación: fichas medias por celda y predicción de cada partido observado."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..estimacion.fase_a import ResultadoFaseA
from ..motor.partido import partido_lote
from ..tipos import COMPONENTES, Q


def ficha_media(res: ResultadoFaseA, club: str, temp: int, tec: str | None) -> np.ndarray:
    """E[b0 + φ[club, temp] + θ[tec] + ε[tec, club]] (θ, ε = 0 si no se observaron)."""
    ix = res.ix
    z = np.zeros(Q)
    for q, n in enumerate(COMPONENTES):
        p = res.posteriores[n]
        v = p.b0.mean()
        if club in ix.clubes:
            c = ix.clubes.index(club)
            v += p.phi[:, c, min(temp, ix.n_temp - 1)].mean()
        if tec in ix.tecnicos:
            v += p.theta[:, ix.tecnicos.index(tec)].mean()
        if (tec, club) in ix.pares:
            v += p.eps[:, ix.pares.index((tec, club))].mean()
        z[q] = v
    return z


def predecir_partidos(res: ResultadoFaseA, partidos: pd.DataFrame, lote: int = 500) -> pd.DataFrame:
    """P(local gana / empate / visitante gana) y xPts de cada partido con las fichas de su celda."""
    cache = {}

    def f(club, temp, tec):
        k = (club, temp, tec)
        if k not in cache:
            cache[k] = ficha_media(res, club, temp, tec)
        return cache[k]

    zl = np.array([f(r.local, r.temporada, r.tecnico_local) for r in partidos.itertuples()])
    zv = np.array([f(r.visitante, r.temporada, r.tecnico_visitante) for r in partidos.itertuples()])
    de = (partidos.elo_local - partidos.elo_visitante).to_numpy()
    out = []
    for a in range(0, len(zl), lote):
        d = partido_lote(res.liga, zl[a : a + lote], zv[a : a + lote], 1.0, de[a : a + lote])
        out.append(
            np.column_stack([d.p_gana, d.p_empata, d.p_pierde, d.xpts_i, d.xpts_j, d.eg_i, d.eg_j])
        )
    o = np.vstack(out)
    return partidos.assign(
        p_local=o[:, 0],
        p_empate=o[:, 1],
        p_visita=o[:, 2],
        xpts_local=o[:, 3],
        xpts_visita=o[:, 4],
        eg_local=o[:, 5],
        eg_visita=o[:, 6],
    )


def puntos(gl, gv):
    gl, gv = np.asarray(gl), np.asarray(gv)
    return np.where(gl > gv, 3, np.where(gl == gv, 1, 0)), np.where(
        gv > gl, 3, np.where(gl == gv, 1, 0)
    )


def rps(p: np.ndarray, resultado: np.ndarray) -> np.ndarray:
    """Ranked probability score de 3 categorías ordenadas (local, empate, visita).

    resultado: 0 = local, 1 = empate, 2 = visita.  (Epstein, 1969; Constantinou y Fenton, 2012)
    """
    o = np.eye(3)[resultado]
    cp, co = np.cumsum(p, 1)[:, :2], np.cumsum(o, 1)[:, :2]
    return ((cp - co) ** 2).sum(1) / 2
