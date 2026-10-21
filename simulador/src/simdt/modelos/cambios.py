"""Cambios (descriptivo, H11): hazard logit en tiempo discreto y tipo de cambio.

hazard_i(t, m) = expit(hazard_base[t] + hazard_m[m] + alpha_i),  t = minutos 45..89
P(tipo | m)    ∝ exp(tipo_base[m, tipo] + gamma_i · (tipo − 1)),  tipo ∈ {defensivo, mismo, ofensivo}
No entra en la intensidad de goles: la diferencia en diferencias del repo dio efecto nulo.
"""

from __future__ import annotations

import numpy as np
from scipy.special import expit

from ..tipos import Liga

MIN_INICIO = 45  # el primer minuto de la ventana (descanso incluido)
N_MIN = 45


def hazard(liga: Liga, alpha: float) -> np.ndarray:
    """(45, 3) probabilidad de hacer un cambio en el minuto t dado el estado m."""
    return expit(liga.hazard_base[:, None] + liga.hazard_m[None, :] + alpha)


def prob_tipo(liga: Liga, gamma: float) -> np.ndarray:
    """(3 estados m, 3 tipos)."""
    lg = liga.tipo_base + gamma * (np.arange(3) - 1)[None, :]
    e = np.exp(lg - lg.max(1, keepdims=True))
    return e / e.sum(1, keepdims=True)


def resumen(liga: Liga, alpha: float, gamma: float, ocupacion: np.ndarray) -> dict:
    """Minuto típico del primer cambio y tipo más común, promediados sobre la ocupación de m.

    ocupacion: (T, 3) P(estado m al inicio de cada minuto), T = 90.
    """
    occ = ocupacion[MIN_INICIO : MIN_INICIO + N_MIN]
    h = (hazard(liga, alpha) * occ).sum(1)  # hazard promedio por minuto
    sobrevive = np.concatenate([[1.0], np.cumprod(1 - h)[:-1]])
    f = sobrevive * h
    acum = np.cumsum(f)
    mediana = MIN_INICIO + int(np.searchsorted(acum, 0.5 * acum[-1]))
    pt = prob_tipo(liga, gamma)
    peso = (f[:, None] * occ).sum(0)  # estados en que suelen ocurrir
    tipos = (peso / max(peso.sum(), 1e-12)) @ pt
    return {
        "minuto_primer_cambio": mediana,
        "p_tipo": tipos.tolist(),
        "tipo_mas_comun": int(np.argmax(tipos)),
        "p_algun_cambio": float(acum[-1]),
    }
