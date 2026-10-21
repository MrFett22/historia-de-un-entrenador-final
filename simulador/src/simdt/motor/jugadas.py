"""«Ver un partido» a nivel de jugadas (D-073): el MISMO proceso de goles del motor, pero armado con sus piezas.

En cada minuto t, con el marcador del momento (m = pierde / empata / gana desde cada lado) y para cada equipo i:
    jugadas de juego abierto de tipo k:   N_ik ~ Poisson(λ_i(t) π_ik(t, m))
    remates de esas jugadas (adelgazamiento):  S_ik ~ Poisson(λ_i π_ik p_ik)
    saques de pelota parada de tipo u:    ~ Poisson(r̄_u e^…),  con remate q_iju  →  S_iu ~ Poisson(saques · q)
    cada remate trae su peligro x (Beta de media g_ik o κ_u) y es gol con probabilidad f·x, con f = goles/xG de la liga.
Para que f·x nunca pase de 1 sin recortar nada, el peligro se sortea ya multiplicado: y = f·x ~ Beta(media f·g, concentración c) y x = y / f. Cada remate es gol con
probabilidad y; marginalmente un remate es gol con probabilidad f·g, sin importar c.

Marcado y adelgazamiento de Poisson: los remates de cada tipo son Poisson(λ π p); cada uno es gol de forma independiente con probabilidad f·g; los goles de ese tipo son
Poisson(f λ π p g); la suma de Poisson independientes es Poisson, así que los goles del minuto son Poisson(f [λ Σ π p g + Σ saques q κ]) = Poisson(μ_ij(t, m)), la misma
intensidad del motor. El marcador entra por π exactamente igual que en el motor.

Momentum de la v7 (se conserva, la app ya no lo usa): peligro_i(t) = suma de los x de los remates de i en el minuto t; momentum(t) = suavizado exponencial de peligro_América(t) − peligro_rival(t).

Presión (v10, D-093; estándar tipo Sofascore): cada equipo POR SEPARADO, en unidades de gol esperado por minuto, para que su media sea la μ del motor:
    amenaza T_i(t) = Σ_k N_ik e_k + Σ_u saques_iu q_u κ_u f        con e_k = f p_k g_k: el valor esperado de CADA jugada y de cada saque, rematen o no
    remates Y_i(t) = Σ_j y_j                                        el valor real (la probabilidad de gol y de cada remate sorteado)
    presión P_i(t) = T_i + s (Y_i − T_i)                            amenaza esperada más una fracción s de la sorpresa de los remates (0 ≤ s ≤ 1: nunca negativa)
    S_i(t) = EMA(P_i)                                               media móvil exponencial con la vida media del config
E[T_i] = E[Y_i] = μ_i(t, m), así que E[P_i] = E[S_i] = μ_i (la EMA conserva la media). Esto solo describe lo que se DIBUJA: los goles se sortean igual que antes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import config
from ..modelos.balon_parado import balon_parado
from ..modelos.cadena import proporciones_fin
from ..modelos.eficiencia import eficiencia
from ..modelos.intensidad import intensidades_lote
from ..tipos import K, U, Liga


@dataclass
class Componentes:
    """Las piezas de μ de UN lado de UN partido (B = 1)."""

    n_k: np.ndarray  # (T, 3, K) jugadas de juego abierto esperadas por minuto
    p: np.ndarray  # (K,) P(remate | jugada)
    g: np.ndarray  # (K,) xG por remate
    saques: np.ndarray  # (T, U) saques esperados por minuto
    q: np.ndarray  # (U,) P(remate | saque)
    kappa: np.ndarray  # (U,) xG por saque con remate
    f: float  # goles / xG de la liga
    mu: np.ndarray  # (T, 3) la μ del motor (solo para comprobar)
    fin_k: np.ndarray | None = (
        None  # (K, 3) de las jugadas que no rematan: fracción que termina en pérdida, fuera e interrupción (cadena de la liga)
    )

    @property
    def T(self) -> int:
        return self.n_k.shape[0]


def componentes(liga: Liga, zi, zj, local_i, elo_diff) -> Componentes:
    """Las piezas de μ_ij con las mismas funciones del motor (`intensidades_lote`, `eficiencia`, `balon_parado`)."""
    zi, zj = np.atleast_2d(zi), np.atleast_2d(zj)
    local_i = np.broadcast_to(np.asarray(local_i, dtype=float), (zi.shape[0],))
    elo_diff = np.broadcast_to(np.asarray(elo_diff, dtype=float), (zi.shape[0],))
    I = intensidades_lote(liga, zi, zj, local_i, elo_diff)
    p, g = eficiencia(liga, zi, zj)
    saques, gps = balon_parado(liga, zi, zj, local_i)
    kappa = np.asarray(liga.kappa, float)
    fin = (
        None
        if liga.P_cadenas is None
        else proporciones_fin(
            np.asarray(liga.P_cadenas),
            np.asarray(liga.mu_cadenas),
            None if liga.P0_cadenas is None else np.asarray(liga.P0_cadenas),
        )
    )
    return Componentes(
        n_k=I.n_k[0],
        p=p[0],
        g=g[0],
        saques=saques[0],
        q=np.clip(gps[0] / kappa, 0.0, 1.0),
        kappa=kappa,
        f=float(liga.factor_gol),
        mu=I.mu[0],
        fin_k=fin,
    )


def _beta(rng, media: float, conc: float, tam: int) -> np.ndarray:
    media = float(np.clip(media, 1e-6, 1 - 1e-6))
    return rng.beta(media * conc, (1.0 - media) * conc, size=tam)


def _lado(C: Componentes, t: int, m: np.ndarray, rng, conc: float) -> dict:
    """Un minuto de un lado para n partidos (m: estado de cada uno). Las jugadas de juego abierto de tipo k son Poisson(λ π); cada una termina en remate con probabilidad p_k
    (Binomial: por adelgazamiento, los remates siguen siendo Poisson(λ π p)) y las que no, en pérdida / fuera / interrupción con las proporciones de la cadena de la liga. Los saques de
    pelota parada de tipo u son Poisson(r̄_u e^…) y cada uno termina en remate con probabilidad q_u. Cada remate trae su peligro y es gol con probabilidad f·x (D-073, D-085)."""
    n = m.size
    goles = np.zeros(n)
    goles_abierto = np.zeros(n)
    remates = np.zeros(n, dtype=np.int64)
    peligro = np.zeros(n)
    jugadas = rng.poisson(C.n_k[t][m])  # (n, K) jugadas de juego abierto
    S_abierto = rng.binomial(jugadas, C.p)  # (n, K) las que terminan en remate
    sin_remate = jugadas - S_abierto
    fin = np.zeros((n, 3), dtype=np.int64)
    if C.fin_k is not None:
        for k in range(K):
            per = rng.binomial(sin_remate[:, k], C.fin_k[k, 0])
            resto = sin_remate[:, k] - per
            den = 1.0 - C.fin_k[k, 0]
            fue = rng.binomial(resto, C.fin_k[k, 1] / den if den > 1e-12 else 0.0)
            fin += np.stack([per, fue, resto - fue], axis=1)
    saques = rng.poisson(C.saques[t], size=(n, U))  # (n, U) pelotas paradas
    S_parado = rng.binomial(saques, C.q)  # (n, U) las que terminan en remate
    tipos = [(S_abierto[:, k], C.g[k], True) for k in range(K)] + [
        (S_parado[:, u], C.kappa[u], False) for u in range(U)
    ]
    idx_n = np.arange(n)
    for s, media, abierto in tipos:
        tot = int(s.sum())
        if tot == 0:
            continue
        y = _beta(
            rng, min(C.f * media, 1 - 1e-6), conc, tot
        )  # probabilidad de gol de cada remate = f·x
        quien = np.repeat(idx_n, s)
        g = np.bincount(quien, weights=(rng.random(tot) < y), minlength=n)
        goles += g
        if abierto:
            goles_abierto += g
        peligro += np.bincount(quien, weights=y / C.f, minlength=n)
        remates += s
    amenaza = jugadas @ (C.f * C.p * C.g) + saques @ (
        C.q * C.kappa * C.f
    )  # valor esperado de cada jugada y de cada saque, rematen o no (D-093)
    return {
        "goles": goles.astype(np.int64),
        "goles_abierto": goles_abierto.astype(np.int64),
        "remates": remates,
        "peligro": peligro,
        "jugadas": jugadas,
        "fin": fin,
        "saques": saques,
        "amenaza": amenaza,
    }


def minuto(
    Ci: Componentes, Cj: Componentes, t: int, m: np.ndarray, rng, conc: float | None = None
) -> dict:
    """Un minuto de n partidos con el marcador dado (m = estado de i: 0 pierde, 1 empata, 2 gana). Sirve para comprobar que los goles del minuto son Poisson(μ)."""
    conc = config.cargar()["partido"]["jugadas"]["concentracion_peligro"] if conc is None else conc
    m = np.asarray(m, dtype=np.int64)
    a = _lado(Ci, t, m, rng, conc)
    b = _lado(Cj, t, 2 - m, rng, conc)
    out = {}
    for lado, r in (("i", a), ("j", b)):
        out[f"goles_{lado}"], out[f"remates_{lado}"], out[f"peligro_{lado}"] = (
            r["goles"],
            r["remates"],
            r["peligro"],
        )
        (
            out[f"goles_abierto_{lado}"],
            out[f"jugadas_{lado}"],
            out[f"fin_{lado}"],
            out[f"saques_{lado}"],
        ) = r["goles_abierto"], r["jugadas"], r["fin"], r["saques"]
        out[f"amenaza_{lado}"] = r["amenaza"]
    return out


def presion(amenaza: np.ndarray, remates: np.ndarray, peso_sorpresa: float) -> np.ndarray:
    """P = T + s (Y − T): la amenaza esperada de todas las jugadas más una fracción s de la sorpresa de los remates (Y = valor real de los remates). Con s en [0, 1] nunca es negativa."""
    return amenaza + peso_sorpresa * (remates - amenaza)


def ema(d: np.ndarray, vida_media: float, inicio: np.ndarray | float = 0.0) -> np.ndarray:
    """Media móvil exponencial con la vida media dada (minutos) sobre el eje 1 de `d` (n, T), empezando en `inicio` (la expectativa antes del primer minuto, para que no haya rampa)."""
    a = 1.0 - 0.5 ** (1.0 / vida_media)
    out = np.empty_like(d, dtype=float)
    acc = np.broadcast_to(np.asarray(inicio, dtype=float), (d.shape[0],)).copy()
    for t in range(d.shape[1]):
        acc = (1 - a) * acc + a * d[:, t]
        out[:, t] = acc
    return out


def suavizar(d: np.ndarray, vida_media: float) -> np.ndarray:
    """Suavizado exponencial con la vida media dada (en minutos) sobre el eje 1 de `d` (n, T)."""
    a = 1.0 - 0.5 ** (1.0 / vida_media)
    out = np.empty_like(d, dtype=float)
    acc = np.zeros(d.shape[0])
    for t in range(d.shape[1]):
        acc = (1 - a) * acc + a * d[:, t]
        out[:, t] = acc
    return out


def simular_partidos(
    Ci: Componentes,
    Cj: Componentes,
    n: int,
    rng,
    conc: float | None = None,
    vida_media: float | None = None,
) -> dict:
    """n partidos minuto a minuto. Devuelve goles finales, goles y remates por minuto, el peligro por minuto de cada lado y el momentum con signo (i arriba, j abajo), más los totales
    por partido de las jugadas de cada tipo (n, K), cómo terminaron las que no remataron (n, 3: pérdida, fuera, interrupción), los saques de pelota parada por tipo (n, U) y los
    goles de juego abierto."""
    cfg = config.cargar()["partido"]["jugadas"]
    conc = cfg["concentracion_peligro"] if conc is None else conc
    vida_media = cfg["vida_media_momentum"] if vida_media is None else vida_media
    T = Ci.T
    a = np.zeros(n, dtype=np.int64)
    b = np.zeros(n, dtype=np.int64)
    out = {
        k: np.zeros((n, T), dtype=float if k.startswith(("peligro", "amenaza", "mu")) else np.int64)
        for k in (
            "goles_i",
            "goles_j",
            "remates_i",
            "remates_j",
            "peligro_i",
            "peligro_j",
            "amenaza_i",
            "amenaza_j",
            "mu_i",
            "mu_j",
        )
    }
    for lado in ("i", "j"):
        out[f"jugadas_{lado}"] = np.zeros((n, K), dtype=np.int64)
        out[f"fin_{lado}"] = np.zeros((n, 3), dtype=np.int64)
        out[f"saques_{lado}"] = np.zeros((n, U), dtype=np.int64)
        out[f"goles_abierto_{lado}"] = np.zeros(n, dtype=np.int64)
    for t in range(T):
        m = np.where(a < b, 0, np.where(a == b, 1, 2))
        r = minuto(Ci, Cj, t, m, rng, conc)
        for k in (
            "goles_i",
            "goles_j",
            "remates_i",
            "remates_j",
            "peligro_i",
            "peligro_j",
            "amenaza_i",
            "amenaza_j",
        ):
            out[k][:, t] = r[k]
        out["mu_i"][:, t], out["mu_j"][:, t] = (
            Ci.mu[t][m],
            Cj.mu[t][2 - m],
        )  # la μ del motor que le tocó a cada lado en ese minuto (para comprobar la media)
        for lado in ("i", "j"):
            out[f"jugadas_{lado}"] += r[f"jugadas_{lado}"]
            out[f"fin_{lado}"] += r[f"fin_{lado}"]
            out[f"saques_{lado}"] += r[f"saques_{lado}"]
            out[f"goles_abierto_{lado}"] += r[f"goles_abierto_{lado}"]
        a += r["goles_i"]
        b += r["goles_j"]
    out["a"], out["b"] = a, b
    out["momentum"] = suavizar(out["peligro_i"] - out["peligro_j"], vida_media)
    s_, v_ = cfg["peso_sorpresa"], cfg["vida_media_presion"]
    for lado, C in (("i", Ci), ("j", Cj)):
        out[f"presion_{lado}"] = presion(
            out[f"amenaza_{lado}"], Ci.f * out[f"peligro_{lado}"], s_
        )  # Y = Σ y = f · Σ x
        out[f"suave_{lado}"] = ema(
            out[f"presion_{lado}"], v_, C.mu[0][1]
        )  # el partido empieza empatado (m = 1)
    out["dominio"] = (
        out["suave_i"] - out["suave_j"]
    )  # M(t) = EMA[(T_i + s (Y_i − T_i)) − (T_j + s (Y_j − T_j))]: la EMA es lineal, así que es la resta de las dos suavizadas (D-096)
    return out
