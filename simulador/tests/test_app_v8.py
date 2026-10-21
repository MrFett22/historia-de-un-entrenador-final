"""App v8 (D-082 en adelante): carta del técnico con el tipo de cambios y sin «Se parece a» fuera de la zona, «Antes de jugar» reacomodada, exigencia del América, simulación en
segundo plano con progreso real, pruebas con su nombre clásico, momentum en barras, partido con más eventos y publicación robusta."""

from __future__ import annotations

import json
import re
import shutil

import numpy as np
import pytest

from simdt import analisis as A
from simdt import config
from simdt.app import textos as T
from simdt.motor import jugadas as J
from simdt.perillas import ejes as mejes
from simdt.servicio import Simulador

SIN_ARTEFACTOS = not (config.ARTEFACTOS / "meta.json").exists()
pytestmark = pytest.mark.skipif(SIN_ARTEFACTOS, reason="sin artefactos")


from test_app_v6 import _app as _app6  # noqa: E402  (el mismo montaje: artefactos con atribución continua, lista corta, perfiles y dispersión)
from test_app_v6 import _boton, _elegir, _texto, dir_v6, sim6  # noqa: E402,F401


@pytest.fixture(scope="module")
def sim8(sim6):
    return sim6


@pytest.fixture(scope="module")
def piezas(sim8):
    t = sim8.tecnico_preset(sim8.p.meta["tecnico_actual_foco"])
    Ci, Cj, _ = A.componentes_partido(sim8, t, 3, True, 5)
    return t, Ci, Cj


@pytest.fixture
def app8(dir_v6, monkeypatch):
    return _app6(monkeypatch, dir_v6)


# ================================================================ Fase A: carta del técnico (D-082)
def test_el_tipo_de_cambios_cambia_el_chip_y_no_cambia_los_puntos_esperados(sim8, app8):
    base = sim8.tecnico_promedio()
    per = sim8.perillas_de(base)
    resultados = {}
    for opcion in T.OPCIONES_CAMBIO:
        t = sim8.tecnico_perillas({**per, "cambios_tipo": opcion}, base, "X")
        r = sim8.simular(t, "rapido", con_estilo=False).temporada.resumen
        resultados[opcion] = (r["puntos_esperados"], tuple(np.asarray(r["p_lugar"]).ravel()))
    primero = resultados[T.OPCIONES_CAMBIO[0]]
    for opcion, v in resultados.items():  # Δ ≡ 0 con la misma semilla
        assert v[0] == primero[0] and v[1] == primero[1], opcion
    at = app8
    chips = {}
    for opcion in T.OPCIONES_CAMBIO:
        at.sidebar.select_slider(key="k_ct").set_value(opcion).run()
        t = _texto(at)
        chips[opcion] = T.CAMBIOS_CHIP.format(x=opcion)
        assert chips[opcion] in t, opcion
        assert all(c not in t for o, c in chips.items() if o != opcion), (
            opcion
        )  # solo el chip de la opción elegida
    if "cambios_tipo" in sim8.p.meta.get("perillas_solo_estilo", []):
        assert T.CAMBIOS_SOLO_ESTILO in _texto(at)


def test_la_ayuda_de_la_carta_dice_que_los_cambios_no_mueven_los_puntos():
    assert (
        T.CALIF_CAMBIOS_AYUDA
        == "Los cambios no mueven los puntos en el simulador: en toda la liga su efecto en goles salió nulo."
    )
    assert T.CALIF_CAMBIOS_AYUDA in T.CALIF_AYUDA


def test_se_parece_a_solo_si_el_punto_cae_dentro_de_la_zona_observada(sim8):
    base = sim8.tecnico_promedio()
    per = sim8.perillas_de(base)
    dentro = A.carta(sim8, per, False)
    assert dentro["dentro"] and dentro["parecido"] in sim8.ejes.nombres
    fuera = {**per, "ataca": 100, "defiende": 100}  # esquina del mapa: nadie ha jugado así
    if sim8.fuera_de_la_zona(fuera, False):
        c = A.carta(sim8, fuera, False)
        assert c["parecido"] is None and not c["dentro"] and not c["es_el_mismo"]


def test_en_modo_sin_limites_con_todo_a_menos_300_la_carta_no_muestra_ningun_nombre_real(
    sim8, app8
):
    from simdt.app import principal

    per = {**sim8.perillas_de(sim8.tecnico_promedio()), **{k: -300 for k in mejes.CLAVES_EJES}}
    assert sim8.fuera_de_la_zona(per, True)
    assert A.carta(sim8, per, True)["parecido"] is None
    at = app8
    at.sidebar.toggle(key="k_ilim").set_value(True).run()
    for k in mejes.CLAVES_EJES:
        at.sidebar.slider(key=principal.LLAVES[k] + "_u").set_value(-300)
    at.run()
    assert not at.exception
    carta = _texto(at).split(T.CARTA_TITULO)[1].split(T.SECCION_MAPA)[0]
    assert T.CARTA_NINGUNO in carta
    for nombre in sim8.ejes.nombres:
        assert (
            T.CARTA_PARECE.format(n=nombre) not in carta
            and T.CARTA_ES.format(n=nombre) not in carta
        )


