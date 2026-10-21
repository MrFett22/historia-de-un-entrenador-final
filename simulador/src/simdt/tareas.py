"""Equivalente a `make <objetivo>` para entornos sin make (Windows).

python -m simdt.tareas sintetico | validar | pruebas | app | todo
"""

from __future__ import annotations

import subprocess
import sys

from . import config


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    obj = argv[0] if argv else "todo"
    py = sys.executable
    if obj == "pruebas":
        return subprocess.call([py, "-m", "pytest", "-q"], cwd=config.RAIZ_SIM)
    if obj == "app":
        return subprocess.call([py, "-m", "streamlit", "run", "app.py"], cwd=config.RAIZ_SIM)
    if obj == "sintetico":
        from .correr_todo import main as correr

        return correr(["--modo", "sintetico"])
    if obj == "validar":
        from .validacion.reporte import main as validar

        return validar(argv[1:])
    if obj == "todo":
        from .correr_todo import main as correr

        return correr(argv[1:])
    print(f"objetivo desconocido: {obj}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
