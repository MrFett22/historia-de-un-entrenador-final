"""Mezcla de K cadenas absorbentes (EM-MAP con encogimiento Dirichlet hacia la liga) CON PASO INICIAL P⁰.

Cada secuencia s = (z1, …, z_{T+1}) del tipo k tiene probabilidad  μ^k[z1] · P0^k[z1, z2] · ∏_{t≥2} P^k[z_t, z_{t+1}]
(la PRIMERA acción tiene su propia matriz P0; ADR-v2-29). Sin P0 la mezcla sobreestima las secuencias de una acción y
reparte distinto los tipos: con los datos de dtcoach daba P(remate) 0.077 / 0.109 / 0.119 en vez de 0.140 / 0.025 / 0.122 (D-047).

Procedencia: dtcoach_revision/dtcoach_revision_20260925_0951/src/dtcoach/mezcla.py@77b720b
(funciones `pooled`, `_loglik_tipos`, `_m_step`, `_objetivo`, `_em`, `_partir`, `ajustar` con
init="escalera" y `ordenar_por_largo`), adaptadas a una matriz dispersa construida sin polars y a
una malla 5×4 sin fases (20 transitorios + 5 absorbentes).
Procedencia: .../dtcoach/estimate.py@77b720b (`shrink`).
Procedencia (paso inicial P⁰, `Prior`, `prior`, `_loglik_tipos`, `_m_step`, `_objetivo`, `_partir`, `Mezcla.inicio`,
`ajustar` con arranque atado y liberación de P0, `ordenar_por_largo`):
    estudio/src/dtcoach/mezcla.py  (ADR-v2-29 en estudio/docs/06_DECISIONES.md)
Diferencias con la fuente: sin polars (`Datos` en vez de `DatosPosesion`), `logsumexp` de scipy en vez de `_lse`, y `_em`
devuelve solo la `Mezcla` (sin la bandera de convergencia ni el diagnóstico de estabilidad).
"""

from __future__ import annotations

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
from scipy.special import logsumexp

from ..modelos.cadena import N_ABS, N_ZONAS, Cadena

_EPS = 1e-300
NT, NS = N_ZONAS, N_ZONAS + N_ABS


@dataclass
class Datos:
    S: sp.csr_matrix  # (n, NT*NS) conteos de TODAS las transiciones
    inicio: np.ndarray  # (n,)
    largo: np.ndarray
    S0: sp.csr_matrix | None = (
        None  # solo la PRIMERA transición de cada secuencia (para P⁰); None = sin paso inicial
    )

    @property
    def n(self):
        return self.S.shape[0]

    @property
    def S1(self) -> sp.csr_matrix:
        """Las transiciones SIGUIENTES a la primera (S − S0); se calcula una vez por instancia (constante en el EM)."""
        s1 = self.__dict__.get("_S1")
        if s1 is None:
            s1 = self.__dict__["_S1"] = self.S - self.S0
        return s1

    def sub(self, idx):
        return Datos(
            self.S[idx],
            self.inicio[idx],
            self.largo[idx],
            None if self.S0 is None else self.S0[idx],
        )


def datos_desde(
    trans_sid: np.ndarray, desde: np.ndarray, hacia: np.ndarray, n: int, inicio: np.ndarray
) -> Datos:
    """`trans_sid`: secuencia de cada transición, en el ORDEN en que ocurren (la 1.ª aparición de un sid es su primer paso)."""
    S = sp.csr_matrix((np.ones(len(desde)), (trans_sid, desde * NS + hacia)), shape=(n, NT * NS))
    S.sum_duplicates()
    largo = np.asarray(S.sum(1)).ravel()
    primera = np.unique(trans_sid, return_index=True)[
        1
    ]  # índice de la 1.ª transición de cada secuencia
    S0 = sp.csr_matrix(
        (np.ones(len(primera)), (trans_sid[primera], desde[primera] * NS + hacia[primera])),
        shape=(n, NT * NS),
    )
    return Datos(S, inicio.astype(np.int64), largo, S0)


