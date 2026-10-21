"""Tabla general, desempates y clasificación.

Orden: puntos, diferencia de goles, goles a favor, sorteo (D-005). Vectorizado sobre torneos.
"""

from __future__ import annotations

import numpy as np


def acumular(calendario: np.ndarray, ga: np.ndarray, gb: np.ndarray, n_equipos: int):
    """ga, gb: (N, n_partidos) goles local/visitante. Devuelve puntos, gf, gc (N, n_equipos).

    Cada equipo suma sus partidos con un producto por una matriz de pertenencia (partido × equipo): son sumas de enteros pequeños, así que el resultado es EXACTAMENTE el mismo
    que con `np.add.at` (que era el 57 % del tiempo de la simulación de torneos, D-095)."""
    loc, vis = calendario[:, 0], calendario[:, 1]
    L = np.zeros((len(calendario), n_equipos))
    V = np.zeros((len(calendario), n_equipos))
    L[np.arange(len(calendario)), loc] = 1.0
    V[np.arange(len(calendario)), vis] = 1.0
    pl = np.where(ga > gb, 3, np.where(ga == gb, 1, 0))
    pv = np.where(gb > ga, 3, np.where(ga == gb, 1, 0))
    pts = pl @ L + pv @ V
    gf = ga @ L + gb @ V
    gc = gb @ L + ga @ V
    return pts, gf, gc


def posiciones(pts: np.ndarray, gf: np.ndarray, gc: np.ndarray, sorteo: np.ndarray) -> np.ndarray:
    """(N, n_equipos) lugar 1..n de cada equipo. sorteo: uniformes (N, n_equipos) en [0, 1)."""
    clave = pts * 1e7 + (gf - gc + 500) * 1e4 + gf * 10 + sorteo * 9.99
    orden = np.argsort(-clave, axis=1, kind="stable")
    lugar = np.empty_like(orden)
    filas = np.arange(pts.shape[0])[:, None]
    lugar[filas, orden] = np.arange(1, pts.shape[1] + 1)[None]
    return lugar
