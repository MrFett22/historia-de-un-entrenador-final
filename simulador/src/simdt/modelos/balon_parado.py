"""M4 — balón parado.

saques_iu(t) = r̄_u[τ] · exp(rho_i[u] + h_bp·(2·local_i − 1))      (penal: solo liga)
q_iju        = expit(logit q̄_u + nu_at_i[u] + nu_co_j[u])         (capa 1; 1 en directo y penal)
goles_iu(t)  = saques_iu(t) · q_iju · κ_u                            (capa 2 = κ de liga, H9)
"""

from __future__ import annotations

import numpy as np
from scipy.special import expit, logit

from ..tipos import BLOQUES, BP_CAPA1, BP_CON_RHO, U, Liga
from .llegada import tramo_minuto


def balon_parado(liga: Liga, zi: np.ndarray, zj: np.ndarray, local_i: np.ndarray):
    """Devuelve (B, T, U) saques por minuto y (B, U) goles por saque."""
    B = zi.shape[0]
    tr = tramo_minuto(liga.minutos)
    rho = np.zeros((B, U))
    rho[:, list(BP_CON_RHO)] = zi[:, BLOQUES["rho"]]
    lin = rho + liga.h_bp * (2 * local_i[:, None] - 1)
    saques = liga.r_bar[:, tr].T[None] * np.exp(lin)[:, None, :]  # (B, T, U)
    q = np.ones((B, U))
    qb = np.clip(liga.q_bar[list(BP_CAPA1)], 1e-6, 1 - 1e-6)
    q[:, list(BP_CAPA1)] = expit(
        logit(qb)[None] + zi[:, BLOQUES["nu_at"]] + zj[:, BLOQUES["nu_co"]]
    )
    return saques, q * liga.kappa[None]