@dataclass
class Mezcla:
    pi: np.ndarray
    mu: np.ndarray  # (K, NT)
    P: np.ndarray  # (K, NT, NS) acciones SIGUIENTES a la primera
    lam: float
    a0: float
    objetivo: list = field(default_factory=list)
    P0: np.ndarray | None = (
        None  # (K, NT, NS) primera acción; None = atado a P (modelo sin paso inicial)
    )
    diagnostico: dict = field(
        default_factory=dict
    )  # multiarranque: J de cada arranque, ganador y dispersión (D-049)

    @property
    def K(self):
        return len(self.pi)

    @property
    def paso_inicial(self) -> bool:
        return self.P0 is not None

    def P0e(self, k: int) -> np.ndarray:
        return self.P[k] if self.P0 is None else self.P0[k]

    def inicio(self, k: int) -> dict:
        """Cantidades desde el INICIO de una secuencia del tipo k (incluye el primer paso):
        E[T] = μ(1 + Q0 t) y P(absorción) = μ(R0 + Q0 B), con t = N 1 y B = N R de la cadena P (04 §4)."""
        cad = Cadena(self.P[k], NT)
        P0 = self.P0e(k)
        Q0, R0 = P0[:, :NT], P0[:, NT:]
        t = cad.largo_esperado()
        B = cad.absorcion()
        mu = self.mu[k]
        return {"E_T": float(mu @ (1.0 + Q0 @ t)), "B": mu @ (R0 + Q0 @ B), "t": t, "cadena": cad}


@dataclass
class Prior:
    Qp: np.ndarray  # destino del encogimiento de P
    Q0p: np.ndarray  # destino del encogimiento de P0
    mup: np.ndarray
    lam: float
    lam0: float
    a0: float
    paso: bool


# Procedencia: dtcoach/estimate.py@77b720b
def shrink(C: np.ndarray, Q: np.ndarray, lam: float) -> np.ndarray:
    n = C.sum(axis=1, keepdims=True)
    return (C + lam * Q) / (n + lam)


def pooled(d: Datos, lam0: float = 1.0):
    C = np.asarray(d.S.sum(axis=0)).ravel().reshape(NT, NS)
    Q = shrink(C, np.full((NT, NS), 1.0 / NS), lam0)
    m = np.bincount(d.inicio, minlength=NT).astype(float) + lam0 / NT
    return Q, m / m.sum()


# Procedencia: estudio/src/dtcoach/mezcla.py (`prior`)
def prior(
    d: Datos,
    lam: float,
    a0: float = 1.0,
    paso: bool = True,
    lam0: float | None = None,
    lam_u: float = 1.0,
    lam_puente: float = 10.0,
) -> Prior:
    U = np.full((NT, NS), 1.0 / NS)
    m = np.bincount(d.inicio, minlength=NT).astype(float) + lam_u / NT
    mup = m / m.sum()
    if not paso:
        Q = shrink(np.asarray(d.S.sum(axis=0)).ravel().reshape(NT, NS), U, lam_u)
        return Prior(Q, Q, mup, lam, lam, a0, False)
    C1 = np.asarray(d.S1.sum(axis=0)).ravel().reshape(NT, NS)
    C0 = np.asarray(d.S0.sum(axis=0)).ravel().reshape(NT, NS)
    Q = shrink(C1, U, lam_u)
    Q0 = shrink(C0, Q, lam_puente)  # primer paso con poco soporte -> dinámica general
    return Prior(Q, Q0, mup, lam, lam if lam0 is None else lam0, a0, True)


def _loglik_tipos(d: Datos, P, mu, P0=None):
    """(n, K) con log L_k(s). Con P0, la primera transición usa P0 y las demás P."""
    K = P.shape[0]
    logP = np.log(np.maximum(P.reshape(K, -1), _EPS)).T
    if P0 is None:
        L = np.asarray(d.S @ logP)
    else:
        logP0 = np.log(np.maximum(P0.reshape(K, -1), _EPS)).T
        L = np.asarray(d.S1 @ logP) + np.asarray(d.S0 @ logP0)
    L += np.log(np.maximum(mu[:, d.inicio], _EPS)).T
    return L


