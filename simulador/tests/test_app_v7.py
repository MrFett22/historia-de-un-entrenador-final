"""App v7 (D-073 en adelante): momentum de «Ver un partido» a nivel de jugadas, «¿Qué pesa más?» en una sola escala, calificación con seguridad, radar sin referencia,
tarjetas en cuadrícula, limpieza, enlaces y despliegue."""

from __future__ import annotations

import json
import re
import shutil

import numpy as np
import pytest
from scipy import stats

from simdt import config
from simdt import analisis as A
from simdt.app import animacion as AN
from simdt.app import paleta as PA
from simdt.app import textos as T
from simdt.motor import jugadas as J
from simdt.motor.partido import distribucion_partido
from simdt.servicio import Simulador

SIN_ARTEFACTOS = not (config.ARTEFACTOS / "meta.json").exists()
pytestmark = pytest.mark.skipif(SIN_ARTEFACTOS, reason="sin artefactos")


@pytest.fixture(scope="module")
def sim7():
    return Simulador(config.ARTEFACTOS)


@pytest.fixture(scope="module")
def piezas(sim7):
    t = sim7.tecnico_preset(sim7.p.meta["tecnico_actual_foco"])
    Ci, Cj, _ = A.componentes_partido(sim7, t, 3, True, 5)
    return t, Ci, Cj


# ================================================================ Fase A: momentum a nivel de jugadas (D-073)
def test_las_piezas_reconstruyen_la_mu_del_motor(piezas):
    _, Ci, Cj = piezas
    for C in (Ci, Cj):
        mu = C.f * ((C.n_k * (C.p * C.g)).sum(-1) + (C.saques * C.q * C.kappa).sum(-1)[:, None])
        assert np.abs(mu - C.mu).max() < 1e-12


@pytest.mark.parametrize("t,m", [(10, 1), (70, 0), (80, 2)])
def test_los_goles_de_un_minuto_son_poisson_de_mu_en_20000_minutos(piezas, t, m):
    """Media y varianza de los goles de un minuto contra μ (Poisson: varianza = media), cada una a ≤ 3 errores estándar."""
    _, Ci, Cj = piezas
    n = 20000
    rng = np.random.default_rng(1000 + 7 * t + m)
    g = J.minuto(Ci, Cj, t, np.full(n, m), rng)["goles_i"]
    mu = Ci.mu[t, m]
    assert abs(g.mean() - mu) < 3 * np.sqrt(mu / n), (g.mean(), mu)
    assert abs(g.var(ddof=1) - mu) < 3 * np.sqrt((mu + 2 * mu**2) / n), (g.var(ddof=1), mu)


def test_la_ley_de_goles_no_depende_de_la_concentracion_del_peligro(piezas):
    """La concentración solo cambia la forma del peligro que se dibuja, no los goles."""
    _, Ci, Cj = piezas
    n, mu = 20000, Ci.mu[40, 1]
    for conc in (1.5, 40.0):
        g = J.minuto(Ci, Cj, 40, np.full(n, 1), np.random.default_rng(5), conc)["goles_i"]
        assert abs(g.mean() - mu) < 3 * np.sqrt(mu / n), (conc, g.mean(), mu)


def test_5000_partidos_jugada_por_jugada_coinciden_con_la_distribucion_exacta(sim7, piezas):
    t, _, _ = piezas
    av = A.autoverificacion_partido(sim7, t, 3, True, 5000, 20261020)
    assert max(abs(z) for z in av["z_resultados"]) < 3, av["z_resultados"]
    assert max(abs(z) for z in av["z_goles"]) < 3, av["z_goles"]
    assert av["p"] > 0.01 and av["pasa"], av


