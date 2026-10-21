"""Paso inicial P⁰ de la mezcla (D-047; ADR-v2-29 de dtcoach, estudio/src/dtcoach/mezcla.py).

Sintéticas: corren en la nube y en cualquier equipo. La prueba "requiere datos" reproduce `mezcla_K3.npz` de dtcoach con sus
transiciones reales y se salta si no hay datos (variable de entorno SIMDT_DATOS_DTCOACH = la carpeta `data/` de dtcoach).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from simdt.estimacion import mezcla as mz
from simdt.estimacion.mezcla import NS, NT
from simdt.modelos.cadena import visitas_por_tipo

K = 2


def _cadena(rng, masa_abs: float, mitad: int) -> np.ndarray:
    dentro = np.arange(NT) // 10 == mitad
    base = rng.dirichlet(np.ones(NT) * 0.6, size=NT) * (0.25 + 0.75 * dentro)[None, :]
    P = np.zeros((NT, NS))
    P[:, :NT] = base / base.sum(1, keepdims=True) * (1 - masa_abs)
    P[:, NT:] = rng.dirichlet(np.ones(NS - NT) * 0.8, size=NT) * masa_abs
    return P


@pytest.fixture(scope="module")
def mundo():
    """Dos tipos con estructura de bloques; el primer paso (P0) absorbe mucho más que el resto (P)."""
    rng = np.random.default_rng(11)
    P = np.stack([_cadena(rng, 0.40, 0), _cadena(rng, 0.12, 1)])
    P0 = np.stack([_cadena(rng, 0.60, 0), _cadena(rng, 0.30, 1)])
    mu = np.stack(
        [
            rng.dirichlet(np.ones(NT) * 0.5) * (0.1 + 0.9 * (np.arange(NT) // 10 == k))
            for k in range(K)
        ]
    )
    mu /= mu.sum(1, keepdims=True)
    pi = np.array([0.45, 0.55])
    n = 30_000
    sid, de, ha, ini, tipo = [], [], [], [], []
    for s in range(n):
        k = rng.choice(K, p=pi)
        z = rng.choice(NT, p=mu[k])
        ini.append(z)
        tipo.append(k)
        M = P0[k]
        while True:
            h = rng.choice(NS, p=M[z])
            sid.append(s), de.append(z), ha.append(h)
            if h >= NT:
                break
            z, M = h, P[k]
    sid, de, ha, ini, tipo = map(np.array, (sid, de, ha, ini, tipo))
    d = mz.datos_desde(sid, de, ha, n, ini)
    return {
        "P": P,
        "P0": P0,
        "mu": mu,
        "pi": pi,
        "sid": sid,
        "de": de,
        "ha": ha,
        "ini": ini,
        "tipo": tipo,
        "d": d,
        "verdad": mz.Mezcla(pi, mu, P, 5.0, 1.0, [], P0),
    }


def test_datos_desde_separa_el_primer_paso(mundo):
    d = mundo["d"]
    assert d.S0 is not None and d.S0.shape == d.S.shape
    assert np.allclose(np.asarray(d.S0.sum(1)).ravel(), 1.0)  # una sola transición por secuencia
    assert np.allclose((d.S1 + d.S0).toarray()[:50], d.S.toarray()[:50])
    primeras = np.unique(mundo["sid"], return_index=True)[1]
    celdas = mundo["de"][primeras] * NS + mundo["ha"][primeras]
    assert np.array_equal(np.asarray(d.S0.argmax(1)).ravel(), celdas)
    assert np.array_equal(d.sub(np.arange(10)).S0.toarray(), d.S0[:10].toarray())


def test_formulas_con_P0_coinciden_con_la_simulacion(mundo):
    """E[T] = μ(1 + Q0 t) y P(absorción) = μ(R0 + Q0 B): contra los promedios de las secuencias simuladas."""
    v, d, tipo, sid = mundo["verdad"], mundo["d"], mundo["tipo"], mundo["sid"]
    fin = mundo["ha"][
        np.r_[np.flatnonzero(np.diff(sid)), len(sid) - 1]
    ]  # absorbente final de cada secuencia
    for k in range(K):
        i = v.inicio(k)
        assert abs(i["E_T"] - d.largo[tipo == k].mean()) < 0.08
        assert abs(i["B"][:2].sum() - np.isin(fin[tipo == k], [20, 21]).mean()) < 0.02
    # sin P0 la misma cadena daría otro E[T]: la fórmula antigua ya no vale
    sin = mz.Mezcla(v.pi, v.mu, v.P, 5.0, 1.0, [], None)
    assert abs(sin.inicio(0)["E_T"] - v.inicio(0)["E_T"]) > 0.3


def test_visitas_M5_con_P0(mundo):
    """v^k = μ^k + μ^k Q^{0,k} N^k contra las visitas por zona contadas en las secuencias simuladas (y sin P0 no coincide)."""
    sid, de, ha, ini, tipo = (mundo[x] for x in ("sid", "de", "ha", "ini", "tipo"))
    v = visitas_por_tipo(mundo["P"], mundo["mu"], mundo["P0"])
    for k in range(K):
        sec = np.flatnonzero(tipo == k)
        emp = np.bincount(ini[sec], minlength=NT).astype(float)  # el estado inicial se visita 1 vez
        m = np.isin(sid, sec) & (ha < NT)
        emp += np.bincount(ha[m], minlength=NT)  # y cada destino transitorio
        emp /= len(sec)
        assert np.max(np.abs(v[k] - emp)) < 0.05
    assert np.max(np.abs(visitas_por_tipo(mundo["P"], mundo["mu"]) - v)) > 0.05


def test_EM_con_P0_recupera_el_vocabulario(mundo):
    m = mz.ajustar(mundo["d"], K, 5.0, 1.0, 1000, 1e-7, seed=1)
    assert m.paso_inicial and m.P0.shape == (K, NT, NS)
    r, v = mz.resumen(m), mz.resumen(mundo["verdad"])
    for k in range(K):
        assert abs(r[k]["pi"] - v[k]["pi"]) < 0.02
        assert abs(r[k]["E_T"] - v[k]["E_T"]) < 0.15
        assert abs(r[k]["p_remate"] - v[k]["p_remate"]) < 0.03
    assert np.all(np.diff(m.objetivo) > -1e-9 * abs(m.objetivo[0]))  # el EM no decrece
    # el primer paso absorbe más que los siguientes (la señal que P⁰ debe capturar), ponderando por dónde empieza el tipo
    w0 = m.mu[0] @ m.P0[0][:, NT:].sum(1)
    w1 = m.mu[0] @ m.P[0][:, NT:].sum(1)
    assert w0 > w1 + 0.05


def test_sin_P0_se_equivoca_donde_P0_acierta(mundo):
    """La razón de ADR-v2-29: sin P0 se subestima P(T = 1); con P0 el modelo la reproduce."""
    d = mundo["d"]
    emp = float((d.largo == 1).mean())

    def p1(m):
        return float(sum(m.pi[k] * (m.mu[k] @ m.P0e(k)[:, NT:].sum(1)) for k in range(m.K)))

    con = mz.ajustar(d, K, 5.0, 1.0, 1000, 1e-7, seed=1)
    sin = mz.ajustar(d, K, 5.0, 1.0, 1000, 1e-7, seed=1, paso_inicial=False)
    assert sin.P0 is None and not sin.paso_inicial
    assert abs(p1(con) - emp) < 0.01
    assert abs(p1(sin) - emp) > 0.05
    assert con.objetivo[-1] > sin.objetivo[-1]


def test_loglik_usa_P0_en_el_primer_paso():
    rng = np.random.default_rng(3)
    P = np.stack([_cadena(rng, 0.3, 0), _cadena(rng, 0.2, 1)])
    P0 = np.stack([_cadena(rng, 0.5, 0), _cadena(rng, 0.4, 1)])
    mu = rng.dirichlet(np.ones(NT), size=K)
    sid = np.array([0, 0, 0, 1])
    de = np.array([3, 5, 7, 12])
    ha = np.array([5, 7, 21, 22])
    d = mz.datos_desde(sid, de, ha, 2, np.array([3, 12]))
    L = mz._loglik_tipos(d, P, mu, P0)
    for k in range(K):
        esperado0 = (
            np.log(mu[k][3]) + np.log(P0[k][3, 5]) + np.log(P[k][5, 7]) + np.log(P[k][7, 21])
        )
        assert np.isclose(L[0, k], esperado0)
        assert np.isclose(
            L[1, k], np.log(mu[k][12]) + np.log(P0[k][12, 22])
        )  # secuencia de una acción: solo P0
    sin = mz._loglik_tipos(d, P, mu, None)
    assert not np.allclose(sin, L)


def test_sin_efecto_de_primer_paso_ambos_modelos_coinciden():
    """Si los datos no tienen efecto de primer toque (P0 = P), con y sin P0 salen vocabularios parecidos."""
    rng = np.random.default_rng(5)
    P = np.stack([_cadena(rng, 0.40, 0), _cadena(rng, 0.12, 1)])
    mu = np.stack(
        [
            rng.dirichlet(np.ones(NT) * 0.5) * (0.1 + 0.9 * (np.arange(NT) // 10 == k))
            for k in range(K)
        ]
    )
    mu /= mu.sum(1, keepdims=True)
    n = 12_000
    sid, de, ha, ini = [], [], [], []
    for s in range(n):
        k = rng.choice(K, p=[0.45, 0.55])
        z = rng.choice(NT, p=mu[k])
        ini.append(z)
        while True:
            h = rng.choice(NS, p=P[k][z])
            sid.append(s), de.append(z), ha.append(h)
            if h >= NT:
                break
            z = h
    d = mz.datos_desde(*map(np.array, (sid, de, ha)), n, np.array(ini))
    a = mz.resumen(mz.ajustar(d, K, 5.0, 1.0, 1000, 1e-7, seed=2))
    b = mz.resumen(mz.ajustar(d, K, 5.0, 1.0, 1000, 1e-7, seed=2, paso_inicial=False))
    for k in range(K):
        assert abs(a[k]["E_T"] - b[k]["E_T"]) < 0.4
        assert abs(a[k]["p_remate"] - b[k]["p_remate"]) < 0.04


def test_artefactos_sin_P0_siguen_cargando(tmp_path):
    """Artefactos anteriores a D-047 (sin P0): M5 usa P en el primer paso y no falla. La prueba arma SUS PROPIOS artefactos de ejemplo sin P⁰
    (copia de los versionados con P0 quitado de cadenas.npz), así que pasa igual con los de la v1 que con los de E (que sí traen P0)."""
    import shutil

    from simdt import artefactos, config
    from simdt.modelos.cadena import mapa_equipo

    if not (config.ARTEFACTOS / "cadenas.npz").exists():
        pytest.skip("sin artefactos")
    shutil.copytree(config.ARTEFACTOS, tmp_path / "art")
    z = np.load(tmp_path / "art" / "cadenas.npz")
    np.savez(tmp_path / "art" / "cadenas.npz", **{k: z[k] for k in z.files if k != "P0"})
    p = artefactos.cargar(tmp_path / "art")
    assert p.liga.P0_cadenas is None
    mapa = mapa_equipo(p.liga.P_cadenas, p.liga.mu_cadenas, np.ones(3), p.liga.P0_cadenas)
    assert mapa.shape == (NT,) and np.all(mapa >= 0)


def test_artefactos_con_P0_cargan_y_usan_P0():
    """Con los artefactos versionados (si traen P0, como los de E): el primer paso usa P0 y el mapa sigue siendo válido."""
    from simdt import artefactos, config
    from simdt.modelos.cadena import mapa_equipo

    if not (config.ARTEFACTOS / "cadenas.npz").exists():
        pytest.skip("sin artefactos")
    p = artefactos.cargar()
    if p.liga.P0_cadenas is None:
        pytest.skip("los artefactos versionados no traen P0 (v1)")
    mapa = mapa_equipo(p.liga.P_cadenas, p.liga.mu_cadenas, np.ones(3), p.liga.P0_cadenas)
    assert mapa.shape == (NT,) and np.all(mapa >= 0)


def test_liga_serializa_P0():
    from simdt.datos.sintetico import liga_sintetica

    L = liga_sintetica()
    L.P0_cadenas = L.P_cadenas.copy()
    L2 = type(L).de_dict(L.a_dict())
    assert np.allclose(L2.P0_cadenas, L.P_cadenas)


@pytest.mark.requiere_datos
@pytest.mark.lento
def test_reproduce_mezcla_K3_de_dtcoach():
    """Requiere datos: con las transiciones de dtcoach (4 absorbentes) el EM con P⁰ reproduce `mezcla_K3.npz`
    (π, E[T] y P(remate) con tolerancia 0.005; E[T] con 0.05).

    1.ª corrida real (script 2b, 2026-10-16): FALLÓ (π 0.314 contra 0.357) con las 467,327 secuencias de hoy, `lam` = 100 y la
    semilla de simdt (20261008). Esta versión elimina tres diferencias con la fuente que no son del EM: usa solo las secuencias
    publicadas (las `seq_uid` de `responsabilidades_K3.parquet`, 461,454), el `lam` y el `a0` guardados en el npz y la semilla de
    dtcoach (`seed: 20260924`, config/default.yaml). Si aun así falla, D-047 sigue incompleta (ver D-048)."""
    raiz = os.environ.get("SIMDT_DATOS_DTCOACH")
    if not raiz:
        pytest.skip("requiere datos: define SIMDT_DATOS_DTCOACH con la carpeta data/ de dtcoach")
    base = Path(raiz) / "processed" / "archivo_4abs"
    npz, trans = base / "mezcla" / "mezcla_K3.npz", base / "transitions.parquet"
    if not (npz.exists() and trans.exists()):
        pytest.skip(f"requiere datos: faltan {npz} o {trans}")
    import pandas as pd

    t = pd.read_parquet(
        trans,
        columns=[
            c
            for c in (
                "seq_uid",
                "poss_uid",
                "event_index",
                "from_state",
                "to_state",
                "is_absorbing",
            )
            if c in __import__("pyarrow.parquet", fromlist=["x"]).read_schema(trans).names
        ],
    )
    if "seq_uid" not in t.columns:
        t = t.sort_values(["poss_uid", "event_index"])
        a = t["is_absorbing"].astype(int)
        t["seq_uid"] = (
            t["poss_uid"].astype(str) + "_s" + (a.groupby(t["poss_uid"]).cumsum() - a).astype(str)
        )
    resp = base / "mezcla" / "responsabilidades_K3.parquet"
    if resp.exists():  # la muestra con la que se ajustó la mezcla publicada
        publicadas = set(pd.read_parquet(resp, columns=["seq_uid"])["seq_uid"])
        t = t[t["seq_uid"].isin(publicadas)]
    t = t.sort_values(["seq_uid", "event_index"], kind="stable")
    sid, uniq = pd.factorize(t["seq_uid"], sort=False)
    primero = t.groupby(sid, sort=True)["from_state"].first().to_numpy().astype(np.int64)
    d = mz.datos_desde(
        sid.astype(np.int64),
        t["from_state"].to_numpy().astype(np.int64),
        t["to_state"].to_numpy().astype(np.int64),
        len(uniq),
        primero,
    )
    z = np.load(npz)
    m = mz.ajustar(d, 3, float(z["lam"]), float(z["a0"]), 1000, 1e-7, seed=20260924, n_corto=25)
    fuente = mz.Mezcla(
        z["pi"],
        z["mu"],
        np.pad(z["P"], ((0, 0), (0, 0), (0, NS - z["P"].shape[2]))),
        float(z["lam"]),
        float(z["a0"]),
        [],
        np.pad(z["P0"], ((0, 0), (0, 0), (0, NS - z["P0"].shape[2]))),
    )
    fuente = mz.ordenar_por_largo(fuente)
    a, b = mz.resumen(m), mz.resumen(fuente)
    for k in range(3):
        assert abs(a[k]["pi"] - b[k]["pi"]) < 0.005
        assert abs(a[k]["p_remate"] - b[k]["p_remate"]) < 0.005
        assert abs(a[k]["E_T"] - b[k]["E_T"]) < 0.05


def test_artefactos_roundtrip_con_P0(tmp_path):
    """escribir → cargar conserva P0 en cadenas.npz y en la liga (los artefactos nuevos lo traerán tras recalibrar)."""
    from simdt import artefactos

    p = artefactos.cargar()
    P, mu = p.cadenas[0], p.cadenas[1]
    P0 = np.clip(P * 0.9, 1e-9, None)
    P0 /= P0.sum(2, keepdims=True)
    artefactos.escribir(
        tmp_path, p.liga, p.piezas, p.meta, p.presets, p.pares, (P, mu, P0), p.fase_a
    )
    q = artefactos.cargar(tmp_path)
    assert q.liga.P0_cadenas is not None and np.allclose(q.liga.P0_cadenas, P0)
    assert q.cadenas[2] is not None and np.allclose(q.cadenas[2], P0)
    assert np.allclose(q.liga.P_cadenas, P)
