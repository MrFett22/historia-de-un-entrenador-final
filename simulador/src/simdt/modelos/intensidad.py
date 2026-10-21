"""μ_ij(t, m): goles esperados por minuto de i contra j en el estado m ∈ {pierde, empata, gana}.

μ_ij(t, m) = f · [λ_i(t) Σ_k π_ik(t, m) · p_ik · g_ik  +  Σ_u saques_iu(t) · q_iju · κ_u]
(f = goles/xG de la liga, D-030; 1 en sintético)
El marcador solo entra por π (M2); el ritmo (H2) y el balón parado no dependen de m.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..tipos import Liga
from .balon_parado import balon_parado
from .eficiencia import eficiencia
from .familias import mezcla
from .llegada import ritmo


@dataclass
class Intensidad:
    mu: np.ndarray  # (B, T, 3)
    n_k: np.ndarray  # (B, T, 3, K) secuencias esperadas por minuto
    goles_k: np.ndarray  # (B, T, 3, K)
    goles_bp: np.ndarray  # (B, T, U) (no depende de m)
    pi: np.ndarray  # (B, T, 3, K)


def intensidades_lote(liga: Liga, zi, zj, local_i, elo_diff) -> Intensidad:
    zi, zj = np.atleast_2d(zi), np.atleast_2d(zj)
    B = zi.shape[0]
    local_i = np.broadcast_to(np.asarray(local_i, dtype=float), (B,))
    elo_diff = np.broadcast_to(np.asarray(elo_diff, dtype=float), (B,))
    lam = ritmo(liga, zi, zj, local_i)  # (B, T)
    pi = mezcla(liga, zi, zj, local_i, elo_diff)  # (B, T, 3, K)
    p, g = eficiencia(liga, zi, zj)  # (B, K)
    n_k = lam[:, :, None, None] * pi
    goles_k = liga.factor_gol * n_k * (p * g)[:, None, None, :]
    saques, gps = balon_parado(liga, zi, zj, local_i)
    goles_bp = liga.factor_gol * saques * gps[:, None, :]
    mu = goles_k.sum(-1) + goles_bp.sum(-1)[:, :, None]
    return Intensidad(mu, n_k, goles_k, goles_bp, pi)


def intensidades(ficha_i, ficha_j, local_i: bool, elo_diff: float, liga: Liga) -> np.ndarray:
    """Contrato de 03_ARQUITECTURA: (T, 3) para un solo partido."""
    return intensidades_lote(liga, ficha_i, ficha_j, float(local_i), float(elo_diff)).mu[0]