# ================================================================ Fase B: «Antes de jugar» reacomodada (D-083)
def _navegador():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    import os

    for ruta in (
        os.environ.get("SIMDT_CHROMIUM"),
        "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        "/opt/pw-browsers/chromium",
        shutil.which("chromium"),
        shutil.which("google-chrome"),
    ):
        if ruta and os.path.exists(ruta):
            return ruta
    return None


JS_TIPOGRAFIA = """(args) => {
    const [panel, cuerpoSel] = args;
    const raiz = document.querySelector(panel);
    const visible = (e) => { const r = e.getBoundingClientRect(); if (!(r.width > 0 && r.height > 0)) return false;
        for (let p = e; p && p !== raiz; p = p.parentElement) { const d = p.closest('details'); if (d && !d.open && p.tagName !== 'SUMMARY' && !(p.closest('summary'))) return false; } return true; };
    const w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT); const chicas = []; let n = 0, min = 999;
    while (w.nextNode()) { const t = w.currentNode; if (!t.textContent.trim()) continue; const e = t.parentElement; if (!visible(e)) continue;
        const f = parseFloat(getComputedStyle(e).fontSize); n++; if (f < min) min = f; if (f < 12.95) chicas.push([t.textContent.trim().slice(0, 40), f]); }
    const cuerpo = [...raiz.querySelectorAll(cuerpoSel)].filter(visible).map(e => parseFloat(getComputedStyle(e).fontSize));
    const tarjetas = [...raiz.querySelectorAll('[class*=st-key-antes_]')].map(c => { const r = c.getBoundingClientRect(); const hs = [...c.children].map(h => h.getBoundingClientRect());
        const top = Math.min(...hs.map(h => h.top)), bot = Math.max(...hs.map(h => h.bottom)); return {alto: r.height, lleno: (bot - top) / r.height, izq: r.left, der: r.right, clase: [...c.classList].find(x => x.startsWith('st-key-'))}; });
    return {n, min, chicas, cuerpo_min: cuerpo.length ? Math.min(...cuerpo) : null, n_cuerpo: cuerpo.length, tarjetas, ancho: window.innerWidth, scroll: document.documentElement.scrollWidth};
}"""


def _servidor(extra_env=None):
    import os
    import socket
    import subprocess
    import sys

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
        env={**os.environ, "PYTHONPATH": str(config.RAIZ_SIM / "src"), **(extra_env or {})},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc, puerto


@pytest.mark.skipif(
    _navegador() is None,
    reason="sin Playwright o sin navegador: se salta (las capturas de capturas/v8 se sacan a mano)",
)
@pytest.mark.parametrize("ancho,cuerpo", [(1440, 16), (390, 15)])
def test_antes_de_jugar_letra_minima_poco_espacio_vacio_y_nada_se_sale(ancho, cuerpo):
    import time
    from playwright.sync_api import sync_playwright

    proc, puerto = _servidor()
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
            pg.wait_for_selector("[class*=st-key-antes_heroe]", timeout=240000)
            pg.wait_for_timeout(2500)
            r = pg.evaluate(
                JS_TIPOGRAFIA,
                [
                    '[data-baseweb="tab-panel"], [role="tabpanel"]',
                    ".reel-linea, .c-bloque, .tipo-frase, .chip-dato span, ul.lista-dos li",
                ],
            )
            b.close()
    finally:
        proc.terminate()
    assert r["n"] > 30 and r["min"] >= 12.95 and not r["chicas"], r["chicas"][
        :5
    ]  # ningún texto visible mide menos de 13 px
    assert r["n_cuerpo"] > 10 and r["cuerpo_min"] >= cuerpo - 0.05, (
        r["cuerpo_min"],
        r["n_cuerpo"],
    )  # el cuerpo mide ≥ 16 px (15 en móvil)
    assert len(r["tarjetas"]) >= 8
    for t in r["tarjetas"]:
        assert t["lleno"] >= 0.65, t  # ninguna tarjeta con más de 35 % de su alto vacío
        assert t["izq"] >= -1 and t["der"] <= r["ancho"] + 1, t
    assert r["scroll"] <= r["ancho"] + 1


# ================================================================ Fase C: «Exigencia América» (D-083)
def _ref(media, ee=0.01):
    return {
        "p_top": {"media": media, "ee": ee},
        "p_liguilla": {"media": min(1.0, media + 0.2), "ee": ee},
    }


