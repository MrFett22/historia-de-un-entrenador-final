"""Perillas en lenguaje común ↔ θ del técnico (04_ESPECIFICACION §6).

Las perillas describen al técnico con un plantel PROMEDIO de la liga (φ = 0, ε = 0): la mezcla
que se muestra es softmax(b_liga·x0 + b0 + θ) en x0 = (1, 0, 0, 0, 1, 0) (empate, local, sin
tramo final, ΔElo = 0). En el América se suma el plantel: ζ = b0 + φ_Am + θ + ε.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from .. import config
from ..tipos import BLOQUES, COMPONENTES, K, NO_REF, Q, REF, Liga

ETIQUETAS_REACCION = ("Nunca", "Poco", "Como la mayoría", "Bastante", "Mucho")
ETIQUETAS_CAMBIO = ("Cuidar el resultado", "Mismo puesto", "Buscar el gol")


NIVEL_PLAUSIBLE = (
    0.90  # técnicos plausibles: el 90 % central de θ ~ N(0, σ_θ), con σ_θ de su posterior
)


def rango_plausible(
    sigma_theta_muestras: np.ndarray, nivel: float = NIVEL_PLAUSIBLE, semilla: int = 20261008
):
    """(lo, hi) por componente: percentiles de θ de un técnico plausible = σ_θ·z con σ_θ de la posterior (M, Q) y z ~ N(0, 1)."""
    z = np.random.default_rng([semilla, 51]).normal(size=sigma_theta_muestras.shape)
    th = sigma_theta_muestras * z
    a = (1 - nivel) / 2
    return np.quantile(th, a, axis=0), np.quantile(th, 1 - a, axis=0)


@dataclass
class Escalas:
    """Lo que el mapeo necesita de la fase A (medianas posteriores).

    atribucion = "binaria" (artefactos anteriores a D-051): solo las componentes que la regla del 0.05 asigna al técnico se mueven con las perillas.
    atribucion = "continua" (D-051): todas se mueven; el rango de cada perilla se acota al de los técnicos plausibles (`theta_lo`, `theta_hi`).
    """

    b0: np.ndarray  # (Q,) intercepto de la etapa 2 (ficha de un equipo promedio)
    sigma_theta: np.ndarray  # (Q,) dispersión entre técnicos
    decisiones: dict  # componente -> 'tecnico' | 'plantel' | 'liga'
    atribucion: str = "binaria"
    theta_lo: np.ndarray | None = None
    theta_hi: np.ndarray | None = None

    @property
    def continua(self) -> bool:
        return self.atribucion == "continua"

    def activa(self, bloque: str) -> bool:
        if self.continua:
            return True
        return any(self.decisiones[COMPONENTES[q]] == "tecnico" for q in BLOQUES[bloque])

    def incierta(self, bloque: str) -> bool:
        """Con atribución continua: la regla del 0.05 dice que el efecto del técnico es poco distinguible en todo el bloque (solo describe)."""
        return self.continua and not any(
            self.decisiones[COMPONENTES[q]] == "tecnico" for q in BLOQUES[bloque]
        )

    def tau(self, q: int) -> float:
        if self.continua:
            return float(self.sigma_theta[q])
        return float(self.sigma_theta[q]) if self.decisiones[COMPONENTES[q]] == "tecnico" else 0.0

    def limitar(self, th: np.ndarray, indices) -> np.ndarray:
        """Acota θ en `indices` al de los técnicos plausibles (solo con atribución continua)."""
        if self.continua and self.theta_lo is not None:
            idx = np.asarray(indices, dtype=int)
            th[idx] = np.clip(th[idx], self.theta_lo[idx], self.theta_hi[idx])
        return th


def _x0() -> np.ndarray:
    return np.asarray(config.cargar()["perillas"]["x0"], dtype=float)


def softmax_inversa(pi: np.ndarray) -> np.ndarray:
    """logits relativos a la referencia para k ≠ ref."""
    pi = np.clip(np.asarray(pi, dtype=float), 1e-12, 1.0)
    return np.array([np.log(pi[k] / pi[REF]) for k in NO_REF])


def _softmax_libres(eta_libres: np.ndarray) -> np.ndarray:
    eta = np.zeros(K)
    eta[list(NO_REF)] = eta_libres
    e = np.exp(eta - eta.max())
    return e / e.sum()


def mezcla_desde_theta(
    theta: np.ndarray, liga: Liga, esc: Escalas, bloque: str = "int_at"
) -> np.ndarray:
    base = liga.b_liga[list(NO_REF)] @ _x0()
    eta = base + esc.b0[BLOQUES[bloque]] + theta[BLOQUES[bloque]]
    if bloque == "int_co":  # el rival promedio también trae su propio intercepto de ataque
        eta = eta + esc.b0[BLOQUES["int_at"]]
    return _softmax_libres(eta)


def theta_desde_mezcla(
    pi: np.ndarray, liga: Liga, esc: Escalas, bloque: str = "int_at"
) -> np.ndarray:
    base = liga.b_liga[list(NO_REF)] @ _x0()
    th = softmax_inversa(pi) - base - esc.b0[BLOQUES[bloque]]
    if bloque == "int_co":
        th = th - esc.b0[BLOQUES["int_at"]]
    return th


def _s_de_etiqueta(et: str) -> float:
    return float(config.cargar()["perillas"]["reactividad"][et])


def perillas_a_tecnico(
    perillas: dict, liga: Liga, esc: Escalas, base: np.ndarray | None = None
) -> np.ndarray:
    """dict de perillas → θ (Q,). Las componentes sin perilla quedan en `base` (0 = liga). Con atribución continua, las componentes que una
    perilla mueve se acotan al rango de los técnicos plausibles: una perilla no promete más de lo que los datos sostienen."""
    th = np.zeros(Q) if base is None else np.array(base, dtype=float)
    tocadas: list[int] = []
    if "mezcla" in perillas:
        pd_, pe = perillas["mezcla"]
        th[BLOQUES["int_at"]] = theta_desde_mezcla(
            np.array([pd_, 1 - pd_ - pe, pe]), liga, esc, "int_at"
        )
        tocadas += list(BLOQUES["int_at"])
    if "rival" in perillas:
        pd_, pe = perillas["rival"]
        th[BLOQUES["int_co"]] = theta_desde_mezcla(
            np.array([pd_, 1 - pd_ - pe, pe]), liga, esc, "int_co"
        )
        tocadas += list(BLOQUES["int_co"])
    for clave, bloque in (("reaccion_marcador", "s_marcador"), ("reaccion_rival", "s_rival")):
        if clave in perillas:
            q = BLOQUES[bloque][0]
            th[q] = _s_de_etiqueta(perillas[clave]) - 1.0 - esc.b0[q]
            tocadas.append(q)
    if "balon_parado" in perillas:  # 1 = de las peores, 99 = de las mejores
        p = np.clip(perillas["balon_parado"], 1, 99) / 100.0
        for q in BLOQUES["nu_co"]:
            th[q] = esc.tau(q) * norm.ppf(1 - p)
            tocadas.append(q)
    if "cambios_momento" in perillas:  # 0 = temprano, 100 = tarde
        p = np.clip(perillas["cambios_momento"], 1, 99) / 100.0
        q = BLOQUES["alpha"][0]
        th[q] = esc.tau(q) * norm.ppf(1 - p)
        tocadas.append(q)
    if "cambios_tipo" in perillas:
        pc = config.cargar()["perillas"]["tipo_cambio_percentil"][perillas["cambios_tipo"]] / 100.0
        q = BLOQUES["gamma"][0]
        th[q] = esc.tau(q) * norm.ppf(pc)
        tocadas.append(q)
    return esc.limitar(th, tocadas) if tocadas else th


def _cercana(valor: float, opciones: dict) -> str:
    return min(opciones, key=lambda k: abs(opciones[k] - valor))


def tecnico_a_perillas(theta: np.ndarray, liga: Liga, esc: Escalas) -> dict:
    """θ (Q,) → perillas para mostrar (presets y θ estimado)."""
    th = np.asarray(theta, dtype=float)
    cfg = config.cargar()["perillas"]
    pi = mezcla_desde_theta(th, liga, esc, "int_at")
    pr = mezcla_desde_theta(th, liga, esc, "int_co")
    qm, qr = BLOQUES["s_marcador"][0], BLOQUES["s_rival"][0]
    out = {
        "mezcla": (float(pi[0]), float(pi[2])),
        "rival": (float(pr[0]), float(pr[2])),
        "reaccion_marcador": _cercana(1 + esc.b0[qm] + th[qm], cfg["reactividad"]),
        "reaccion_rival": _cercana(1 + esc.b0[qr] + th[qr], cfg["reactividad"]),
    }
    vals = [norm.cdf(-th[q] / esc.tau(q)) for q in BLOQUES["nu_co"] if esc.tau(q) > 0]
    out["balon_parado"] = int(np.clip(round(100 * np.mean(vals)), 1, 99)) if vals else 50
    qa = BLOQUES["alpha"][0]
    out["cambios_momento"] = (
        int(np.clip(round(100 * norm.cdf(-th[qa] / esc.tau(qa))), 1, 99)) if esc.tau(qa) > 0 else 50
    )
    qg = BLOQUES["gamma"][0]
    if esc.tau(qg) > 0:
        p = 100 * norm.cdf(th[qg] / esc.tau(qg))
        out["cambios_tipo"] = _cercana(p, cfg["tipo_cambio_percentil"])
    else:
        out["cambios_tipo"] = "Mismo puesto"
    return out


def perillas_inciertas(esc: Escalas) -> dict:
    """Perillas cuyo efecto del técnico es poco distinguible según la regla descriptiva del 0.05 (se muestran con aviso, pero se pueden usar)."""
    return {
        "mezcla": esc.incierta("int_at"),
        "rival": esc.incierta("int_co"),
        "reaccion_marcador": esc.incierta("s_marcador"),
        "reaccion_rival": esc.incierta("s_rival"),
        "balon_parado": esc.incierta("nu_co"),
        "cambios_momento": esc.incierta("alpha"),
        "cambios_tipo": esc.incierta("gamma"),
    }


def _mezcla_en_caja(
    lo: np.ndarray, hi: np.ndarray, liga: Liga, esc: Escalas, bloque: str
) -> np.ndarray:
    """Mezclas (directa, circulación, elaborada) en las 4 esquinas de la caja de θ plausibles del bloque (π es monótona en cada coordenada)."""
    q0 = BLOQUES[bloque]
    out = []
    for a in (lo[q0[0]], hi[q0[0]]):
        for b in (lo[q0[1]], hi[q0[1]]):
            th = np.zeros(Q)
            th[q0[0]], th[q0[1]] = a, b
            out.append(mezcla_desde_theta(th, liga, esc, bloque))
    return np.array(out)


def rangos_perillas(esc: Escalas, liga: Liga) -> dict:
    """Rango de cada deslizador en las unidades de la app. Con atribución binaria: los fijos de siempre.
    Con atribución continua: el que cubre a los técnicos plausibles (percentiles 5 y 95 de θ ~ N(0, σ_θ), con la posterior de σ_θ)."""
    fijos = {
        "mezcla": {"directa": (5, 85), "elaborada": (5, 85)},
        "rival": {"directa": (5, 85), "elaborada": (5, 85)},
        "balon_parado": (1, 99),
        "cambios_momento": (0, 100),
    }
    if not (esc.continua and esc.theta_lo is not None):
        return fijos
    out = {}
    for clave, bloque in (("mezcla", "int_at"), ("rival", "int_co")):
        pi = _mezcla_en_caja(esc.theta_lo, esc.theta_hi, liga, esc, bloque)
        d, e = 100 * pi[:, 0], 100 * pi[:, 2]
        # la mezcla de la liga siempre es alcanzable (θ = 0 está dentro de la caja); se deja al menos 1 punto de ancho y 10 % para el resto
        out[clave] = {
            "directa": (
                int(np.clip(np.floor(d.min()), 5, 85)),
                int(np.clip(np.ceil(d.max()), 5, 85)),
            ),
            "elaborada": (
                int(np.clip(np.floor(e.min()), 5, 85)),
                int(np.clip(np.ceil(e.max()), 5, 85)),
            ),
        }
    for clave, bloque in (("balon_parado", "nu_co"), ("cambios_momento", "alpha")):
        qs = [q for q in BLOQUES[bloque] if esc.tau(q) > 0]
        # percentil de la perilla en el extremo de la caja: p = 100·Φ(−θ/τ); mejores = θ más negativo
        lo = np.mean([100 * norm.cdf(-esc.theta_hi[q] / esc.tau(q)) for q in qs]) if qs else 1
        hi = np.mean([100 * norm.cdf(-esc.theta_lo[q] / esc.tau(q)) for q in qs]) if qs else 99
        out[clave] = (int(np.clip(np.floor(lo), 1, 49)), int(np.clip(np.ceil(hi), 51, 99)))
    return out


def perillas_activas(esc: Escalas) -> dict:
    """Qué perillas mueven algo: con atribución binaria, según la regla del 0.05 (las demás se muestran en gris); con la continua, todas."""
    return {
        "mezcla": esc.activa("int_at"),
        "rival": esc.activa("int_co"),
        "reaccion_marcador": esc.activa("s_marcador"),
        "reaccion_rival": esc.activa("s_rival"),
        "balon_parado": esc.activa("nu_co"),
        "cambios_momento": esc.activa("alpha"),
        "cambios_tipo": esc.activa("gamma"),
    }
