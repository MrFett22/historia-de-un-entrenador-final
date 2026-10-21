"""Fichas ζ de los equipos vigentes y piezas para cambiar al técnico del América.

ζ_equipo = b0 + φ[club, temp_obj] + θ[técnico] + ε[técnico, club]       (por muestra posterior)
- Técnico no observado: θ ~ N(0, σ_θ); par no observado: ε ~ N(0, σ_int) (misma z por muestra).
- Club sin celdas: φ ~ N(0, σ_φ). Temporada objetivo después de la última: caminata aleatoria.
Para el América con otro técnico T*:
  atribución CONTINUA (D-051, por omisión): TODAS las componentes son base_Am + θ_T* + ε_T*,Am (base_Am = b0 + φ_Am = "plantel"),
      con la posterior completa de θ y su encogimiento jerárquico; f_θ y la regla del 0.05 solo describen ("efecto del técnico poco distinguible").
  atribución BINARIA (artefactos anteriores a D-051):
      componentes del TÉCNICO : base_Am + θ_T* + ε_T*,Am
      componentes del PLANTEL : ζ_Am actual (el técnico no las mueve; regla de atribución pre-registrada)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..tipos import COMPONENTES, Q
from .fase_a import ResultadoFaseA


@dataclass
class PiezasFichas:
    equipos: list
    fichas: np.ndarray  # (M, 18, Q) con los técnicos vigentes
    base_foco: np.ndarray  # (M, Q) b0 + φ_Am (plantel del foco)
    theta_tec: dict  # técnico observado -> (M, Q)
    eps_foco: dict  # técnico observado con el foco -> (M, Q)
    sigma: np.ndarray  # (M, Q, 4) σ_θ, σ_φ, σ_int, σ_Δ
    z_eps: np.ndarray  # (M, Q) normales fijas para ε de un técnico nuevo en el foco
    decisiones: dict
    foco: int
    tecnico_actual_foco: str
    atribucion: str = (
        "binaria"  # "continua" (D-051) | "binaria" (regla del 0.05 decide qué mueve el técnico)
    )


def _phi(p, ix, club, temp_obj, idx, z):
    if club not in ix.clubes:
        return p.sigma[idx, 1] * z
    c = ix.clubes.index(club)
    if temp_obj < ix.n_temp:
        return p.phi[idx, c, temp_obj]
    pasos = temp_obj - ix.n_temp + 1
    return p.phi[idx, c, -1] + p.sigma[idx, 3] * np.sqrt(pasos) * z


def armar(
    res: ResultadoFaseA,
    equipos: list,
    tecnicos_vigentes: dict,
    temp_obj: int,
    foco: str,
    M: int = 1000,
    semilla: int = 0,
    tecnicos_guardar: list | None = None,
    atribucion: str = "binaria",
) -> PiezasFichas:
    rng = np.random.default_rng([semilla, 202])
    ix = res.ix
    D = len(next(iter(res.posteriores.values())).b0)
    idx = rng.choice(D, M, replace=M > D)
    zs = rng.normal(size=(5, M, len(equipos), Q))  # φ nuevo, θ nuevo, ε nuevo, z_eps foco
    fichas = np.zeros((M, len(equipos), Q))
    sigma = np.zeros((M, Q, 4))
    base_foco = np.zeros((M, Q))
    guardar = set(tecnicos_guardar or []) | set(tecnicos_vigentes.values())
    theta_tec = {t: np.zeros((M, Q)) for t in guardar if t in ix.tecnicos}
    eps_foco = {}
    for q, nombre in enumerate(COMPONENTES):
        p = res.posteriores[nombre]
        sigma[:, q] = p.sigma[idx]
        for e, club in enumerate(equipos):
            tec = tecnicos_vigentes.get(club)
            phi = _phi(p, ix, club, temp_obj, idx, zs[0, :, e, q])
            th = (
                p.theta[idx, ix.tecnicos.index(tec)]
                if tec in ix.tecnicos
                else p.sigma[idx, 0] * zs[1, :, e, q]
            )
            par = (tec, club)
            ep = (
                p.eps[idx, ix.pares.index(par)]
                if par in ix.pares
                else p.sigma[idx, 2] * zs[2, :, e, q]
            )
            fichas[:, e, q] = p.b0[idx] + phi + th + ep
            if club == foco:
                base_foco[:, q] = p.b0[idx] + phi
        for t in theta_tec:
            theta_tec[t][:, q] = p.theta[idx, ix.tecnicos.index(t)]
            if (t, foco) in ix.pares:
                eps_foco.setdefault(t, np.zeros((M, Q)))[:, q] = p.eps[
                    idx, ix.pares.index((t, foco))
                ]
    f = equipos.index(foco)
    return PiezasFichas(
        equipos,
        fichas,
        base_foco,
        theta_tec,
        eps_foco,
        sigma,
        zs[3, :, f, :],
        dict(res.decisiones),
        f,
        tecnicos_vigentes.get(foco),
        atribucion,
    )


def ficha_foco(
    piezas: PiezasFichas,
    theta: np.ndarray,
    idx_muestras: np.ndarray,
    tecnico_observado: str | None = None,
) -> np.ndarray:
    """(R, Q) ficha del América con un técnico dado por θ (vector (Q,) o muestras (M, Q))."""
    th = np.asarray(theta, dtype=float)
    th = th[idx_muestras] if th.ndim == 2 else np.broadcast_to(th, (len(idx_muestras), Q))
    if tecnico_observado is not None and tecnico_observado in piezas.eps_foco:
        eps = piezas.eps_foco[tecnico_observado][idx_muestras]
    else:
        eps = piezas.sigma[idx_muestras, :, 2] * piezas.z_eps[idx_muestras]
    nueva = piezas.base_foco[idx_muestras] + th + eps
    if piezas.atribucion == "continua":
        return nueva
    actual = piezas.fichas[idx_muestras, piezas.foco]
    tecnico = np.array([piezas.decisiones[n] == "tecnico" for n in COMPONENTES])
    return np.where(tecnico[None], nueva, actual)