def _m_step(d: Datos, r, pr: Prior):
    K = r.shape[1]
    if pr.paso:
        C = np.asarray(d.S1.T @ r).T.reshape(K, NT, NS)
        C0 = np.asarray(d.S0.T @ r).T.reshape(K, NT, NS)
        P = (C + pr.lam * pr.Qp[None]) / (C.sum(2, keepdims=True) + pr.lam)
        # Prior FIJO del primer paso (primeros pasos de la liga): mantiene el EM exacto y monótono (ADR-v2-29).
        P0 = (C0 + pr.lam0 * pr.Q0p[None]) / (C0.sum(2, keepdims=True) + pr.lam0)
    else:
        C = np.asarray(d.S.T @ r).T.reshape(K, NT, NS)
        P0 = None
        P = (C + pr.lam * pr.Qp[None]) / (C.sum(2, keepdims=True) + pr.lam)
    M = np.stack([np.bincount(d.inicio, weights=r[:, k], minlength=NT) for k in range(K)])
    mu = (M + pr.a0 * pr.mup[None]) / (M.sum(axis=1, keepdims=True) + pr.a0)
    pi = np.clip(r.mean(axis=0), 1e-12, None)
    return pi / pi.sum(), mu, P, P0


def _objetivo(Lpi, P, P0, mu, pr: Prior):
    J = float(logsumexp(Lpi, axis=1).sum())
    J += pr.lam * float((pr.Qp[None] * np.log(np.maximum(P, _EPS))).sum())
    if P0 is not None:
        J += pr.lam0 * float((pr.Q0p[None] * np.log(np.maximum(P0, _EPS))).sum())
    return J + pr.a0 * float((pr.mup[None] * np.log(np.maximum(mu, _EPS))).sum())


def _em(d, pi, mu, P, P0, pr: Prior, max_iter, tol):
    obj = []
    for it in range(max_iter):
        Lpi = _loglik_tipos(d, P, mu, P0) + np.log(pi)[None]
        obj.append(_objetivo(Lpi, P, P0, mu, pr))
        r = np.exp(Lpi - logsumexp(Lpi, axis=1, keepdims=True))
        pi, mu, P, P0 = _m_step(d, r, pr)
        if len(pi) == 1 or (it > 0 and abs(obj[-1] - obj[-2]) < tol * abs(obj[-2])):
            break
    return Mezcla(pi, mu, P, pr.lam, pr.a0, obj, P0)


def _partir(m: Mezcla, k: int, rng, eps: float = 0.25):
    """Duplica el tipo k perturbando su distribución de inicio en direcciones opuestas."""
    u = rng.normal(size=m.mu.shape[1])
    a = np.clip(m.mu[k] * np.exp(eps * u), 1e-12, None)
    b = np.clip(m.mu[k] * np.exp(-eps * u), 1e-12, None)
    mu = np.vstack([np.delete(m.mu, k, 0), a / a.sum(), b / b.sum()])
    P = np.concatenate([np.delete(m.P, k, 0), m.P[k][None], m.P[k][None]])
    P0 = (
        None
        if m.P0 is None
        else np.concatenate([np.delete(m.P0, k, 0), m.P0[k][None], m.P0[k][None]])
    )
    pi = np.append(np.delete(m.pi, k), [m.pi[k] / 2, m.pi[k] / 2])
    return pi / pi.sum(), mu, P, P0


def largo_esperado(m: Mezcla) -> np.ndarray:
    """E[T] desde el INICIO de la secuencia de cada tipo (con P0 si lo hay)."""
    return np.array([m.inicio(k)["E_T"] for k in range(m.K)])


def ordenar_por_largo(m: Mezcla) -> Mezcla:
    o = np.argsort(largo_esperado(m))
    return Mezcla(
        m.pi[o], m.mu[o], m.P[o], m.lam, m.a0, m.objetivo, None if m.P0 is None else m.P0[o]
    )


