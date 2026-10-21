"""M1 — llegadas de juego abierto.

λ_i(t) = lam_bar[τ(t)] · exp(l_at_i + l_co_j + h·(2·local_i − 1))
Secuencias de juego abierto por minuto del equipo i contra j (H2: perfil temporal común).
"""

from __future__ import annotations

import numpy as np

from ..tipos import BLOQUES, Liga


def tramo_minuto(T: int = 90) -> np.ndarray:
    return np.minimum(np.arange(T) // (T // 6), 5)


def ritmo(liga: Liga, zi: np.ndarray, zj: np.ndarray, local_i: np.ndarray) -> np.ndarray:
    """(B, T) secuencias por minuto."""
    tr = tramo_minuto(liga.minutos)
    lin = zi[:, BLOQUES["l_at"][0]] + zj[:, BLOQUES["l_co"][0]] + liga.h_ritmo * (2 * local_i - 1)
    return liga.lam_bar[tr][None, :] * np.exp(lin)[:, None]