def test_los_niveles_de_exigencia_son_monotonos_en_p_top_con_numeros_sinteticos():
    rango = {"alerta": 0, "corto": 1, "top": 2}
    peor = {"nombre": "X", "media": 0.20, "ee": 0.01}
    niveles = [
        A.nivel_exigencia(t, 0.01, 0.40, 0.01, peor, 2.0) for t in np.linspace(0.0, 0.8, 161)
    ]
    r = [rango[n] for n in niveles]
    assert r == sorted(r) and set(niveles) == {"alerta", "corto", "top"}
    umbral_top = 0.40 - 2.0 * np.hypot(0.01, 0.01)
    assert (
        A.nivel_exigencia(umbral_top + 1e-9, 0.01, 0.40, 0.01, peor, 2.0) == "top"
        and A.nivel_exigencia(umbral_top - 1e-3, 0.01, 0.40, 0.01, peor, 2.0) != "top"
    )
    assert A.nivel_exigencia(0.30, 0.01, 0.40, 0.01, peor, 2.0) == "corto"
    assert A.nivel_exigencia(0.10, 0.01, 0.40, 0.01, peor, 2.0) == "alerta"
    assert (
        A.nivel_exigencia(0.10, 0.01, 0.40, 0.01, None, 2.0) == "corto"
    )  # sin el peor técnico real medido no hay «alerta»


def test_almada_siempre_sale_a_la_altura_por_construccion():
    for top in (0.05, 0.3, 0.5, 0.9):
        for ee in (0.0, 0.005, 0.03):
            assert (
                A.nivel_exigencia(
                    top, ee, top, ee, {"nombre": "X", "media": top - 0.1, "ee": ee}, 2.0
                )
                == "top"
            )


def test_el_peor_tecnico_real_sale_de_la_referencia_medida():
    ex = {"tecnicos": {"A": _ref(0.35), "B": _ref(0.12, 0.02), "C": _ref(0.28)}}
    assert A.peor_tecnico_real(ex) == {"nombre": "B", "media": 0.12, "ee": 0.02}
    assert A.peor_tecnico_real(None) is None and A.peor_tecnico_real({}) is None


def test_p_top_nunca_pasa_de_p_liguilla_y_los_lugares_suman_uno(sim8):
    for nombre in sim8.nombres_lista_corta()[:3]:
        R = sim8.simular(sim8.tecnico_preset(nombre), "rapido", con_estilo=False).temporada.resumen
        assert R["p_top"]["media"] <= R["p_liguilla"]["media"] + 1e-12
        assert abs(sum(R["p_lugar"]) - 1.0) <= 1e-9
        assert R["p_top"]["media"] == pytest.approx(
            sum(R["p_lugar"][: config.cargar()["exigencia"]["top"]]), abs=1e-12
        )


