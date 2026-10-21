"""Atribución continua (D-051): el técnico mueve TODAS las componentes con la posterior completa de θ.

Dos mundos: (1) copia de los artefactos versionados con `atribucion: continua` (rápido; técnicos reales); (2) el sintético con verdad conocida
(usa el caché `fase_a_sintetico.pkl` de test_fase4: la primera vez en un equipo nuevo tarda lo de esa prueba).
"""

from __future__ import annotations

import json
import shutil
from itertools import combinations
from types import SimpleNamespace

import numpy as np
import pytest

from simdt import calibrar, config
from simdt.datos import sintetico
from simdt.estimacion import fase_a
from simdt.estimacion.fichas import PiezasFichas, armar, ficha_foco
from simdt.motor.comparar import comparar
from simdt.motor.temporada import muestras_replicas, precalcular, simular_temporada
from simdt.perillas import mapeo
from simdt.servicio import Simulador
from simdt.tipos import BLOQUES, COMPONENTES, Q, ResultadoTemporada, Tecnico
from simdt.validacion import sensibilidad

SIN_ARTEFACTOS = not (config.ARTEFACTOS / "meta.json").exists()
pytestmark = []


# ---------------------------------------------------------------- unitarias
def _piezas(atrib: str, decisiones: str):
    rng = np.random.default_rng(3)
    M = 50
    return PiezasFichas(
        [f"E{i}" for i in range(18)],
        rng.normal(size=(M, 18, Q)),
        rng.normal(size=(M, Q)),
        {},
        {},
        np.full((M, Q, 4), 0.1),
        rng.normal(size=(M, Q)),
        {n: decisiones for n in COMPONENTES},
        0,
        "Actual",
        atrib,
    )


def test_ficha_foco_continua_mueve_todas_las_componentes_aunque_la_regla_diga_plantel():
    th = np.random.default_rng(1).normal(size=Q)
    idx = np.arange(50)
    cont, binr = _piezas("continua", "plantel"), _piezas("binaria", "plantel")
    f_c, f_b = ficha_foco(cont, th, idx), ficha_foco(binr, th, idx)
    assert np.allclose(
        f_c, cont.base_foco + th + cont.sigma[:, :, 2] * cont.z_eps
    )  # todas: base + θ + ε
    assert np.allclose(f_b, binr.fichas[:, 0])  # binaria: el técnico no mueve nada
    assert not np.allclose(f_c, f_b)


def test_las_perillas_estan_activas_y_acotadas_por_los_tecnicos_plausibles():
    rng = np.random.default_rng(5)
    sig = np.abs(rng.normal(0.1, 0.03, size=(2000, Q)))
    lo, hi = mapeo.rango_plausible(sig)
    assert np.all(lo < 0) and np.all(hi > 0) and np.allclose(np.abs(lo), hi, rtol=0.3)
    esc = mapeo.Escalas(
        np.zeros(Q), np.median(sig, 0), {n: "plantel" for n in COMPONENTES}, "continua", lo, hi
    )
    assert all(mapeo.perillas_activas(esc).values()) and all(mapeo.perillas_inciertas(esc).values())
    liga = sintetico.liga_sintetica()
    th = mapeo.perillas_a_tecnico(
        {
            "balon_parado": 99,
            "cambios_momento": 1,
            "reaccion_marcador": "Mucho",
            "mezcla": (0.85, 0.05),
            "cambios_tipo": "Buscar el gol",
        },
        liga,
        esc,
    )
    tocadas = np.concatenate(
        [BLOQUES[b] for b in ("nu_co", "alpha", "s_marcador", "int_at", "gamma")]
    )
    assert np.all(th[tocadas] >= lo[tocadas] - 1e-12) and np.all(th[tocadas] <= hi[tocadas] + 1e-12)
    r = mapeo.rangos_perillas(esc, liga)  # los deslizadores cubren solo a los plausibles
    assert (
        5 <= r["mezcla"]["directa"][0] < r["mezcla"]["directa"][1] < 85
        and 1 < r["balon_parado"][0] < r["balon_parado"][1] < 99
    )
    esc_b = mapeo.Escalas(np.zeros(Q), np.median(sig, 0), {n: "plantel" for n in COMPONENTES})
    assert not any(mapeo.perillas_activas(esc_b).values()) and mapeo.rangos_perillas(esc_b, liga)[
        "balon_parado"
    ] == (1, 99)


