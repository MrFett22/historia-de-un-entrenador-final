"""Mide el servicio sin Streamlit: arranque, simular rápido/preciso y comparar.

    cd simulador && .venv/bin/python herramientas/medir_servicio.py

Lo independiente del hardware (puntos esperados, P(liguilla), Δ) debe coincidir con la primera corrida:
26.64 pts, P(liguilla) 67.7 %, Δ = +0.26 [-0.16, +0.71]. Los tiempos dependen del equipo; el primer
`simular rapido` incluye la compilación JIT de numba (la caché queda en __pycache__).
"""

import time, json, numpy as np, os

t0 = time.perf_counter()
from simdt.servicio import Simulador

t1 = time.perf_counter()
sim = Simulador()
t2 = time.perf_counter()
print(f"import {t1 - t0:.2f}s | Simulador() {t2 - t1:.2f}s")
alm = "Jorge Guillermo Almada Alves"
t = sim.tecnico_preset(alm)
prom = sim.tecnico_promedio()
print("tecnico_actual_foco:", sim.p.meta.get("tecnico_actual_foco"), "| semilla", sim.semilla)
for modo in ("rapido", "preciso"):
    for rep in (1, 2):
        t0 = time.perf_counter()
        r = sim.simular(t, modo)
        dt = time.perf_counter() - t0
        s = r.temporada.resumen
        print(
            f"simular {modo} #{rep}: {dt:.2f}s | pts_esp {s['puntos_esperados']:.2f} (EE {s['puntos_esperados_ee']:.3f}) rango80 {s['puntos_rango80']} | P(lig) {100 * s['p_liguilla']['media']:.1f}% (EE {100 * s['p_liguilla']['ee']:.2f}) | lugar {s['lugar_mas_probable']}"
        )
for modo in ("rapido", "preciso"):
    t0 = time.perf_counter()
    c, r1, r2 = sim.comparar(t, prom, modo)
    dt = time.perf_counter() - t0
    print(
        f"comparar {modo}: {dt:.2f}s | veredicto {c.veredicto} | {json.dumps({k: (np.round(v, 3).tolist() if isinstance(v, (list, float)) else v) for k, v in c.resumen.items() if k in ('media', 'ee', 'int90', 'int95', 'rango_torneo80')})}"
    )
    print(
        f"   pts promedio {r2.temporada.resumen['puntos_esperados']:.2f} | P(lig) prom {100 * r2.temporada.resumen['p_liguilla']['media']:.1f}%"
    )
