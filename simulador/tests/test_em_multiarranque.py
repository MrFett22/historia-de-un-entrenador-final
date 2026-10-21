"""Multiarranque del EM (D-049): nunca da una J peor que un solo arranque, es reproducible y llega al óptimo de la fuente con datos reales."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from simdt.estimacion import mezcla as mz
from simdt.estimacion import vocab_fuente as vf
from simdt.estimacion.mezcla import NS, NT

K = 3


def _cadena(rng, masa, bloque):
    dentro = (np.arange(NT) * 3 // NT) == bloque
    base = rng.dirichlet(np.ones(NT) * 0.5, size=NT) * (0.2 + 0.8 * dentro)[None, :]
    P = np.zeros((NT, NS))
    P[:, :NT] = base / base.sum(1, keepdims=True) * (1 - masa)
    P[:, NT:] = rng.dirichlet(np.ones(NS - NT) * 0.8, size=NT) * masa
    return P


@pytest.fixture(scope="module")
def datos():
    """Tres tipos solapados (los óptimos locales son fáciles de encontrar con K = 3), 6,000 secuencias."""
    rng = np.random.default_rng(3)
    P = np.stack([_cadena(rng, m, b) for b, m in enumerate((0.45, 0.25, 0.12))])
    P0 = np.stack([_cadena(rng, m, b) for b, m in enumerate((0.6, 0.4, 0.25))])
    mu = np.stack([rng.dirichlet(np.ones(NT) * 0.6) for _ in range(K)])
    pi = np.array([0.4, 0.3, 0.3])
    sid, de, ha, ini = [], [], [], []
    n = 6000
    for s in range(n):
        k = rng.choice(K, p=pi)
        z = int(rng.choice(NT, p=mu[k]))
        ini.append(z)
        M = P0[k]
        while True:
            h = int(rng.choice(NS, p=M[z]))
            sid.append(s), de.append(z), ha.append(h)
            if h >= NT:
                break
            z, M = h, P[k]
    return mz.datos_desde(np.array(sid), np.array(de), np.array(ha), n, np.array(ini))


def test_semillas_reproducibles_distintas_e_incluyen_la_de_la_fuente():
    s = mz.semillas_arranques(20261008, 8)
    assert len(s) == len(set(s)) == 8 and s[0] == 20261008 and s[1] == mz.SEMILLA_FUENTE
    assert s == mz.semillas_arranques(20261008, 8) and mz.semillas_arranques(20261008, 1) == [
        20261008
    ]
    assert (
        mz.semillas_arranques(mz.SEMILLA_FUENTE, 3)[0] == mz.SEMILLA_FUENTE
        and len(set(mz.semillas_arranques(mz.SEMILLA_FUENTE, 3))) == 3
    )


def test_el_multiarranque_nunca_da_una_J_peor_que_un_solo_arranque(datos):
    lam, a0 = 20.0, 1.0
    sem = mz.semillas_arranques(11, 4)
    m = mz.ajustar_multi(datos, K, lam, a0, 300, 1e-7, semillas=sem, n_corto=10)
    unicos = [
        mz.objetivo_final(mz.ajustar(datos, K, lam, a0, 300, 1e-7, s, 10), datos, lam, a0)
        for s in sem
    ]
    Jm = mz.objetivo_final(m, datos, lam, a0)
    assert (
        Jm >= max(unicos) - 1e-6 and Jm >= unicos[0] - 1e-6
    )  # nunca peor que el arranque de la semilla global
    d = m.diagnostico
    assert (
        d["semillas"] == sem
        and d["J_ganador"] == pytest.approx(Jm)
        and d["J_ganador"] == max(d["J"])
    )
    assert (
        np.allclose(d["J"], unicos)
        and min(d["dJ"]) == 0.0
        and d["semilla_ganadora"] == sem[int(np.argmax(unicos))]
    )
    assert d["n_en_el_optimo"] >= 1 and set(d["dispersion"]) == {"pi", "E_T", "p_remate"}
    assert all(d["dispersion_optimo"][c] <= d["dispersion"][c] + 1e-12 for c in d["dispersion"])


def test_un_arranque_es_igual_a_ajustar(datos):
    a = mz.ajustar_multi(datos, K, 20.0, 1.0, 300, 1e-7, seed=5, n_corto=10, n_arranques=1)
    b = mz.ajustar(datos, K, 20.0, 1.0, 300, 1e-7, 5, 10)
    assert np.array_equal(a.P, b.P) and np.array_equal(a.pi, b.pi) and a.diagnostico["ganador"] == 0


def test_en_paralelo_da_lo_mismo_que_en_serie(datos):
    sem = mz.semillas_arranques(7, 3)
    s = mz.ajustar_multi(datos, K, 20.0, 1.0, 300, 1e-7, semillas=sem, n_corto=10, n_jobs=1)
    p = mz.ajustar_multi(datos, K, 20.0, 1.0, 300, 1e-7, semillas=sem, n_corto=10, n_jobs=3)
    assert s.diagnostico["semilla_ganadora"] == p.diagnostico["semilla_ganadora"] and np.allclose(
        s.diagnostico["J"], p.diagnostico["J"]
    )
    assert np.allclose(s.P, p.P) and np.allclose(s.pi, p.pi)


@pytest.mark.requiere_datos
@pytest.mark.lento
def test_el_multiarranque_desde_la_semilla_de_simdt_llega_a_la_J_de_la_fuente():
    """Con las secuencias publicadas, `lam`/`a0` del npz y la semilla de simdt (20261008), el multiarranque llega a J ≥ J(fuente) − 1.
    Script 2c: con la semilla de simdt sola, ΔJ = −976 (óptimo local peor); con la de dtcoach, ΔJ = +1.7."""
    raiz = os.environ.get("SIMDT_DATOS_DTCOACH")
    if not raiz:
        pytest.skip("requiere datos: define SIMDT_DATOS_DTCOACH con la carpeta data/ de dtcoach")
    base = Path(raiz) / "processed" / "archivo_4abs"
    npz = base / "mezcla" / "mezcla_K3.npz"
    if not (npz.exists() and (base / "transitions.parquet").exists()):
        pytest.skip(f"requiere datos: faltan {npz} o {base / 'transitions.parquet'}")
    d, _, _ = vf.datos_publicados(base)
    z = np.load(npz)
    lam, a0 = float(z["lam"]), float(z["a0"])
    pad = ((0, 0), (0, 0), (0, NS - z["P"].shape[2]))
    fuente = mz.ordenar_por_largo(
        mz.Mezcla(z["pi"], z["mu"], np.pad(z["P"], pad), lam, a0, [], np.pad(z["P0"], pad))
    )
    J_fuente = mz.objetivo_final(fuente, d, lam, a0)
    m = mz.ajustar_multi(
        d, 3, lam, a0, 1000, 1e-7, seed=20261008, n_corto=25, n_arranques=3, n_jobs=3
    )
    assert m.diagnostico["J_ganador"] >= J_fuente - 1.0
    a, b = mz.resumen(m), mz.resumen(fuente)
    for k in range(3):
        assert (
            abs(a[k]["pi"] - b[k]["pi"]) < 0.005
            and abs(a[k]["p_remate"] - b[k]["p_remate"]) < 0.005
        )
