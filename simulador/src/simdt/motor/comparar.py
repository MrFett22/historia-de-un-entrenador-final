"""Comparación de dos técnicos con números aleatorios comunes (04_ESPECIFICACION §5).

Δ^(r) = puntos esperados exactos con el técnico 1 − con el técnico 2, en la MISMA réplica r
(misma muestra posterior de los rivales y del plantel, mismos uniformes).
Veredicto con δ = 3 puntos:
  - "igual"  si el intervalo del 90 % de Δ está dentro de (−δ, δ)  (equivalencia, estilo TOST);
  - "mejor"/"peor" si el intervalo del 95 % excluye el 0;
  - "no_se_sabe" en cualquier otro caso.
Aparte: rango del 80 % de la diferencia de puntos en UN torneo concreto (incluye el azar).
"""

from __future__ import annotations

import numpy as np

from .. import config
from ..tipos import Comparacion, ResultadoTemporada


def comparar(
    res1: ResultadoTemporada, res2: ResultadoTemporada, delta: float | None = None
) -> Comparacion:
    cfg = config.cargar()["simulacion"]
    delta = cfg["delta_equivalencia"] if delta is None else delta
    a_eq, a_sup, a_tor = (
        cfg["nivel_equivalencia"],
        cfg["nivel_superioridad"],
        cfg["nivel_rango_torneo"],
    )
    d = res1.puntos_exactos - res2.puntos_exactos
    lo90, hi90 = np.quantile(d, [(1 - a_eq) / 2, 1 - (1 - a_eq) / 2])
    lo95, hi95 = np.quantile(d, [(1 - a_sup) / 2, 1 - (1 - a_sup) / 2])
    if np.all(d == 0):
        veredicto = "igual"
    elif lo90 > -delta and hi90 < delta:
        veredicto = "igual"
    elif lo95 > 0:
        veredicto = "mejor"
    elif hi95 < 0:
        veredicto = "peor"
    else:
        veredicto = "no_se_sabe"
    dt = (res1.puntos - res2.puntos).ravel()
    lo_t, hi_t = np.quantile(dt, [(1 - a_tor) / 2, 1 - (1 - a_tor) / 2])
    return Comparacion(
        delta=d,
        veredicto=veredicto,
        resumen={
            "media": float(d.mean()),
            "ee": float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else 0.0,
            "int90": [float(lo90), float(hi90)],
            "int95": [float(lo95), float(hi95)],
            "rango_torneo80": [float(lo_t), float(hi_t)],
            "delta": delta,
            "p_liguilla_dif": float(
                res1.resumen["p_liguilla"]["media"] - res2.resumen["p_liguilla"]["media"]
            ),
        },
    )
