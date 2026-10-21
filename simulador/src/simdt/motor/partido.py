"""Recursión exacta del marcador (vectorizada sobre un lote de partidos).

Estado: P_t(a, b) = probabilidad de ir a–b al inicio del minuto t (a = goles de i).
Cada minuto, i anota X ~ Poisson(μ_ij(t, m(a,b))) y j anota Y ~ Poisson(μ_ji(t, m'(a,b))),
independientes dado el estado; m = signo de a − b (pierde, empata, gana) desde i y m' = 2 − m.

    P_{t+1}(a + x, b + y) += P_t(a, b) · Pois(x; μ_ij) · Pois(y; μ_ji),   x, y ≤ max_goles_minuto

Se trunca en G goles por equipo y en `max_goles_minuto`; todo lo que se pierde se acumula en
`masa_truncada` (T-P2 exige < 1e-6). Como μ solo depende del signo del marcador, el costo es
O(T · (max+1)² · (G+1)²) por partido y se vectoriza sobre el lote.
"""

from __future__ import annotations

import numpy as np

from .. import config
from ..modelos.intensidad import Intensidad, intensidades_lote
from ..tipos import DistPartido, Liga
from . import _nucleo


def _estado(G1: int) -> np.ndarray:
    a = np.arange(G1)
    d = a[:, None] - a[None, :]
    return np.where(d < 0, 0, np.where(d == 0, 1, 2))


def distribucion_partido(
    mu_ij: np.ndarray,
    mu_ji: np.ndarray,
    G: int | None = None,
    max_por_minuto: int | None = None,
    usar_numba: bool = True,
) -> DistPartido:
    """mu_ij, mu_ji: (T, 3) o (B, T, 3), cada uno indexado por el estado de su propio equipo.

    Implementación: dentro de cada región de marcador m (pierde/empata/gana) las intensidades
    son constantes, así que el paso de un minuto es separable:
        P_{t+1} = Σ_m  T_A[m] · (P_t ∘ 1[m]) · T_B[m]ᵀ
    con T_A[m] la matriz Toeplitz triangular de Pois(·; μ_ij(t, m)) (desplaza los goles de i)
    y T_B[m] la de Pois(·; μ_ji(t, 2 − m)). Son dos productos matriciales por minuto.
    """
    cfg = config.cargar()["partido"]
    G = cfg["G"] if G is None else G
    X = cfg.get("max_goles_minuto", G) if max_por_minuto is None else max_por_minuto
    X = min(X, G)
    mu_ij = np.asarray(mu_ij, dtype=float)
    mu_ji = np.asarray(mu_ji, dtype=float)
    if mu_ij.ndim == 2:
        mu_ij, mu_ji = mu_ij[None], mu_ji[None]
    B, T, _ = mu_ij.shape
    G1 = G + 1
    if _nucleo.DISPONIBLE and usar_numba:
        P, ocup, eg_i, eg_j = _nucleo.recursion(
            np.ascontiguousarray(mu_ij), np.ascontiguousarray(mu_ji), G, X
        )
        dif = np.subtract.outer(np.arange(G1), np.arange(G1))
        return _salida(P, dif, eg_i, eg_j, ocup)
    Mi = _estado(G1)
    mascara = (np.arange(3)[:, None, None] == Mi[None]).astype(float)  # (3, G1, G1)
    dif = np.subtract.outer(np.arange(G1), np.arange(G1))  # i − j
    xs = np.arange(X + 1)
    # E[x] = 1 en las celdas (i, j) con i − j = x: T = pmf @ E arma la Toeplitz con un producto
    E = np.zeros((X + 1, G1 * G1))
    for x in xs:
        E[x] = (dif == x).ravel()
    logfact = np.cumsum(np.r_[0.0, np.log(np.arange(1, X + 1))])
    P = np.zeros((B, G1, G1))
    P[:, 0, 0] = 1.0
    ocup = np.empty((B, T, 3))
    eg_i = np.zeros(B)
    eg_j = np.zeros(B)
    m3 = mascara[None]  # (1, 3, G1, G1)

    def toeplitz(lam):  # lam (B, 3)
        lam = np.maximum(lam, 1e-300)
        pmf = np.exp(-lam[..., None] + xs * np.log(lam[..., None]) - logfact)  # (B, 3, X+1)
        return (pmf.reshape(-1, X + 1) @ E).reshape(B, 3, G1, G1)

    for t in range(T):
        la = mu_ij[:, t]  # (B, 3) por m de i
        lb = mu_ji[:, t, ::-1]  # (B, 3) por m de i
        Pm = P[:, None] * m3  # (B, 3, G1, G1)
        o = Pm.sum((2, 3))
        ocup[:, t] = o
        eg_i += (o * la).sum(1)
        eg_j += (o * lb).sum(1)
        P = np.matmul(np.matmul(toeplitz(la), Pm), toeplitz(lb).transpose(0, 1, 3, 2)).sum(1)
    return _salida(P, dif, eg_i, eg_j, ocup)