def test_la_media_de_remates_coincide_con_lo_esperado_en_los_90_minutos(piezas):
    """E[remates] = Σ_t Σ_m ocupación(t, m) · (Σ_k λ π p + Σ_u saques q), con la ocupación del cálculo exacto."""
    _, Ci, Cj = piezas
    d = distribucion_partido(Ci.mu, Cj.mu)
    occ_i = d.ocupacion[0]  # (T, 3) desde el América
    esp_i = float(((Ci.n_k * Ci.p).sum(-1) * occ_i).sum() + (Ci.saques * Ci.q).sum())
    esp_j = float(((Cj.n_k * Cj.p).sum(-1) * occ_i[:, ::-1]).sum() + (Cj.saques * Cj.q).sum())
    n = 3000
    r = J.simular_partidos(Ci, Cj, n, np.random.default_rng(42))
    for esp, x in ((esp_i, r["remates_i"].sum(1)), (esp_j, r["remates_j"].sum(1))):
        assert abs(x.mean() - esp) < 3 * x.std(ddof=1) / np.sqrt(n), (x.mean(), esp)


def test_el_momentum_cambia_de_signo_en_casi_todos_los_partidos(piezas):
    _, Ci, Cj = piezas
    r = J.simular_partidos(Ci, Cj, 2000, np.random.default_rng(3))
    m = r["momentum"]
    cambia = ((m[:, 1:] * m[:, :-1]) < 0).any(1)
    assert cambia.mean() >= 0.90, cambia.mean()
    assert m.shape == (2000, 90) and np.isfinite(m).all()


def test_el_momentum_es_el_suavizado_de_la_diferencia_de_peligro(piezas):
    _, Ci, Cj = piezas
    r = J.simular_partidos(Ci, Cj, 5, np.random.default_rng(8))
    vida = config.cargar()["partido"]["jugadas"]["vida_media_momentum"]
    a = 1 - 0.5 ** (1 / vida)
    d = r["peligro_i"] - r["peligro_j"]
    esperado = np.zeros_like(d)
    acc = np.zeros(5)
    for t in range(90):
        acc = (1 - a) * acc + a * d[:, t]
        esperado[:, t] = acc
    assert np.allclose(r["momentum"], esperado)
    assert (r["peligro_i"] >= 0).all() and (r["peligro_j"] >= 0).all()


def test_el_peligro_solo_existe_en_minutos_con_remates(piezas):
    _, Ci, Cj = piezas
    r = J.simular_partidos(Ci, Cj, 50, np.random.default_rng(9))
    assert ((r["peligro_i"] > 0) == (r["remates_i"] > 0)).all()
    assert (r["goles_i"] <= r["remates_i"]).all()


def test_con_la_misma_semilla_el_mismo_partido_y_la_app_ya_no_usa_el_peligro_por_tramos(
    sim7, piezas
):
    t, _, _ = piezas
    a, b, c = (A.partido_unico(sim7, t, 3, True, s, muestra=5) for s in (11, 11, 12))
    assert (
        a == b
        and a["peligro_america"] != c["peligro_america"]
        and len(a["peligro_america"]) == len(a["peligro_rival"]) == 90
    )
    assert (
        set(a) >= {"peligro_america", "peligro_rival", "remates_america", "remates_rival", "goles"}
        and "momentum" not in a
    )  # v8 (D-088): barras por minuto, sin suavizar
    assert (a["america"], a["rival"]) == (
        (a["goles"][-1][2], a["goles"][-1][3]) if a["goles"] else (0, 0)
    )
    assert not (hasattr(T, "SECCION_MOMENTUM")) and "momentum" in T.PALABRAS_PROHIBIDAS


