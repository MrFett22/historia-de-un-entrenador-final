"""Corte por fecha (D-050): ninguna celda del torneo objetivo entra a la fase A ni a la liga."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from simdt import calibrar
from simdt.datos import sintetico
from simdt.datos.corte import TABLAS_POR_PARTIDO, cortar_por_fecha
from simdt.estimacion.celdas import asignar_celdas


@pytest.fixture(scope="module")
def mundo():
    tablas, _ = sintetico.generar()
    p = tablas["partidos"]
    t_obj = int(p.temporada.max())
    corte = pd.to_datetime(p[p.temporada == t_obj].fecha).min()
    return tablas, t_obj, corte


def test_el_corte_quita_todo_lo_posterior_y_nada_de_lo_anterior(mundo):
    tablas, t_obj, corte = mundo
    cortadas, info = cortar_por_fecha(tablas, corte)
    p0, p1 = tablas["partidos"], cortadas["partidos"]
    assert (pd.to_datetime(p1.fecha) < corte).all() and len(p1) == int(
        (pd.to_datetime(p0.fecha) < corte).sum()
    )
    assert info["partidos_quitados"] == len(p0) - len(p1) > 0 and info["temporadas_quitadas"] == [
        t_obj
    ]
    ids = set(p1.match_id)
    for n in TABLAS_POR_PARTIDO:
        assert set(cortadas[n].match_id) <= ids, n
        assert len(cortadas[n]) == int(tablas[n].match_id.isin(ids).sum()), n
    assert len(tablas["partidos"]) == len(p0)  # no modifica la entrada


def test_sin_celdas_del_torneo_objetivo(mundo):
    tablas, t_obj, corte = mundo
    assert (
        asignar_celdas(tablas["partidos"]).temporada == t_obj
    ).any()  # con fuga, sí hay celdas del torneo objetivo
    cortadas, _ = cortar_por_fecha(tablas, corte)
    c = asignar_celdas(cortadas["partidos"])
    assert len(c) and (c.temporada < t_obj).all()


def test_cortes_extremos(mundo):
    tablas, _, _ = mundo
    _, info = cortar_por_fecha(
        tablas, pd.Timestamp("2999-01-01")
    )  # posterior a todo: no quita nada
    assert info["partidos_quitados"] == 0 and info["partidos_despues"] == len(tablas["partidos"])
    vacias, info = cortar_por_fecha(
        tablas, pd.Timestamp("1900-01-01")
    )  # anterior a todo: queda el esquema vacío
    assert info["partidos_despues"] == 0 and all(len(vacias[n]) == 0 for n in TABLAS_POR_PARTIDO)


def test_calibrar_entrega_a_la_fase_a_solo_partidos_anteriores_al_corte(
    mundo, monkeypatch, tmp_path
):
    """`calibrar()` corta ANTES de llamar a la fase A y lee el técnico vigente ANTES de cortar."""
    tablas, ctx, cad = calibrar.preparar_sintetico()
    p = tablas["partidos"]
    t_obj = int(p.temporada.max())
    corte = pd.to_datetime(p[p.temporada == t_obj].fecha).min()
    vistas = {}

    class Parar(Exception):
        pass

    def falsa(tab, *a, **k):
        vistas["tablas"] = tab
        vistas["cache"] = k.get("cache")
        raise Parar

    monkeypatch.setattr(calibrar.fase_a, "correr", falsa)
    ctx = {**ctx, "corte_fecha": str(corte.date())}
    with pytest.raises(Parar):
        calibrar.calibrar(
            tablas, ctx, cad, tmp_path, "fase_a_demo.pkl", verbose=False, precalculo_completo=False
        )
    v = vistas["tablas"]
    assert (pd.to_datetime(v["partidos"].fecha) < corte).all() and not (
        v["partidos"].temporada == t_obj
    ).any()
    for n in ("juego", "exposicion", "saques", "cambios", "panel"):
        assert set(v[n].match_id) <= set(v["partidos"].match_id)
    assert ctx["corte"]["partidos_quitados"] > 0 and ctx["corte"]["temporadas_quitadas"] == [t_obj]
    assert vistas["cache"] != "fase_a_demo.pkl" and vistas["cache"].startswith(
        "fase_a_demo_"
    )  # clave del caché


def test_la_clave_del_cache_cambia_con_el_corte(mundo):
    tablas, _, corte = mundo
    cad = (np.ones((2, 2)), np.ones(2))
    a = calibrar._cache_con_clave("fase_a_real.pkl", tablas, cad, {"corte_fecha": None})
    b = calibrar._cache_con_clave(
        "fase_a_real.pkl", tablas, cad, {"corte_fecha": str(corte.date())}
    )
    assert a != b and a.startswith("fase_a_real_") and a.endswith(".pkl")