def test_el_veredicto_no_se_sabe_puede_salir():
    rng = np.random.default_rng(2)

    def res(media, sd, R=400):
        p = media + sd * rng.normal(size=R)
        return ResultadoTemporada(
            p,
            np.tile(p[:, None], (1, 3)),
            np.ones((R, 3)),
            p,
            p,
            resumen={"p_liguilla": {"media": 0.5}},
        )

    c = comparar(
        res(30.0, 6.0), res(28.0, 6.0)
    )  # Δ ≈ 2 ± 8: ni "igual" (IC90 sale de ±3) ni distinto de 0
    assert c.veredicto == "no_se_sabe" and c.resumen["int95"][0] < 0 < c.resumen["int95"][1]
    ident = res(30.0, 6.0)
    assert comparar(ident, ident).veredicto == "igual"


# ---------------------------------------------------------------- artefactos versionados en modo continuo
@pytest.fixture(scope="module")
def sim_continuo(tmp_path_factory):
    if SIN_ARTEFACTOS:
        pytest.skip("sin artefactos")
    d = tmp_path_factory.mktemp("art_continuo")
    shutil.copytree(config.ARTEFACTOS, d, dirs_exist_ok=True)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    meta["atribucion"] = "continua"
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return Simulador(d)


def test_TT5_un_tecnico_consigo_mismo_da_delta_cero(sim_continuo):
    t = sim_continuo.tecnico_preset(sim_continuo.nombres_preset()[0])
    c, _, _ = sim_continuo.comparar(t, t, "rapido")
    assert np.all(c.delta == 0.0) and c.veredicto == "igual"


def test_la_incertidumbre_de_theta_entra_a_los_intervalos_de_delta(sim_continuo):
    # con R = 100 el ancho de UN intervalo es ruidoso: se compara el ancho medio de varios técnicos
    sim = sim_continuo
    prom = sim.tecnico_promedio()
    w = lambda c: c.resumen["int95"][1] - c.resumen["int95"][0]  # noqa: E731
    wp, wm = [], []
    for n in sim.nombres_preset()[:4]:
        t = sim.tecnico_preset(n)
        wp.append(w(sim.comparar(t, prom, "rapido")[0]))
        wm.append(
            w(sim.comparar(Tecnico(t.nombre, t.theta.mean(0), observado=True), prom, "rapido")[0])
        )  # sin incertidumbre de θ
    assert np.mean(wp) > np.mean(wm) and min(wp) > 0


def test_el_efecto_de_un_tecnico_ya_no_es_cero_por_construccion(sim_continuo):
    sim = sim_continuo
    d = [
        sim.comparar(sim.tecnico_preset(n), sim.tecnico_promedio(), "rapido")[0].resumen["media"]
        for n in sim.nombres_preset()[:6]
    ]
    assert np.any(np.abs(d) > 1e-6)
    assert all(mapeo.perillas_activas(sim.p.escalas).values()) and sim.p.escalas.continua


def test_la_app_arranca_con_atribucion_continua(sim_continuo, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import streamlit as st

    monkeypatch.setattr(config, "ARTEFACTOS", sim_continuo.dir)
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=180)
    at.run()
    assert not at.exception
    assert len(at.sidebar.slider) >= 4 and not any(s.disabled for s in at.sidebar.slider)
    st.cache_resource.clear()


