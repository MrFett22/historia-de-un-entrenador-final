"""Pruebas del motor de partido T-P1 a T-P7 (07_PRUEBAS.md)."""

import time

import numpy as np
from scipy.stats import poisson

from simdt.motor.partido import distribucion_partido, partido_lote, simular_eventos
from simdt.modelos.intensidad import intensidades_lote
from simdt.tipos import BLOQUES, Q


def _fichas(rng, n=1, escala=0.15):
    return rng.normal(size=(n, Q)) * escala


def test_TP1_poisson_independientes(liga, rng):
    zi, zj = _fichas(rng), _fichas(rng)
    zi[:, BLOQUES["s_marcador"]] = -1.0  # s = 0: π no depende del marcador
    zj[:, BLOQUES["s_marcador"]] = -1.0
    Ii = intensidades_lote(liga, zi, zj, 1.0, 30.0)
    Ij = intensidades_lote(liga, zj, zi, 0.0, -30.0)
    assert np.allclose(Ii.mu[..., 0], Ii.mu[..., 2])
    d = distribucion_partido(Ii.mu, Ij.mu, G=15, max_por_minuto=6)
    la, lb = Ii.mu[0, :, 1].sum(), Ij.mu[0, :, 1].sum()
    g = np.arange(16)
    ref = np.outer(poisson.pmf(g, la), poisson.pmf(g, lb))
    assert np.max(np.abs(d.P[0] - ref)) < 1e-10


def test_TP2_masa(liga, rng):
    # fichas realistas: desviación 0.15 por componente (≈ el doble de lo estimado con datos
    # reales); con 0.3 en las 32 componentes a la vez salen equipos de 8 goles por partido.
    zi, zj = _fichas(rng, 200, 0.15), _fichas(rng, 200, 0.15)
    d = partido_lote(liga, zi, zj, rng.integers(0, 2, 200), rng.normal(0, 150, 200))
    assert np.allclose(d.P.sum((1, 2)), 1 - d.masa_truncada, atol=1e-14)
    assert d.masa_truncada.max() < 1e-6


def test_TP3_eventos_contra_exacto(liga, rng):
    zi, zj = _fichas(rng), _fichas(rng)
    Ii = intensidades_lote(liga, zi, zj, 1.0, 50.0)
    Ij = intensidades_lote(liga, zj, zi, 0.0, -50.0)
    d = distribucion_partido(Ii.mu, Ij.mu)
    n = 100_000
    a, b = simular_eventos(Ii.mu[0], Ij.mu[0], n, rng)
    for p_hat, p in (((a > b).mean(), d.p_gana[0]), ((a == b).mean(), d.p_empata[0])):
        se = np.sqrt(p * (1 - p) / n)
        assert abs(p_hat - p) < 3 * se


def test_TP4_identidad_goles(liga, rng):
    zi, zj = _fichas(rng, 50), _fichas(rng, 50)
    d = partido_lote(liga, zi, zj, 1.0, 0.0)
    g = np.arange(d.P.shape[1])
    e_a = (d.P.sum(2) * g).sum(1)
    e_b = (d.P.sum(1) * g).sum(1)
    assert np.max(np.abs(e_a - d.eg_i)) < 1e-6
    assert np.max(np.abs(e_b - d.eg_j)) < 1e-6


def test_TP5_simetria(liga, rng):
    zi, zj = _fichas(rng, 5), _fichas(rng, 5)
    loc = np.array([1, 0, 1, 0, 1.0])
    de = rng.normal(0, 100, 5)
    d1 = partido_lote(liga, zi, zj, loc, de)
    d2 = partido_lote(liga, zj, zi, 1 - loc, -de)
    assert np.max(np.abs(d1.P - np.transpose(d2.P, (0, 2, 1)))) < 1e-14
    assert np.allclose(d1.xpts_i, d2.xpts_j)


def test_TP6_m1_m4_cierran_xg(sint_pequeno):
    from simdt.estimacion.liga import estimar_liga, xg_predicho_liga

    tablas, _ = sint_pequeno
    liga_est, diag = estimar_liga(tablas)
    pred = xg_predicho_liga(liga_est, tablas)
    assert abs(pred / diag["xg_total_obs"] - 1) < 0.01


def test_TP7_tiempo(liga, rng):
    n = 1000
    zi, zj = _fichas(rng, n), _fichas(rng, n)
    loc = rng.integers(0, 2, n).astype(float)
    de = rng.normal(0, 100, n)
    partido_lote(liga, zi[:10], zj[:10], loc[:10], de[:10])  # calentamiento
    medidas = []
    for _ in range(3):  # mejor de 3, como timeit (D-040): aísla la carga del equipo
        t0 = time.perf_counter()
        for i in range(0, n, 250):
            partido_lote(liga, zi[i : i + 250], zj[i : i + 250], loc[i : i + 250], de[i : i + 250])
        medidas.append((time.perf_counter() - t0) / n)
    por_partido = min(medidas)
    print(f"tiempo por partido: {por_partido * 1e3:.3f} ms")
    assert por_partido < 2e-3


def test_numba_igual_a_numpy(liga, rng):
    zi, zj = _fichas(rng, 20), _fichas(rng, 20)
    Ii = intensidades_lote(liga, zi, zj, 1.0, 40.0)
    Ij = intensidades_lote(liga, zj, zi, 0.0, -40.0)
    a = distribucion_partido(Ii.mu, Ij.mu, usar_numba=True)
    b = distribucion_partido(Ii.mu, Ij.mu, usar_numba=False)
    assert np.max(np.abs(a.P - b.P)) < 1e-12
    assert np.max(np.abs(a.ocupacion - b.ocupacion)) < 1e-12
