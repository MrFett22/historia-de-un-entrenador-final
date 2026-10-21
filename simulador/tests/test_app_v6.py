"""App v6 (D-065 a D-072): selector con técnicos fijos, «¿Qué pesa más?» con medición directa, calificación que no contradice al simulador, mapa de estilos, «Ver un partido» con peligro
de gol minuto a minuto, precisión explicada, «Antes de jugar» y la validación en ocho tarjetas; más lo que viene de la v5 (modo sin límites, carta, tabla final, «Gira un torneo», ficha
completa, animaciones suaves). Corre con una copia de los artefactos versionados (sin calibrar de nuevo); el modelo y la calibración NO cambian.
"""

from __future__ import annotations

import json
import re
import shutil

import numpy as np
import pytest
from scipy import stats

from simdt import analisis as A
from simdt import artefactos, config
from simdt.app import animacion as AN
from simdt.app import componentes as C
from simdt.app import paleta as PA
from simdt.app import textos as T
from simdt.estimacion import lista_corta as lc
from simdt.perillas import ejes as mejes
from simdt.servicio import CREA, Simulador
from simdt.validacion import dispersion as DSP

SIN_ARTEFACTOS = not (config.ARTEFACTOS / "meta.json").exists()
pytestmark = pytest.mark.skipif(SIN_ARTEFACTOS, reason="sin artefactos")
VAL_REPO = config.VALIDACION
SOLO_ESTILO = ["cambios_momento", "cambios_tipo", "reaccion_marcador", "reaccion_rival"]
DISPERSION = {
    "var_real": {"valor": 60.9, "ic95": [48.0, 70.0]},
    "var_azar": {"valor": 27.8, "ic95": [26.9, 28.6]},
    "sd_fuerza_real": {"valor": 5.75, "ic95": [4.47, 6.33]},
    "sd_fuerza_modelo": {"valor": 3.79, "ic95": [3.37, 3.96]},
    "r": {"valor": 1.52, "ic95": [1.23, 1.70], "p_h0": 0.0, "rechaza_h0": True},
    "azar_sobre_real": {"valor": 0.46, "ic95": [0.41, 0.58]},
    "piso_en_cero": False,
    "n_torneos": 10,
    "n_equipo_torneo": 180,
    "n_boot": 2000,
}


@pytest.fixture(scope="module")
def dir_v6(tmp_path_factory):
    d = tmp_path_factory.mktemp("art_v6")
    shutil.copytree(config.ARTEFACTOS, d, dirs_exist_ok=True)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    meta["atribucion"] = "continua"
    meta["perillas_solo_estilo"] = SOLO_ESTILO
    p = artefactos.cargar(d)
    th = {t: v.mean(0) for t, v in p.piezas.theta_tec.items()}
    sig = np.median(p.piezas.sigma[:, :, 0], axis=0)
    vig = meta["tecnico_actual_foco"]
    ant = next(x["nombre"] for x in p.presets if "Jardine" in x["nombre"])
    out = lc.calcular(
        p.presets, th, sig, {x["nombre"]: x["partidos"] for x in p.presets}, None, vig, ant
    )
    meta["lista_corta"] = out["meta"]
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    presets = lc.aplicar(p.presets, out)
    (d / "presets.json").write_text(
        json.dumps(presets, ensure_ascii=False, default=float), encoding="utf-8"
    )
    perfil = {
        "version": 1,
        "n_referencia": 40,
        "min_partidos": 30,
        "tecnicos": {
            x["nombre"]: {
                "partidos": x["partidos"],
                "metricas": {
                    k: {"valor": 1.0, "pct": 85.0 if k == "presion" else 50.0}
                    for k in T.PERFIL_ORDEN
                },
            }
            for x in presets
            if x.get("lista_corta")
        },
        "perilla_defensa": {"nombre": T.DEFIENDE_PRESION, "decision": "relación clara"},
        "efecto_perillas": {
            "ataca": {"delta": 4.0, "nivel": "mucho"},
            "defiende": {"delta": 1.5, "nivel": "algo"},
            "pp_contra": {"delta": 0.3, "nivel": "nada"},
            "pp_favor": {"delta": 2.0, "nivel": "algo"},
        },
        "tipos_fuente": {
            "archivo": "mezcla_K3.npz",
            "pi": [0.354, 0.263, 0.383],
            "toques": [3.6, 6.7, 9.2],
            "remate": [14.0, 2.6, 12.2],
            "goles100": [2.1, 0.4, 1.9],
        },
        "dispersion": DISPERSION,
    }
    (d / "perfiles_tecnicos.json").write_text(
        json.dumps(perfil, ensure_ascii=False), encoding="utf-8"
    )
    s = Simulador(
        d
    )  # los Δ contra el estilo neutro de la lista corta, como los deja la medición de la dispersión
    perfil["calificacion"] = {
        "modo": "rapido",
        "referencia": "θ = 0 con el plantel del América",
        "tecnicos": A.deltas_reales(s, s.nombres_lista_corta(), "rapido"),
    }
    (d / "perfiles_tecnicos.json").write_text(
        json.dumps(perfil, ensure_ascii=False), encoding="utf-8"
    )
    return d


@pytest.fixture(scope="module")
def sim6(dir_v6):
    return Simulador(dir_v6)


def _app(monkeypatch, d):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(config, "ARTEFACTOS", d)
    monkeypatch.delenv("SIMDT_VALIDACION", raising=False)
    vacia = d.parent / (d.name + "_sin_validacion")
    vacia.mkdir(exist_ok=True)
    monkeypatch.setattr(config, "VALIDACION", vacia)
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=300)
    at.run()
    assert not at.exception
    return at


def _limpio(o: str) -> str:
    return o.replace(f" {T.PRESET_ACTUAL}", "").replace(f" {T.PRESET_ANTECESOR}", "")


def _elegir(at, nombre):
    sel = at.sidebar.selectbox(key="k_preset")
    sel.select(next(o for o in sel.options if _limpio(o) == nombre)).run()


def _boton(at, etiqueta):
    return next(b for b in at.sidebar.button if b.label == etiqueta)