def test_el_partido_se_dibuja_en_barras_por_minuto_sin_curvas(sim7, piezas):
    t, _, _ = piezas
    p = A.partido_unico(sim7, t, 3, True, 7, muestra=5)
    html = AN.html_partido(
        {**AN.datos_partido(p), "rival": "X", "iniciales": "XX", "local": True},
        {
            "hover": "h",
            "hover_fila": "{eq} {x}",
            "america": "A",
            "gol": "g",
            "resultado": ["a", "b", "c"],
            "sin_goles": "s",
            "minuto": "m",
            "antes": "x",
            "barras": T.PARTIDO_BARRAS,
            "cien": "c",
            "remates": "r",
        },
    )
    assert (
        html.count('id="barras"') == 1
        and 'id="pp"' not in html
        and 'id="pn"' not in html
        and "empuje" not in html
        and "createElementNS" in html
    )
    assert "prefers-reduced-motion" in html and '"dominio"' in html


# ================================================================ Fase B: «¿Qué pesa más?» en la misma escala (D-074)
DISP = {
    "var_real": {"valor": 60.9, "ic95": [48.0, 70.0]},
    "var_azar": {"valor": 27.8, "ic95": [26.9, 28.6]},
    "sd_fuerza_real": {"valor": 5.75, "ic95": [4.47, 6.33]},
    "sd_fuerza_modelo": {"valor": 3.79, "ic95": [3.37, 3.96]},
    "r": {"valor": 1.52, "ic95": [1.23, 1.70], "p_h0": 0.0, "rechaza_h0": True},
    "azar_sobre_real": {"valor": 0.46, "ic95": [0.41, 0.58]},
    "piso_en_cero": False,
}


class _SimFalso:
    """Un simulador con solo lo que necesita `escala_efectos`: sus perfiles y las calificaciones ya calculadas."""

    def __init__(self, disp, deltas):
        self._perfiles = {"dispersion": disp}
        self._calif = {f"T{i}": {"delta": d} for i, d in enumerate(deltas)}

    def perfiles(self):
        return self._perfiles


def test_las_tres_barras_usan_la_misma_definicion_con_numeros_sinteticos():
    """suerte = √Var_azar, jugadores = SD_fuerza_real, técnico = desviación típica (n − 1) de los Δ de los técnicos reales."""
    deltas = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    e = A.escala_efectos(_SimFalso(DISP, deltas))
    assert e["suerte"] == pytest.approx(np.sqrt(27.8)) and e["suerte_ic"] == pytest.approx(
        [np.sqrt(26.9), np.sqrt(28.6)]
    )
    assert e["jugadores"] == 5.75 and e["jugadores_ic"] == [4.47, 6.33]
    assert (
        e["tecnico"] == pytest.approx(np.std(deltas, ddof=1))
        and e["tecnico_ic"][0] < e["tecnico"] < e["tecnico_ic"][1]
        and e["n_tecnicos"] == 6
    )
    assert e["azar_sobre_real"] == 0.46 and e["r"] == 1.52
    # con los números medidos del proyecto: la suerte (≈ 5.3) casi igual que los jugadores (5.75)
    assert 5.2 < e["suerte"] < 5.3


def test_sin_dispersion_medida_no_se_inventa_ninguna_barra():
    e = A.escala_efectos(_SimFalso({}, [0.0, 1.0, -1.0]))
    assert e["suerte"] is None and e["jugadores"] is None and e["tecnico"] is not None
    assert A.frase_pesa_mas(e) is None and A.frase_suerte(e["azar_sobre_real"]) is None


@pytest.mark.parametrize(
    "e,esperada",
    [
        ({"suerte": 5.27, "jugadores": 5.75, "tecnico": 0.6}, T.PESA_FRASE_IGUALES),
        ({"suerte": 7.0, "jugadores": 3.0, "tecnico": 0.6}, T.PESA_FRASE_UNO["suerte"]),
        ({"suerte": 2.0, "jugadores": 6.0, "tecnico": 0.5}, T.PESA_FRASE_UNO["jugadores"]),
        (
            {"suerte": 2.0, "jugadores": 2.5, "tecnico": 2.4},
            T.PESA_FRASE_NEUTRA.format(que="los jugadores"),
        ),
        ({"suerte": 2.0, "jugadores": 2.5, "tecnico": 6.0}, T.PESA_FRASE_TECNICO),
    ],
)
def test_la_frase_cambia_con_los_numeros_en_cinco_escenarios_sinteticos(e, esperada):
    assert A.frase_pesa_mas(e) == esperada


