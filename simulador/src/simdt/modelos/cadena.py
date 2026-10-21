"""M5 descriptivo: visitas por zona con las cadenas de la LIGA (H3: el técnico no mueve P^k).

v^k = μ^k N^k  (visitas esperadas a cada zona en una secuencia del tipo k)
mapa del equipo = Σ_k E[N_k] · v^k
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.linalg as sla

N_ZONAS = 20
N_ABS = 5  # GOL, REMATE, PERDIDA, FUERA, INTERRUPCION


# Procedencia: dtcoach_revision/dtcoach_revision_20260925_0951/src/dtcoach/absorbing.py@77b720b
@dataclass
class Cadena:
    P: np.ndarray  # (n_transient, n_states), filas suman 1
    n_transient: int

    @property
    def Q(self) -> np.ndarray:
        return self.P[:, : self.n_transient]

    @property
    def R(self) -> np.ndarray:
        return self.P[:, self.n_transient :]

    def _lu(self):
        if not hasattr(self, "_lu_cache"):
            self._lu_cache = sla.lu_factor(np.eye(self.n_transient) - self.Q)
        return self._lu_cache

    def fundamental(self) -> np.ndarray:
        return sla.lu_solve(self._lu(), np.eye(self.n_transient))

    def largo_esperado(self) -> np.ndarray:
        return sla.lu_solve(self._lu(), np.ones(self.n_transient))

    def absorcion(self) -> np.ndarray:
        return sla.lu_solve(self._lu(), self.R)

    def rho(self) -> float:
        return float(np.max(np.abs(np.linalg.eigvals(self.Q))))


def visitas_por_tipo(P: np.ndarray, mu: np.ndarray, P0: np.ndarray | None = None) -> np.ndarray:
    """(K, 20) visitas esperadas por secuencia: v^k = μ^k + μ^k Q^{0,k} N^k (04 §4; spec 04 §3).

    Con paso inicial P0 la primera acción sale de Q^{0,k} y las siguientes de P^k; sin P0 (artefactos anteriores a D-047,
    P0 = None) se usa P también en el primer paso y queda v^k = μ^k N^k.
    """
    out = []
    for k in range(P.shape[0]):
        c = Cadena(P[k], N_ZONAS)
        if P0 is None:
            out.append(sla.lu_solve(c._lu(), mu[k], trans=1))
        else:
            Q0 = P0[k][:, :N_ZONAS]
            out.append(mu[k] + sla.lu_solve(c._lu(), mu[k] @ Q0, trans=1))
    return np.array(out)


def proporciones_fin(P: np.ndarray, mu: np.ndarray, P0: np.ndarray | None = None) -> np.ndarray:
    """(K, 3): de las jugadas de cada tipo que NO terminan en remate, la fracción que termina en pérdida, fuera e interrupción (faltas y fuera de lugar van juntos en interrupción:
    el modelo no los separa). Sale de la absorción de la cadena de la LIGA por tipo, condicionada a no rematar (D-085). Con paso inicial P0 la primera acción sale de P0."""
    out = []
    for k in range(P.shape[0]):
        B = Cadena(P[k], N_ZONAS).absorcion()  # (20, 5): GOL, REMATE, PERDIDA, FUERA, INTERRUPCION
        a = mu[k] @ B if P0 is None else mu[k] @ (P0[k][:, N_ZONAS:] + P0[k][:, :N_ZONAS] @ B)
        x = np.clip(a[2:5], 0.0, None)
        out.append(x / x.sum())
    return np.array(out)


def mapa_equipo(
    P: np.ndarray, mu: np.ndarray, E_N_k: np.ndarray, P0: np.ndarray | None = None
) -> np.ndarray:
    """(20,) visitas esperadas por zona en un partido, dadas las secuencias esperadas por tipo."""
    return E_N_k @ visitas_por_tipo(P, mu, P0)


def cadenas_sinteticas(largo=(3.5, 6.7, 9.2), p_remate=(0.14, 0.025, 0.12), semilla: int = 0):
    """Cadenas de demostración (modo sintético): avance hacia el arco más fuerte en Directa,
    lateral en Ataque elaborado, en el propio campo en Circulación estéril."""
    rng = np.random.default_rng(semilla)
    nx, ny = 5, 4
    P = np.zeros((3, N_ZONAS, N_ZONAS + N_ABS))
    mu = np.zeros((3, N_ZONAS))
    sesgo_x = (1.2, -0.2, 0.5)
    sesgo_banda = (0.0, 0.0, 0.8)
    for k in range(3):
        for z in range(N_ZONAS):
            ix, iy = divmod(z, ny)
            w = np.zeros(N_ZONAS)
            for z2 in range(N_ZONAS):
                jx, jy = divmod(z2, ny)
                d = abs(jx - ix) + abs(jy - iy)
                if d <= 2:
                    banda = 1.0 if jy in (0, ny - 1) else 0.0
                    w[z2] = np.exp(-d + sesgo_x[k] * (jx - ix) + sesgo_banda[k] * banda)
            w *= np.exp(0.1 * rng.normal(size=N_ZONAS))
            w /= w.sum()
            # absorción: remate más probable cerca del arco
            remate = (
                p_remate[k] / largo[k] * (2.5 if ix == nx - 1 else (0.6 if ix == nx - 2 else 0.05))
            )
            fin = 1.0 / largo[k]
            otros = max(fin - remate, 0.0)
            P[k, z, :N_ZONAS] = (1 - fin) * w
            P[k, z, N_ZONAS:] = [
                remate * 0.12,
                remate * 0.88,
                otros * 0.6,
                otros * 0.25,
                otros * 0.15,
            ]
            P[k, z] /= P[k, z].sum()
        inicio = np.array(
            [np.exp(-0.5 * abs(divmod(z, ny)[0] - (1 if k != 1 else 0))) for z in range(N_ZONAS)]
        )
        mu[k] = inicio / inicio.sum()
    return P, mu