# ---------------------------------------------------------------- sintético con verdad conocida
@pytest.fixture(scope="module")
def mundo():
    tablas, v = sintetico.generar()
    res = fase_a.correr(
        tablas,
        P_cadenas=v.liga.P_cadenas,
        mu_cadenas=v.liga.mu_cadenas,
        cache="fase_a_sintetico.pkl",
        verbose=False,
    )
    _, ctx, _ = calibrar.preparar_sintetico()
    vig = calibrar._vigentes(tablas["partidos"], ctx["temp_obj"], ctx["equipos"])
    foco = config.cargar()["torneo"]["club_foco"]
    cand = [t for t in v.tecnicos if t in res.ix.tecnicos]
    pz = armar(
        res,
        ctx["equipos"],
        vig,
        ctx["temp_obj"],
        foco,
        M=300,
        semilla=7,
        tecnicos_guardar=cand,
        atribucion="continua",
    )
    tab = res.tabla()
    esc = mapeo.Escalas(
        tab.set_index("componente").loc[list(COMPONENTES), "b0"].to_numpy(),
        np.median(pz.sigma[:, :, 0], 0),
        res.decisiones,
        "continua",
    )
    esc.theta_lo, esc.theta_hi = mapeo.rango_plausible(pz.sigma[:, :, 0])
    sim = SimpleNamespace(
        p=SimpleNamespace(piezas=pz, liga=v.liga, escalas=esc),
        calendario=np.asarray(ctx["calendario"]),
        elo=np.asarray(ctx["elo"], float),
        foco=pz.foco,
    )
    return SimpleNamespace(res=res, v=v, pz=pz, sim=sim, esc=esc)


def test_sobol_vuelve_a_dar_perillas_con_efecto_en_el_sintetico(mundo):
    """Con atribución binaria, las componentes que la regla manda al plantel dejan perillas sin efecto; con la continua las perillas mueven puntos."""
    s = sensibilidad.evaluar(mundo.sim, N=128)
    assert max(r["ST"] for r in s["tabla"]) > 0.2
    # las perillas que sí mueven puntos (cómo ataca, qué obliga al rival, balón parado) tienen efecto; las de cambios y reacciones pueden no tenerlo
    assert not ({"mezcla", "rival", "balon_parado"} & set(s["solo_estilo"])), s["solo_estilo"]
    lim = sensibilidad.limites(mundo.esc, mundo.sim.p.liga)
    assert all(b > a for a, b in lim)


@pytest.mark.lento
def test_cobertura_de_delta_con_theta_conocido(mundo):
    """Pares de técnicos del sintético que nunca dirigieron al foco: el intervalo del 95 % de Δ contiene el Δ calculado con los θ verdaderos."""
    pz, v, sim = mundo.pz, mundo.v, mundo.sim
    foco = sim.p.piezas.equipos[pz.foco]
    tecs = [t for t in pz.theta_tec if t in v.tecnicos and (t, foco) not in mundo.res.ix.pares][:9]
    assert len(tecs) >= 6
    R, S = 80, 20
    idx = muestras_replicas(pz.fichas.shape[0], R, 20261008)
    pre = precalcular(sim.p.liga, pz.fichas, sim.calendario, sim.elo, pz.foco, indices=idx)
    sims = {}
    for t in tecs:
        ff = ficha_foco(pz, pz.theta_tec[t], idx, None)
        sims[t] = simular_temporada(
            sim.p.liga,
            pz.fichas,
            ff,
            sim.calendario,
            sim.elo,
            pz.foco,
            idx,
            S,
            20261008,
            pre,
            con_estilo=False,
        )
    verdad = sensibilidad.puntos_esperados(
        sim, np.array([v.theta[v.tecnicos.index(t)] for t in tecs])
    )
    dentro, total = 0, 0
    for (i, a), (j, b) in combinations(list(enumerate(tecs)), 2):
        c = comparar(sims[a], sims[b])
        lo, hi = c.resumen["int95"]
        dentro += lo <= verdad[i] - verdad[j] <= hi
        total += 1
    print(f"cobertura de Δ (95 %): {dentro}/{total}")
    assert dentro / total >= 0.75
