"""Números de las siete tarjetas de «¿Le podemos creer?» a partir de `graficas_validacion.json` y `validacion.json` (sin reajustar nada del modelo).

Cada prueba devuelve un dict con sus números y `pasa` (True/False). Los textos viven en `app/textos.py`; aquí solo hay estadística.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

ALFA = 0.05
MAX_GOLES = 5  # los goles de 5 en adelante se agrupan en «5+»
UMBRAL_RECUPERACION = 0.85
TOL_XPTS = 0.005


def _agrupa(v: list, k: int) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return np.append(v[:k], v[k:].sum()) if len(v) > k + 1 else v


def goles(g: dict, n_partidos: int) -> dict:
    """χ² de bondad de ajuste entre la distribución de goles simulada y la real (equipo-partidos = 2 × partidos); agrupa 5+ goles."""
    sim, real = _agrupa(g["simulado"], MAX_GOLES), _agrupa(g["real"], MAX_GOLES)
    etiquetas = list(g["bins"][:MAX_GOLES]) + (
        [f"{MAX_GOLES}+"] if len(g["bins"]) > MAX_GOLES + 1 else list(g["bins"][MAX_GOLES:])
    )
    N = 2 * n_partidos
    E, O = N * sim / sim.sum(), N * real / real.sum()
    chi2 = float(np.sum((O - E) ** 2 / np.maximum(E, 1e-9)))
    gl = len(E) - 1
    p = float(stats.chi2.sf(chi2, gl))
    peor = int(np.argmax((O - E) ** 2 / np.maximum(E, 1e-9)))
    return {
        "chi2": chi2,
        "gl": gl,
        "p": p,
        "n": N,
        "bins": etiquetas,
        "simulado": sim.tolist(),
        "real": real.tolist(),
        "peor_bin": etiquetas[peor],
        "pasa": p >= ALFA,
    }


def puntos(pts: list, error_xpts: float | None) -> dict:
    """Regresión de los puntos reales sobre los predichos por equipo y torneo: la pendiente debe contener al 1 (el error de puntos totales, ≤ 0.5 %, es un filtro de la publicación)."""
    x = np.array([p["predichos"] for p in pts], dtype=float)
    y = np.array([p["reales"] for p in pts], dtype=float)
    r = stats.linregress(x, y)
    t = stats.t.ppf(0.975, len(x) - 2)
    lo, hi = float(r.slope - t * r.stderr), float(r.slope + t * r.stderr)
    pasa = (
        lo <= 1.0 <= hi
    )  # la regla de su fila: que el rango de la pendiente incluya el 1 (el error de puntos totales se muestra)
    return {
        "pendiente": float(r.slope),
        "ic95": [lo, hi],
        "intercepto": float(r.intercept),
        "r2": float(r.rvalue**2),
        "n": int(len(x)),
        "error_xpts": error_xpts,
        "contiene_1": bool(lo <= 1.0 <= hi),
        "pasa": bool(pasa),
    }


def calibracion(calib: dict) -> dict:
    """Prueba tipo Hosmer-Lemeshow por resultado: Σ n (observada − predicha)² / (predicha (1 − predicha)) ~ χ² con tantos grados como bandas.
    Con una sola banda (probabilidad casi constante) es el mismo estadístico con 1 grado de libertad."""
    out = {}
    for k, bandas in calib.items():
        n = np.array([b["n"] for b in bandas], dtype=float)
        p = np.clip(np.array([b["predicha"] for b in bandas]), 1e-6, 1 - 1e-6)
        o = np.array([b["observada"] for b in bandas])
        hl = float(np.sum(n * (o - p) ** 2 / (p * (1 - p))))
        gl = len(bandas)
        out[k] = {"chi2": hl, "gl": gl, "p": float(stats.chi2.sf(hl, gl)), "bandas": len(bandas)}
    pmin = min(v["p"] for v in out.values())
    return {"por_resultado": out, "p_min": pmin, "pasa": pmin >= ALFA}


def independencia(v: dict) -> dict:
    ic, pic = v["autocorrelacion_ic95"], v.get("pendiente_ic95")
    r_ok = ic[0] <= 0 <= ic[1]
    d_ok = True if pic is None else pic[0] <= 0 <= pic[1]
    return {
        "rho": v["autocorrelacion_lag1"],
        "ic95": ic,
        "pendiente": v.get("pendiente_descanso_por_dia"),
        "pendiente_ic95": pic,
        "n_pares": v.get("n_pares"),
        "pasa": bool(r_ok and d_ok),
    }


def placebo(v: dict) -> dict:
    pl = v.get("placebos", [])
    k = sum(1 for p in pl if p.get("contiene_cero"))
    return {
        "k": k,
        "n": len(pl),
        "n_componentes": len(v.get("componentes_tecnico", [])),
        "placebos": pl,
        "pasa": bool(v.get("todos_contienen_cero")) and k == len(pl),
    }


def recuperacion(v: dict) -> dict:
    det = v.get("detalle", [])
    k = sum(1 for d in det if d.get("dentro"))
    return {
        "fraccion": v["fraccion_dentro"],
        "k": k,
        "n": v["n_pares"],
        "umbral": UMBRAL_RECUPERACION,
        "pasa": v["fraccion_dentro"] >= UMBRAL_RECUPERACION,
    }


def retro(r: dict) -> dict:
    mejor = r["mae_simulador"] < r["mae_inercia"]
    p = r.get("dm_p")
    return {
        "n": r["n"],
        "mae": r["mae_simulador"],
        "mae_inercia": r["mae_inercia"],
        "rmse": r.get("rmse_simulador"),
        "rmse_inercia": r.get("rmse_inercia"),
        "dm": r.get("dm_estadistico"),
        "p": p,
        "mejor": bool(mejor),
        "pasa": bool(mejor and p is not None and p < ALFA),
    }


def partido(av: dict) -> dict:
    """χ² de bondad de ajuste del sorteo jugada por jugada contra el cálculo exacto del motor: pasa si p ≥ 0.05 (no se rechaza que el sorteo siga al motor)."""
    return {
        "p": av["p"],
        "chi2": av["chi2"],
        "gl": av["gl"],
        "n": av["n"],
        "frecuencias": av["frecuencias"],
        "exactas": av["exactas"],
        "pasa": bool(av["p"] >= ALFA),
    }


def todas(graficas: dict, validacion: dict | None) -> list[dict]:
    """Las siete pruebas, en orden. Las que dependen de `validacion.json` se omiten si no hay."""
    v = validacion or {}
    cartas = []
    cartas.append({"id": "goles", **goles(graficas["goles"], graficas["n_partidos"])})
    cartas.append(
        {
            "id": "puntos",
            **puntos(graficas["puntos"], (v.get("calibracion") or {}).get("error_xpts")),
        }
    )
    cartas.append({"id": "calibracion", **calibracion(graficas["calibracion"])})
    if v.get("independencia"):
        cartas.append({"id": "independencia", **independencia(v["independencia"])})
    if v.get("placebo"):
        cartas.append({"id": "placebo", **placebo(v["placebo"])})
    if v.get("recuperacion"):
        cartas.append({"id": "recuperacion", **recuperacion(v["recuperacion"])})
    r = graficas.get("retroprueba") or v.get("retroprueba")
    if r and r.get("mae_simulador") is not None:
        if v.get("retroprueba"):  # el DM y los RMSE vienen completos en validacion.json
            r = {**v["retroprueba"], **r}
        cartas.append({"id": "retro", **retro(r)})
    return cartas
