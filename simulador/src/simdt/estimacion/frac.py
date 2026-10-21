"""Logit multinomial FRACCIONAL (cuasi-verosimilitud de Papke y Wooldridge, 1996) con
varianza sandwich agrupada por partido.

Para cada fila i hay conteos fraccionales y_ik = Σ_s r_sk (suma de responsabilidades) y
un predictor lineal en los parámetros:  η_ik = offset_ik + A_ik · β.
Q(β) = Σ_i Σ_k y_ik log softmax(η_i)_k. Es consistente para E[y_ik / n_i] = π_ik(β) aunque
y no sea multinomial; la varianza correcta es la sandwich H⁻¹ (Σ_g s_g s_gᵀ) H⁻¹.
Reimplementa la idea de dtcoach/pesos.py (ADR-v2-21) sin polars.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AjusteFrac:
    beta: np.ndarray
    cov: np.ndarray  # sandwich agrupado
    cov_modelo: np.ndarray  # −H⁻¹
    convergio: bool
    n_grupos: int


def _softmax(eta):
    e = np.exp(eta - eta.max(1, keepdims=True))
    return e / e.sum(1, keepdims=True)


def ajustar(
    Y: np.ndarray,
    A: np.ndarray,
    grupos: np.ndarray,
    offset: np.ndarray | None = None,
    beta0: np.ndarray | None = None,
    max_iter: int = 50,
    tol: float = 1e-10,
    ridge: float = 1e-8,
) -> AjusteFrac:
    """Y: (n, K) conteos fraccionales; A: (n, K, P) diseño; grupos: (n,) clúster (partido)."""
    n, K, P = A.shape
    off = np.zeros((n, K)) if offset is None else offset
    beta = np.zeros(P) if beta0 is None else beta0.astype(float).copy()
    tot = Y.sum(1)
    convergio = False
    for _ in range(max_iter):
        pi = _softmax(off + A @ beta)
        resid = Y - tot[:, None] * pi  # (n, K)
        g = np.einsum("nk,nkp->p", resid, A)
        Abar = np.einsum("nk,nkp->np", pi, A)  # Σ_k π_k A_k
        # H = −Σ_i n_i [Σ_k π_k A_k A_kᵀ − Ā Āᵀ]
        H = -(
            np.einsum("n,nk,nkp,nkq->pq", tot, pi, A, A) - np.einsum("n,np,nq->pq", tot, Abar, Abar)
        )
        H -= ridge * np.eye(P)
        paso = np.linalg.solve(H, -g)
        # búsqueda de línea simple (la cuasi-verosimilitud es cóncava)
        f0 = (Y * np.log(np.maximum(pi, 1e-300))).sum()
        t = 1.0
        while t > 1e-6:
            b1 = beta + t * paso
            f1 = (Y * np.log(np.maximum(_softmax(off + A @ b1), 1e-300))).sum()
            if f1 >= f0 - 1e-12:
                break
            t /= 2
        beta = b1
        if np.max(np.abs(t * paso)) < tol:
            convergio = True
            break
    pi = _softmax(off + A @ beta)
    resid = Y - tot[:, None] * pi
    S_i = np.einsum("nk,nkp->np", resid, A)
    _, inv = np.unique(grupos, return_inverse=True)
    G = inv.max() + 1
    S_g = np.zeros((G, P))
    np.add.at(S_g, inv, S_i)
    Abar = np.einsum("nk,nkp->np", pi, A)
    H = -(np.einsum("n,nk,nkp,nkq->pq", tot, pi, A, A) - np.einsum("n,np,nq->pq", tot, Abar, Abar))
    Hinv = np.linalg.pinv(H)
    meat = S_g.T @ S_g * (G / max(G - 1, 1))
    cov = Hinv @ meat @ Hinv
    return AjusteFrac(beta, cov, -Hinv, convergio, G)


def diseno_liga(X: np.ndarray, K: int, ref: int) -> np.ndarray:
    """A (n, K, (K−1)·p): coeficientes libres para cada k ≠ ref, columnas de X."""
    n, p = X.shape
    libres = [k for k in range(K) if k != ref]
    A = np.zeros((n, K, len(libres) * p))
    for r, k in enumerate(libres):
        A[:, k, r * p : (r + 1) * p] = X
    return A
