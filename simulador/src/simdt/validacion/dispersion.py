"""Diagnóstico de dispersión (D-066): ¿el simulador aplana las diferencias entre equipos?

Hecho que lo motiva: en E la pendiente de los puntos reales contra los predichos sale 1.30–1.71 y la calibración de ganar/empatar/perder da p < 0.001: el simulador
ACORTA las diferencias entre equipos. Aquí se mide directo, sin pasar por el simulador, cuánto de la variación de los puntos reales es fuerza de los equipos y cuánto
es suerte, y se compara con la dispersión de los puntos esperados del modelo.

Entrada: una fila por equipo y torneo (fase regular) con
    torneo, equipo, reales (puntos reales), predichos (puntos esperados del modelo), var_azar (varianza de los puntos de ese equipo en ese torneo según el motor)
`var_azar` sale de las probabilidades de cada partido: para un partido con P(gana) = g, P(empata) = e, la varianza de los puntos del equipo es 9g + e − (3g + e)²,
y las de sus partidos se suman (los partidos son independientes dado el modelo).

  Var_real  = varianza entre equipos de los puntos reales, dentro de cada torneo, promediada entre torneos
  Var_azar  = varianza media de los puntos de un equipo en un torneo según el motor
  SD_fuerza_real   = √max(Var_real − Var_azar, 0)                       (puntos por torneo)
  SD_fuerza_modelo = √(varianza entre equipos de los puntos esperados del modelo, promediada entre torneos)
  r = SD_fuerza_real / SD_fuerza_modelo                                   H0: r = 1 (el modelo tiene la dispersión correcta) contra H1: r > 1 (el modelo aplana)
  azar_sobre_real = Var_azar / Var_real                                   qué parte de la variación de los puntos reales es suerte

Intervalos del 95 % por bootstrap ESTRATIFICADO por torneo: en cada réplica se remuestrean los equipos dentro de cada torneo (los torneos quedan fijos). p de H0 = proporción
de réplicas con r* ≤ 1. Solo agregados: nada por partido ni por equipo sale de aquí.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

B_POR_OMISION = 2000


def var_puntos_partido(p_gana, p_empata) -> np.ndarray:
    """Varianza de los puntos (3, 1, 0) de un equipo en UN partido con esas probabilidades."""
    g, e = np.asarray(p_gana, float), np.asarray(p_empata, float)
    return 9 * g + e - (3 * g + e) ** 2


def _estadisticos(grupos: list[tuple[np.ndarray, np.ndarray, np.ndarray]]) -> dict:
    """grupos: por torneo, (reales, predichos, var_azar) de sus equipos."""
    vr = np.mean([np.var(r, ddof=1) for r, _, _ in grupos if len(r) > 1])
    vm = np.mean([np.var(p, ddof=1) for _, p, _ in grupos if len(p) > 1])
    va = np.mean(np.concatenate([a for _, _, a in grupos]))
    sd_real = float(np.sqrt(max(vr - va, 0.0)))
    sd_modelo = float(np.sqrt(vm))
    return {
        "var_real": float(vr),
        "var_azar": float(va),
        "sd_fuerza_real": sd_real,
        "sd_fuerza_modelo": sd_modelo,
        "r": sd_real / sd_modelo if sd_modelo > 1e-12 else float("nan"),
        "azar_sobre_real": float(va / vr) if vr > 1e-12 else float("nan"),
    }


def _ic(x: np.ndarray) -> list[float]:
    x = x[np.isfinite(x)]
    return (
        [float(v) for v in np.quantile(x, [0.025, 0.975])]
        if len(x)
        else [float("nan"), float("nan")]
    )


def dispersion(
    df: pd.DataFrame,
    n_boot: int = B_POR_OMISION,
    semilla: int = 20261020,
    pendiente_ic95: list | None = None,
) -> dict:
    """Los cinco números del diagnóstico con su IC 95 % y la prueba de H0: r = 1. `pendiente_ic95` (el IC de la pendiente de la tarjeta de puntos) solo sirve para
    decir si r es consistente con ella."""
    grupos = [
        (g.reales.to_numpy(float), g.predichos.to_numpy(float), g.var_azar.to_numpy(float))
        for _, g in df.groupby("torneo")
    ]
    est = _estadisticos(grupos)
    rng = np.random.default_rng(semilla)
    boot = {
        k: np.empty(n_boot)
        for k in (
            "var_real",
            "var_azar",
            "sd_fuerza_real",
            "sd_fuerza_modelo",
            "r",
            "azar_sobre_real",
        )
    }
    for b in range(n_boot):
        gs = []
        for r, p, a in grupos:
            i = rng.integers(0, len(r), len(r))
            gs.append((r[i], p[i], a[i]))
        e = _estadisticos(gs)
        for k in boot:
            boot[k][b] = e[k]
    out = {k: {"valor": est[k], "ic95": _ic(boot[k])} for k in boot}
    rb = boot["r"][np.isfinite(boot["r"])]
    out["r"]["p_h0"] = (
        float((rb <= 1.0).mean()) if len(rb) else float("nan")
    )  # H0: r = 1 contra H1: r > 1
    out["r"]["rechaza_h0"] = bool(out["r"]["p_h0"] < 0.05 and est["r"] > 1)
    out["piso_en_cero"] = bool(
        est["var_real"] < est["var_azar"]
    )  # la fuerza medida cae por debajo de la suerte: SD = 0 y se reporta
    out["n_torneos"] = int(len(grupos))
    out["n_equipo_torneo"] = int(len(df))
    out["n_boot"] = int(n_boot)
    out["metodo"] = (
        "bootstrap estratificado por torneo (equipos remuestreados dentro de cada torneo); Var_azar de las probabilidades de cada partido del motor; "
        "p de H0 = proporción de réplicas con r ≤ 1"
    )
    if pendiente_ic95 is not None:
        lo, hi = out["r"]["ic95"]
        out["consistente_con_pendiente"] = bool(
            lo <= pendiente_ic95[1] and hi >= pendiente_ic95[0]
        )  # los dos rangos se traslapan
        out["pendiente_ic95"] = [float(pendiente_ic95[0]), float(pendiente_ic95[1])]
    return out


def tabla_de_puntos(
    partidos: pd.DataFrame, p_gana, p_empata, xpts_local, xpts_visita, regular=None
) -> pd.DataFrame:
    """De una tabla de partidos con sus probabilidades del motor (punto de vista del local) a una fila por equipo y torneo.
    `partidos` trae: local, visitante, torneo, goles_local, goles_visitante."""
    g, e = np.asarray(p_gana, float), np.asarray(p_empata, float)
    gl, gv = partidos.goles_local.to_numpy(), partidos.goles_visitante.to_numpy()
    pl = np.where(gl > gv, 3, np.where(gl == gv, 1, 0))
    pv = np.where(gv > gl, 3, np.where(gl == gv, 1, 0))
    v_local = var_puntos_partido(g, e)
    v_visita = var_puntos_partido(
        1 - g - e, e
    )  # el visitante gana con la probabilidad de que el local pierda
    reg = np.ones(len(partidos), bool) if regular is None else np.asarray(regular, bool)
    a = pd.DataFrame(
        {
            "equipo": partidos.local,
            "torneo": partidos.torneo,
            "pred": xpts_local,
            "real": pl,
            "var": v_local,
        }
    )[reg]
    b = pd.DataFrame(
        {
            "equipo": partidos.visitante,
            "torneo": partidos.torneo,
            "pred": xpts_visita,
            "real": pv,
            "var": v_visita,
        }
    )[reg]
    x = (
        pd.concat([a, b])
        .groupby(["equipo", "torneo"])
        .agg(
            partidos=("pred", "size"),
            predichos=("pred", "sum"),
            reales=("real", "sum"),
            var_azar=("var", "sum"),
        )
        .reset_index()
    )
    return x
