"""M2 — mezcla de tipos de jugada bajo contexto.

logit π_ik(t, m) − logit π_i,ref = b0_k + int_at_i[k] + int_co_j[k]
     + (1 + s_marcador_i) · (b_pierde_k·[m = pierde] + b_gana_k·[m = gana])
     + b_tf_k·[τ = 6] + b_loc_k·local_i + (1 + s_rival_i) · b_elo_k · ΔElo/100
Fila de referencia (Circulación estéril) = 0. El técnico mueve π, no P^k (H3).
"""

from __future__ import annotations

import numpy as np

from ..tipos import BLOQUES, NO_REF, K, Liga
from .llegada import tramo_minuto


def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)


def mezcla(
    liga: Liga, zi: np.ndarray, zj: np.ndarray, local_i: np.ndarray, elo_diff: np.ndarray
) -> np.ndarray:
    """(B, T, 3 estados m, K) probabilidades de cada tipo de jugada."""
    B = zi.shape[0]
    tr = tramo_minuto(liga.minutos)
    final = (tr == 5).astype(float)  # (T,)
    b = liga.b_liga  # (K, 6)
    sm = 1.0 + zi[:, BLOQUES["s_marcador"][0]]
    sr = 1.0 + zi[:, BLOQUES["s_rival"][0]]
    inter = np.zeros((B, K))
    inter[:, list(NO_REF)] = zi[:, BLOQUES["int_at"]] + zj[:, BLOQUES["int_co"]]
    base = (
        b[None, :, 0]
        + inter
        + b[None, :, 4] * local_i[:, None]
        + sr[:, None] * b[None, :, 5] * (elo_diff[:, None] / 100.0)
    )  # (B, K)
    marc = np.stack([b[:, 1], np.zeros(K), b[:, 2]])  # (3, K)
    lg = (
        base[:, None, None, :]
        + final[None, :, None, None] * b[None, None, None, :, 3]
        + sm[:, None, None, None] * marc[None, None, :, :]
    )  # (B, T, 3, K)
    return softmax(lg, axis=-1)