def ajustar(
    d: Datos,
    K: int,
    lam: float,
    a0: float = 1.0,
    max_iter: int = 300,
    tol: float = 1e-7,
    seed: int = 0,
    n_corto: int = 25,
    verbose: bool = False,
    paso_inicial: bool = True,
    lam0: float | None = None,
) -> Mezcla:
    """Escalera (ADR-v2-17): sube de 1 a K partiendo el mejor tipo en cada nivel.

    Con paso inicial (ADR-v2-29) los TIPOS se encuentran con el modelo atado (P0 = P) y después se libera P0 continuando
    el EM: arrancar la escalera con P0 libre desordenaba la mezcla (P0 le da a cada tipo otra forma de explicar las
    secuencias cortas y la escalera cae en otro óptimo). Sin `S0` en los datos se ajusta sin paso inicial.
    """
    if lam <= 0:
        raise ValueError("lam debe ser > 0 (sin encogimiento, un tipo vacío da filas 0/0)")
    paso = bool(paso_inicial and d.S0 is not None)
    pr = prior(d, lam, a0, paso, lam0)
    if paso:
        C = np.asarray(d.S.sum(axis=0)).ravel().reshape(NT, NS)
        pr_tipos = Prior(
            shrink(C, np.full(C.shape, 1.0 / C.shape[1]), 1.0),
            None,
            pr.mup,
            pr.lam,
            pr.lam,
            pr.a0,
            False,
        )
        pr_tipos.Q0p = pr_tipos.Qp
    else:
        pr_tipos = pr
    rng = np.random.default_rng([seed, K])
    m = _em(d, *_m_step(d, np.ones((d.n, 1)), pr_tipos), pr_tipos, max_iter, tol)
    for nivel in range(2, K + 1):
        cand = []
        for k in range(m.K):
            mk = _em(d, *_partir(m, k, rng), pr_tipos, n_corto, tol)
            cand.append((mk.objetivo[-1], k, mk))
        _, k0, m0 = max(cand, key=lambda t: t[0])
        m = _em(d, m0.pi, m0.mu, m0.P, m0.P0, pr_tipos, max_iter, tol)
        if verbose:
            print(
                f"    K={nivel}: partiendo el tipo {k0 + 1} -> J={m.objetivo[-1]:.1f}", flush=True
            )
    if paso:
        J_atado = m.objetivo[-1]
        m = _em(d, m.pi, m.mu, m.P, m.P.copy(), pr, max_iter, tol)
        if verbose:
            print(
                f"    paso inicial liberado: J {J_atado:.1f} (atado) -> {m.objetivo[-1]:.1f}",
                flush=True,
            )
    return ordenar_por_largo(m)


def responsabilidades(m: Mezcla, d: Datos, lote: int = 200_000) -> np.ndarray:
    out = np.empty((d.n, m.K))
    for a in range(0, d.n, lote):
        sub = d.sub(np.arange(a, min(a + lote, d.n)))
        Lpi = _loglik_tipos(sub, m.P, m.mu, m.P0) + np.log(m.pi)[None]
        out[a : a + lote] = np.exp(Lpi - logsumexp(Lpi, axis=1, keepdims=True))
    return out


def resumen(m: Mezcla) -> list[dict]:
    out = []
    for k in range(m.K):
        i = m.inicio(k)
        out.append(
            {
                "pi": float(m.pi[k]),
                "E_T": i["E_T"],
                "p_remate": float(i["B"][:2].sum()),
                "p_gol": float(i["B"][0]),
                "rho_Q": i["cadena"].rho(),
            }
        )
    return out


# ----------------------------------------------------------------------------------------------
# Multiarranque (D-049)
# ----------------------------------------------------------------------------------------------
SEMILLA_FUENTE = 20260924  # `seed` de dtcoach (config/default.yaml): con ella la escalera cae en el óptimo de la fuente


def objetivo_final(
    m: Mezcla, d: Datos, lam: float, a0: float = 1.0, lam0: float | None = None
) -> float:
    """J (log-verosimilitud + log-priors) de `m` sobre `d` con el prior de `prior()`: comparable entre ajustes de los mismos datos."""
    pr = prior(d, lam, a0, m.P0 is not None, lam0)
    Lpi = _loglik_tipos(d, m.P, m.mu, m.P0) + np.log(m.pi)[None]
    return float(_objetivo(Lpi, m.P, m.P0, m.mu, pr))


def semillas_arranques(seed: int, n: int, fuente: int = SEMILLA_FUENTE) -> list[int]:
    """`n` semillas distintas y reproducibles: la global, la de dtcoach y las derivadas de la global."""
    out = [int(seed)]
    if n > 1 and fuente not in out:
        out.append(int(fuente))
    for v in np.random.SeedSequence(int(seed)).generate_state(4 * n + 4):
        if len(out) >= n:
            break
        v = int(v) % (2**31)
        if v not in out:
            out.append(v)
    return out[:n]


