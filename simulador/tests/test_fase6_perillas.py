"""Pruebas de perillas T-M1 a T-M4 (07_PRUEBAS.md)."""

import numpy as np
import pytest

from simdt.estimacion.fichas import PiezasFichas, ficha_foco
from simdt.modelos.familias import mezcla
from simdt.perillas import mapeo
from simdt.perillas.coherencia import Coherencia
from simdt.tipos import BLOQUES, COMPONENTES, Q


@pytest.fixture
def esc():
    rng = np.random.default_rng(4)
    return mapeo.Escalas(
        b0=rng.normal(0, 0.05, Q),
        sigma_theta=np.full(Q, 0.1),
        decisiones={n: "tecnico" for n in COMPONENTES},
    )


def test_TM1_inversa_softmax(liga, esc):
    for pi in ([0.354, 0.263, 0.383], [0.6, 0.1, 0.3], [0.2, 0.5, 0.3]):
        pi = np.array(pi)
        th = np.zeros(Q)
        th[BLOQUES["int_at"]] = mapeo.theta_desde_mezcla(pi, liga, esc, "int_at")
        assert np.max(np.abs(mapeo.mezcla_desde_theta(th, liga, esc, "int_at") - pi)) < 1e-12
        th[BLOQUES["int_co"]] = mapeo.theta_desde_mezcla(pi, liga, esc, "int_co")
        assert np.max(np.abs(mapeo.mezcla_desde_theta(th, liga, esc, "int_co") - pi)) < 1e-12
    # y por el camino completo de las perillas
    th = mapeo.perillas_a_tecnico({"mezcla": (0.5, 0.3)}, liga, esc)
    assert np.allclose(mapeo.mezcla_desde_theta(th, liga, esc), [0.5, 0.2, 0.3], atol=1e-12)


def _pi_por_m(liga, zi):
    zj = np.zeros((1, Q))
    return mezcla(liga, zi, zj, np.array([1.0]), np.array([0.0]))[0, 0]  # (3 estados, K)


def test_TM2_reactividad(liga, esc):
    esc0 = mapeo.Escalas(np.zeros(Q), esc.sigma_theta, esc.decisiones)  # plantel promedio = liga
    th1 = mapeo.perillas_a_tecnico({"reaccion_marcador": "Como la mayoría"}, liga, esc0)
    zi1 = (esc0.b0 + th1)[None]
    pi1 = _pi_por_m(liga, zi1)
    pi_liga = _pi_por_m(liga, np.zeros((1, Q)))
    assert np.allclose(pi1, pi_liga, atol=1e-14)
    th0 = mapeo.perillas_a_tecnico({"reaccion_marcador": "Nunca"}, liga, esc0)
    pi0 = _pi_por_m(liga, (esc0.b0 + th0)[None])
    assert np.allclose(pi0[0], pi0[1]) and np.allclose(pi0[2], pi0[1])  # π constante en el marcador
    # con el b0 estimado también: la ficha total s = 1 + b0 + θ vale lo que dice la perilla
    th = mapeo.perillas_a_tecnico({"reaccion_marcador": "Mucho"}, liga, esc)
    q = BLOQUES["s_marcador"][0]
    assert abs(1 + esc.b0[q] + th[q] - 2.0) < 1e-12


def test_TM3_percentiles(liga, esc):
    th = mapeo.perillas_a_tecnico({"balon_parado": 50, "cambios_momento": 50}, liga, esc)
    assert np.allclose(th[BLOQUES["nu_co"]], 0.0) and abs(th[BLOQUES["alpha"][0]]) < 1e-12
    mejor = mapeo.perillas_a_tecnico({"balon_parado": 99}, liga, esc)
    assert np.all(mejor[BLOQUES["nu_co"]] < 0)  # concede menos remates
    dec = dict(esc.decisiones)
    for q in BLOQUES["nu_co"]:
        dec[COMPONENTES[q]] = "plantel"
    esc_p = mapeo.Escalas(esc.b0, esc.sigma_theta, dec)
    assert not mapeo.perillas_activas(esc_p)["balon_parado"]
    th = mapeo.perillas_a_tecnico({"balon_parado": 99}, liga, esc_p)
    assert np.allclose(th[BLOQUES["nu_co"]], 0.0)  # τ = 0: no mueve nada


def test_TM4_promedio_en_el_america():
    rng = np.random.default_rng(9)
    M = 20000
    base = rng.normal(0.1, 0.02, (M, Q))
    sigma = np.zeros((M, Q, 4))
    sigma[:, :, 2] = 0.05
    fichas = rng.normal(size=(M, 18, Q))
    piezas = PiezasFichas(
        [f"E{i}" for i in range(18)],
        fichas,
        base,
        {},
        {},
        sigma,
        rng.normal(size=(M, Q)),
        {n: "tecnico" for n in COMPONENTES},
        0,
        "Actual",
    )
    idx = np.arange(M)
    f = ficha_foco(piezas, np.zeros(Q), idx)
    # θ = 0: ficha = plantel (b0 + φ_Am) + ε nuevo de media cero
    assert np.allclose(f.mean(0), base.mean(0), atol=4 * 0.05 / np.sqrt(M))
    assert np.allclose((f - base).std(0), 0.05, rtol=0.05)


def test_coherencia_extremo():
    rng = np.random.default_rng(1)
    pares = rng.normal(0, 0.1, (40, Q))
    c = Coherencia(pares)
    assert not c.es_extremo(np.zeros(Q))
    assert c.es_extremo(np.full(Q, 1.0))


@pytest.mark.skipif(
    not __import__("simdt.config", fromlist=["x"]).ARTEFACTOS.joinpath("meta.json").exists(),
    reason="sin artefactos",
)
def test_preset_sin_tocar_es_el_mismo_tecnico():
    """Los deslizadores redondean a 1 %: un preset sin tocar debe seguir usando su posterior completa
    (comparado consigo mismo da Δ ≡ 0)."""
    from simdt.servicio import Simulador

    s = Simulador()
    for nombre in s.nombres_preset()[:10]:
        t = s.tecnico_preset(nombre)
        p = dict(t.perillas)  # perillas de la v3: enteros en la escala del deslizador
        assert all(isinstance(v, (int, str)) for v in p.values()), p
        assert not s.perillas_cambiadas(t, p), nombre
        assert s.perillas_cambiadas(t, {**p, "ataca": p["ataca"] + 1}), nombre
