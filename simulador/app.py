"""Entrada de Streamlit: streamlit run simulador/app.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from simdt.app.principal import main  # noqa: E402

if (
    __name__ != "__mp_main__"
):  # los procesos hijos de multiprocessing (spawn) re-importan este archivo: no deben dibujar la app
    main()
