#!/usr/bin/env bash
# Abre el simulador en http://localhost:8501 con los parámetros publicados (simulador/artefactos/).
# Uso, desde cualquier carpeta:  bash simulador/correr_app.sh
# Python: el de SIMDT_PYTHON si está definido; si no, simulador/.venv o .venv en la raíz.
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${SIMDT_PYTHON:-}"
if [ -z "$PY" ]; then
  for v in "$RAIZ/simulador/.venv" "$RAIZ/.venv"; do
    for c in "$v/Scripts/python.exe" "$v/bin/python"; do
      if [ -x "$c" ]; then PY="$c"; break 2; fi
    done
  done
fi
if [ -z "$PY" ]; then
  echo "No encontré un entorno de Python. Créalo con:" >&2
  echo "  cd simulador && python -m venv .venv && .venv/bin/python -m pip install -e .   (Windows: .venv/Scripts/python)" >&2
  exit 1
fi
cd "$RAIZ"  # Streamlit lee .streamlit/config.toml de la carpeta desde donde corre
exec "$PY" -m streamlit run simulador/app.py --server.headless true --server.port "${PUERTO:-8501}"
