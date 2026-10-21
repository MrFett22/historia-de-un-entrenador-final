"""Placebo: se barajan las etiquetas de técnico entre las celdas (se rompe el vínculo técnico ↔
celda) y se reajusta la etapa 2 de las componentes del técnico. Un técnico placebo así estimado,
comparado con el técnico promedio en el América, debe dar un intervalo de Δ que contenga el 0."""

from __future__ import annotations

import numpy as np

from ..estimacion import cruzado
from ..tipos import COMPONENTES, Q, Tecnico


def correr(
    res,
    sim,
    n_placebos: int = 3,
    semilla: int = 20261008,
    modo: str = "rapido",
    mcmc: dict | None = None,
    verbose: bool = False,
) -> dict:
    rng = np.random.default_rng([semilla, 77])
    cel = res.celdas.copy()
    cel["tecnico"] = rng.permutation(cel.tecnico.to_numpy())
    # con atribución continua (D-051) todas las componentes llevan θ; con la binaria, solo las que la regla asigna al técnico
    tecnicas = [n for n in COMPONENTES if sim.p.escalas.continua or res.decisiones[n] == "tecnico"]
    post, ix = cruzado.ajustar_todas(
        cel,
        res.yv,
        semilla + 5,
        n_temp=res.ix.n_temp,
        verbose=verbose,
        componentes=tecnicas,
        mcmc=mcmc,
    )
    n_cel = cel.groupby("tecnico").size().sort_values(ascending=False)
    M = sim.p.piezas.fichas.shape[0]
    prom = sim.tecnico_promedio()
    filas = []
    for nombre in n_cel.index[:n_placebos]:
        th = np.zeros((M, Q))
        for n in tecnicas:
            p = post[n]
            d = rng.integers(0, p.theta.shape[0], M)
            th[:, COMPONENTES.index(n)] = p.theta[d, ix.tecnicos.index(nombre)]
        t = Tecnico(f"placebo ({nombre})", th, observado=False)
        c, _, _ = sim.comparar(t, prom, modo)
        filas.append(
            {
                "placebo": nombre,
                "celdas": int(n_cel[nombre]),
                "media": c.resumen["media"],
                "int95": c.resumen["int95"],
                "contiene_cero": bool(c.resumen["int95"][0] <= 0 <= c.resumen["int95"][1]),
                "veredicto": c.veredicto,
            }
        )
    return {
        "componentes_tecnico": tecnicas,
        "placebos": filas,
        "todos_contienen_cero": bool(all(f["contiene_cero"] for f in filas)) if filas else None,
    }