def test_la_linea_de_la_suerte_sale_de_la_fraccion_medida():
    assert A.frase_suerte(0.46) == T.PESA_SUERTE_LINEA.format(medida=T.PESA_SUERTE_CASI, pct=46)
    assert T.PESA_SUERTE_CASI == "Casi la mitad" and "pura suerte" in T.PESA_SUERTE_LINEA
    assert (
        A.frase_suerte(0.6).startswith(T.PESA_SUERTE_MAS)
        and A.frase_suerte(0.3).startswith(T.PESA_SUERTE_TERCIO)
        and A.frase_suerte(0.1).startswith(T.PESA_SUERTE_POCO)
    )


def test_la_tarjeta_de_la_app_trae_tres_barras_con_rango_y_la_frase_calculada(
    monkeypatch, tmp_path
):
    from streamlit.testing.v1 import AppTest
    import streamlit as st

    d = tmp_path / "art"
    shutil.copytree(config.ARTEFACTOS, d)
    pf = (
        json.loads((d / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
        if (d / "perfiles_tecnicos.json").exists()
        else {}
    )
    pf["dispersion"] = DISP
    nombres = Simulador(config.ARTEFACTOS).nombres_lista_corta()
    pf["calificacion"] = {
        "modo": "rapido",
        "tecnicos": {
            n: {"delta": x, "ic90": [x - 1.0, x + 1.0]}
            for n, x in zip(nombres, [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5])
        },
    }
    (d / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    monkeypatch.setattr(config, "ARTEFACTOS", d)
    vacia = tmp_path / "sinval"
    vacia.mkdir()
    monkeypatch.setattr(config, "VALIDACION", vacia)
    monkeypatch.delenv("SIMDT_VALIDACION", raising=False)
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=300).run()
    html = " ".join(m.value for m in at.markdown)
    assert (
        html.count('class="pesa-pista"') >= 3 and html.count('class="pesa-ic"') >= 3
    )  # las tres con rango probable
    assert (
        T.PESA_FRASE_IGUALES in html
        and T.PESA_SUERTE_CASI in html
        and '±<span class="est">5.3</span>' in html
        and '±<span class="est">5.8</span>' in html
    )
    assert "desviación estándar" not in html.lower()


# ================================================================ Fase C: calificación entendible (D-075)
@pytest.mark.parametrize(
    "rango,esperada",
    [
        ([0.0, 10.0], "baja"),
        ([2.4, 9.8], "baja"),
        ([0.0, 6.01], "baja"),
        ([0.0, 6.0], "media"),
        ([2.0, 5.0], "media"),
        ([0.0, 3.7], "media"),
        ([5.0, 7.99], "alta"),
        ([5.0, 8.0], "media"),
        ([4.5, 5.5], "alta"),
    ],
)
def test_los_umbrales_de_seguridad_son_ancho_mayor_a_6_baja_de_3_a_6_media_menor_a_3_alta(
    rango, esperada
):
    assert A.seguridad(rango) == esperada
    assert A.seguridad(None) is None


def test_una_seguridad_baja_siempre_cruza_el_centro_asi_que_nunca_hay_color_sin_seguridad():
    """En 0–10, un rango de más de 6 puntos siempre contiene al 5."""
    rng = np.random.default_rng(0)
    for _ in range(2000):
        lo, hi = np.sort(rng.uniform(0, 10, 2))
        if A.seguridad([lo, hi]) == "baja":
            assert lo <= 5.0 <= hi
    assert (
        A.color_calificacion(8.0, False, "baja") == A.COLOR_NEUTRO
        and A.color_calificacion(8.0, True, "alta") == A.COLOR_NEUTRO
        and A.color_calificacion(8.0, False, None) == A.COLOR_NEUTRO
    )
    assert (
        A.color_calificacion(8.0, False, "media") == "amarillo"
    )  # v11 (D-097): solo amarillo, gris o rojo


def test_jardine_sale_gris_con_seguridad_baja_y_un_tecnico_claramente_peor_sale_en_rojo():
    """Con Δ de los datos medidos: Jardine +0.57 [−1.49, +2.60] (gris, baja) y un técnico como Ambriz −1.18 [−2.23, −0.10] (rojo si su seguridad no es baja)."""
    deltas = {
        "Almada": (0.57, [-0.41, 1.45]),
        "Jardine": (0.57, [-1.49, 2.60]),
        "Mohamed": (0.75, [-1.0, 2.2]),
        "Herrera": (0.58, [-0.9, 2.0]),
        "Gerk": (-0.57, [-2.0, 0.9]),
        "Ambriz": (-1.18, [-2.23, -0.10]),
        "N1": (0.1, [-1.0, 1.2]),
        "N2": (-0.2, [-1.2, 0.8]),
        "N3": (0.3, [-0.8, 1.4]),
        "N4": (-0.1, [-1.0, 0.9]),
    }

    class S:
        def perfiles(self):
            return {
                "calificacion": {
                    "tecnicos": {n: {"delta": d, "ic90": ic} for n, (d, ic) in deltas.items()}
                }
            }

    cal = A.calificaciones_reales(S())
    j, a = cal["Jardine"], cal["Ambriz"]
    assert (
        j["seguridad"] == "baja"
        and j["cruza"]
        and A.color_calificacion(j["calif"], j["cruza"], j["seguridad"]) == A.COLOR_NEUTRO
        and j["calif"] > 5.0
    )
    assert not a["cruza"] and a["seguridad"] != "baja" and a["calif"] < 3.5
    assert A.color_calificacion(a["calif"], a["cruza"], a["seguridad"]) == "rojo"
    for v in cal.values():  # el signo de (calificación − 5) es el de Δ
        assert np.sign(v["calif"] - 5.0) == np.sign(v["delta"])


def test_la_carta_dice_la_seguridad_el_delta_en_grande_y_pone_el_rango_en_la_ayuda(
    monkeypatch, tmp_path
):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    d = tmp_path / "art"
    shutil.copytree(config.ARTEFACTOS, d)
    sim = Simulador(d)
    nombres = sim.nombres_lista_corta()
    pf = (
        json.loads((d / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
        if (d / "perfiles_tecnicos.json").exists()
        else {}
    )
    pf["calificacion"] = {
        "modo": "rapido",
        "tecnicos": {
            n: {"delta": x, "ic90": ic}
            for n, x, ic in zip(
                nombres,
                [1.8, 0.05, -1.5, 0.4, -0.3, 1.1],
                [[0.6, 3.0], [-2.44, 2.53], [-2.8, -0.2], [-1.0, 1.9], [-1.9, 1.2], [-0.4, 2.6]],
            )
        },
    }
    (d / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    monkeypatch.setattr(config, "ARTEFACTOS", d)
    vacia = tmp_path / "sinval"
    vacia.mkdir()
    monkeypatch.setattr(config, "VALIDACION", vacia)
    monkeypatch.delenv("SIMDT_VALIDACION", raising=False)
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=300).run()
    at.sidebar.selectbox(key="k_preset").set_value(
        nombres[1]
    ).run()  # el de Δ +0.05 y rango que cruza el 5
    t = " ".join(m.value for m in at.markdown)
    cal = A.calificaciones_reales(Simulador(d))[nombres[1]]
    assert (
        T.CALIF_SEGURIDAD.format(s=cal["seguridad"]) in t
        and "+0.1 puntos por torneo contra un estilo neutro" in t
    )
    assert (
        T.CALIF_RANGO.format(a=f"{cal['rango'][0]:.1f}", b=f"{cal['rango'][1]:.1f}") in t
        and T.CALIF_AVISO in t
    )
    carta = t.split(T.CARTA_TITULO)[1].split(T.SECCION_MAPA)[0]
    assert PA.color(A.COLOR_NEUTRO) in carta and "rango probable: " not in carta.replace(
        T.CALIF_RANGO.format(a=f"{cal['rango'][0]:.1f}", b=f"{cal['rango'][1]:.1f}"), ""
    )


# ================================================================ Fase D: radar sin referencia fija (D-076)
def test_el_radar_tiene_una_sola_traza_de_datos_y_el_hexagono_de_fondo_es_neutro():
    from simdt.app import graficas as G

    fig = G.radar([70, 50, 40, 60, 30, 80], T.CARTA_ATRIBUTOS_RADAR, "#3FB950")
    assert len(fig.data) == 1 and fig.data[0].fill == "toself"
    assert (
        list(fig.layout.polar.radialaxis.tickvals) == [25, 50, 75]
        and fig.layout.showlegend is False
    )
    spec = fig.to_json()
    assert "Almada" not in spec and "dot" not in spec


def test_la_app_dibuja_el_radar_con_una_sola_traza_y_sin_el_america_actual(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("SIMDT_VALIDACION", raising=False)
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=300).run()
    radar = [
        json.loads(g.proto.spec) for g in at.get("plotly_chart") if '"scatterpolar"' in g.proto.spec
    ]
    assert radar and all(len(r["data"]) == 1 for r in radar)
    assert not hasattr(T, "CARTA_SIN_ACTUAL")


# ================================================================ Fase E: tarjetas en cuadrícula, todas del mismo tamaño (D-077)
def _navegador():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    import os
    import shutil as sh

    for ruta in (
        os.environ.get("SIMDT_CHROMIUM"),
        "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        "/opt/pw-browsers/chromium",
        sh.which("chromium"),
        sh.which("google-chrome"),
    ):
        if ruta and os.path.exists(ruta):
            return ruta
    return None


@pytest.mark.skipif(
    _navegador() is None,
    reason="sin Playwright o sin navegador: se salta (las capturas de capturas/v7 se sacan a mano)",
)
@pytest.mark.parametrize("ancho,columnas", [(1440, 3), (390, 1)])
def test_las_tarjetas_de_cada_cuadricula_miden_lo_mismo_de_alto_y_no_se_salen(ancho, columnas):
    import os
    import socket
    import subprocess
    import sys
    import time
    from playwright.sync_api import sync_playwright

    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        puerto = so.getsockname()[1]
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(config.RAIZ_SIM / "app.py"),
            "--server.port",
            str(puerto),
            "--server.headless",
            "true",
        ],
        cwd=str(config.RAIZ_SIM),
        env={**os.environ, "PYTHONPATH": str(config.RAIZ_SIM / "src")},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    js = """(sel) => { const g = document.querySelector(sel); if (!g) return null;
        const cs = [...g.children].map(w => w.firstElementChild).map(e => e.getBoundingClientRect());
        return {n: cs.length, alturas: cs.map(r => Math.round(r.height)), izq: Math.min(...cs.map(r => r.left)), der: Math.max(...cs.map(r => r.right)),
                columnas: new Set(cs.map(r => Math.round(r.left))).size, ancho: window.innerWidth, scroll: document.documentElement.scrollWidth}; }"""
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=_navegador(), args=["--no-sandbox"])
            pg = b.new_page(viewport={"width": ancho, "height": 1200})
            for _ in range(60):
                try:
                    pg.goto(f"http://localhost:{puerto}", wait_until="networkidle")
                    break
                except Exception:
                    time.sleep(1)
            pg.wait_for_selector(
                "[class*=st-key-antes_heroe]", timeout=240000
            )  # la primera vez compila el núcleo: puede tardar
            pg.wait_for_timeout(2500)
            pg.locator("[role=tab]").nth(2).evaluate("e => e.click()")
            try:
                pg.wait_for_selector("[class*=st-key-rejilla_creer]", timeout=20000)
            except Exception:
                pass
            pg.wait_for_timeout(2500)
            creer = pg.evaluate(js, "[class*=st-key-rejilla_creer]")
            b.close()
    finally:
        proc.terminate()
    for nombre, g in (("creer", creer),):  # «Antes de jugar» ya no es cuadrícula (v8, D-083)
        if g is None:  # sin validación versionada no hay tarjetas de pruebas
            continue
        assert max(g["alturas"]) - min(g["alturas"]) <= 2, (nombre, g["alturas"])
        assert g["columnas"] == columnas, (nombre, g)
        assert g["der"] <= g["ancho"] + 1 and g["izq"] >= -1 and g["scroll"] <= g["ancho"] + 1, (
            nombre,
            g,
        )
    if creer is not None:
        assert creer["n"] == 8, creer


def test_ya_no_hay_carruseles_ni_deslizar_de_lado_en_el_codigo():
    css = (config.RAIZ_SIM / "src" / "simdt" / "app" / "estilos.css").read_text(encoding="utf-8")
    py = (config.RAIZ_SIM / "src" / "simdt" / "app" / "principal.py").read_text(encoding="utf-8")
    assert (
        "scroll-snap" not in css
        and "carrusel" not in css
        and "carrusel" not in " ".join(re.findall(r'key="[^"]+"', py))
    )
    assert (
        "display: grid" in css
        and "repeat(3, minmax(0, 1fr))" in css
        and "min-width: 1200px" in css
        and "minmax(min-content, 1fr)" in css
    )
    assert not hasattr(T, "ANTES_DESLIZA") and not hasattr(T, "CREER_DESLIZA")


# ================================================================ Fase F: limpieza del simulador (D-078)
PROHIBIDAS_V7 = (
    "xG",
    "percentil",
    "posterior",
    "componente",
    "θ",
    "μ",
    "intensidad",
    "parámetro",
    "desviación estándar",
    "momentum",
    "apostar",
    "cuotas",
)
RESTOS = (
    "Listo en",
    "Refuerzos",
    "otro plantel",
    "técnico promedio",
    "momentum de un partido típico",
    "partido típico",
    "Desliza para ver",
)


def test_no_queda_ningun_indicador_de_tiempo_ni_resto_de_versiones_anteriores_en_los_textos():
    todo = " ".join(
        v
        for n, v in vars(T).items()
        if isinstance(v, str) and not n.startswith("_") and n != "PALABRAS_PROHIBIDAS"
    )
    for r in RESTOS:
        assert r.lower() not in todo.lower(), r
    assert not hasattr(T, "TIEMPO")
    fuente = (config.RAIZ_SIM / "src" / "simdt" / "app" / "principal.py").read_text(
        encoding="utf-8"
    )
    assert "segundos" not in fuente and "T.TIEMPO" not in fuente
    for p in PROHIBIDAS_V7:
        assert p in T.PALABRAS_PROHIBIDAS or p == "θ", p


def test_lo_que_se_ve_en_las_tres_pestanas_no_trae_palabras_prohibidas_ni_restos(monkeypatch):
    """T-U1 a T-U5 sobre la app armada (simulada la primera vez): el texto de las tres pestañas, con la ayuda de cada tarjeta."""
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("SIMDT_VALIDACION", raising=False)
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=600).run()
    [b for b in at.sidebar.button if b.label == T.BOTON_SIMULAR][0].click().run()
    at.button(key="b_partido").click().run()
    vistos = " ".join(
        [m.value for m in at.markdown]
        + [str(getattr(c, "value", "")) for c in at.caption]
        + [str(getattr(m, "help", "") or "") for m in at.markdown]
    )
    plano = re.sub(r"<style.*?</style>", " ", vistos, flags=re.S)
    plano = re.sub(r"(?<=[\w»\"])[\"'][^<>]*?>", " ", plano)
    bajo = plano.lower()
    for r in RESTOS:
        assert r.lower() not in bajo, r
    for p in PROHIBIDAS_V7:
        if p == "xG":
            assert not re.search(r"\bxg\b", bajo), p
        else:
            assert p.lower() not in bajo, p
    assert not at.exception


def test_la_tarjeta_de_puntos_muestra_r_con_dos_decimales_y_su_rango(monkeypatch, tmp_path):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    d = tmp_path / "art"
    shutil.copytree(config.ARTEFACTOS, d)
    pf = (
        json.loads((d / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
        if (d / "perfiles_tecnicos.json").exists()
        else {}
    )
    pf["dispersion"] = DISP
    (d / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    monkeypatch.setattr(config, "ARTEFACTOS", d)
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=300).run()
    t = " ".join(m.value for m in at.markdown)
    if (
        "rango probable 1.23 a 1.70" not in t
    ):  # sin graficas_validacion.json no hay tarjeta de puntos
        pytest.skip("sin validación versionada: no hay tarjeta de puntos")
    assert "son 1.52× las del simulador" in t


# ================================================================ Fase G: enlaces (D-079)
ESTUDIO = "https://github.com/MrFett22/historia-de-un-entrenador-final/blob/main/docs/MODELO.md"


def test_el_enlace_principal_es_el_del_estudio_original_y_viene_del_config():
    e = config.cargar()["enlaces"]
    assert e["estudio_original"] == ESTUDIO and "repo_original" not in e
    assert (
        e["validacion"]
        == "https://github.com/MrFett22/historia-de-un-entrenador-final/blob/main/docs/VALIDACION.md"
    )
    assert (
        T.ESTUDIO_ORIGINAL == "Ver la documentación del modelo"
        and T.VER_DETALLE == "Detalle técnico del simulador"
    )
    fuente = (config.RAIZ_SIM / "src" / "simdt" / "app" / "principal.py").read_text(
        encoding="utf-8"
    )
    assert "http" not in fuente.replace(
        "https://fonts.googleapis.com", ""
    )  # ninguna URL escrita a mano en el código de la app


def test_el_enlace_principal_aparece_en_antes_de_jugar_y_en_le_podemos_creer(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("SIMDT_VALIDACION", raising=False)
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=300).run()
    antes = [(b.label, b.proto.url) for b in at.tabs[0].get("link_button")]
    assert (T.ESTUDIO_ORIGINAL, ESTUDIO) in antes and any(l == T.VER_DETALLE for l, _ in antes)
    creer = [(b.label, b.proto.url) for b in at.tabs[2].get("link_button")]
    if creer:  # sin validación versionada la pestaña solo avisa
        assert (T.ESTUDIO_ORIGINAL, ESTUDIO) in creer and any(l == T.VER_DETALLE for l, _ in creer)
    assert not at.get("download_button")


def test_la_escala_del_azar_de_la_app_no_lee_azar_pm_de_la_escala_vieja():
    """`azar_pm` (la mitad del rango del 80 %, escala vieja) puede seguir en perfiles_tecnicos.json de corridas anteriores, pero la app ya no lo usa (D-074)."""
    pf = {
        "azar_pm": 99.0,
        "dispersion": DISP,
        "calificacion": {
            "tecnicos": {f"T{i}": {"delta": d} for i, d in enumerate([-1.0, 0.0, 1.0])}
        },
    }

    class S:
        _calif = {n: {"delta": v["delta"]} for n, v in pf["calificacion"]["tecnicos"].items()}

        def perfiles(self):
            return pf

    assert A.escala_efectos(S())["suerte"] == pytest.approx(np.sqrt(27.8))
    fuente = (config.RAIZ_SIM / "src" / "simdt").rglob("*.py")
    assert not any("azar_pm" in f.read_text(encoding="utf-8") for f in fuente)