def _texto(at, pestana=1) -> str:
    return "\n".join(m.value for m in at.tabs[pestana].markdown)


# ---------------------------------------------------------------- ¿qué pesa más?


# ---------------------------------------------------------------- refuerzos (D-062)


# ---------------------------------------------------------------- modo sin límites
def test_modo_sin_limites_avisa_con_letras_grandes_y_marca_fuera_de_lo_visto(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    assert T.LIMITES_AVISO_TITULO not in _texto(at)
    at.sidebar.toggle(key="k_ilim").set_value(True).run()
    assert not at.exception
    assert T.LIMITES_AVISO_TITULO in _texto(at) and T.LIMITES_AVISO in _texto(at)
    desliz = at.sidebar.slider(key="k_ataca_u")
    assert (desliz.min, desliz.max) == (-300, 300)
    assert {
        at.sidebar.slider(key=k).max for k in ("k_ataca_u", "k_defiende_u", "k_ppc_u", "k_ppf_u")
    } == {300}
    desliz.set_value(250).run()
    _boton(at, T.BOTON_SIMULAR).click().run()
    assert (
        not at.exception and at.session_state["limites_simulado"] and at.session_state["fuera_zona"]
    )
    t = _texto(at)
    assert T.INSIGNIA_FUERA in t and T.MAPA_FUERA in t
    fig = [json.loads(g.proto.spec) for g in at.get("plotly_chart")]
    mapa = next(
        f
        for f in fig
        if any(a.get("text") == T.MAPA_FUERA for a in f["layout"].get("annotations", []))
    )
    assert (
        mapa["layout"]["xaxis"]["range"][1] > 300
    )  # el mapa se amplía para ver el punto fuera de la zona


def test_al_prender_o_apagar_el_modo_el_tecnico_se_conserva(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    antes = {k: at.sidebar.slider(key=k).value for k in ("k_ataca", "k_defiende")}
    at.sidebar.toggle(key="k_ilim").set_value(True).run()
    at.sidebar.toggle(key="k_ilim").set_value(False).run()
    assert {k: at.sidebar.slider(key=k).value for k in antes} == antes
    sim = Simulador(dir_v6)
    th = sim.tecnico_preset(sim.p.meta["tecnico_actual_foco"]).theta.mean(0)
    for k in mejes.CLAVES_EJES:
        e = sim.ejes[k]
        assert e.limites_de(True) == (-300, 300) and abs(e.posicion(th, True)) <= 300
        # en el modo sin límites ±100 es el técnico real más extremo, igual que en el modo normal para los dos ejes bipolares
        if e.bipolar:
            assert e.posicion(th, True) == e.posicion(th, False)


def test_el_modo_sin_limites_deja_pasar_lo_que_el_normal_acota(dir_v6):
    s = Simulador(dir_v6)
    base = s.tecnico_promedio()
    per = dict(s.perillas_de(base, True))
    per["ataca"] = 300
    t = s.tecnico_perillas(per, base, "x", True)
    th0 = s.ejes["ataca"].z(t.theta)
    assert th0 > s.ejes["ataca"].z_hi * 2.5
    normal = s.tecnico_perillas({**base.perillas, "ataca": 100}, base, "x", False)
    assert s.ejes["ataca"].z(normal.theta) <= s.ejes["ataca"].z_hi + 1e-9
    assert s.fuera_de_la_zona(per, True) and not s.fuera_de_la_zona(base.perillas, False)


# ---------------------------------------------------------------- calificación y carta


def test_se_parece_a_devuelve_un_tecnico_real_solo_dentro_de_la_zona(sim6):
    rng = np.random.default_rng(3)
    for _ in range(25):
        per = {
            "ataca": int(rng.integers(-100, 101)),
            "defiende": int(rng.integers(-100, 101)),
            "pp_contra": int(rng.integers(1, 100)),
            "pp_favor": int(rng.integers(1, 100)),
            "reaccion": str(rng.choice(T.OPCIONES_REACCION)),
            "cambios_momento": int(rng.integers(1, 100)),
            "cambios_tipo": "Mismo puesto",
        }
        c = A.carta(sim6, per)
        assert c["distancia"] >= 0
        assert (
            (c["parecido"] in sim6.ejes.nombres) if c["dentro"] else c["parecido"] is None
        )  # v8: fuera de la zona observada no se nombra a nadie (D-082)
    # el atributo extremo hace que se parezca a alguien distinto de la base
    base = sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"])
    c = A.carta(sim6, {**base.perillas, "ataca": -100, "pp_favor": 1})
    assert not c["es_el_mismo"]


# ---------------------------------------------------------------- partido típico, goles en la cancha, tabla


def test_la_tabla_final_suma_lo_que_debe(sim6):
    t = sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"])
    r = sim6.simular(t, "rapido")
    tb = A.tabla_final(sim6, r)
    nl = config.cargar()["torneo"]["liguilla_directa"]
    assert (
        len(tb) == 18
        and [f["lugar"] for f in tb] == list(range(1, 19))
        and sum(f["foco"] for f in tb) == 1
    )
    assert [f["puntos"] for f in tb] == sorted((f["puntos"] for f in tb), reverse=True)
    assert sum(f["p_liguilla"] for f in tb) == pytest.approx(
        nl, abs=1e-6
    )  # en cada torneo entran exactamente `nl` equipos
    it = r.temporada.interno
    assert sum(f["puntos"] for f in tb) == pytest.approx(
        float(np.mean(it["suma_puntos_liga"])), rel=1e-3
    )
    assert next(f for f in tb if f["foco"])["puntos"] == pytest.approx(
        r.temporada.resumen["puntos_esperados"], rel=0.02
    )


# ---------------------------------------------------------------- gira un torneo y ver un partido
def test_todos_los_torneos_de_la_muestra_dan_una_tabla_valida(sim6):
    t = sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"])
    r = sim6.simular(t, "rapido")
    m = r.temporada.interno["torneos_muestra"]
    n = A.n_torneos_muestra(r)
    assert n > 100
    cal = np.asarray(sim6.calendario)
    for i in range(n):
        g = A.girar_torneo(sim6, r, i)
        assert A.tabla_valida(g["tabla"]), i
        assert len(g["racha"]) == 17 and set(g["racha"]) <= {"G", "E", "P"}
        ga, gb = m["ga"][i].astype(int), m["gb"][i].astype(int)
        assert sum(f["puntos"] for f in g["tabla"]) == 3 * int((ga != gb).sum()) + 2 * int(
            (ga == gb).sum()
        )  # cada partido reparte 3 o 2 puntos
        assert g["tabla"][0]["lugar"] == 1 and g["clasifica"] == (g["lugar"] <= g["liguilla"])
        w, e = g["racha"].count("G"), g["racha"].count("E")
        foco = next(f for f in g["tabla"] if f["foco"])
        assert foco["puntos"] == 3 * w + e and foco["lugar"] == g["lugar"]
    # la tabla de un torneo cualquiera se puede recomputar de los marcadores
    g = A.girar_torneo(sim6, r, 7)
    pts = np.zeros(18, int)
    for p in range(len(cal)):
        a, b = int(m["ga"][7][p]), int(m["gb"][7][p])
        pts[cal[p, 0]] += 3 if a > b else (1 if a == b else 0)
        pts[cal[p, 1]] += 3 if b > a else (1 if a == b else 0)
    assert {f["equipo"]: f["puntos"] for f in g["tabla"]} == {
        sim6.p.meta["equipos"][e]: int(pts[e]) for e in range(18)
    }


def test_gira_un_torneo_no_vuelve_a_simular_y_acumula_el_contador(dir_v6, monkeypatch):
    llamadas = []
    original = Simulador.simular

    def contando(self, *a, **k):
        llamadas.append(1)
        return original(self, *a, **k)

    monkeypatch.setattr(Simulador, "simular", contando)
    at = _app(monkeypatch, dir_v6)
    _boton(at, T.BOTON_SIMULAR).click().run()
    n0 = len(llamadas)
    assert at.session_state["casino"]["giros"] == 0 and T.CASINO_SIN in _texto(at)
    lugares = []
    for _ in range(3):
        at.button(key="b_girar").click().run()
        assert not at.exception
        lugares.append(at.session_state["casino"]["ultimo"]["lugar"])
    assert len(llamadas) == n0  # NO se volvió a simular
    c = at.session_state["casino"]
    assert c["giros"] == 3 and c["mejor"] == min(lugares) and c["peor"] == max(lugares)
    assert T.CASINO_CONTADOR.format(n=3, mejor=min(lugares), peor=max(lugares)) in _texto(at)
    assert A.tabla_valida(c["ultimo"]["tabla"])
    # una simulación nueva reinicia los giros
    _boton(at, T.BOTON_SIMULAR).click().run()
    assert at.session_state["casino"]["giros"] == 0


# ---------------------------------------------------------------- tarjetas, ficha completa, validación
def test_las_tarjetas_miden_contra_el_america_actual_con_verde_y_rojo(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    s = Simulador(dir_v6)
    _elegir(at, s.p.meta["tecnico_actual_foco"])
    _boton(at, T.BOTON_SIMULAR).click().run()
    t = _texto(at)
    assert T.TARJETA_VS in t and "Lugar más probable" not in t
    assert f"= {T.TARJETA_VS_IGUAL}" in t  # el técnico de hoy contra sí mismo: igual
    at.sidebar.selectbox(key="k_preset").select(
        T.PRESET_CREA
    ).run()  # solo «Crea tu propio técnico» deja mover perillas
    at.sidebar.slider(key="k_ataca").set_value(-100).run()
    at.sidebar.slider(key="k_ppf").set_value(1).run()
    _boton(at, T.BOTON_SIMULAR).click().run()
    t = _texto(at)
    assert ("▲" in t or "▼" in t) and (C.VERDE in t or C.ROJO in t)
    pts = at.session_state["resultado"].temporada.resumen["puntos_esperados"]
    base = (
        Simulador(dir_v6)
        .simular(
            Simulador(dir_v6).tecnico_preset(Simulador(dir_v6).p.meta["tecnico_actual_foco"]),
            "rapido",
        )
        .temporada.resumen["puntos_esperados"]
    )
    flecha = "▲" if pts - base >= 0.05 else ("▼" if pts - base <= -0.05 else "=")
    assert re.search(re.escape(flecha) + r"\s*[+−]?<span class=\"num", t) or flecha == "="


def test_los_numeros_traen_el_valor_final_y_se_animan_solo_con_css():
    h = C.numero(26.54, 1)
    assert 'class="est">26.5<' in h and "--fin-ent:26" in h and "--fin-dec:5" in h
    assert C.numero(64.4, 0, "", " %").count("64") >= 2 and C.numero(0.123, 3).count("0.123") == 1
    r = C.numero(
        60.6, 0, "", " %"
    )  # el contador termina en el mismo número que el texto (redondeado, no truncado)
    assert 'class="est">61<' in r and "--fin-ent:61" in r and "--fin-dec:0" in r
    r = C.numero(9.96, 1)
    assert 'class="est">10.0<' in r and "--fin-ent:10" in r and "--fin-dec:0" in r
    css = (config.RAIZ_SIM / "src" / "simdt" / "app" / "estilos.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in css and "animation: none !important" in css
    assert "@supports (animation-composition: replace)" in css and "@property --ent" in css
    assert (
        not re.search(r"animation[^;{]*infinite", css) and "blink" not in css.lower()
    )  # nada parpadea ni se repite


def test_la_ficha_completa_esta_a_la_vista_con_todas_las_metricas_y_colores(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    at.sidebar.slider(key="k_ataca").set_value(-100).run()
    _boton(at, T.BOTON_SIMULAR).click().run()
    t = _texto(at)
    assert T.SECCION_FICHA in t and not list(at.tabs[0].expander)
    for g in T.FICHA_GRUPOS.values():
        assert g in t, g
    for c in T.FICHA_COLUMNAS:
        assert c in t
    assert 'class="der cambio ' in t and T.FICHA_TABLA_TITULO in t
    m = A.metricas(Simulador(dir_v6), at.session_state["resultado"].estilo)
    assert set(m) >= {
        "pi",
        "pi_rival",
        "remates",
        "remates_rival",
        "goles_k_favor",
        "goles_k_contra",
        "bp_favor",
        "bp_contra",
        "min_cambio",
        "tipo_cambio",
    }


def test_textos_de_la_v6_sin_palabras_prohibidas_ni_lenguaje_de_apuestas():
    todo = " ".join(_cadenas(T)).lower()
    for p in ("μ", "intensidad", "momentum", "apuesta", "apostar", "jackpot", "premio", "dinero"):
        assert not re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", todo), p
    assert {"μ", "intensidad", "momentum"} <= set(T.PALABRAS_PROHIBIDAS)
    for nombre in (
        "PESA_TITULO",
        "CARTA_TITULO",
        "SECCION_MAPA",
        "SECCION_GOLES",
        "SECCION_TABLA",
        "CASINO_TITULO",
        "PARTIDO_TITULO",
        "SECCION_FICHA",
        "ANTES_QUE_ES_TITULO",
        "ANTES_QUE_NO_TITULO",
        "ANTES_TIPOS_TITULO",
        "ANTES_FIJOS_TITULO",
        "ANTES_NO_SIMULA_TITULO",
    ):
        assert len(getattr(T, nombre)) <= 60, nombre


def _cadenas(modulo) -> list[str]:
    out = []

    def aplana(v):
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, (tuple, list)):
            for x in v:
                aplana(x)
        elif isinstance(v, dict):
            for x in v.values():
                aplana(x)

    for nombre, v in vars(modulo).items():
        if not nombre.startswith("_") and nombre != "PALABRAS_PROHIBIDAS" and not callable(v):
            aplana(v)
    return out


def test_los_textos_que_se_ven_en_el_simulador_no_traen_palabras_prohibidas(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    _boton(at, T.BOTON_SIMULAR).click().run()
    visibles = re.sub(
        r"<[^>]+>", " ", "\n".join(m.value for t in (at.tabs[1], at.tabs[0]) for m in t.markdown)
    ).lower()
    sin_nombres = visibles
    for n in Simulador(dir_v6).p.meta["equipos"] + list(Simulador(dir_v6).ejes.nombres):
        sin_nombres = sin_nombres.replace(n.lower(), " ")
    for p in T.PALABRAS_PROHIBIDAS:
        assert not re.search(r"(?<!\w)" + re.escape(p.lower()) + r"(?!\w)", sin_nombres), p


def test_la_tabla_de_tipos_usa_los_cuatro_datos_de_la_fuente(dir_v6):
    s = Simulador(dir_v6)
    for k, t in enumerate(s.tipos_de_jugada()):
        assert t["pct"] == pytest.approx([35.4, 26.3, 38.3][k]) and t["toques"] == pytest.approx(
            [3.6, 6.7, 9.2][k]
        )
        assert t["remate"] == pytest.approx([14.0, 2.6, 12.2][k]) and t[
            "goles100"
        ] == pytest.approx([2.1, 0.4, 1.9][k])


# ================================================================ Fase A: selector y técnicos fijos (D-065)
PERILLAS_SLIDER = ("k_ataca", "k_defiende", "k_ppc", "k_ppf", "k_cm")


def test_el_selector_no_dice_promedio_y_la_primera_opcion_es_crear(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    opciones = at.sidebar.selectbox(key="k_preset").options
    assert (
        opciones[0] == T.PRESET_CREA and T.PRESET_CREA == "Crea tu propio técnico"
    )  # v11 (D-099): sin emoji
    assert not any("promedio" in o.lower() for o in opciones) and len(set(opciones)) == len(
        opciones
    )
    sim = Simulador(dir_v6)
    assert [_limpio(o) for o in opciones[1:]] == sim.nombres_lista_corta()[:0] + [
        sim.p.meta["tecnico_actual_foco"]
    ] + [n for n in sim.nombres_lista_corta() if n != sim.p.meta["tecnico_actual_foco"]]


def test_con_un_tecnico_real_todas_las_perillas_estan_bloqueadas_en_su_posicion(
    dir_v6, monkeypatch
):
    at = _app(monkeypatch, dir_v6)
    sim = Simulador(dir_v6)
    for n in sim.nombres_lista_corta():
        _elegir(at, n)
        assert all(at.sidebar.slider(key=k).disabled for k in PERILLAS_SLIDER), n
        assert (
            at.sidebar.select_slider(key="k_reac").disabled
            and at.sidebar.select_slider(key="k_ct").disabled
        )
        esperado = sim.tecnico_preset(n).perillas
        assert (
            at.sidebar.slider(key="k_ataca").value == esperado["ataca"]
            and at.sidebar.slider(key="k_ppf").value == esperado["pp_favor"]
        )
        assert any(T.BLOQUEADO.format(nombre=n) in m.value for m in at.sidebar.markdown)
        assert not [
            t for t in at.sidebar.toggle if t.key == "k_ilim"
        ]  # el modo sin límites solo existe al crear


def test_con_crea_tu_propio_tecnico_todas_las_perillas_estan_habilitadas(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    assert at.sidebar.selectbox(key="k_preset").value == CREA
    assert not any(at.sidebar.slider(key=k).disabled for k in PERILLAS_SLIDER)
    assert (
        not at.sidebar.select_slider(key="k_reac").disabled
        and not at.sidebar.select_slider(key="k_ct").disabled
    )
    assert [t for t in at.sidebar.toggle if t.key == "k_ilim"]
    sim = Simulador(dir_v6)
    neutro = sim.ejes.posiciones(np.zeros(32))
    assert (
        at.sidebar.slider(key="k_ataca").value == neutro["ataca"]
        and at.sidebar.slider(key="k_defiende").value == neutro["defiende"]
    )
    todo = " ".join(m.value for m in at.sidebar.markdown)
    assert T.CREA_NOTA in todo and "promedio" not in todo.lower()


def test_lo_que_inventas_se_guarda_al_mirar_un_tecnico_real(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    at.sidebar.slider(key="k_ataca").set_value(-60).run()
    _elegir(at, Simulador(dir_v6).p.meta["tecnico_actual_foco"])
    assert at.sidebar.slider(key="k_ataca").value != -60
    at.sidebar.selectbox(key="k_preset").select(T.PRESET_CREA).run()
    assert at.sidebar.slider(key="k_ataca").value == -60


def test_un_tecnico_real_simulado_dos_veces_con_la_misma_semilla_da_delta_cero(sim6):
    """T-T5: mismos números aleatorios, mismo técnico, Δ idéntico a 0."""
    from simdt.motor.comparar import comparar

    n = sim6.nombres_lista_corta()[1]
    a = sim6.simular(sim6.tecnico_preset(n), "rapido", con_estilo=False)
    b = sim6.simular(sim6.tecnico_preset(n), "rapido", con_estilo=False)
    c = comparar(a.temporada, b.temporada)
    assert (
        c.resumen["media"] == 0.0
        and c.resumen["int90"] == [0.0, 0.0]
        or max(abs(x) for x in c.resumen["int90"]) < 1e-9
    )


def test_refuerzos_otro_plantel_y_tecnico_promedio_ya_no_existen_en_ninguna_parte():
    from pathlib import Path

    raiz = config.RAIZ_SIM / "src" / "simdt"
    prohibidas = (
        "Refuerzos",
        "refuerzos",
        "otro plantel",
        "técnico promedio",
        "Un técnico promedio",
        "delta_plantel",
        "sensibilidad_plantel",
        "k_ref",
    )
    for f in list((raiz / "app").glob("*.py")) + [
        raiz / "servicio.py",
        raiz / "analisis.py",
        raiz / "tipos.py",
    ]:
        t = f.read_text(encoding="utf-8")
        for x in prohibidas:
            assert x not in t, (f.name, x)
    for x in ("Refuerzos", "otro plantel", "técnico promedio", "Técnico promedio"):
        assert x not in " ".join(_cadenas(T)), x
    assert "k_ref" not in " ".join(
        k for k in Path(raiz / "app" / "principal.py").read_text(encoding="utf-8").split()
    )


# ================================================================ Fase B: dispersión (D-066)
def _sintetico(rng, SD=6.0, va=21.0, k=0.6, T=10, n=18):
    import pandas as pd

    filas = []
    for t in range(T):
        s = rng.normal(0, SD, n)
        e = rng.normal(0, np.sqrt(va), n)
        filas.append(
            pd.DataFrame(
                {
                    "torneo": f"T{t}",
                    "equipo": range(n),
                    "reales": 25 + s + e,
                    "predichos": 25 + k * s + rng.normal(0, 0.5, n),
                    "var_azar": va * rng.uniform(0.9, 1.1, n),
                }
            )
        )
    return pd.concat(filas)


def test_la_dispersion_recupera_la_fuerza_real_dentro_de_su_rango_en_al_menos_90_por_ciento_de_50_repeticiones():
    rng = np.random.default_rng(1)
    dentro = 0
    for i in range(50):
        r = DSP.dispersion(_sintetico(rng), n_boot=400, semilla=i)
        lo, hi = r["sd_fuerza_real"]["ic95"]
        dentro += lo <= 6.0 <= hi
    assert dentro / 50 >= 0.90, dentro / 50


def test_el_modelo_que_aplana_tiene_r_mayor_que_1_y_el_que_no_aplana_no_rechaza_h0():
    rng = np.random.default_rng(2)
    plano = DSP.dispersion(_sintetico(rng, k=0.6), n_boot=500)
    assert plano["r"]["valor"] > 1.3 and plano["r"]["rechaza_h0"] and plano["r"]["p_h0"] < 0.01
    rechazos = 0  # con un modelo que NO aplana, H0 casi nunca se rechaza
    for i in range(20):
        exacto = DSP.dispersion(_sintetico(rng, k=1.0), n_boot=200, semilla=i)
        rechazos += exacto["r"]["rechaza_h0"]
    assert rechazos <= 5, rechazos
    assert (
        0 < plano["azar_sobre_real"]["valor"] < 1
        and plano["n_equipo_torneo"] == 180
        and plano["n_torneos"] == 10
    )
    con_pendiente = DSP.dispersion(_sintetico(rng, k=0.6), n_boot=300, pendiente_ic95=[1.3, 1.71])
    assert con_pendiente["consistente_con_pendiente"] is True


def test_si_la_varianza_real_es_menor_que_la_del_azar_la_fuerza_es_cero_y_se_reporta():
    import pandas as pd

    rng = np.random.default_rng(3)
    df = pd.concat(
        [
            pd.DataFrame(
                {
                    "torneo": f"T{t}",
                    "equipo": range(18),
                    "reales": 25 + rng.normal(0, 2, 18),
                    "predichos": 25 + rng.normal(0, 1, 18),
                    "var_azar": 30.0,
                }
            )
            for t in range(10)
        ]
    )
    r = DSP.dispersion(df, n_boot=200)
    assert (
        r["piso_en_cero"] is True
        and r["sd_fuerza_real"]["valor"] == 0.0
        and r["sd_fuerza_real"]["ic95"][0] == 0.0
    )


def test_la_varianza_de_los_puntos_de_un_partido_es_la_exacta():
    g, e = 0.45, 0.27
    p = np.array([g, e, 1 - g - e])
    pts = np.array([3, 1, 0])
    assert DSP.var_puntos_partido(g, e) == pytest.approx(
        float((p * pts**2).sum() - (p * pts).sum() ** 2)
    )
    import pandas as pd

    partidos = pd.DataFrame(
        {
            "local": ["A", "B"],
            "visitante": ["B", "A"],
            "torneo": ["T", "T"],
            "goles_local": [2, 0],
            "goles_visitante": [1, 0],
        }
    )
    x = DSP.tabla_de_puntos(partidos, [0.5, 0.4], [0.25, 0.3], [1.75, 1.5], [0.8, 1.2])
    a = x[x.equipo == "A"].iloc[0]
    assert a.reales == 3 + 1 and a.partidos == 2 and a.predichos == pytest.approx(1.75 + 1.2)
    assert a.var_azar == pytest.approx(
        DSP.var_puntos_partido(0.5, 0.25) + DSP.var_puntos_partido(1 - 0.4 - 0.3, 0.3)
    )


def test_la_tarjeta_de_puntos_dice_que_el_simulador_acorta_y_muestra_r(
    dir_v6, monkeypatch, tmp_path
):
    g = (
        json.loads((VAL_REPO / "graficas_validacion.json").read_text(encoding="utf-8"))
        if (VAL_REPO / "graficas_validacion.json").exists()
        else None
    )
    if g is None:
        pytest.skip("sin validación versionada")
    from simdt.validacion import tarjetas as VT

    v = (
        json.loads((VAL_REPO / "validacion.json").read_text(encoding="utf-8"))
        if (VAL_REPO / "validacion.json").exists()
        else None
    )
    c = VT.puntos(g["puntos"], (v or {}).get("calibracion", {}).get("error_xpts"))
    assert (
        "ojo" in T.CARTAS["puntos"]
        and "acorta las diferencias" in T.CARTAS["puntos"]["ojo"]
        and "Es un límite conocido" in T.CARTAS["puntos"]["ojo"]
    )
    assert "{r}" in T.CARTAS["puntos"]["r_linea"] and c["n"] > 0


# ================================================================ Fase C: calificación que no contradice al simulador (D-067)
def test_el_mapa_de_calificacion_es_creciente_con_el_signo_del_delta_y_spearman_1():
    rng = np.random.default_rng(4)
    d = rng.normal(0.1, 1.2, 40)
    f = A.mapa_calificacion(list(d))
    cal = np.array([f(x) for x in d])
    assert (np.sign(cal - 5) == np.sign(d)).all()  # el signo de (calificación − 5) es el del Δ
    assert stats.spearmanr(cal, d)[0] == pytest.approx(1.0)
    assert (
        f(0.0) == pytest.approx(5.0)
        and f(d.max()) == pytest.approx(10.0)
        and f(d.min()) == pytest.approx(0.0)
    )
    assert f(d.max() + 5) == 10.0 and f(d.min() - 5) == 0.0
    assert all(f(a) <= f(b) for a, b in zip(np.sort(d), np.sort(d)[1:]))


def test_la_calificacion_de_los_tecnicos_reales_coincide_en_signo_con_su_delta(sim6):
    cal = A.calificaciones_reales(sim6)
    assert set(cal) == set(sim6.nombres_lista_corta())
    d = np.array([v["delta"] for v in cal.values()])
    c = np.array([v["calif"] for v in cal.values()])
    assert (np.sign(c - 5.0) == np.sign(d)).all()
    assert stats.spearmanr(c, d)[0] == pytest.approx(1.0)
    for v in cal.values():
        assert v["rango"][0] <= v["calif"] <= v["rango"][1] and v["cruza"] == (
            v["rango"][0] <= 5.0 <= v["rango"][1]
        )


def test_el_color_se_pone_solo_si_el_rango_no_cruza_el_centro_y_nunca_es_rojo_con_delta_positivo():
    assert (
        A.color_calificacion(5.4, cruza=True) == A.COLOR_NEUTRO
        and A.color_calificacion(2.0, cruza=True) == A.COLOR_NEUTRO
    )
    esperados = {
        0.5: "rojo",
        3.4: "rojo",
        3.5: "rojo",
        4.9: "rojo",
        5.0: "amarillo",
        6.9: "amarillo",
        7.0: "amarillo",
        8.9: "amarillo",
        9.0: "amarillo",
        10.0: "amarillo",
    }  # v11 (D-097)
    for x, c in esperados.items():
        assert A.color_calificacion(x) == c, x
    f = A.mapa_calificacion([-2.0, -1.0, -0.2, 0.05, 0.4, 1.1, 1.8])
    assert (
        A.color_calificacion(f(0.05)) != "rojo"
    )  # un Δ positivo, aunque chico, nunca sale en rojo


def test_un_tecnico_con_delta_positivo_y_rango_que_cruza_el_cero_no_sale_en_rojo_en_la_app(
    dir_v6, monkeypatch, tmp_path
):
    """Jardine en E: Δ +0.05, rango [−2.44, 2.53]. La carta lo pone en gris y dice que no se puede separar del promedio."""
    sim = Simulador(dir_v6)
    nuevo = tmp_path / "art"
    shutil.copytree(dir_v6, nuevo)
    pf = json.loads((dir_v6 / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
    nombres = sim.nombres_lista_corta()
    fijos = {
        nombres[0]: (1.8, [0.6, 3.0]),
        nombres[1]: (0.05, [-2.44, 2.53]),
        nombres[2]: (-1.5, [-2.8, -0.2]),
        nombres[3]: (0.4, [-1.0, 1.9]),
        nombres[4]: (-0.3, [-1.9, 1.2]),
        nombres[5]: (1.1, [-0.4, 2.6]),
    }
    pf["calificacion"]["tecnicos"] = {n: {"delta": d, "ic90": ic} for n, (d, ic) in fijos.items()}
    (nuevo / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    at = _app(monkeypatch, nuevo)
    cal = A.calificaciones_reales(Simulador(nuevo))
    assert cal[nombres[1]]["cruza"] and cal[nombres[1]]["calif"] > 5.0
    _elegir(at, nombres[1])
    t = _texto(at)
    assert (
        T.CALIF_NO_SEPARA in t
        and PA.color(A.COLOR_NEUTRO) in t
        and PA.color("rojo") not in t.split(T.CARTA_TITULO)[1].split(T.SECCION_MAPA)[0]
    )
    assert T.CALIF_AVISO in t
    _elegir(at, nombres[0])  # Δ > 0 con el rango arriba del 5: color de verdad
    t = _texto(at)
    assert (
        T.CALIF_NO_SEPARA not in t.split(T.CARTA_TITULO)[1].split(T.SECCION_MAPA)[0]
        and PA.color(
            A.color_calificacion(
                cal[nombres[0]]["calif"], cal[nombres[0]]["cruza"], cal[nombres[0]]["seguridad"]
            )
        )
        in t
    )
    _elegir(at, nombres[2])  # Δ < 0 con el rango abajo del 5
    assert cal[nombres[2]]["calif"] < 5.0 and PA.color(
        A.color_calificacion(
            cal[nombres[2]]["calif"], cal[nombres[2]]["cruza"], cal[nombres[2]]["seguridad"]
        )
    ) in _texto(at)


def test_la_calificacion_de_tu_tecnico_es_estimada_hasta_que_simulas_y_luego_trae_su_rango(
    dir_v6, monkeypatch
):
    at = _app(monkeypatch, dir_v6)
    at.sidebar.slider(key="k_ataca").set_value(-80).run()
    t = _texto(at)
    assert T.CALIF_ESTIMADA in t and PA.color(A.COLOR_NEUTRO) in t
    _boton(at, T.BOTON_SIMULAR).click().run()
    cc = at.session_state["calif_creada"]
    cal = A.calificacion_de_delta(Simulador(dir_v6), cc["delta"], cc["ic90"])
    t = _texto(at)
    assert T.CALIF_ESTIMADA not in t.split(T.CARTA_TITULO)[1].split(T.SECCION_MAPA)[0]
    assert T.CALIF_RANGO.format(a=f"{cal['rango'][0]:.1f}", b=f"{cal['rango'][1]:.1f}") in t
    at.sidebar.slider(key="k_ataca").set_value(
        -20
    ).run()  # cambia la perilla: la calificación vuelve a ser estimada
    assert T.CALIF_ESTIMADA in _texto(at)


def test_la_carta_en_la_app_se_mueve_con_cualquier_perilla_sin_simular(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    t0 = _texto(at)
    assert T.CARTA_TITULO in t0 and "resultado" not in at.session_state
    for llave, valor in (
        ("k_ataca", -95),
        ("k_defiende", 80),
        ("k_ppc", 5),
        ("k_ppf", 95),
        ("k_cm", 5),
    ):
        at.sidebar.slider(key=llave).set_value(valor).run()
        t1 = _texto(at)
        assert t1 != t0, llave
        t0 = t1
    at.sidebar.select_slider(key="k_reac").set_value("Nunca").run()
    assert _texto(at) != t0
    radar = [
        json.loads(g.proto.spec) for g in at.get("plotly_chart") if '"scatterpolar"' in g.proto.spec
    ]
    assert radar and len(radar[0]["data"]) == 1


# ================================================================ Fase D: mapa de estilos explicado (D-068)
def test_el_mapa_sombrea_la_densidad_sin_grupos_ni_fronteras_y_dice_nombre_y_calificacion(
    dir_v6, monkeypatch
):
    at = _app(monkeypatch, dir_v6)
    mapa = next(
        json.loads(g.proto.spec)
        for g in at.get("plotly_chart")
        if any(t.get("name") == T.MAPA_TECNICO for t in json.loads(g.proto.spec)["data"])
    )
    tipos = [t["type"] for t in mapa["data"]]
    assert "heatmap" in tipos and not {"contour", "histogram2dcontour", "densitymap"} & set(
        tipos
    )  # sombreado suave, sin curvas de nivel ni fronteras
    assert (
        sum(1 for t in mapa["data"] if t.get("fill") == "toself") == 1
    )  # solo la zona (la figura que encierra a los técnicos reales)
    assert not mapa["layout"].get("shapes")
    assert any("%{customdata}" in t.get("hovertemplate", "") for t in mapa["data"])
    fuente = list((config.RAIZ_SIM / "src" / "simdt" / "app").glob("*.py")) + [
        config.RAIZ_SIM / "src" / "simdt" / "analisis.py"
    ]
    assert not any(
        re.search(
            r"kmeans|KMeans|AgglomerativeClustering|silhouette", f.read_text(encoding="utf-8")
        )
        for f in fuente
    )
    califs = A.calificaciones_reales(Simulador(dir_v6))
    nombre = next(iter(califs))
    textos = [x for t in mapa["data"] if t.get("customdata") is not None for x in t["customdata"]]
    assert T.MAPA_PUNTO_CALIF.format(nombre=nombre, c=f"{califs[nombre]['calif']:.1f}") in textos


def test_la_ayuda_del_mapa_explica_los_ejes_y_la_zona_en_lenguaje_simple(
    dir_v6, monkeypatch, tmp_path
):
    from simdt.app import principal

    sim = Simulador(dir_v6)
    ayuda = principal._ayuda_mapa(sim)
    assert (
        T.MAPA_AYUDA_X in ayuda
        and T.MAPA_AYUDA_Y_PRESION in ayuda
        and T.MAPA_AYUDA_ZONA in ayuda
        and "la figura más chica" in ayuda
        and "Afuera" in ayuda
    )
    nuevo = tmp_path / "art"
    shutil.copytree(dir_v6, nuevo)
    pf = json.loads((nuevo / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
    pf["perilla_defensa"] = {"nombre": T.DEFIENDE, "decision": "sin relación clara"}
    (nuevo / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    assert "presión real" not in principal._ayuda_mapa(
        Simulador(nuevo)
    )  # no se afirma que se parece a la presión real si los datos no lo dicen


def test_la_densidad_es_un_sombreado_normalizado(sim6):
    xs, ys, Z = A.densidad_tecnicos(sim6.ejes.puntos)
    Z = np.array(Z)
    assert Z.shape == (len(ys), len(xs)) and Z.max() == pytest.approx(1.0) and Z.min() >= 0


# ================================================================ Fase E: «Ver un partido» con peligro de gol minuto a minuto (D-069)
def test_el_partido_sorteado_se_parece_al_calculo_exacto_en_5000_partidos(sim6):
    t = sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"])
    av = A.autoverificacion_partido(sim6, t, 3, True, 5000, 20261020)
    assert av["n"] == 5000
    assert max(abs(z) for z in av["z_resultados"]) < 3, av[
        "z_resultados"
    ]  # G, E y P a ≤ 3 errores estándar de la distribución exacta
    assert max(abs(z) for z in av["z_goles"]) < 3, av[
        "z_goles"
    ]  # goles medios de cada lado contra E[goles] exacto
    assert av["p"] > 0.01 and av["pasa"], (
        av
    )  # χ² de los marcadores (4+ agrupados) contra el cálculo exacto


def test_con_la_misma_semilla_sale_el_mismo_partido_y_con_otra_no(sim6):
    t = sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"])
    a = A.partido_unico(sim6, t, 3, True, 11, muestra=5)
    b = A.partido_unico(sim6, t, 3, True, 11, muestra=5)
    c = A.partido_unico(sim6, t, 3, True, 12, muestra=5)
    assert a == b and (a["goles"], a["peligro_america"]) != (c["goles"], c["peligro_america"])


def test_ver_un_partido_en_la_app_trae_las_barras_y_el_cierre_de_cien_partidos(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    _boton(at, T.BOTON_SIMULAR).click().run()
    t = _texto(at)
    assert "¿Cómo se juega un partido típico?" not in t and not hasattr(
        T, "SECCION_MOMENTUM"
    )  # el partido típico ya no es una gráfica aparte
    at.button(key="b_partido").click().run()
    assert not at.exception
    p = at.session_state["partido"]
    assert (
        len(p["peligro_america"]) == len(p["peligro_rival"]) == p["minutos"] == 90
        and p["semilla"] is not None
    )
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
            "cien": T.PARTIDO_FINAL.format(x=44),
            "remates": "r",
        },
    )
    assert (
        'id="graf"' in html
        and "dominio" in html
        and "En 100 partidos así, el América gana 44" in html
        and "prefers-reduced-motion" in html
    )


# ================================================================ Fase F: precisión y enlaces (D-072)


def test_el_boton_del_reporte_md_es_un_link_a_github(dir_v6, monkeypatch):
    enlaces = config.cargar()["enlaces"]
    assert (
        enlaces["validacion"]
        == "https://github.com/MrFett22/historia-de-un-entrenador-final/blob/main/docs/VALIDACION.md"
    )
    assert (
        enlaces["estudio_original"]
        == "https://github.com/MrFett22/historia-de-un-entrenador-final/blob/main/docs/MODELO.md"
    )
    fuente = (config.RAIZ_SIM / "src" / "simdt" / "app" / "principal.py").read_text(
        encoding="utf-8"
    )
    assert "download_button" not in fuente and "link_button" in fuente


# ================================================================ Fase G: «Antes de jugar» (D-070)
def test_antes_de_jugar_va_primero_en_este_orden_y_el_boton_lleva_al_simulador(dir_v6, monkeypatch):
    at = _app(monkeypatch, dir_v6)
    assert [t.label for t in at.tabs] == [T.PESTANA_ANTES, T.PESTANA_SIMULADOR, T.PESTANA_CREER]
    antes = _texto(at, 0)
    orden = [
        T.PESA_TITULO,
        T.ANTES_QUE_ES_TITULO,
        T.ANTES_QUE_NO_TITULO,
        T.ANTES_FIJOS_TITULO,
        T.ANTES_NIVELES_TITULO,
        T.ANTES_TIPOS_TITULO,
        T.ANTES_PERILLAS_TITULO,
        T.ANTES_NO_SIMULA_TITULO,
    ]
    pos = [antes.index(x) for x in orden]
    assert pos == sorted(pos), dict(zip(orden, pos))
    for parte in T.ANTES_QUE_ES + T.ANTES_NO_SIMULA + T.ANTES_FIJOS:
        assert parte in antes
    assert not any(
        b.key == "b_vamos" for b in at.button
    )  # v11 (D-094): el botón «¡Vamos a jugar!» ya no existe
    assert (
        len(set(re.findall(r'class="c-titulo">([^<]+)<', antes))) >= 8
    )  # una idea por tarjeta (v8: el héroe, cuatro cortas, tipos, perillas y lo que no simula)


def test_las_frases_de_antes_de_jugar_son_cortas_y_sin_jerga():
    todo = (
        list(T.ANTES_QUE_ES)
        + list(T.ANTES_QUE_NO)
        + list(T.ANTES_FIJOS)
        + list(T.ANTES_NO_SIMULA)
        + [T.ANTES_CIERRE, T.ANTES_TIPOS_INTRO]
    )
    for f in todo:
        assert len(f.split()) <= 16, f
    assert all(len(v.split()) <= 18 for _, (_, c, sm) in T.FICHAS.items() for v in (c, sm))


# ================================================================ Fase H: validación en ocho tarjetas (D-071)
def test_cada_tarjeta_de_validacion_tiene_pregunta_h0_estadistico_numero_veredicto_y_que_significa():
    assert set(T.CARTAS) == {
        "goles",
        "puntos",
        "calibracion",
        "independencia",
        "placebo",
        "recuperacion",
        "retro",
        "partido",
    }
    for k, c in T.CARTAS.items():
        for campo in ("titulo", "hipotesis0", "mide", "tec", "pasa", "ojo", "tipo"):
            assert c[campo], (k, campo)
        assert c["tipo"] == ("dificil" if k == "retro" else "facil")
        assert (
            "?" in c["titulo"] or k == "retro"
        )  # v11 (D-099): sin emoji al final; la prueba difícil no es pregunta
        assert "IC 95 %" not in c["mide"] and "p " not in c["mide"].split("?")[0].replace(
            "¿", ""
        )  # lo técnico va solo en letra chica
    assert (
        "casualidad" in T.CARTAS["goles"]["mide"]
        and "Acorta o exagera" in T.CARTAS["puntos"]["mide"]
        or "acorta o exagera" in T.CARTAS["puntos"]["mide"].lower()
    )


def test_un_rango_que_toca_el_centro_tampoco_se_separa_del_promedio(dir_v6):
    """Crea en el centro: Δ ≡ 0 y rango 5.0 a 5.0. Toca el 5, así que va neutro (no verde)."""
    c = A.calificacion_de_delta(Simulador(dir_v6), 0.0, [0.0, 0.0])
    assert c["calif"] == 5.0 and c["rango"] == [5.0, 5.0] and c["cruza"]
    assert A.color_calificacion(c["calif"], c["cruza"]) == A.COLOR_NEUTRO
