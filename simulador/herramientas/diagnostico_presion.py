"""Fase D de la v10 (D-093): por qué el momentum se veía plano y qué tan llena queda la gráfica con la presión de cada equipo.

Sortea n partidos (1,000 por defecto: el técnico vigente en casa contra el rival de fuerza mediana, con la misma muestra de la fase A de la app) y mide:
  · v8: el peligro de los remates sin suavizar, con el eje ajustado al mayor pico del partido (cómo se veía) y con el percentil 95;
  · cuánto se cancela al restar los dos equipos (la v7);
  · v10: la presión suavizada de cada equipo por separado (P = T + s (Y − T), EMA) con el eje en el percentil 95: % de minutos con barras visibles (≥ 3 % del eje), cuántas barras pasan del
    marco y si la media de la presión coincide con la media de μ.
Uso:  SIMDT_ARTEFACTOS=<carpeta> python herramientas/diagnostico_presion.py [--n 1000] [--salida diagnostico_presion.json]"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from simdt import analisis as A  # noqa: E402
from simdt import config  # noqa: E402
from simdt.motor import jugadas as J  # noqa: E402
from simdt.servicio import Simulador  # noqa: E402


def _rival_mediano(sim) -> int:
    rivales = [e for e in range(len(sim.elo)) if e != sim.foco]
    return rivales[int(np.argsort(sim.elo[rivales])[len(rivales) // 2])]


def diagnostico(sim, n: int = 1000, semilla: int = 20261020, muestra: int = 5) -> dict:
    cfg = config.cargar()["partido"]["jugadas"]
    t = sim.tecnico_preset(sim.p.meta["tecnico_actual_foco"])
    Ci, Cj, _ = A.componentes_partido(sim, t, _rival_mediano(sim), True, muestra)
    r = J.simular_partidos(Ci, Cj, n, np.random.default_rng(semilla))
    minimo = cfg["minimo_visible"]
    out = {"n": n, "minutos": int(Ci.T), "minimo_visible": minimo}
    frac = lambda cond_a, cond_b: float(
        (cond_a.sum() + cond_b.sum()) / (cond_a.size + cond_b.size)
    )  # fracción de minutos-equipo que cumplen la condición
    # ---- v8: el peligro crudo (suma de los x de los remates), el eje sigue al mayor pico del partido
    a, b = r["peligro_i"], r["peligro_j"]
    eje_max = np.maximum(a.max(1), b.max(1))[:, None]
    p95 = np.percentile(np.concatenate([a, b], 1), cfg["percentil_eje"], axis=1)[:, None]
    out["v8"] = {
        "bajo_eje_max": frac(a < minimo * eje_max, b < minimo * eje_max),
        "bajo_eje_p95": frac(a < minimo * p95, b < minimo * p95),
        "max_sobre_p95": float(np.median(eje_max / np.maximum(p95, 1e-12))),
        "sin_remate": float(np.concatenate([r["remates_i"] == 0, r["remates_j"] == 0], 1).mean()),
        "pico_sobre_mediana_remate": float(
            np.median(
                [x.max() / np.median(x[x > 0]) for x in np.concatenate([a, b], 1) if (x > 0).any()]
            )
        ),
    }
    # ---- v7: la diferencia de los dos equipos
    d = r["peligro_i"] - r["peligro_j"]
    out["v7_resta"] = {
        "cancelacion": float(1 - np.abs(d).mean() / (a + b).mean()),
        "minutos_casi_cero": float(
            (np.abs(r["momentum"]) < minimo * np.abs(r["momentum"]).max(1, keepdims=True)).mean()
        ),
    }
    # ---- v10: presión de cada equipo, suavizada
    Si, Sj = r["suave_i"], r["suave_j"]
    S = np.concatenate([Si, Sj], 1)
    tope = np.percentile(S, cfg["percentil_eje"], axis=1)[:, None]
    techo = np.minimum(S.max(1)[:, None], tope * (1 + cfg["margen_eje"]))
    dif = Si - Sj
    mu_i, mu_j = r["mu_i"].mean(1), r["mu_j"].mean(1)
    dmi, dmj = Si.mean(1) - mu_i, Sj.mean(1) - mu_j
    ee = lambda x: float(x.std(ddof=1) / np.sqrt(len(x)))
    out["v10"] = {
        "visibles": frac(Si >= minimo * tope, Sj >= minimo * tope),
        "las_dos_visibles": float(((Si >= minimo * tope) & (Sj >= minimo * tope)).mean()),
        "pasan_del_marco": frac(Si > techo + 1e-12, Sj > techo + 1e-12),
        "partidos_con_recorte": float(((S > techo + 1e-12).any(1)).mean()),
        "pico_sobre_p95_p90": float(np.percentile(S.max(1) / tope[:, 0], 90)),
        "pasan_del_tope": frac(Si > tope, Sj > tope),
        "max_sobre_p95": float(np.median(S.max(1)[:, None] / tope)),
        "cancelacion": float(1 - np.abs(dif).mean() / (Si + Sj).mean()),
        "media_S_menos_mu": {
            "america": float(dmi.mean()),
            "america_ee": ee(dmi),
            "rival": float(dmj.mean()),
            "rival_ee": ee(dmj),
        },
        "media_mu": {"america": float(mu_i.mean()), "rival": float(mu_j.mean())},
        "presion_negativa": float(
            (J.presion(r["amenaza_i"], Ci.f * r["peligro_i"], cfg["peso_sorpresa"]) < 0).sum()
        ),
        "peso_sorpresa": cfg["peso_sorpresa"],
        "vida_media": cfg["vida_media_presion"],
    }
    # ---- v11: el dominio M(t) de una sola barra por minuto (D-096): minutos visibles, cambios de signo y signo del favorito, con el rival mediano y el más débil
    M = r["dominio"]
    eje = np.percentile(np.abs(M), cfg["percentil_eje"], axis=1)[:, None]
    de_mediano = float(sim.elo[sim.foco] - sim.elo[_rival_mediano(sim)])
    out["v11"] = {
        "visibles": float((np.abs(M) >= minimo * eje).mean()),
        "cambios_de_signo_mediana": float(np.median((np.diff(np.sign(M), axis=1) != 0).sum(1))),
        "signo_del_favorito": float(((M.mean(1) > 0) == (de_mediano > 0)).mean()),
        "delta_elo": de_mediano,
    }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--salida")
    a = ap.parse_args()
    d = diagnostico(Simulador(os.environ.get("SIMDT_ARTEFACTOS")), a.n)
    v8, v7, v10 = d["v8"], d["v7_resta"], d["v10"]
    print(
        f"{d['n']} partidos · v8 (peligro crudo): {100 * v8['bajo_eje_max']:.1f} % de los minutos con barra < {100 * d['minimo_visible']:.0f} % del eje (eje en el mayor pico; con el percentil 95: {100 * v8['bajo_eje_p95']:.1f} %); "
        f"el pico mayor es {v8['max_sobre_p95']:.1f} veces el percentil 95; {100 * v8['sin_remate']:.0f} % de los minutos sin remate"
    )
    print(
        f"  v7 (resta): cancela {100 * v7['cancelacion']:.0f} % de la altura; {100 * v7['minutos_casi_cero']:.1f} % de los minutos con |diferencia| < {100 * d['minimo_visible']:.0f} % del eje"
    )
    print(
        f"  v10: {100 * v10['visibles']:.1f} % de los minutos con barra visible ({100 * v10['las_dos_visibles']:.1f} % con las dos); pico mayor {v10['max_sobre_p95']:.2f} veces el percentil 95; "
        f"{100 * v10['pasan_del_marco']:.2f} % de las barras se recortan ({100 * v10['partidos_con_recorte']:.1f} % de los partidos tiene alguna); media S − μ América {v10['media_S_menos_mu']['america']:+.5f} ± {v10['media_S_menos_mu']['america_ee']:.5f}"
    )
    v11 = d["v11"]
    print(
        f"  v11 (una barra por minuto, rival mediano, ΔElo {v11['delta_elo']:+.0f}): {100 * v11['visibles']:.1f} % de los minutos con |M| ≥ {100 * d['minimo_visible']:.0f} % del eje (spec: ≥ 95 %); "
        f"cambios de signo, mediana {v11['cambios_de_signo_mediana']:.0f} (spec: ≥ 6); la media de M tiene el signo del favorito en {100 * v11['signo_del_favorito']:.1f} % de los partidos (spec: ≥ 90 %)"
    )
    if a.salida:
        Path(a.salida).write_text(json.dumps(d, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