@pytest.fixture
def exig_app(dir_v6, monkeypatch, tmp_path, sim8):
    """La app con la referencia de exigencia medida de los técnicos de la lista corta (modo rápido), como la deja la medición de la exigencia."""
    nuevo = tmp_path / "art_ex"
    shutil.copytree(dir_v6, nuevo)
    pf = json.loads((nuevo / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
    tec = {}
    for n in sim8.nombres_lista_corta():
        R = sim8.simular(sim8.tecnico_preset(n), "rapido", con_estilo=False).temporada.resumen
        tec[n] = {
            "p_top": {"media": R["p_top"]["media"], "ee": R["p_top"]["ee"]},
            "p_liguilla": {"media": R["p_liguilla"]["media"], "ee": R["p_liguilla"]["ee"]},
        }
    pf["exigencia"] = {
        "modo": "rapido",
        "top": config.cargar()["exigencia"]["top"],
        "tecnicos": tec,
    }
    (nuevo / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    return _app6(monkeypatch, nuevo)


def test_en_la_app_almada_sale_a_la_altura_y_celebra_y_el_modo_sin_limites_extremo_no(
    exig_app, monkeypatch
):
    at = exig_app
    sel = at.sidebar.selectbox(key="k_preset")
    almada = (
        next(o for o in sel.options if "dirige hoy" in o or "hoy" in o.lower())
        if any("hoy" in o.lower() for o in sel.options)
        else sel.options[1]
    )
    sel.select(almada).run()
    _boton(at, T.BOTON_SIMULAR).click().run()
    assert not at.exception
    t = _texto(at)
    assert T.EXIGENCIA["top"][1] in t and "exigencia-top" in t
    assert T.TARJETA_TOP.format(n=config.cargar()["exigencia"]["top"]) in t and T.NIVELES_NOTA in t
    assert not hasattr(T, "BANNER_LIGUILLA")  # v11 (D-094): la franja de celebración ya no existe
    # sin límites, todo a −300: un estilo que nadie ha usado
    at.sidebar.selectbox(key="k_preset").select(
        at.sidebar.selectbox(key="k_preset").options[0]
    ).run()  # «Crea tu propio técnico» es la primera opción
    at.sidebar.toggle(key="k_ilim").set_value(True).run()
    from simdt.app import principal

    for k in mejes.CLAVES_EJES:
        at.sidebar.slider(key=principal.LLAVES[k] + "_u").set_value(-300)
    at.run()
    _boton(at, T.BOTON_SIMULAR).click().run()
    t = _texto(at)
    assert "exigencia-top" not in t and ("exigencia-alerta" in t or "exigencia-corto" in t)


# ================================================================ Fase D: simular sin congelar la app, con progreso real (D-084)
def _esperar(job, tope=240):
    import time

    t0 = time.time()
    while job.estado == "corriendo" and time.time() - t0 < tope:
        time.sleep(0.05)
    return job


def test_la_simulacion_por_bloques_da_exactamente_lo_mismo_que_la_de_un_solo_bloque(sim8):
    t = sim8.tecnico_preset(sim8.p.meta["tecnico_actual_foco"])
    uno = sim8.simular(t, "rapido")
    for tam in (7, 30, 64):
        varios = sim8.simular(t, "rapido", tam_bloque=tam)
        a, b = uno.temporada.resumen, varios.temporada.resumen
        assert abs(a["puntos_esperados"] - b["puntos_esperados"]) < 1e-12
        assert np.abs(np.array(a["p_lugar"]) - np.array(b["p_lugar"])).max() < 1e-12
        assert (
            abs(a["p_top"]["media"] - b["p_top"]["media"]) < 1e-12
            and abs(a["p_liguilla"]["media"] - b["p_liguilla"]["media"]) < 1e-12
        )
        assert (uno.temporada.puntos == varios.temporada.puntos).all() and (
            uno.temporada.posicion == varios.temporada.posicion
        ).all()
        for k in ("ga", "gb", "pts", "lugar"):  # «Gira un torneo» muestra los mismos torneos
            assert (
                uno.temporada.interno["torneos_muestra"][k]
                == varios.temporada.interno["torneos_muestra"][k]
            ).all()
        for k, v in uno.estilo.items():
            if not isinstance(v, (dict, list)) or k in ("pi", "pi_rival"):
                assert np.allclose(
                    np.asarray(v, dtype=float),
                    np.asarray(varios.estilo[k], dtype=float),
                    atol=1e-12,
                ), k


@pytest.mark.asincrono
def test_el_progreso_es_monotono_termina_en_100_y_las_cifras_salen_de_r_s_y_el_calendario(sim8):
    from simdt.trabajo import Tarea, Trabajo

    t = sim8.tecnico_preset(sim8.p.meta["tecnico_actual_foco"])
    j = Trabajo(sim8, [Tarea("objetivo", t, "rapido", True)])
    assert j.progreso == 0.0 and j.restante() is None
    vistos = []
    j.iniciar()
    while j.estado == "corriendo":
        vistos.append(j.progreso)
        _esperar(j, 0.02)
    _esperar(j)
    vistos.append(j.progreso)
    assert (
        j.estado == "listo"
        and vistos == sorted(vistos)
        and vistos[-1] == 1.0
        and j.hechos == j.total >= 2
    )
    c = sim8.cifras_modo("preciso")
    s = config.cargar()["simulacion"]["preciso"]
    assert (
        c["torneos"] == s["R"] * s["S"]
        and c["partidos_por_torneo"] == len(sim8.calendario)
        and c["partidos"] == c["torneos"] * c["partidos_por_torneo"]
    )


@pytest.mark.asincrono
def test_cancelar_deja_un_estado_valido_sin_resultados_a_medias(sim8):
    from simdt.trabajo import Tarea, Trabajo

    t = sim8.tecnico_preset(sim8.p.meta["tecnico_actual_foco"])
    j = Trabajo(sim8, [Tarea("objetivo", t, "preciso", True)]).iniciar()
    j.cancelar()
    _esperar(j)
    assert j.estado == "cancelado" and j.resultados == {} and j.progreso < 1.0
    assert (
        sim8.simular(t, "rapido").temporada.resumen["puntos_esperados"] > 0
    )  # el simulador sigue sirviendo


@pytest.mark.asincrono
def test_dos_sesiones_simultaneas_no_se_mezclan(sim8):
    from simdt.trabajo import Tarea, Trabajo

    nombres = sim8.nombres_lista_corta()
    ta, tb = sim8.tecnico_preset(nombres[0]), sim8.tecnico_preset(nombres[2])
    sola_a = sim8.simular(ta, "rapido").temporada.resumen["puntos_esperados"]
    sola_b = sim8.simular(tb, "rapido").temporada.resumen["puntos_esperados"]
    ja, jb = (
        Trabajo(sim8, [Tarea("objetivo", ta, "rapido", True)]).iniciar(),
        Trabajo(sim8, [Tarea("objetivo", tb, "rapido", True)]).iniciar(),
    )
    _esperar(ja), _esperar(jb)
    assert ja.estado == jb.estado == "listo"
    assert (
        ja.resultados["objetivo"].temporada.resumen["puntos_esperados"] == sola_a
        and jb.resultados["objetivo"].temporada.resumen["puntos_esperados"] == sola_b
    )


def test_no_hay_esperas_artificiales_en_el_codigo():
    import re as _re

    for f in (config.RAIZ_SIM / "src" / "simdt").rglob("*.py"):
        assert "time.sleep" not in f.read_text(encoding="utf-8"), f
    css_js = (config.RAIZ_SIM / "src" / "simdt" / "app" / "animacion.py").read_text(
        encoding="utf-8"
    )
    assert "sleep" not in css_js


@pytest.mark.asincrono
def test_en_la_app_simular_no_bloquea_cancelar_funciona_y_el_resultado_llega(app8, sim8):
    at = app8
    at.sidebar.segmented_control(key="k_precision").set_value(T.OPCIONES_PRECISION[1])
    _boton(at, T.BOTON_SIMULAR).click().run()
    assert not at.exception
    j = at.session_state["trabajo"]
    assert (
        j.estado in ("corriendo", "listo")
        and "resultado" not in at.session_state
        or j.estado == "listo"
    )
    if j.estado == "corriendo":
        assert any(
            T.SIM_TITULO.split("{")[0] in m.value for m in at.sidebar.markdown
        )  # el título del avance, con cifras reales
        at.button(key="b_cancelar").click().run()
        _esperar(j)
        at.run()
        assert j.estado == "cancelado" and "resultado" not in at.session_state and not at.exception
        assert any(T.SIM_CANCELADA in m.value for m in at.sidebar.markdown)
    at.sidebar.segmented_control(key="k_precision").set_value(T.OPCIONES_PRECISION[0])
    _boton(at, T.BOTON_SIMULAR).click().run()
    j2 = at.session_state["trabajo"]
    _esperar(j2)
    at.run()
    assert j2.estado == "listo" and "resultado" in at.session_state and not at.exception


# ================================================================ Fase E: «¿Le podemos creer?» con nombres clásicos e hipótesis explícitas (D-087)
from simdt.validacion import tarjetas as VT  # noqa: E402

NOMBRES_CLASICOS = {
    "goles": "χ² de bondad de ajuste de Pearson",
    "puntos": "Regresión lineal simple",
    "calibracion": "Hosmer-Lemeshow",
    "independencia": "Autocorrelación de los residuos",
    "placebo": "Prueba de permutación",
    "recuperacion": "Cobertura de intervalos bootstrap",
    "retro": "Diebold-Mariano",
    "partido": "χ² de bondad de ajuste",
}


def test_cada_tarjeta_trae_pregunta_prueba_clasica_h0_h1_y_aqui_queremos():
    assert set(T.CARTAS) == set(NOMBRES_CLASICOS)
    for k, c in T.CARTAS.items():
        for campo in (
            "titulo",
            "clasica",
            "hipotesis0",
            "hipotesis1",
            "queremos",
            "mide",
            "tec",
            "pasa",
            "ojo",
            "tipo",
        ):
            assert c[campo], (k, campo)
        assert NOMBRES_CLASICOS[k].lower() in c["clasica"].lower(), k
    assert (
        T.CREER_CLASICA == "Prueba clásica:"
        and T.CREER_H0 == "H0"
        and T.CREER_H1 == "H1"
        and T.CREER_QUEREMOS == "Aquí queremos…"
    )
    assert (
        T.CREER_NO_RECHAZAR
        == "No rechazar H0 no demuestra que sea cierta: dice que los datos no encontraron diferencia."
    )
    assert {k for k, c in T.CARTAS.items() if c["cero_bueno"]} == {
        "independencia",
        "placebo",
    }  # aquí el 0 dentro es buena noticia
    assert T.CREER_CERO_BUENO == "Aquí el 0 dentro es buena noticia: significa que no hay efecto."
    assert (
        "Durbin-Watson" in T.CARTAS["independencia"]["clasica"]
        and "Ljung-Box" in T.CARTAS["independencia"]["clasica"]
        and "Harvey" in T.CARTAS["retro"]["clasica"]
    )


def test_los_veredictos_siguen_la_regla_de_su_fila_con_numeros_sinteticos():
    g = {
        "bins": [0, 1, 2, 3, 4, 5],
        "simulado": [0.25, 0.35, 0.25, 0.1, 0.04, 0.01],
        "real": [0.25, 0.35, 0.25, 0.1, 0.04, 0.01],
    }
    assert VT.goles(g, 1701)["pasa"]  # χ² con p > 0.05
    g2 = {**g, "real": [0.35, 0.25, 0.25, 0.1, 0.04, 0.01]}
    assert not VT.goles(g2, 1701)["pasa"]
    x = np.linspace(10, 40, 60)
    rng = np.random.default_rng(1)
    bien = [{"predichos": float(a), "reales": float(a + rng.normal(0, 4))} for a in x]
    aplanado = [
        {"predichos": float(a), "reales": float(25 + 1.5 * (a - 25) + rng.normal(0, 2))} for a in x
    ]
    assert (
        VT.puntos(bien, 0.001)["pasa"] and not VT.puntos(aplanado, 0.001)["pasa"]
    )  # que el rango de la pendiente incluya el 1
    assert VT.puntos(bien, 0.5)[
        "pasa"
    ]  # el error de puntos totales se muestra; no cambia la regla de la fila
    cal_bien = {
        "ganar": [
            {"n": 500, "predicha": 0.3, "observada": 0.31},
            {"n": 500, "predicha": 0.6, "observada": 0.59},
        ]
    }
    cal_mal = {
        "ganar": [
            {"n": 500, "predicha": 0.3, "observada": 0.45},
            {"n": 500, "predicha": 0.6, "observada": 0.5},
        ]
    }
    assert (
        VT.calibracion(cal_bien)["pasa"] and not VT.calibracion(cal_mal)["pasa"]
    )  # Hosmer-Lemeshow, p > 0.05
    assert VT.independencia({"autocorrelacion_lag1": -0.01, "autocorrelacion_ic95": [-0.05, 0.03]})[
        "pasa"
    ]
    assert not VT.independencia(
        {"autocorrelacion_lag1": 0.08, "autocorrelacion_ic95": [0.03, 0.13]}
    )["pasa"]  # el rango debe CONTENER el 0
    assert VT.placebo({"placebos": [{"contiene_cero": True}] * 3, "todos_contienen_cero": True})[
        "pasa"
    ]
    assert not VT.placebo(
        {
            "placebos": [{"contiene_cero": True}, {"contiene_cero": False}],
            "todos_contienen_cero": False,
        }
    )["pasa"]
    assert (
        VT.recuperacion({"fraccion_dentro": 0.93, "n_pares": 15, "detalle": []})["pasa"]
        and not VT.recuperacion({"fraccion_dentro": 0.40, "n_pares": 15, "detalle": []})["pasa"]
    )
    base = {
        "n": 50,
        "mae_inercia": 0.38,
        "rmse_simulador": 0.45,
        "rmse_inercia": 0.5,
        "dm_estadistico": -1.3,
    }
    assert (
        VT.retro({**base, "mae_simulador": 0.37, "dm_p": 0.195})["pasa"] is False
    )  # mejor pero sin rechazar H0 (hoy: ⚠️ → «describe estilos»)
    assert VT.retro({**base, "mae_simulador": 0.30, "dm_p": 0.01})["pasa"] is True
    assert VT.retro({**base, "mae_simulador": 0.40, "dm_p": 0.01})["pasa"] is False
    av = {
        "chi2": 5.0,
        "gl": 6,
        "n": 5000,
        "frecuencias": [0.4, 0.3, 0.3],
        "exactas": [0.4, 0.3, 0.3],
    }
    assert VT.partido({**av, "p": 0.26})["pasa"] and not VT.partido({**av, "p": 0.03})["pasa"]


def test_con_los_numeros_medidos_de_e_los_veredictos_son_los_que_dicen_las_hipotesis():
    """E: goles p = 0.91 ✅, pendiente 1.50 [1.30, 1.71] ⚠️, HL p < 0.001 ⚠️, rachas −0.009 [−0.05, 0.03] ✅, placebo 3 de 3 ✅, recuperación 93 % ✅, DM p = 0.195 ⚠️."""
    assert VT.independencia(
        {"autocorrelacion_lag1": -0.009, "autocorrelacion_ic95": [-0.05, 0.03]}
    )["pasa"]
    assert VT.placebo({"placebos": [{"contiene_cero": True}] * 3, "todos_contienen_cero": True})[
        "pasa"
    ]
    assert VT.recuperacion({"fraccion_dentro": 0.93, "n_pares": 15, "detalle": []})["pasa"]
    assert not VT.retro(
        {
            "n": 50,
            "mae_simulador": 0.371,
            "mae_inercia": 0.381,
            "dm_p": 0.195,
            "dm_estadistico": -1.3,
        }
    )["pasa"]
    x = np.linspace(10, 40, 180)
    assert not VT.puntos(
        [{"predichos": float(a), "reales": float(25 + 1.5 * (a - 25))} for a in x], 0.0043
    )["pasa"]


JS_CREER = """() => {
    const raiz = document.querySelector('[class*=st-key-rejilla_creer]'); if (!raiz) return null;
    const cartas = [...raiz.children].map(w => w.firstElementChild);
    const visible = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT); let min = 999, n = 0; const chicas = [];
    while (w.nextNode()) { const t = w.currentNode; if (!t.textContent.trim() || !visible(t.parentElement)) continue; const f = parseFloat(getComputedStyle(t.parentElement).fontSize); n++; if (f < min) min = f; if (f < 12.95) chicas.push([t.textContent.trim().slice(0, 30), f]); }
    const huecos = cartas.map(c => { const h = c.getBoundingClientRect().height; const hs = [...c.children].map(x => x.getBoundingClientRect()); let v = 0;
        for (let i = 1; i < hs.length; i++) { const g = hs[i].top - hs[i - 1].bottom; if (g > 40) v += g; } return {alto: h, vacio: v / h, texto: c.innerText.slice(0, 30)}; });
    return {n, min, chicas, huecos, textos: cartas.map(c => c.innerText), ancho: window.innerWidth, scroll: document.documentElement.scrollWidth,
            der: Math.max(...cartas.map(c => c.getBoundingClientRect().right)), izq: Math.min(...cartas.map(c => c.getBoundingClientRect().left))};
}"""


@pytest.mark.skipif(_navegador() is None, reason="sin Playwright o sin navegador: se salta")
@pytest.mark.parametrize("ancho", [1440, 390])
def test_las_ocho_pruebas_letra_minima_poco_espacio_vacio_y_con_sus_hipotesis(ancho):
    import os
    import time
    from playwright.sync_api import sync_playwright

    val = (
        config.ARTEFACTOS
        if (config.ARTEFACTOS / "graficas_validacion.json").exists()
        else config.VALIDACION
    )
    if not (val / "graficas_validacion.json").exists():
        pytest.skip("sin graficas_validacion.json (sin validación versionada)")
    proc, puerto = _servidor({"SIMDT_VALIDACION": str(val)})
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
            pg.wait_for_selector("[class*=st-key-antes_heroe]", timeout=240000)
            pg.locator("[role=tab]").nth(2).evaluate("e => e.click()")
            pg.wait_for_selector("[class*=st-key-rejilla_creer]", timeout=60000)
            pg.wait_for_timeout(4000)
            r = pg.evaluate(JS_CREER)
            b.close()
    finally:
        proc.terminate()
    assert r["min"] >= 12.95 and not r["chicas"], r["chicas"][:5]
    assert len(r["textos"]) == 8
    for t in r["textos"]:
        assert "Prueba clásica:" in t and "H0" in t and "H1" in t and "Aquí queremos" in t, t[:80]
    assert all(h["vacio"] <= 0.25 for h in r["huecos"]), [
        (h["texto"], round(h["vacio"], 2)) for h in r["huecos"]
    ]
    assert r["izq"] >= -1 and r["der"] <= r["ancho"] + 1 and r["scroll"] <= r["ancho"] + 1


# ================================================================ Fase F: momentum en barras por minuto (D-088; en la v10, la presión de cada equipo, D-093)
# (v11, D-096: «90 barras por lado» se retira: ahora es UNA barra por minuto; lo cubre `test_la_grafica_tiene_una_serie_de_90_barras…` de tests/test_app_v11.py)


# ================================================================ Fase G: partido con más eventos, honesto (D-085)
def test_las_proporciones_de_fin_de_jugada_salen_de_la_cadena_y_suman_uno(sim8):
    from simdt.modelos.cadena import proporciones_fin

    L = sim8.p.liga
    f = proporciones_fin(
        np.asarray(L.P_cadenas),
        np.asarray(L.mu_cadenas),
        None if L.P0_cadenas is None else np.asarray(L.P0_cadenas),
    )
    assert f.shape == (3, 3) and np.allclose(f.sum(1), 1.0) and (f >= 0).all()


def test_los_goles_siguen_siendo_poisson_de_mu_con_el_partido_de_mas_eventos(piezas):
    _, Ci, Cj = piezas
    n = 20000
    for t, m in ((10, 1), (70, 0)):
        g = J.minuto(Ci, Cj, t, np.full(n, m), np.random.default_rng(31 + t))["goles_i"]
        mu = Ci.mu[t, m]
        assert abs(g.mean() - mu) < 3 * np.sqrt(mu / n) and abs(g.var(ddof=1) - mu) < 3 * np.sqrt(
            (mu + 2 * mu**2) / n
        )


@pytest.fixture(scope="module")
def cinco_mil(sim8):
    t = sim8.tecnico_preset(sim8.p.meta["tecnico_actual_foco"])
    Ci, Cj, _ = A.componentes_partido(sim8, t, 3, True, 5)
    return Ci, Cj, J.simular_partidos(Ci, Cj, 5000, np.random.default_rng(20261021))


def test_en_5000_partidos_los_saques_de_pelota_parada_coinciden_con_lo_esperado_dentro_de_3_ee(
    cinco_mil,
):
    Ci, Cj, r = cinco_mil
    for lado, C in (("i", Ci), ("j", Cj)):
        esperado = C.saques.sum(
            0
        )  # Σ_t r̄_u(t)·(ajuste de ficha y de localía): no depende del marcador
        x = r[f"saques_{lado}"]
        for u in range(x.shape[1]):
            ee = x[:, u].std(ddof=1) / np.sqrt(len(x))
            assert abs(x[:, u].mean() - esperado[u]) < 3 * max(ee, 1e-9), (
                lado,
                u,
                x[:, u].mean(),
                esperado[u],
            )


def test_en_5000_partidos_las_jugadas_por_tipo_y_su_fin_coinciden_con_la_cadena_dentro_de_3_ee(
    cinco_mil, sim8
):
    from simdt.motor.partido import distribucion_partido

    Ci, Cj, r = cinco_mil
    d = distribucion_partido(Ci.mu, Cj.mu)
    occ = {"i": d.ocupacion[0], "j": d.ocupacion[0][:, ::-1]}
    for lado, C in (("i", Ci), ("j", Cj)):
        esp_jug = np.einsum(
            "tm,tmk->k", occ[lado], C.n_k
        )  # jugadas esperadas por tipo (con la ocupación exacta del marcador)
        x = r[f"jugadas_{lado}"]
        for k in range(x.shape[1]):
            assert abs(x[:, k].mean() - esp_jug[k]) < 3 * x[:, k].std(ddof=1) / np.sqrt(len(x)), (
                lado,
                k,
            )
        no_rem = np.einsum(
            "tm,tmk,k->k", occ[lado], C.n_k, 1.0 - C.p
        )  # jugadas esperadas que NO terminan en remate, por tipo
        esperado = (no_rem[:, None] * C.fin_k).sum(
            0
        ) / no_rem.sum()  # fracción esperada de pérdida, fuera e interrupción
        obs = r[f"fin_{lado}"].sum(0)
        N = obs.sum()
        assert abs(N / len(r[f"fin_{lado}"]) - no_rem.sum()) < 3 * r[f"fin_{lado}"].sum(1).std(
            ddof=1
        ) / np.sqrt(len(r[f"fin_{lado}"]))
        for c in range(3):
            p = esperado[c]
            assert abs(obs[c] / N - p) < 3 * np.sqrt(p * (1 - p) / N), (
                lado,
                c,
                obs[c] / N,
                p,
            )  # el reparto sigue a la cadena de la liga


def test_las_estadisticas_del_partido_son_coherentes(sim8):
    t = sim8.tecnico_preset(sim8.p.meta["tecnico_actual_foco"])
    for semilla in range(12):
        p = A.partido_unico(sim8, t, 3, True, semilla, muestra=5)
        for lado in ("america", "rival"):
            e = p["estadisticas"][lado]
            assert (
                set(A.BP_CLAVES) <= set(e)
                and e["remates"] >= 0
                and e["directa"] + e["toque"] + e["elaborada"] > 0
            )
            assert (
                e["gol_abierto"] + e["remate_sin_gol"] + e["perdidas"] + e["fuera_interrupcion"]
                == e["directa"] + e["toque"] + e["elaborada"]
            )  # cada jugada termina en algo
            assert e["remate_sin_gol"] >= 0 and e["gol_abierto"] <= e["remates"]
        assert (
            p["remates_america"] == p["estadisticas"]["america"]["remates"]
            and p["remates_rival"] == p["estadisticas"]["rival"]["remates"]
        )


def test_el_panel_de_estadisticas_dice_la_frase_honesta_y_oculta_los_contadores_fuera_de_5_por_ciento(
    dir_v6, monkeypatch, tmp_path, sim6
):
    from simdt.app import principal

    t = sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"])
    p = A.partido_unico(sim6, t, 3, True, 5, muestra=5)
    grupos = principal.estadisticas_para_panel(sim6, p)
    etiquetas = [e for _, filas in grupos for e, _, _ in filas]
    assert (
        T.PARTIDO_STATS["corner"] in etiquetas
        and T.PARTIDO_STATS["penal"] in etiquetas
        and T.TIPOS_JUGADA[0] in etiquetas
    )
    nuevo = tmp_path / "art_ocultos"
    shutil.copytree(dir_v6, nuevo)
    pf = json.loads((nuevo / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
    pf["exigencia"] = {
        "contadores": {
            "corner": {"real": 5.0, "simulado": 5.4, "dif_pct": 8.0, "ok": False},
            "penal": {"real": 0.1, "simulado": 0.1, "dif_pct": 1.0, "ok": True},
        }
    }
    (nuevo / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    s2 = Simulador(nuevo)
    et2 = [e for _, filas in principal.estadisticas_para_panel(s2, p) for e, _, _ in filas]
    assert (
        T.PARTIDO_STATS["corner"] not in et2
        and T.PARTIDO_STATS["penal"] in et2
        and T.PARTIDO_STATS["remates"] in et2
    )
    assert (
        T.PARTIDO_HONESTO
        == "El torneo usa exactamente estas reglas, pero calculadas de forma exacta, sin sortear jugada por jugada, para que sea rápido."
    )
    at = _app6(monkeypatch, dir_v6)
    _boton(at, T.BOTON_SIMULAR).click().run()
    at.button(key="b_partido").click().run()
    t_ = _texto(at)
    assert T.PARTIDO_STATS_TITULO in t_ and T.PARTIDO_HONESTO in t_ and 'class="est-fila"' in t_


def test_las_cifras_del_progreso_se_dicen_con_sus_numeros_exactos():
    from simdt.app import principal

    assert (
        principal._cifra_partidos(50_000 * 153) == "7.6 millones de partidos"
    )  # 7,650,000: se trunca, no se redondea hacia arriba
    assert principal._cifra_partidos(10_000 * 153) == "1.5 millones de partidos"
    assert principal._cifra_partidos(900_000) == "900,000 partidos"
    assert (
        principal._tiempo(0.2) == "1 s"
        and principal._tiempo(59.1) == "60 s"
        or principal._tiempo(59.1) == "1 min 0 s"
    )
    assert principal._tiempo(125) == "2 min 5 s"
