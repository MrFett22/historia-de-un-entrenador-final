"""Detección del modo de datos (fase 0) y reporte INVENTARIO.md.

MODO_REAL           : existen tablas derivadas del pipeline (secuencias con r_sk, eras, ...).
MODO_REAL_PIPELINE  : solo hay eventos crudos de StatsBomb -> se derivan en simulador/_cache/.
MODO_SINTETICO      : no hay datos -> todo corre con el generador sintético.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from .. import config

MODO_REAL = "MODO_REAL"
MODO_REAL_PIPELINE = "MODO_REAL_PIPELINE"
MODO_SINTETICO = "MODO_SINTETICO"


def _tablas_derivadas() -> list[Path]:
    """Busca tablas del pipeline dtcoach (parquet) en ubicaciones conocidas."""
    cand = []
    for patron in (
        "data/processed/**/*.parquet",
        "data/interim/**/*.parquet",
        "dtcoach_revision/**/data/processed/**/*.parquet",
    ):
        cand += [Path(p) for p in glob.glob(str(config.RAIZ_REPO / patron), recursive=True)]
    return cand


def detectar() -> dict:
    cfg = config.cargar()
    ev_dir = config.ruta_repo(cfg["datos"]["eventos_dir"])
    eventos = sorted(ev_dir.glob("events_*.json")) if ev_dir.exists() else []
    partidos = sorted(glob.glob(str(config.RAIZ_REPO / cfg["datos"]["partidos_glob"])))
    derivadas = _tablas_derivadas()
    if derivadas:
        modo = MODO_REAL
    elif eventos and partidos:
        modo = MODO_REAL_PIPELINE
    else:
        modo = MODO_SINTETICO
    return {
        "modo": modo,
        "n_eventos": len(eventos),
        "archivos_partidos": [Path(p).name for p in partidos],
        "tablas_derivadas": [str(p) for p in derivadas],
        "eventos_dir": str(ev_dir),
    }


def modo_actual() -> str:
    """Modo con el que se generaron los artefactos (lo que ve la app)."""
    p = config.ARTEFACTOS / "meta.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("modo", MODO_SINTETICO)
    return MODO_SINTETICO
