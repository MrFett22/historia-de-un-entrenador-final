"""Recalcula los números de control de la entrega con los artefactos publicados (sin recalibrar).

    python docs/herramientas/numeros_control.py [--salida docs/numeros_control.json]

- Almada en el América (modo preciso): puntos esperados, P(liguilla) y Δ contra el estilo neutro.
- Las tarjetas de «¿Le podemos creer?» (mismas funciones que la app, `simdt.validacion.tarjetas`).
- La escala de «¿Qué pesa más?»: suerte, jugadores y r (`simdt.analisis.escala_efectos`).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "simulador" / "src"))


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, default=RAIZ / "docs" / "numeros_control.json")
    a = ap.parse_args(argv)
    from simdt import analisis as A
    from simdt.servicio import Simulador
    from simdt.validacion import tarjetas

    t0 = time.perf_counter()
    sim = Simulador()
    out = {"arranque_s": time.perf_counter() - t0, "modo_datos": sim.p.meta.get("modo")}
    almada = sim.p.meta.get("tecnico_actual_foco")
    t1 = time.perf_counter()
    cmp, r1, r2 = sim.comparar(sim.tecnico_preset(almada), sim.tecnico_promedio(), "preciso")
    R = r1.temporada.resumen
    out["almada"] = {
        "tecnico": almada,
        "puntos_esperados": R["puntos_esperados"],
        "p_liguilla": R["p_liguilla"]["media"],
        "delta_vs_neutro": cmp.resumen["media"],
        "delta_ic90": cmp.resumen["int90"],
        "veredicto": cmp.veredicto,
        "segundos": time.perf_counter() - t1,
    }
    g, val, _ = sim.validacion_total()
    cartas = tarjetas.todas(g, val)
    # la octava prueba (autoverificación de «Ver un partido»), como la calcula la app: técnico
    # vigente contra el rival de fuerza mediana, de local, 5,000 partidos sorteados
    import numpy as np

    rivales = [e for e in range(len(sim.elo)) if e != sim.foco]
    rival = rivales[int(np.argsort(sim.elo[rivales])[len(rivales) // 2])]
    av = A.autoverificacion_partido(sim, sim.tecnico_preset(almada), rival, True, 5000)
    cartas.append({"id": "partido", **tarjetas.partido(av)})
    out["tarjetas"] = [
        {k: v for k, v in c.items() if isinstance(v, (int, float, str, bool)) or v is None}
        for c in cartas
    ]
    v = val or {}
    out["validacion_E"] = {
        "error_xpts": v.get("calibracion", {}).get("error_xpts"),
        "autocorrelacion_lag1": v.get("independencia", {}).get("autocorrelacion_lag1"),
        "autocorrelacion_ic95": v.get("independencia", {}).get("autocorrelacion_ic95"),
        "placebo_limpio": v.get("placebo", {}).get("todos_contienen_cero"),
        "recuperacion": v.get("recuperacion", {}).get("fraccion_dentro"),
        "dm_p": v.get("retroprueba", {}).get("dm_p"),
    }
    out["escala"] = A.escala_efectos(sim)
    a.salida.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
