"""Orquesta todas las fases sin intervención.

    python -m simdt.correr_todo                  # detecta el modo (reales si hay datos)
    python -m simdt.correr_todo --modo sintetico # datos de demostración → simulador/_cache/artefactos_sintetico
    python -m simdt.correr_todo --modo real

Pasos: inventario → calibración (fase A, fichas, artefactos) → validación → pruebas rápidas.
En modo sintético NO toca artefactos/ (los de la app); escribe en _cache/artefactos_sintetico. Para
abrir la app con ellos: SIMDT_ARTEFACTOS=simulador/_cache/artefactos_sintetico streamlit run simulador/app.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from . import config
from .datos import inventario


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["auto", "sintetico", "real"], default="auto")
    ap.add_argument("--sin-pruebas", action="store_true")
    ap.add_argument("--N-sobol", type=int, default=1024)
    a = ap.parse_args(argv)
    t0 = time.time()
    inv = inventario.detectar()
    modo = (
        a.modo
        if a.modo != "auto"
        else ("sintetico" if inv["modo"] == inventario.MODO_SINTETICO else "real")
    )
    print(f"[1/4] inventario: {inv['modo']} → corrida en modo {modo}", flush=True)
    from . import calibrar
    from .validacion import reporte

    if modo == "sintetico":
        salida = config.cache_dir() / "artefactos_sintetico"
        print("[2/4] calibración con datos sintéticos...", flush=True)
        calibrar.main(["--sintetico", "--salida", str(salida)])
        print("[3/4] validación (sintético; sin retroprueba)...", flush=True)
        reporte.main(["--artefactos", str(salida), "--sin-retro", "--N-sobol", str(a.N_sobol)])
    else:
        print("[2/4] calibración con datos reales...", flush=True)
        calibrar.main([])
        print("[3/4] validación completa...", flush=True)
        reporte.main(["--N-sobol", str(a.N_sobol)])
    codigo = 0
    if not a.sin_pruebas:
        print("[4/4] pruebas rápidas...", flush=True)
        codigo = subprocess.call(
            [sys.executable, "-m", "pytest", "-q", "-m", "not lento"], cwd=config.RAIZ_SIM
        )
    print(f"listo en {time.time() - t0:.0f} s (código de pruebas {codigo})", flush=True)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
