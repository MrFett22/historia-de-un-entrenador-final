"""Fase 5: adaptador de datos reales y calibración de punta a punta."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from simdt import config
from simdt.datos import esquema, repo

CACHE = config.RAIZ_SIM / "_cache"


def test_zona_y_puesto():
    assert repo.zona(0, 0) == 0 and repo.zona(119.9, 79.9) == 19 and repo.zona(60, 10) == 8
    assert repo.nivel_puesto("Left Center Back") == 1 and repo.nivel_puesto("Center Forward") == 5
    assert repo.nivel_puesto("Goalkeeper") == 0 and repo.nivel_puesto(None) is None


@pytest.mark.skipif(
    not (CACHE / "tablas_reales.pkl").exists(), reason="sin datos reales en este entorno"
)
def test_tablas_reales_con_esquema():
    tablas, _ = pd.read_pickle(CACHE / "tablas_reales.pkl")
    assert esquema.validar(tablas) == []
    # r_sk suma 1 por secuencia: el total fraccional = número de secuencias de juego abierto
    assert tablas["juego"].n.sum() > 400_000


@pytest.mark.skipif(
    not (CACHE / "artefactos_demo" / "meta.json").exists(),
    reason="corre calibrar --datos con tablas sintéticas",
)
def test_calibrar_con_tablas_sinteticas():
    from simdt.servicio import Simulador

    s = Simulador(CACHE / "artefactos_demo")
    assert s.p.meta["modo"] == "MODO_REAL" and "América" in s.p.meta["equipos"]
    r = s.simular(s.tecnico_promedio())
    assert 0 < r.temporada.resumen["puntos_esperados"] < 51


@pytest.mark.skipif(not (config.ARTEFACTOS / "meta.json").exists(), reason="sin artefactos")
def test_artefactos_de_la_app():
    from simdt.servicio import Simulador

    s = Simulador()
    assert len(s.p.meta["equipos"]) == 18 and len(s.calendario) == 153
    assert np.all(np.bincount(s.calendario.ravel(), minlength=18) == 17)
    for f in ("fichas_posterior.parquet", "tecnicos_posterior.parquet", "plantel_america.parquet"):
        assert (config.ARTEFACTOS / f).exists()
