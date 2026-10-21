"""Fase 7: corre toda la validación y escribe reportes/validacion/.

    python -m simdt.validacion.reporte [--rapida] [--sin-retro]

Lee artefactos/ (y la fase A guardada en simulador/_cache/). Al final actualiza la etiqueta
global ("predictivo" / "descriptivo") y las perillas "solo estilo" en artefactos/meta.json.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time

import numpy as np
import pandas as pd

from .. import config
from ..datos import inventario


def _md_tabla(df: pd.DataFrame, cols=None, fmt="{:.4f}") -> str:
    cols = cols or list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df[cols].iterrows():
        out.append(
            "| "
            + " | ".join(
                fmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in r
            )
            + " |"
        )
    return "\n".join(out)


def rendimiento(sim, directorio=None) -> dict:
    from ..motor.partido import partido_lote
    from ..motor.temporada import error_dos_etapas

    rng = np.random.default_rng(0)
    z = sim.p.piezas.fichas[0]
    zi, zj = z[rng.integers(0, 18, 1000)], z[rng.integers(0, 18, 1000)]
    t0 = time.perf_counter()
    for a in range(0, 1000, 250):
        partido_lote(sim.p.liga, zi[a : a + 250], zj[a : a + 250], 1.0, 0.0)
    t_partido = (time.perf_counter() - t0) / 1000
    t = sim.tecnico_promedio()
    sim.simular(t, "rapido")  # calentamiento + caché
    tiempos = {}
    for modo in ("rapido", "preciso"):
        t0 = time.perf_counter()
        r = sim.simular(t, modo)
        tiempos[modo] = time.perf_counter() - t0
    # costo por réplica y por torneo interno: dos corridas con S distinto (R fijo)
    from ..motor.temporada import muestras_replicas, simular_temporada
    from ..estimacion.fichas import ficha_foco

    R = 100
    idx = muestras_replicas(sim.p.piezas.fichas.shape[0], R, sim.semilla)
    pre = sim._precalculo(idx, R)
    ff = ficha_foco(sim.p.piezas, t.theta, idx)
    medidas = {}
    for S in (10, 200):
        t0 = time.perf_counter()
        rr = simular_temporada(
            sim.p.liga,
            sim.p.piezas.fichas,
            ff,
            sim.calendario,
            sim.elo,
            sim.foco,
            idx,
            S,
            sim.semilla,
            pre,
            con_estilo=False,
        )
        medidas[S] = time.perf_counter() - t0
    c_S = (medidas[200] - medidas[10]) / (R * 190)
    c_R = medidas[10] / R - 10 * c_S
    e = error_dos_etapas(
        (rr.posicion <= config.cargar()["torneo"]["liguilla_directa"]).astype(float)
    )
    s_opt = float(
        np.sqrt(max(c_R, 1e-9) * e["sigma_w2"] / (max(c_S, 1e-12) * max(e["sigma_b2"], 1e-12)))
    )
    t0 = time.perf_counter()
    from ..servicio import Simulador

    Simulador(directorio)
    t_arranque = time.perf_counter() - t0
    return {
        "partido_ms": t_partido * 1e3,
        "torneo_rapido_s": tiempos["rapido"],
        "torneo_preciso_s": tiempos["preciso"],
        "costo_replica_s": c_R,
        "costo_torneo_interno_s": c_S,
        "sigma_b2_liguilla": e["sigma_b2"],
        "sigma_w2_liguilla": e["sigma_w2"],
        "S_optimo": s_opt,
        "arranque_servicio_s": t_arranque,
        "replica_s": medidas[10] / R,
    }


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-retro", action="store_true")
    ap.add_argument("--sin-placebo", action="store_true")
    ap.add_argument("--N-sobol", type=int, default=1024)
    ap.add_argument("--artefactos", default=None)
    ap.add_argument(
        "--salida",
        default=None,
        help="carpeta de salida (por omisión reportes/validacion/); p. ej. _cache/validacion_E",
    )
    a = ap.parse_args(argv)
    from ..servicio import Simulador
    from . import calibracion, independencia, placebo, recuperacion, retroprueba, sensibilidad

    sim = Simulador(a.artefactos)
    modo = sim.p.meta["modo"]
    real = modo != inventario.MODO_SINTETICO
    cache = config.cache_dir()
    with open(cache / ("fase_a_real.pkl" if real else "fase_a_demo.pkl"), "rb") as f:
        res = pickle.load(f)
    tablas = pd.read_pickle(cache / "tablas_reales.pkl")[0] if real else None
    if tablas is None:
        from ..datos import sintetico

        tablas, _ = sintetico.generar()
    from pathlib import Path

    V = Path(a.salida) if a.salida else config.VALIDACION
    V.mkdir(parents=True, exist_ok=True)
    sufijo = "" if real else "_demo"
    out = {"modo": modo}
    print("calibración...", flush=True)
    cal, pr = calibracion.evaluar(res, tablas)
    out["calibracion"] = cal
    print("H1...", flush=True)
    out["independencia"] = independencia.evaluar(pr)
    print("recuperación...", flush=True)
    out["recuperacion"] = recuperacion.evaluar(res, tablas)
    print("Sobol...", flush=True)
    out["sobol"] = sensibilidad.evaluar(sim, N=a.N_sobol)
    if not a.sin_placebo:
        print("placebo...", flush=True)
        out["placebo"] = placebo.correr(res, sim, mcmc=retroprueba.MCMC_LIGERO)
    if real and not a.sin_retro:
        print("retroprueba...", flush=True)
        n_t = int(tablas["partidos"].temporada.max())
        rp = retroprueba.correr(tablas, [n_t - 2, n_t - 1, n_t])
        rp["tabla"].to_csv(V / "retroprueba_llegadas.csv", index=False)
        out["retroprueba"] = {k: v for k, v in rp.items() if k != "tabla"}
    print("rendimiento...", flush=True)
    out["rendimiento"] = rendimiento(sim, a.artefactos)
    (V / f"validacion{sufijo}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )
    escribir_md(out, V / f"VALIDACION{sufijo}.md")
    # etiqueta global y perillas solo-estilo -> meta.json (lo que muestra la app)
    meta_p = (
        config.ARTEFACTOS if a.artefactos is None else __import__("pathlib").Path(a.artefactos)
    ) / "meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    meta["etiqueta_global"] = out.get("retroprueba", {}).get("etiqueta", "descriptivo")
    meta["perillas_solo_estilo"] = out["sobol"]["solo_estilo"]
    meta["validacion"] = {
        "fecha": time.strftime("%Y-%m-%d"),
        "archivo": f"reportes/validacion/validacion{sufijo}.json",
    }
    meta_p.write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )
    print("listo", flush=True)
    return 0


def escribir_md(out: dict, ruta) -> None:
    c = out["calibracion"]
    L = [
        f"# Validación ({out['modo']})",
        "",
        "## Calibración (dentro de muestra, fichas de la celda de cada partido)",
        f"- Partidos: {c['n_partidos']}",
        f"- RPS motor {c['rps_motor']:.4f} · frecuencias base {c['rps_base']:.4f} · simulador vigente (Poisson + log5) {c['rps_vigente']:.4f}",
        f"- Diferencia motor − base (IC 95 % bootstrap): [{c['dif_motor_base_ic95'][0]:.4f}, {c['dif_motor_base_ic95'][1]:.4f}]",
        f"- Diferencia motor − vigente (IC 95 %): [{c['dif_motor_vigente_ic95'][0]:.4f}, {c['dif_motor_vigente_ic95'][1]:.4f}]",
        f"- Puntos reales {c['puntos_reales']} · xPts del motor {c['xpts_motor']:.1f} · error {100 * c['error_xpts']:.2f} % (tolerancia 0.5 %)",
        f"- Goles reales {c['goles_reales']:.0f} · esperados {c['goles_esperados']:.1f}; empates reales {c['empates_reales']:.3f} · motor {c['empates_motor']:.3f}",
        f"- Cumple RPS: {c['cumple_rps']} · cumple xPts: {c['cumple_xpts']}",
        "",
    ]
    h = out["independencia"]
    L += [
        "## H1: independencia entre partidos",
        f"- Autocorrelación lag 1 de (puntos − xPts) dentro de equipo-torneo: {h['autocorrelacion_lag1']:.4f} "
        f"(IC 95 % [{h['autocorrelacion_ic95'][0]:.4f}, {h['autocorrelacion_ic95'][1]:.4f}], n = {h['n_pares']})",
        f"- Pendiente sobre la diferencia de días de descanso: {h['pendiente_descanso_por_dia']:.4f} puntos por día "
        f"(IC 95 % [{h['pendiente_ic95'][0]:.4f}, {h['pendiente_ic95'][1]:.4f}], n = {h['n_descanso']})",
        "",
    ]
    r = out["recuperacion"]
    L += [
        "## Recuperación (técnicos con ≥ 50 partidos en un club)",
        f"- Pares: {r['n_pares']} · mezcla simulada dentro del rango observado (95 %): {100 * r['fraccion_dentro']:.0f} %",
        "",
    ]
    if r["detalle"]:
        df = pd.DataFrame(r["detalle"])
        L += [_md_tabla(df, ["tecnico", "club", "partidos", "simulada", "observada", "dentro"]), ""]
    s = out["sobol"]
    L += [
        f"## Sobol (Saltelli, N = {s['N']}, {s['evaluaciones']} evaluaciones; salida = puntos esperados del América)",
        f"- Puntos esperados en el muestreo: media {s['puntos_media']:.2f}, DE {s['puntos_sd']:.2f}, rango "
        f"[{s['puntos_rango'][0]:.2f}, {s['puntos_rango'][1]:.2f}]",
        _md_tabla(pd.DataFrame(s["tabla"])),
        f'- Perillas marcadas "solo cambia el estilo, no los puntos" (S_T + IC < {s["umbral_ST"]}): {s["solo_estilo"]}',
        "",
    ]
    if "placebo" in out:
        pl = out["placebo"]
        L += [
            "## Placebo (etiquetas de técnico barajadas entre celdas)",
            f"- Componentes reajustadas: {pl['componentes_tecnico']}",
            _md_tabla(pd.DataFrame(pl["placebos"]))
            if pl["placebos"]
            else "(sin componentes del técnico)",
            f"- Todos los intervalos del 95 % contienen el 0: {pl['todos_contienen_cero']}",
            "",
        ]
    if "retroprueba" in out:
        rp = out["retroprueba"]
        L += [
            "## Retroprueba (llegadas de técnico, sin mirar el futuro)",
            f"- Llegadas evaluadas: {rp['n']} (detalle en retroprueba_llegadas.csv)",
            f"- MAE simulador {rp.get('mae_simulador', float('nan')):.3f} · inercia {rp.get('mae_inercia', float('nan')):.3f} puntos por partido",
            f"- RMSE simulador {rp.get('rmse_simulador', float('nan')):.3f} · inercia {rp.get('rmse_inercia', float('nan')):.3f}",
            f"- Diebold-Mariano (HLN): {rp.get('dm_estadistico', float('nan')):.3f}, p = {rp['dm_p']:.3f} → etiqueta **{rp['etiqueta']}**",
            f"- Cobertura conforme del 80 %: {100 * rp.get('cobertura_conforme80', float('nan')):.0f} %",
            "",
        ]
    p = out["rendimiento"]
    L += [
        "## Rendimiento",
        f"- Un partido (en lote): {p['partido_ms']:.3f} ms · una réplica: {p['replica_s'] * 1e3:.1f} ms",
        f"- Torneo rápido: {p['torneo_rapido_s']:.2f} s · preciso: {p['torneo_preciso_s']:.2f} s · arranque del servicio: {p['arranque_servicio_s']:.2f} s",
        f"- c_R = {p['costo_replica_s'] * 1e3:.2f} ms, c_S = {p['costo_torneo_interno_s'] * 1e6:.1f} µs; σ_b² = {p['sigma_b2_liguilla']:.4f}, "
        f"σ_w² = {p['sigma_w2_liguilla']:.4f} (P de liguilla) → S* = {p['S_optimo']:.0f}",
        "",
    ]
    from pathlib import Path

    Path(ruta).write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
