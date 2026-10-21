"""Lectura de config/simulador.yaml y rutas del proyecto."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

RAIZ_SIM = Path(__file__).resolve().parents[2]  # simulador/
RAIZ_REPO = RAIZ_SIM.parent  # raíz del repositorio
import os

ARTEFACTOS = Path(
    os.environ.get("SIMDT_ARTEFACTOS", RAIZ_SIM / "artefactos")
)  # la demo puede apuntar a otra carpeta
REPORTES = RAIZ_SIM / "reportes"
VALIDACION = REPORTES / "validacion"


@lru_cache(maxsize=1)
def cargar(ruta: str | None = None) -> dict:
    p = Path(ruta) if ruta else RAIZ_SIM / "config" / "simulador.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ruta_repo(rel: str) -> Path:
    return RAIZ_REPO / rel


def cache_dir() -> Path:
    p = RAIZ_REPO / cargar()["datos"]["cache_dir"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def tramo_de_minuto(minuto):
    """Índice de tramo (0..5) para minutos 0..89 (la reposición ya viene recortada)."""
    import numpy as np

    bordes = cargar()["partido"]["tramos"]
    return np.clip(
        np.searchsorted(bordes, np.asarray(minuto), side="right") - 1, 0, len(bordes) - 2
    )
