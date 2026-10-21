"""Aviso de coherencia: ¿el técnico inventado es más extremo que los observados?

D² de Mahalanobis del θ (en las componentes con perilla) contra los θ + ε de los pares
técnico-club con ≥ 30 partidos, con covarianza de Ledoit-Wolf (encogida, estable con pocos
pares). Aviso si D² > χ²_{d, 0.95}.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import chi2
from sklearn.covariance import LedoitWolf

from .. import config
from ..tipos import BLOQUES

BLOQUES_PERILLA = ("int_at", "int_co", "s_marcador", "s_rival", "nu_co", "alpha", "gamma")


def indices_perilla() -> np.ndarray:
    return np.concatenate([BLOQUES[b] for b in BLOQUES_PERILLA])


class Coherencia:
    def __init__(self, thetas_pares: np.ndarray):
        idx = indices_perilla()
        X = np.asarray(thetas_pares)[:, idx]
        self.idx = idx
        self.media = X.mean(0)
        self.lw = LedoitWolf().fit(X)
        self.prec = np.linalg.pinv(self.lw.covariance_)
        nivel = config.cargar()["perillas"]["coherencia_nivel"]
        self.umbral = float(chi2.ppf(nivel, len(idx)))
        self.d2_observados = np.array([self.d2_vec(x) for x in X])

    def d2_vec(self, x: np.ndarray) -> float:
        d = x - self.media
        return float(d @ self.prec @ d)

    def d2(self, theta: np.ndarray) -> float:
        return self.d2_vec(np.asarray(theta)[self.idx])

    def es_extremo(self, theta: np.ndarray) -> bool:
        return self.d2(theta) > self.umbral
