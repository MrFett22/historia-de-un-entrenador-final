"""Fase A de la v10: ¿cuánto cambian entre técnicos las tres gráficas candidatas a quitarse?

  · mapa de calor de zonas («¿Por dónde movería el balón?»),
  · goles por zona en la cancha («¿De dónde vienen sus goles?»),
  · goles por tipo de jugada («¿Qué jugadas dan sus goles?»).

Simula a cada técnico real (rápido, con estilo) y a los extremos del modo sin límites, y mide, contra el estilo neutro (la referencia de la liga): la variación máxima en
puntos porcentuales del mapa (cada celda como % del total) y el cambio relativo máximo por celda / por barra. Solo lee los artefactos; no escribe nada salvo --salida.
Uso:  SIMDT_ARTEFACTOS=<carpeta> python herramientas/variacion_graficas.py [--salida variacion_graficas.json]"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from simdt.modelos.cadena import mapa_equipo, visitas_por_tipo  # noqa: E402
from simdt.perillas import ejes as mejes  # noqa: E402
from simdt.servicio import Simulador  # noqa: E402

UMBRAL_REL = 0.05  # la gráfica de goles por tipo se queda solo si alguna barra cambia ≥ 5 % entre técnicos reales (spec v10)
# Barras de goles por tipo: las tres de juego abierto y las cinco de pelota parada, de TODA la lista (a favor y en contra)


NX, NY = 5, 4


def _goles_por_zona(sim, estilo: dict) -> dict:
    """Lo que dibujaba «¿De dónde vienen sus goles?» (v4 a v9): goles por tipo de jugada repartidos por zona con los pesos FIJOS de la liga (visitas · P(gol) de la cadena)."""
    L = sim.p.liga
    V = visitas_por_tipo(L.P_cadenas, L.mu_cadenas, L.P0_cadenas)
    nt = V.shape[1]
    w = np.zeros((3, nt))
    for k in range(3):
        pg = L.P_cadenas[k][:, nt]
        w[k] = (
            (L.mu_cadenas[k] * L.P0_cadenas[k][:, nt] + (V[k] - L.mu_cadenas[k]) * pg)
            if L.P0_cadenas is not None
            else V[k] * pg
        )
        w[k] = w[k] / max(w[k].sum(), 1e-12)
    espejo = [(NX - 1 - z // NY) * NY + (NY - 1 - z % NY) for z in range(nt)]
    return {
        "favor": np.asarray(estilo["goles_k_favor"])[:, None] * w,
        "contra": (np.asarray(estilo["goles_k_contra"])[:, None] * w)[:, espejo],
    }


def _vectores(sim, estilo: dict) -> dict:
    """Lo que dibujaba el mapa de calor: los toques por zona del equipo (cadenas de la LIGA ponderadas por la mezcla de jugadas de ESTE técnico)."""
    gz = _goles_por_zona(sim, estilo)
    zonas = np.asarray(
        mapa_equipo(
            sim.p.liga.P_cadenas,
            sim.p.liga.mu_cadenas,
            np.asarray(estilo["N_k"]),
            sim.p.liga.P0_cadenas,
        ),
        float,
    )
    barras_favor = np.r_[estilo["goles_k_favor"], estilo["goles_bp_favor"]]
    barras_contra = np.r_[estilo["goles_k_contra"], estilo["goles_bp_contra"]]
    return {
        "zonas": zonas / zonas.sum(),
        "goles_favor": gz["favor"] / gz["favor"].sum(),
        "goles_contra": gz["contra"] / gz["contra"].sum(),
        "goles_zona_favor_abs": gz["favor"],
        "goles_zona_contra_abs": gz["contra"],
        "barras_favor": barras_favor,
        "barras_contra": barras_contra,
    }


def _rel(x: np.ndarray, ref: np.ndarray) -> float:
    return float(np.max(np.abs(x - ref) / np.maximum(np.abs(ref), 1e-12)))


def medir(sim, nombres: list[str], extremos: bool = True, modo: str = "rapido") -> dict:
    neutro = sim.simular(sim.tecnico_promedio(), modo)
    ref = _vectores(sim, neutro.estilo)
    casos = [(n, sim.tecnico_preset(n), "real") for n in nombres]
    if extremos:
        base = sim.tecnico_promedio()
        per0 = sim.ejes.posiciones(np.zeros_like(base.theta), ilim=True)
        for k in mejes.CLAVES_EJES:
            lo, hi = sim.ejes[k].limites_de(True)
            for etiqueta, v in (("mín", lo), ("máx", hi)):
                per = {**(base.perillas or {}), **per0, k: v}
                casos.append(
                    (
                        f"extremo {k} {etiqueta}",
                        sim.tecnico_perillas(per, base=base, ilimitado=True),
                        "extremo",
                    )
                )
    filas = []
    for n, t, tipo in casos:
        v = _vectores(sim, sim.simular(t, modo).estilo)
        filas.append(
            {
                "nombre": n,
                "tipo": tipo,
                "zonas_pp": 100 * float(np.max(np.abs(v["zonas"] - ref["zonas"]))),
                "zonas_rel": _rel(v["zonas"], ref["zonas"]),
                "goles_zona_pp": 100
                * float(
                    max(
                        np.max(np.abs(v["goles_favor"] - ref["goles_favor"])),
                        np.max(np.abs(v["goles_contra"] - ref["goles_contra"])),
                    )
                ),
                "goles_zona_rel": float(
                    max(
                        _rel(v["goles_zona_favor_abs"], ref["goles_zona_favor_abs"]),
                        _rel(v["goles_zona_contra_abs"], ref["goles_zona_contra_abs"]),
                    )
                ),
                "barras_rel": float(
                    max(
                        _rel(v["barras_favor"], ref["barras_favor"]),
                        _rel(v["barras_contra"], ref["barras_contra"]),
                    )
                ),
                "barras_rel_por_barra": [
                    float(x)
                    for x in np.maximum(
                        np.abs(v["barras_favor"] - ref["barras_favor"]) / ref["barras_favor"],
                        np.abs(v["barras_contra"] - ref["barras_contra"]) / ref["barras_contra"],
                    )
                ],
            }
        )
    out = {
        "n_reales": len(nombres),
        "n_extremos": len(filas) - len(nombres),
        "umbral_rel": UMBRAL_REL,
    }
    for tipo in ("real", "extremo"):
        fs = [f for f in filas if f["tipo"] == tipo]
        if not fs:
            continue
        out[tipo] = {
            c: float(max(f[c] for f in fs))
            for c in ("zonas_pp", "zonas_rel", "goles_zona_pp", "goles_zona_rel", "barras_rel")
        }
        out[tipo]["quien_barras"] = max(fs, key=lambda f: f["barras_rel"])["nombre"]
    out["barras_se_quedan"] = bool(out["real"]["barras_rel"] >= UMBRAL_REL)
    out["filas"] = filas
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida")
    ap.add_argument("--sin-extremos", action="store_true")
    a = ap.parse_args()
    sim = Simulador(os.environ.get("SIMDT_ARTEFACTOS"))
    r = medir(sim, list(sim.ejes.nombres), not a.sin_extremos)
    for tipo in ("real", "extremo"):
        if tipo in r:
            x = r[tipo]
            n = r["n_reales"] if tipo == "real" else r["n_extremos"]
            print(
                f"{tipo}s ({n}): zonas {x['zonas_pp']:.3f} pp / {100 * x['zonas_rel']:.2f} % rel · goles en la cancha {x['goles_zona_pp']:.3f} pp / {100 * x['goles_zona_rel']:.2f} % rel · "
                f"goles por tipo {100 * x['barras_rel']:.2f} % rel (la mayor: {x['quien_barras']})"
            )
    print(
        "«¿Qué jugadas dan sus goles?» "
        + ("SE QUEDA (≥ 5 %)" if r["barras_se_quedan"] else "SE QUITA (< 5 % en todas las barras)")
    )
    if a.salida:
        Path(a.salida).write_text(json.dumps(r, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
