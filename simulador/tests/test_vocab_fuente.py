"""Vocabulario FIJO de dtcoach (`--vocab-dtcoach`, D-048): carga de `mezcla_K3.npz`, r_sk y emparejamiento de secuencias.

Sintéticas: corren en la nube y en cualquier equipo. La prueba "requiere datos" comprueba con los datos reales que el vocabulario
de la calibración sale igual al de la fuente (tolerancia 1e-3) y que el emparejamiento con `responsabilidades_K3.parquet` es alto.
Variables de entorno: SIMDT_DATOS_DTCOACH (carpeta `data/` de dtcoach) y, opcional, SIMDT_DATOS_1767 (raíz con cache_events/ de simdt).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from simdt import config
from simdt.datos import repo
from simdt.estimacion import mezcla as mz
from simdt.estimacion import vocab_fuente as vf
from simdt.estimacion.mezcla import NS, NT

K = 3
PP = ["Regular Play", "From Throw In", "From Counter", "From Corner"]


def _filas(rng, masa, n_abs=NS - NT):
    base = rng.dirichlet(np.ones(NT) * 0.7, size=NT)
    P = np.zeros((NT, NS))
    P[:, :NT] = base * (1 - masa)
    ab = rng.dirichlet(np.ones(n_abs) * 0.8, size=NT) * masa
    P[:, NT : NT + n_abs] = ab
    return P


@pytest.fixture(scope="module")
def mundo():
    """Mezcla de 3 tipos (con P0) ordenada por E[T], y 40 partidos × 2 equipos con secuencias simuladas de ella."""
    rng = np.random.default_rng(5)
    P = np.stack([_filas(rng, m) for m in (0.45, 0.25, 0.10)])
    P0 = np.stack([_filas(rng, m) for m in (0.60, 0.40, 0.25)])
    mu = rng.dirichlet(np.ones(NT) * 0.8, size=K)
    pi = np.array([0.36, 0.26, 0.38])
    m = mz.Mezcla(pi, mu, P, 100.0, 1.0, [], P0)
    assert np.all(np.diff(mz.largo_esperado(m)) > 0)
    filas, trans, sid = [], [], 0
    for mid in range(1000, 1040):
        for eq in ("Alfa", "Beta"):
            for _ in range(int(rng.integers(120, 160))):
                k = rng.choice(K, p=pi)
                z = int(rng.choice(NT, p=mu[k]))
                ini, M, largo = z, P0[k], 0
                while True:
                    h = int(rng.choice(NS, p=M[z]))
                    trans.append((sid, z, h))
                    largo += 1
                    if h >= NT:
                        break
                    z, M = h, P[k]
                filas.append(
                    {
                        "sid": sid,
                        "match_id": mid,
                        "equipo": eq,
                        "inicio": ini,
                        "largo": largo,
                        "pp": PP[0] if k else PP[int(rng.integers(0, 4))],
                        "u": -1 if rng.random() > 0.05 else 0,
                        "tipo": k,
                    }
                )
                sid += 1
    s = pd.DataFrame(filas)
    t = pd.DataFrame(trans, columns=["sid", "desde", "hacia"])
    return {"m": m, "s": s, "t": t}


def _escribir(carpeta: Path, m: mz.Mezcla, mundo, n_abs=5, parquet=True, alterar=None):
    carpeta.mkdir(parents=True, exist_ok=True)
    P, P0 = m.P[:, :, : NT + n_abs], m.P0[:, :, : NT + n_abs]
    if n_abs == 4:  # la fuente de 4 absorbentes: INTERRUPCIÓN contaba como PÉRDIDA
        P, P0 = P.copy(), P0.copy()
        P[:, :, NT + 2] += m.P[:, :, NT + 4]
        P0[:, :, NT + 2] += m.P0[:, :, NT + 4]
    np.savez(
        carpeta / "mezcla_K3.npz",
        pi=m.pi,
        mu=m.mu,
        P=P,
        P0=P0,
        lam=m.lam,
        a0=m.a0,
        objetivo=np.array([0.0]),
    )
    if parquet:
        s = mundo["s"]
        d = mz.datos_desde(
            mundo["t"].sid.to_numpy(),
            mundo["t"].desde.to_numpy(),
            mundo["t"].hacia.to_numpy(),
            len(s),
            s.inicio.to_numpy(),
        )
        r = mz.responsabilidades(m, d)
        df = pd.DataFrame(
            {
                "seq_uid": [
                    f"{a}_{i // 3 + 1}_s{i % 3}" for a, i in zip(s.match_id, range(len(s)))
                ],
                "match_id": s.match_id,
                "team": s.equipo,
                "play_pattern": s.pp,
                "largo": s.largo,
                **{f"r_{k + 1}": r[:, k] for k in range(K)},
            }
        )
        if alterar:
            df = alterar(df)
        df.to_parquet(carpeta / "responsabilidades_K3.parquet")


def test_cargar_5_absorbentes_y_4_absorbentes(mundo, tmp_path):
    m = mundo["m"]
    _escribir(tmp_path / "a5", m, mundo, 5, parquet=False)
    _escribir(tmp_path / "a4", m, mundo, 4, parquet=False)
    m5, n5 = vf.cargar_mezcla(tmp_path / "a5" / "mezcla_K3.npz")
    m4, n4 = vf.cargar_mezcla(tmp_path / "a4" / "mezcla_K3.npz")
    assert (n5, n4) == (5, 4) and m5.P.shape == m4.P.shape == (K, NT, NS)
    assert np.allclose(m5.P, m.P) and np.allclose(m5.P0, m.P0) and m5.lam == 100.0 and m5.a0 == 1.0
    assert (
        np.all(m4.P[:, :, NS - 1] == 0)
        and np.allclose(m4.P.sum(2), 1)
        and np.allclose(m4.P0.sum(2), 1)
    )
    assert vf.buscar(tmp_path / "a5")[0] == tmp_path / "a5" / "mezcla_K3.npz"
    (tmp_path / "p" / "mezcla").mkdir(parents=True)
    (tmp_path / "a5" / "mezcla_K3.npz").rename(tmp_path / "p" / "mezcla" / "mezcla_K3.npz")
    assert vf.buscar(tmp_path / "p")[1] is None


def test_malla_distinta_se_rechaza(tmp_path):
    np.savez(
        tmp_path / "mezcla_K3.npz",
        pi=np.ones(3) / 3,
        mu=np.ones((3, 96)) / 96,
        P=np.ones((3, 96, 100)) / 100,
        lam=1.0,
        a0=1.0,
    )
    with pytest.raises(ValueError, match="transitorios"):
        vf.cargar_mezcla(tmp_path / "mezcla_K3.npz")


def test_emparejar_con_inserciones_y_borrados(mundo, tmp_path):
    s = mundo["s"]
    _escribir(tmp_path, mundo["m"], mundo)
    resp = pd.read_parquet(tmp_path / "responsabilidades_K3.parquet")
    quitar = np.sort(
        np.random.default_rng(1).choice(len(resp), 40, replace=False)
    )  # 40 de la fuente que simdt no tiene (~0.1 %)
    resp2 = resp.drop(index=quitar).reset_index(drop=True)
    s2 = s.drop(
        index=np.sort(np.random.default_rng(2).choice(len(s), 40, replace=False))
    ).reset_index(drop=True)  # y 40 de simdt que la fuente no tiene
    par, est = vf.emparejar(s2, resp2)
    assert est["pct_emparejadas"] > 0.99 and est["emparejadas"] == int((par >= 0).sum())
    ok = par >= 0
    assert np.array_equal(resp2.largo.to_numpy()[par[ok]], s2.largo.to_numpy()[ok])
    assert est["sin_par_simdt"] + est["emparejadas"] == len(s2) and est["sin_par_fuente"] + est[
        "emparejadas"
    ] == len(resp2)


def test_r_del_parquet_en_las_emparejadas_y_del_modelo_en_el_resto(mundo, tmp_path):
    s, t = mundo["s"], mundo["t"]
    _escribir(tmp_path, mundo["m"], mundo)
    abierto = np.flatnonzero(s.u.to_numpy() < 0)
    m, r, info = vf.aplicar(tmp_path, s, t, abierto, "parquet", verbose=False)
    assert info["modo_r_usado"] == "parquet" and info["emparejamiento"]["pct_emparejadas"] == 1.0
    assert (
        info["r_fuente_vs_modelo"]["acuerdo_tipo"] == 1.0
        and info["r_fuente_vs_modelo"]["dif_abs_media"] < 1e-9
    )
    assert r.shape == (len(abierto), K) and np.allclose(r.sum(1), 1)
    m_m, r_m, info_m = vf.aplicar(tmp_path, s, t, abierto, "modelo", verbose=False)
    assert info_m["modo_r_usado"] == "modelo" and np.allclose(r, r_m)
    assert (
        np.allclose(m.P, mundo["m"].P)
        and np.allclose(m.P0, mundo["m"].P0)
        and np.allclose(m.pi, mundo["m"].pi)
    )
    json.dumps(info)  # va a meta.json: sin tipos de numpy


def test_si_las_etiquetas_no_coinciden_se_usa_el_modelo(mundo, tmp_path):
    s, t = mundo["s"], mundo["t"]

    def permutar(df):
        df = df.copy()
        df[["r_1", "r_2", "r_3"]] = df[
            ["r_3", "r_1", "r_2"]
        ].to_numpy()  # columnas rotadas: otra etiqueta por tipo
        return df

    _escribir(tmp_path, mundo["m"], mundo, alterar=permutar)
    abierto = np.flatnonzero(s.u.to_numpy() < 0)
    _, r, info = vf.aplicar(tmp_path, s, t, abierto, "parquet", verbose=False)
    assert info["modo_r_usado"] == "modelo" and "modelo" in info["parquet"]
    _, r_m, _ = vf.aplicar(tmp_path, s, t, abierto, "modelo", verbose=False)
    assert np.allclose(r, r_m)


def test_si_se_empareja_poco_se_usa_el_modelo(mundo, tmp_path):
    s, t = mundo["s"], mundo["t"]
    _escribir(
        tmp_path,
        mundo["m"],
        mundo,
        alterar=lambda df: df.assign(play_pattern="Otro", largo=df.largo + 7),
    )
    abierto = np.flatnonzero(s.u.to_numpy() < 0)
    _, _, info = vf.aplicar(tmp_path, s, t, abierto, "parquet", verbose=False)
    assert (
        info["emparejamiento"]["pct_emparejadas"] < vf.UMBRAL_EMPAREJADO
        and info["modo_r_usado"] == "modelo"
    )


def test_cuatro_absorbentes_pliega_interrupcion_en_perdida(mundo, tmp_path):
    s, t = mundo["s"], mundo["t"]
    _escribir(tmp_path, mundo["m"], mundo, 4, parquet=False)
    abierto = np.flatnonzero(s.u.to_numpy() < 0)
    _, r, info = vf.aplicar(tmp_path, s, t, abierto, "modelo", verbose=False)
    assert info["n_absorbentes"] == 4 and np.isfinite(r).all() and np.allclose(r.sum(1), 1)
    # sin plegar, una secuencia que termina en INTERRUPCIÓN tendría probabilidad 0 en todos los tipos
    assert (t.hacia == NS - 1).any()


def test_ajustar_mezcla_con_vocab_no_reajusta(mundo, tmp_path, monkeypatch):
    s, t = mundo["s"], mundo["t"]
    _escribir(tmp_path, mundo["m"], mundo)

    def boom(*a, **k):
        raise AssertionError("con --vocab-dtcoach no se debe ajustar el EM")

    monkeypatch.setattr(mz, "ajustar", boom)
    ext = {"secuencias": s, "transiciones": t}
    m, abierto, r = repo.ajustar_mezcla(ext, verbose=False, vocab=tmp_path)
    assert np.allclose(m.pi, mundo["m"].pi) and len(abierto) == len(r) == int((s.u < 0).sum())
    assert ext["vocab_dtcoach"]["modo_r_usado"] == "parquet"


def test_cli_ignora_vocab_con_sintetico(capsys, tmp_path, monkeypatch):
    from simdt import calibrar

    monkeypatch.setattr(
        calibrar, "preparar_sintetico", lambda: (_ for _ in ()).throw(RuntimeError("paro aquí"))
    )
    with pytest.raises(RuntimeError, match="paro aquí"):
        calibrar.main(
            ["--sintetico", "--vocab-dtcoach", str(tmp_path), "--salida", str(tmp_path / "x")]
        )
    assert "se ignora" in capsys.readouterr().err


@pytest.mark.requiere_datos
@pytest.mark.lento
def test_vocabulario_de_la_calibracion_igual_al_de_la_fuente_con_datos():
    """Con los datos reales: la mezcla que usa la calibración es la de la fuente (tol 1e-3) y el emparejamiento es alto."""
    raiz = os.environ.get("SIMDT_DATOS_DTCOACH")
    if not raiz:
        pytest.skip("requiere datos: define SIMDT_DATOS_DTCOACH con la carpeta data/ de dtcoach")
    carpeta = Path(raiz) / "processed" / "mezcla"
    if not (carpeta / "mezcla_K3.npz").exists():
        pytest.skip(f"requiere datos: falta {carpeta / 'mezcla_K3.npz'}")
    cache = config.cache_dir() / "extraccion.pkl"
    datos = os.environ.get("SIMDT_DATOS_1767")
    if not cache.exists() and not datos:
        pytest.skip(
            "requiere datos: no hay _cache/extraccion.pkl; define SIMDT_DATOS_1767 con la raíz de simdt (cache_events/ + matches_*.json)"
        )
    ext = repo.extraer(raiz=Path(datos) if datos else None, verbose=False)
    m, abierto, r = repo.ajustar_mezcla(ext, verbose=False, vocab=carpeta)
    fuente, _ = vf.cargar_mezcla(carpeta / "mezcla_K3.npz")
    a, b = mz.resumen(m), mz.resumen(fuente)
    for k in range(K):
        for c in ("pi", "E_T", "p_remate"):
            assert abs(a[k][c] - b[k][c]) < 1e-3
    info = ext["vocab_dtcoach"]
    if "emparejamiento" in info:
        assert info["emparejamiento"]["pct_emparejadas"] > vf.UMBRAL_EMPAREJADO
        assert info["r_fuente_vs_modelo"]["acuerdo_tipo"] > vf.UMBRAL_ARGMAX
    assert r.shape == (len(abierto), K)