def _un_arranque(t: tuple) -> Mezcla:
    d, a, semilla = t
    return ajustar(
        d,
        a["K"],
        a["lam"],
        a["a0"],
        a["max_iter"],
        a["tol"],
        semilla,
        a["n_corto"],
        False,
        a["paso_inicial"],
        a["lam0"],
    )


def _tarjetas_de(m: Mezcla) -> np.ndarray:
    r = resumen(m)
    return np.array([[x["pi"], x["E_T"], x["p_remate"]] for x in r])


def ajustar_multi(
    d: Datos,
    K: int,
    lam: float,
    a0: float = 1.0,
    max_iter: int = 300,
    tol: float = 1e-7,
    seed: int = 0,
    n_corto: int = 25,
    n_arranques: int = 8,
    semillas: list[int] | None = None,
    n_jobs: int = 1,
    verbose: bool = False,
    paso_inicial: bool = True,
    lam0: float | None = None,
) -> Mezcla:
    """`ajustar` desde `n_arranques` semillas y se queda con la de mayor J (D-049).

    La escalera depende de la semilla (las direcciones con que parte cada tipo): con la semilla de simdt (20261008) cae en un óptimo
    local 976 unidades de J peor que la de dtcoach (20260924) y el vocabulario cambia (P(remate) 0.079 / 0.104 / 0.122 en vez de 0.140 / 0.025 / 0.122).
    `m.diagnostico`: semillas, J de cada arranque, ganador, ΔJ contra el ganador y dispersión de (π, E[T], P(remate)) entre arranques
    (tipos ordenados por E[T]); `dispersion_optimo` solo con los arranques a menos de 1 unidad de J del mejor.
    """
    sem = list(semillas) if semillas else semillas_arranques(seed, n_arranques)
    args = {
        "K": K,
        "lam": lam,
        "a0": a0,
        "max_iter": max_iter,
        "tol": tol,
        "n_corto": n_corto,
        "paso_inicial": paso_inicial,
        "lam0": lam0,
    }
    trabajos = [(d, args, s_) for s_ in sem]
    if n_jobs > 1 and len(sem) > 1:
        # "spawn" y no "fork": con hilos de BLAS / OpenMP / numba ya iniciados, fork puede bloquearse; los datos (matriz dispersa) pesan decenas de MB
        with ProcessPoolExecutor(min(n_jobs, len(sem)), mp_context=mp.get_context("spawn")) as ex:
            ms = list(ex.map(_un_arranque, trabajos))
    else:
        ms = [_un_arranque(t) for t in trabajos]
    J = np.array([objetivo_final(m, d, lam, a0, lam0) for m in ms])
    g = int(np.argmax(J))
    T = [_tarjetas_de(m) for m in ms]
    disp = lambda idx: {
        c: float(max(np.abs(T[i][:, j] - T[g][:, j]).max() for i in idx))  # noqa: E731
        for j, c in enumerate(("pi", "E_T", "p_remate"))
    }
    cerca = [i for i in range(len(ms)) if J[g] - J[i] <= 1.0]
    diag = {
        "semillas": [int(x) for x in sem],
        "J": [float(x) for x in J],
        "J_por_secuencia": [float(x / d.n) for x in J],
        "ganador": g,
        "semilla_ganadora": int(sem[g]),
        "J_ganador": float(J[g]),
        "dJ": [float(J[g] - x) for x in J],
        "iteraciones": [len(m.objetivo) for m in ms],
        "n_en_el_optimo": len(cerca),
        "dispersion": disp(range(len(ms))),
        "dispersion_optimo": disp(cerca),
        "tarjetas_ganador": T[g].tolist(),
    }
    if verbose:
        print(
            f"    multiarranque: {len(sem)} semillas, J = {np.round(J, 1).tolist()}; gana {sem[g]} (J {J[g]:,.1f}); "
            f"{len(cerca)} en el óptimo; dispersión de π {diag['dispersion']['pi']:.4f}",
            flush=True,
        )
    m = ms[g]
    m.diagnostico = diag
    return m
