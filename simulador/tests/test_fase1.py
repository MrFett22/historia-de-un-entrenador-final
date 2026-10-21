"""Fase 1: el generador produce tablas con la estructura común y la verdad pedida en 07_PRUEBAS."""

import numpy as np

from simdt.datos import esquema
from simdt.tipos import COMPONENTES, Q


def test_esquema(sint_pequeno):
    tablas, _ = sint_pequeno
    assert esquema.validar(tablas) == []


def test_registro_componentes():
    assert Q == len(COMPONENTES) == 32


def test_verdad_completa():
    from simdt.datos import sintetico

    tablas, v = sintetico.generar()
    p = tablas["partidos"]
    assert p["temporada"].nunique() == 6 and len(p) == 6 * 153
    tecs = set(p["tecnico_local"]) | set(p["tecnico_visitante"])
    assert len(tecs) == 30
    # técnicos que dirigieron a 2 o más clubes
    pares = set(zip(p["tecnico_local"], p["local"])) | set(
        zip(p["tecnico_visitante"], p["visitante"])
    )
    por_tec = {}
    for t, c in pares:
        por_tec.setdefault(t, set()).add(c)
    assert sum(len(c) >= 2 for c in por_tec.values()) >= 8
    # clubes con cambio a mitad de temporada
    mitad = 0
    for (club, temp), g in pd_concat(p).groupby(["club", "temporada"]):
        mitad += g["tecnico"].nunique() > 1
    assert mitad >= 4
    # un componente con sigma_theta = 0 (regla de atribución)
    assert (v.sigmas[:, 0] == 0).any()
    assert np.allclose(v.theta[:, v.sigmas[:, 0] == 0], 0)


def pd_concat(p):
    import pandas as pd

    a = p[["local", "temporada", "tecnico_local"]].set_axis(
        ["club", "temporada", "tecnico"], axis=1
    )
    b = p[["visitante", "temporada", "tecnico_visitante"]].set_axis(
        ["club", "temporada", "tecnico"], axis=1
    )
    return pd.concat([a, b])


def test_numeros_de_contexto(sint_pequeno):
    tablas, _ = sint_pequeno
    j = tablas["juego"]
    n = j.groupby("k")["n"].sum()
    pi = (n / n.sum()).to_numpy()
    assert np.allclose(pi, [0.354, 0.263, 0.383], atol=0.06)
    pr = (j.groupby("k")["remates"].sum() / n).to_numpy()
    assert np.allclose(pr, [0.14, 0.025, 0.12], atol=0.03)
