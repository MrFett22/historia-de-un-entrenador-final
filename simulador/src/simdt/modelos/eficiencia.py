"""M3 — eficiencia por tipo de jugada.

P(remate | k) = expit(logit p̄_k + u_at_i[k] + u_co_j[k])
xG por remate = ḡ_k · exp(w_at_i[k] + w_co_j[k])
"""

from __future__ import annotations

import numpy as np
from scipy.special import expit, logit

from ..tipos import BLOQUES, Liga


def eficiencia(liga: Liga, zi: np.ndarray, zj: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(B, K) P(remate) y (B, K) xG por remate."""
    p = expit(logit(liga.p_bar)[None] + zi[:, BLOQUES["u_at"]] + zj[:, BLOQUES["u_co"]])
    g = liga.g_bar[None] * np.exp(zi[:, BLOQUES["w_at"]] + zj[:, BLOQUES["w_co"]])
    return p, g
