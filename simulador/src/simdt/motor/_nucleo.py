"""Núcleo compilado (numba) de la recursión del marcador. Misma ecuación que la versión numpy de
`partido.py`; se omiten celdas y goles por minuto con probabilidad < 1e-20 (esa masa queda en
`masa_truncada`). Si numba no está disponible, `partido.py` usa la versión numpy."""

from __future__ import annotations

import math

import numpy as np

try:
    from numba import njit, prange

    DISPONIBLE = True
except ImportError:  # pragma: no cover
    DISPONIBLE = False

UMBRAL = 1e-20

if DISPONIBLE:

    @njit(parallel=True, cache=True, fastmath=False)
    def recursion(mu_ij, mu_ji, G, X):
        B, T, _ = mu_ij.shape
        G1 = G + 1
        Pout = np.zeros((B, G1, G1))
        ocup = np.zeros((B, T, 3))
        eg_i = np.zeros(B)
        eg_j = np.zeros(B)
        for b in prange(B):
            P = np.zeros((G1, G1))
            Pn = np.zeros((G1, G1))
            P[0, 0] = 1.0
            pA = np.zeros((3, X + 1))
            pB = np.zeros((3, X + 1))
            nA = np.zeros(3, dtype=np.int64)
            nB = np.zeros(3, dtype=np.int64)
            for t in range(T):
                for m in range(3):
                    la = max(mu_ij[b, t, m], 1e-300)
                    lb = max(mu_ji[b, t, 2 - m], 1e-300)
                    va = math.exp(-la)
                    vb = math.exp(-lb)
                    nA[m] = 0
                    nB[m] = 0
                    for x in range(X + 1):
                        pA[m, x] = va
                        pB[m, x] = vb
                        if va > UMBRAL:
                            nA[m] = x + 1
                        if vb > UMBRAL:
                            nB[m] = x + 1
                        va = va * la / (x + 1)
                        vb = vb * lb / (x + 1)
                for i in range(G1):
                    for j in range(G1):
                        Pn[i, j] = 0.0
                o0 = 0.0
                o1 = 0.0
                o2 = 0.0
                for a in range(G1):
                    for c in range(G1):
                        p = P[a, c]
                        if p < UMBRAL:
                            continue
                        m = 0 if a < c else (1 if a == c else 2)
                        if m == 0:
                            o0 += p
                        elif m == 1:
                            o1 += p
                        else:
                            o2 += p
                        xa = min(nA[m], G1 - a)
                        yb = min(nB[m], G1 - c)
                        for x in range(xa):
                            px = p * pA[m, x]
                            for y in range(yb):
                                Pn[a + x, c + y] += px * pB[m, y]
                ocup[b, t, 0] = o0
                ocup[b, t, 1] = o1
                ocup[b, t, 2] = o2
                eg_i[b] += o0 * mu_ij[b, t, 0] + o1 * mu_ij[b, t, 1] + o2 * mu_ij[b, t, 2]
                eg_j[b] += o0 * mu_ji[b, t, 2] + o1 * mu_ji[b, t, 1] + o2 * mu_ji[b, t, 0]
                for i in range(G1):
                    for j in range(G1):
                        P[i, j] = Pn[i, j]
            Pout[b] = P
        return Pout, ocup, eg_i, eg_j