def _salida(P, dif, eg_i, eg_j, ocup) -> DistPartido:
    trunc = 1.0 - P.sum((1, 2))
    pg = (P * (dif > 0)).sum((1, 2))
    pe = (P * (dif == 0)).sum((1, 2))
    pp = (P * (dif < 0)).sum((1, 2))
    return DistPartido(
        P=P,
        p_gana=pg,
        p_empata=pe,
        p_pierde=pp,
        xpts_i=3 * pg + pe,
        xpts_j=3 * pp + pe,
        eg_i=eg_i,
        eg_j=eg_j,
        ocupacion=ocup,
        masa_truncada=trunc,
    )


def partido_lote(
    liga: Liga, zi: np.ndarray, zj: np.ndarray, local_i, elo_diff, con_detalle: bool = False, **kw
) -> DistPartido:
    """Intensidades de los dos lados + recursión; con_detalle agrega E[N_k], E[goles_k], E[goles_bp]."""
    zi, zj = np.atleast_2d(zi), np.atleast_2d(zj)
    B = zi.shape[0]
    local_i = np.broadcast_to(np.asarray(local_i, dtype=float), (B,))
    elo_diff = np.broadcast_to(np.asarray(elo_diff, dtype=float), (B,))
    Ii = intensidades_lote(liga, zi, zj, local_i, elo_diff)
    Ij = intensidades_lote(liga, zj, zi, 1.0 - local_i, -elo_diff)
    d = distribucion_partido(Ii.mu, Ij.mu, **kw)
    if con_detalle:
        d.extra = detalle(d, Ii, Ij)
    return d


def detalle(d: DistPartido, Ii: Intensidad, Ij: Intensidad) -> dict:
    occ_i = d.ocupacion  # (B, T, 3) desde i
    occ_j = occ_i[:, :, ::-1]  # desde j
    out = {}
    for lado, I, occ in (("i", Ii, occ_i), ("j", Ij, occ_j)):
        out[f"N_k_{lado}"] = np.einsum("btm,btmk->bk", occ, I.n_k)
        out[f"goles_k_{lado}"] = np.einsum("btm,btmk->bk", occ, I.goles_k)
        out[f"goles_bp_{lado}"] = I.goles_bp.sum(1)  # (B, U)
        out[f"pi_{lado}"] = out[f"N_k_{lado}"] / out[f"N_k_{lado}"].sum(1, keepdims=True)
    out["ocupacion_m"] = occ_i.mean(1)  # (B, 3) fracción del partido
    return out


def simular_eventos(
    mu_ij: np.ndarray, mu_ji: np.ndarray, n: int, rng
) -> tuple[np.ndarray, np.ndarray]:
    """Simulación minuto a minuto (para T-P3): devuelve goles de i y de j en n partidos."""
    T = mu_ij.shape[0]
    a = np.zeros(n, dtype=int)
    b = np.zeros(n, dtype=int)
    for t in range(T):
        m = np.where(a < b, 0, np.where(a == b, 1, 2))
        ga = rng.poisson(mu_ij[t, m])
        gb = rng.poisson(mu_ji[t, 2 - m])
        a += ga
        b += gb
    return a, b


def simular_partido_minutos(
    mu_ij: np.ndarray, mu_ji: np.ndarray, rng
) -> tuple[int, int, list, np.ndarray, np.ndarray]:
    """UN partido minuto a minuto con el MISMO proceso de `simular_eventos` (T-P3): en cada minuto i anota Poisson(μ_ij(t, m)) y j anota Poisson(μ_ji(t, 2 − m)), con m el
    signo del marcador al empezar el minuto. Las cuentas de Poisson de las tres posibilidades de m se sortean de una vez y solo se usa la del estado real (el resultado
    es el mismo proceso, porque cada celda es independiente).
    Devuelve (goles de i, goles de j, [(minuto, 'i' | 'j', goles de i, goles de j) ...], peligro de i por minuto, peligro de j por minuto); «peligro» = la intensidad
    de gol que se usó en ese minuto (la que cambia con el marcador). Un minuto con varios goles los anota en orden i, j."""
    T = mu_ij.shape[0]
    X = rng.poisson(mu_ij)  # (T, 3) por estado de i
    Y = rng.poisson(mu_ji)  # (T, 3) por estado de j
    a = b = 0
    goles, pi_, pj_ = [], np.empty(T), np.empty(T)
    for t in range(T):
        m = 0 if a < b else (1 if a == b else 2)
        pi_[t], pj_[t] = mu_ij[t, m], mu_ji[t, 2 - m]
        for _ in range(int(X[t, m])):
            a += 1
            goles.append((t + 1, "i", a, b))
        for _ in range(int(Y[t, 2 - m])):
            b += 1
            goles.append((t + 1, "j", a, b))
    return a, b, goles, pi_, pj_
