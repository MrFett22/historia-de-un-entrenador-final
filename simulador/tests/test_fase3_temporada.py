"""Pruebas de temporada T-T1 a T-T6 (07_PRUEBAS.md) con un entorno sintético."""

import numpy as np
import pytest
from scipy.stats import ks_2samp

from simdt.motor import calendario as cal_mod
from simdt.motor import tabla
from simdt.motor.comparar import comparar
from simdt.motor.temporada import muestras_replicas, precalcular, simular_temporada
from simdt.tipos import Q

FOCO = 0


@pytest.fixture(scope="module")
def entorno(liga):
    rng = np.random.default_rng(5)
    base = rng.normal(size=(18, Q)) * 0.08
    fichas = base[None] + rng.normal(size=(60, 18, Q)) * 0.03  # "posterior" de 60 muestras
    cal = cal_mod.todos_contra_todos(18)
    elo = 1500 + rng.normal(0, 60, 18)
    pre = precalcular(liga, fichas, cal, elo, FOCO, usar_cache=False)
    return fichas, cal, elo, pre


def _correr(liga, entorno, R=60, S=60, semilla=11, cal=None, pre=None, foco_fichas=None):
    fichas, cal0, elo, pre0 = entorno
    cal = cal0 if cal is None else cal
    pre = pre0 if pre is None else pre
    idx = muestras_replicas(fichas.shape[0], R, semilla)
    ff = fichas[idx, FOCO] if foco_fichas is None else foco_fichas
    return simular_temporada(liga, fichas, ff, cal, elo, FOCO, idx, S, semilla, pre)


def test_TT1_permutar_calendario(liga, entorno):
    fichas, cal, elo, _ = entorno
    perm = np.random.default_rng(3).permutation(len(cal))
    cal2 = cal[perm]
    pre2 = precalcular(liga, fichas, cal2, elo, FOCO, usar_cache=False)
    a = _correr(liga, entorno, semilla=21)
    b = _correr(liga, entorno, semilla=22, cal=cal2, pre=pre2)
    for x, y in ((a.puntos.ravel(), b.puntos.ravel()), (a.posicion.ravel(), b.posicion.ravel())):
        assert ks_2samp(x, y).pvalue > 0.01
    ee = np.hypot(a.resumen["puntos_mc"]["ee"], b.resumen["puntos_mc"]["ee"])
    assert abs(a.puntos.mean() - b.puntos.mean()) < 3 * ee


def test_TT2_exactos_contra_montecarlo(liga, entorno):
    r = _correr(liga, entorno, R=20, S=400)
    m = r.puntos.mean(1)
    ee = r.puntos.std(1, ddof=1) / np.sqrt(r.puntos.shape[1])
    z = (m - r.puntos_exactos) / ee
    assert np.mean(np.abs(z) < 3) >= 0.95  # cada réplica dentro de 3 EE (tolerancia binomial)
    assert abs((m - r.puntos_exactos).mean()) < 3 * np.sqrt((ee**2).sum()) / len(m)


def test_TT3_desempates():
    # 4 equipos: A y B empatan en puntos y DG; A tiene más GF. C y D empatan en todo -> sorteo.
    pts = np.array([[10, 10, 7, 7.0]])
    gf = np.array([[8, 6, 5, 5.0]])
    gc = np.array([[4, 2, 5, 5.0]])
    lugar = tabla.posiciones(pts, gf, gc, np.array([[0.1, 0.9, 0.2, 0.8]]))
    assert lugar.tolist() == [[1, 2, 4, 3]]
    # la diferencia de goles va antes que los goles a favor
    lugar = tabla.posiciones(
        np.array([[5, 5.0]]), np.array([[9, 3.0]]), np.array([[9, 1.0]]), np.zeros((1, 2))
    )
    assert lugar.tolist() == [[2, 1]]
    # puntos mandan
    lugar = tabla.posiciones(
        np.array([[4, 5.0]]), np.array([[20, 0.0]]), np.array([[0, 9.0]]), np.zeros((1, 2))
    )
    assert lugar.tolist() == [[2, 1]]


def test_TT4_suma_de_puntos(liga, entorno):
    r = _correr(liga, entorno, R=10, S=20)
    total = r.interno["suma_puntos_liga"].ravel()
    v, e = r.interno["victorias"], r.interno["empates"]
    assert np.array_equal(total, 3 * v + 2 * e)


def test_TT5_numeros_comunes(liga, entorno):
    a = _correr(liga, entorno, semilla=8)
    b = _correr(liga, entorno, semilla=8)
    c = comparar(a, b)
    assert np.all(c.delta == 0) and c.veredicto == "igual"
    assert np.array_equal(a.puntos, b.puntos)


def test_TT6_error_reportado(liga, entorno):
    medias, ees, pl, pl_ee = [], [], [], []
    for k in range(30):
        r = _correr(liga, entorno, R=40, S=30, semilla=1000 + k)
        medias.append(r.resumen["puntos_esperados"])
        ees.append(r.resumen["puntos_esperados_ee"])
        pl.append(r.resumen["p_liguilla"]["media"])
        pl_ee.append(r.resumen["p_liguilla"]["ee"])
    for est, rep in ((medias, ees), (pl, pl_ee)):
        cociente = np.mean(rep) / np.std(est, ddof=1)
        print(f"EE reportado / DE observada = {cociente:.3f}")
        assert 0.8 <= cociente <= 1.2
