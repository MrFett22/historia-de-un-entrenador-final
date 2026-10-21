"""Fase A completa: liga → celdas (etapa 1) → efectos cruzados (etapa 2) → decisiones."""

from __future__ import annotations

import pickle
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import config
from ..tipos import COMPONENTES, Liga
from . import cruzado
from .celdas import estimar_celdas
from .liga import estimar_liga


# La regla del 0.05 ya no decide qué mueve el técnico (D-051): solo etiqueta
ETIQUETAS = {
    "tecnico": "efecto del técnico distinguible",
    "plantel": "efecto del técnico poco distinguible",
    "liga": "sin estimar (queda en la liga)",
}


@dataclass
class ResultadoFaseA:
    liga: Liga
    diag_liga: dict
    celdas: pd.DataFrame
    yv: pd.DataFrame
    posteriores: dict  # componente -> cruzado.Posterior
    ix: cruzado.Indices
    decisiones: dict  # componente -> 'tecnico' | 'plantel' | 'liga'

    def tabla(self) -> pd.DataFrame:
        filas = []
        for n in COMPONENTES:
            p = self.posteriores[n]
            f = p.f_theta
            filas.append(
                {
                    "componente": n,
                    "b0": float(np.median(p.b0)),
                    "f_theta_mediana": float(np.median(f)),
                    "f_theta_p2.5": float(np.quantile(f, 0.025)),
                    "f_theta_p97.5": float(np.quantile(f, 0.975)),
                    "sigma_theta": float(np.median(p.sigma[:, 0])),
                    "sigma_phi": float(np.median(p.sigma[:, 1])),
                    "sigma_int": float(np.median(p.sigma[:, 2])),
                    "sigma_int_p97.5": float(np.quantile(p.sigma[:, 2], 0.975)),
                    "sigma_delta": float(np.median(p.sigma[:, 3])),
                    "rhat_max": p.diag.get("rhat_max"),
                    "ess_min": p.diag.get("ess_min"),
                    "metodo": p.diag.get("metodo"),
                    "decision": self.decisiones[n],
                    "etiqueta": ETIQUETAS.get(self.decisiones[n], ""),
                }
            )
        return pd.DataFrame(filas)


def correr(
    tablas: dict,
    semilla: int | None = None,
    P_cadenas=None,
    mu_cadenas=None,
    n_temp: int | None = None,
    verbose: bool = True,
    cache: str | None = None,
    mcmc: dict | None = None,
    P0_cadenas=None,
) -> ResultadoFaseA:
    semilla = config.cargar()["semilla"] if semilla is None else semilla
    if cache:
        ruta = config.cache_dir() / cache
        if ruta.exists():
            with open(ruta, "rb") as f:
                return pickle.load(f)
    liga, diag = estimar_liga(
        tablas, P_cadenas=P_cadenas, mu_cadenas=mu_cadenas, P0_cadenas=P0_cadenas
    )
    if verbose:
        print("  liga estimada; etapa 1 (celdas)...", flush=True)
    celdas, yv = estimar_celdas(tablas, liga)
    if verbose:
        print(f"  {len(celdas)} celdas; etapa 2 (efectos cruzados)...", flush=True)
    post, ix = cruzado.ajustar_todas(celdas, yv, semilla, n_temp=n_temp, verbose=verbose, mcmc=mcmc)
    dec = {n: cruzado.decision(p) for n, p in post.items()}
    res = ResultadoFaseA(liga, diag, celdas, yv, post, ix, dec)
    if cache:
        with open(config.cache_dir() / cache, "wb") as f:
            pickle.dump(res, f)
    return res


def escribir_reporte(res: ResultadoFaseA, ruta, titulo: str, extra: str = "") -> None:
    tab = res.tabla()
    lineas = [
        f"# {titulo}",
        "",
        f"Celdas técnico × club × temporada (≥ 8 partidos): {len(res.celdas)} · técnicos: "
        f"{len(res.ix.tecnicos)} · clubes: {len(res.ix.clubes)} · temporadas: {res.ix.n_temp}",
        "",
        "Regla pre-registrada: f_θ = σ_θ² / (σ_θ² + σ_φ² + σ_int²); si su percentil 2.5 < 0.05 → plantel. "
        'Desde D-051 solo etiqueta ("efecto del técnico poco distinguible"): las fichas usan la posterior completa de θ.',
        "",
        "| componente | f_θ mediana | f_θ IC 95 % | σ_θ | σ_φ | σ_int (p97.5) | σ_Δ | R̂ máx | ESS mín | método | decisión |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in tab.iterrows():
        lineas.append(
            f"| {r['componente']} | {r['f_theta_mediana']:.2f} | [{r['f_theta_p2.5']:.3f}, {r['f_theta_p97.5']:.2f}] | "
            f"{r['sigma_theta']:.3f} | {r['sigma_phi']:.3f} | {r['sigma_int']:.3f} ({r['sigma_int_p97.5']:.3f}) | "
            f"{r['sigma_delta']:.3f} | {(r['rhat_max'] or float('nan')):.4f} | {(r['ess_min'] or float('nan')):.0f} | "
            f"{r['metodo']} | {r['decision']} |"
        )
    n_tec = int((tab.decision == "tecnico").sum())
    lineas += [
        "",
        f"Componentes del técnico: {n_tec} de {len(tab)}; del plantel: {int((tab.decision == 'plantel').sum())}; "
        f"en la liga: {int((tab.decision == 'liga').sum())}.",
        "",
        extra,
    ]
    from pathlib import Path

    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    Path(ruta).write_text("\n".join(lineas), encoding="utf-8")
