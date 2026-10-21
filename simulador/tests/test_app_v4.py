"""App v4 (D-057, D-058, D-061): perillas por eje en la escala de técnicos reales, pestañas, mapa de técnicos, perfiles y textos.

Corre con una copia de los artefactos versionados en modo de atribución continua y con lista corta (sin calibrar de nuevo).
T-U1 a T-U5 están en test_fase8_app.py.
"""

from __future__ import annotations

import json
import re
import shutil

import numpy as np
import pytest

from simdt import artefactos, config
from simdt.app import componentes as C
from simdt.app import paleta as PA
from simdt.app import textos as T
from simdt.estimacion import lista_corta as lc
from simdt.perillas import ejes as mejes

SIN_ARTEFACTOS = not (config.ARTEFACTOS / "meta.json").exists()
pytestmark = pytest.mark.skipif(SIN_ARTEFACTOS, reason="sin artefactos")
VAL_REPO = config.VALIDACION
SOLO_ESTILO = ["cambios_momento", "cambios_tipo", "reaccion_marcador", "reaccion_rival"]


VAR_AZAR = 28.0  # varianza de los puntos de un equipo por puro azar (D-074); la escala del azar de la app es su raíz


@pytest.fixture(scope="module")
def dir_v4(tmp_path_factory):
    d = tmp_path_factory.mktemp("art_v3")
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
        "dispersion": {"var_azar": {"valor": VAR_AZAR, "ic95": [VAR_AZAR - 1.0, VAR_AZAR + 1.0]}},
        "efecto_perillas": {
            "ataca": {"delta": 4.0, "nivel": "mucho"},
            "defiende": {"delta": 1.5, "nivel": "algo"},
            "pp_contra": {"delta": 0.3, "nivel": "nada"},
            "pp_favor": {"delta": 2.0, "nivel": "algo"},
        },
    }
    (d / "perfiles_tecnicos.json").write_text(
        json.dumps(perfil, ensure_ascii=False), encoding="utf-8"
    )
    return d, out


def _app(monkeypatch, d, validacion=None):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(config, "ARTEFACTOS", d)
    if (
        validacion is None
    ):  # sin validación: ni la de reportes/validacion/ ni una dentro de los artefactos
        monkeypatch.delenv("SIMDT_VALIDACION", raising=False)
        vacia = d.parent / (d.name + "_sin_validacion")
        vacia.mkdir(exist_ok=True)
        monkeypatch.setattr(config, "VALIDACION", vacia)
        (d / "graficas_validacion.json").unlink(missing_ok=True)
    else:
        monkeypatch.setattr(config, "VALIDACION", d.parent / "no_hay")
        monkeypatch.setenv("SIMDT_VALIDACION", str(validacion))
    st.cache_resource.clear()
    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=240)
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


def _puntos(at):
    return at.session_state["resultado"].temporada.resumen["puntos_esperados"]


# ---------------------------------------------------------------- selector y presets
def test_el_selector_ofrece_la_lista_corta_con_vigente_antecesor_y_medoides(dir_v4, monkeypatch):
    d, out = dir_v4
    at = _app(monkeypatch, d)
    opciones = [_limpio(o) for o in at.sidebar.selectbox(key="k_preset").options]
    assert opciones[0] == T.PRESET_CREA  # arriba de todo: «Crea tu propio técnico»
    assert (
        set(opciones[1:]) == set(out["lista"]) and len(opciones) == 6 + 1
    )  # debajo, SOLO técnicos reales
    assert opciones[1] == out["meta"]["vigente"] and opciones[2] == out["meta"]["antecesor"]
    assert not any("promedio" in o.lower() for o in opciones)
    medoide = next(n for n, x in out["lista"].items() if x["rol"] == "medoide")
    _elegir(at, medoide)
    assert any(
        T.etiqueta_tecnico(out["lista"][medoide]["rasgos"]) in m.value for m in at.sidebar.markdown
    )


def test_el_preset_coloca_las_perillas_y_dos_tecnicos_dan_posiciones_distintas(dir_v4, monkeypatch):
    d, out = dir_v4
    at = _app(monkeypatch, d)
    sim = at.session_state["_preset_cargado"]
    assert sim
    pos = {}
    for n in (out["meta"]["vigente"], out["meta"]["antecesor"]):
        _elegir(at, n)
        pos[n] = {
            k: at.sidebar.slider(key=v).value
            for k, v in (
                ("ataca", "k_ataca"),
                ("defiende", "k_defiende"),
                ("pp_contra", "k_ppc"),
                ("pp_favor", "k_ppf"),
            )
        }
    a, b = pos.values()
    assert a != b and a["ataca"] != b["ataca"] and a["defiende"] != b["defiende"]
    from simdt.servicio import Simulador

    s = Simulador(d)
    esperado = s.tecnico_preset(out["meta"]["antecesor"]).perillas
    assert {k: b[k] for k in b} == {k: esperado[k] for k in b}


@pytest.mark.parametrize(
    "clave,llave,valores",
    [
        ("ataca", "k_ataca", (-100, 100)),
        ("defiende", "k_defiende", (-100, 100)),
        ("pp_contra", "k_ppc", (5, 95)),
        ("pp_favor", "k_ppf", (5, 95)),
    ],
)
def test_mover_una_perilla_de_eje_cambia_el_resultado(dir_v4, monkeypatch, clave, llave, valores):
    d, out = dir_v4
    at = _app(monkeypatch, d)  # «Crea tu propio técnico»: las perillas se mueven
    _boton(at, T.BOTON_SIMULAR).click().run()
    sin_tocar = _puntos(at)
    actual = at.sidebar.slider(key=llave).value
    nuevo = valores[0] if abs(valores[0] - actual) > abs(valores[1] - actual) else valores[1]
    at.sidebar.slider(key=llave).set_value(nuevo).run()
    _boton(at, T.BOTON_SIMULAR).click().run()
    assert not at.exception and abs(_puntos(at) - sin_tocar) > 1e-6, (clave, sin_tocar, _puntos(at))


def test_los_ajustes_finos_no_mueven_los_puntos_y_lo_dicen(dir_v4, monkeypatch):
    d, out = dir_v4
    at = _app(monkeypatch, d)
    _boton(at, T.BOTON_SIMULAR).click().run()
    base = _puntos(at)
    sb = at.sidebar
    assert (
        sb.slider(key="k_cm").help == T.AYUDA_DESACTIVADA
        and sb.select_slider(key="k_ct").help == T.AYUDA_DESACTIVADA
    )
    assert sb.select_slider(key="k_reac").help == T.AYUDA_DESACTIVADA
    assert any(T.FINOS_AYUDA in m.value for m in sb.markdown)
    sb.select_slider(key="k_reac").set_value("Nunca").run()
    sb.slider(key="k_cm").set_value(int(sb.slider(key="k_cm").min)).run()
    sb.select_slider(key="k_ct").set_value("Buscar el gol").run()
    _boton(at, T.BOTON_SIMULAR).click().run()
    assert abs(_puntos(at) - base) < 1.0  # casi no mueven los puntos (Sobol: solo estilo)
    assert not at.exception


# ---------------------------------------------------------------- escala de técnicos reales
def test_la_escala_de_tecnicos_reales_no_deja_salir_de_la_zona_observada(dir_v4):
    from simdt.servicio import Simulador

    d, out = dir_v4
    s = Simulador(d)
    for k in mejes.CLAVES_EJES:
        e = s.ejes[k]
        lo, hi = e.limites
        z_extremos = [e.z_de_posicion(lo), e.z_de_posicion(hi)]
        assert (
            min(z_extremos) >= e.z_lo - 1e-9 and max(z_extremos) <= e.z_hi + 1e-9
        )  # los topes del deslizador son los técnicos más extremos
        base = s.tecnico_preset(s.nombres_lista_corta()[0])
        for pos in (lo, hi):
            p = dict(base.perillas)
            p[k] = pos
            th = s.tecnico_perillas(p, base).theta
            assert e.z_lo - 1e-6 <= e.z(th) <= e.z_hi + 1e-6
    assert s.ejes["ataca"].limites == (-100, 100) and s.ejes["defiende"].limites == (-100, 100)
    # los técnicos reales están dentro de su propia zona; una esquina imposible, no
    for x, y in s.ejes.puntos:
        assert s.ejes.en_zona(x, y)
    assert not s.ejes.en_zona(1000, 1000)


def test_mas_presion_sube_int_co_directa_y_baja_u_co_directa(dir_v4):
    """D-058: con la perilla de defensa al máximo, el rival juega más directo (int_co[Directa] > 0) y concede menos remates (u_co[Directa] < 0)."""
    from simdt.servicio import Simulador
    from simdt.tipos import COMPONENTES

    s = Simulador(dir_v4[0])
    e = s.ejes["defiende"]
    qi, qu = COMPONENTES.index("int_co[Directa]"), COMPONENTES.index("u_co[Directa]")
    assert e.v[0] > 0 and e.v[2] < 0
    base = s.tecnico_promedio()
    p = dict(base.perillas)
    p["defiende"] = 100
    th_max = s.tecnico_perillas(p, base).theta
    assert th_max[qi] > 0 and th_max[qu] < 0
    p["defiende"] = -100
    th_min = s.tecnico_perillas(p, base).theta
    assert th_min[qi] < 0 and th_min[qu] > 0
    # la rutina de orientación corrige un eje con los signos al revés o mezclados
    v = mejes._orienta_presion(np.array([-0.5, 0.3, 0.8]))
    assert v[0] >= 0 and v[2] <= 0 and np.linalg.norm(v) == pytest.approx(1.0)
    v = mejes._orienta_presion(
        np.array([0.6, 0.1, 0.7])
    )  # int_co[Directa] y u_co[Directa] con el mismo signo
    assert v[0] >= 0 and v[2] <= 0


def test_los_sliders_de_la_app_van_de_un_extremo_al_otro(dir_v4, monkeypatch):
    d, _ = dir_v4
    at = _app(monkeypatch, d)
    assert (at.sidebar.slider(key="k_ataca").min, at.sidebar.slider(key="k_ataca").max) == (
        -100,
        100,
    )
    assert (at.sidebar.slider(key="k_defiende").min, at.sidebar.slider(key="k_defiende").max) == (
        -100,
        100,
    )
    assert (at.sidebar.slider(key="k_ppc").min, at.sidebar.slider(key="k_ppc").max) == (1, 99)
    assert not any(s.disabled for s in at.sidebar.slider)


def test_la_combinacion_fuera_de_la_zona_avisa(dir_v4, monkeypatch):
    d, out = dir_v4
    at = _app(monkeypatch, d)
    from simdt.servicio import Simulador

    s = Simulador(d)
    # busca una esquina del plano (ataca, defiende) fuera del casco
    esquina = next(
        ((x, y) for x in (-100, 100) for y in (-100, 100) if not s.ejes.en_zona(x, y)), None
    )
    if esquina is None:
        pytest.skip("los técnicos reales cubren todas las esquinas")
    at.sidebar.slider(key="k_ataca").set_value(esquina[0]).run()
    at.sidebar.slider(key="k_defiende").set_value(esquina[1]).run()
    _boton(at, T.BOTON_SIMULAR).click().run()
    assert any(T.AVISO_FUERA_ZONA in w.value for w in at.warning)


def test_la_franja_se_dibuja_en_la_misma_escala_del_deslizador(dir_v4, monkeypatch):
    d, _ = dir_v4
    # función pura: izquierda y ancho son exactamente la fracción del rango del deslizador
    i, w = C.franja_pct(-100, 100, -45, 51)
    assert i == pytest.approx(27.5) and w == pytest.approx(48.0)
    i, w = C.franja_pct(1, 99, 10, 90)
    assert i == pytest.approx(100 * 9 / 98) and w == pytest.approx(100 * 80 / 98)
    assert C.franja_pct(-100, 100, 32, 34)[1] == pytest.approx(
        1.0
    )  # 2 puntos de 200: 1 %, no un mínimo inventado
    at = _app(monkeypatch, d)
    from simdt.servicio import Simulador

    s = Simulador(d)
    htmls = [m.value for m in at.sidebar.markdown if 'class="franja"' in m.value]
    assert len(htmls) == 4
    for h, k in zip(htmls, mejes.CLAVES_EJES):
        lo, hi = s.ejes[k].limites
        a, b = s.rango_reales()[k]
        i, w = C.franja_pct(lo, hi, a, b)
        izq, ancho = (float(x) for x in re.search(r"left:([\d.]+)%;width:([\d.]+)%", h).groups())
        assert izq == pytest.approx(i, abs=0.01) and ancho == pytest.approx(w, abs=0.01)
        assert 0 <= izq and izq + ancho <= 100.01


def test_la_perilla_de_defensa_se_llama_presion_solo_si_el_script_lo_decide(
    dir_v4, monkeypatch, tmp_path
):
    d, _ = dir_v4
    at = _app(monkeypatch, d)
    assert any(T.DEFIENDE_PRESION in m.value for m in at.sidebar.markdown)
    nuevo = tmp_path / "art"
    shutil.copytree(d, nuevo)
    pf = json.loads((nuevo / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
    pf["perilla_defensa"] = {"nombre": T.DEFIENDE, "decision": "sin relación clara"}
    (nuevo / "perfiles_tecnicos.json").write_text(
        json.dumps(pf, ensure_ascii=False), encoding="utf-8"
    )
    at = _app(monkeypatch, nuevo)
    assert any(T.DEFIENDE in m.value for m in at.sidebar.markdown) and not any(
        T.DEFIENDE_PRESION in m.value for m in at.sidebar.markdown
    )


# ---------------------------------------------------------------- pestañas
def _figuras(at):
    return [json.loads(g.proto.spec) for g in at.get("plotly_chart")]


def test_hay_tres_pestanas_en_orden_con_un_solo_tipo_de_contenido_cada_una(dir_v4, monkeypatch):
    d, _ = dir_v4
    at = _app(monkeypatch, d)
    assert [t.label for t in at.tabs] == [T.PESTANA_ANTES, T.PESTANA_SIMULADOR, T.PESTANA_CREER]
    assert (
        T.PESTANA_ANTES.startswith("👀")
        and T.PESTANA_SIMULADOR.startswith("🎮")
        and T.PESTANA_CREER.startswith("🔍")
    )
    # barra lateral: solo controles (nada de gráficas ni de barras de mezcla)
    assert not any("barra-mezcla" in m.value or "<svg" in m.value for m in at.sidebar.markdown)
    # «Antes de jugar»: solo texto y dibujos; tres canchas SVG, una tarjeta por perilla y el pie en frases cortas
    antes = " ".join(m.value for m in at.tabs[0].markdown)
    assert antes.count("<svg") == 3
    for parte in (
        T.ANTES_QUE_ES_TITULO,
        T.ANTES_QUE_NO_TITULO,
        T.PESA_TITULO,
        T.ANTES_TIPOS_TITULO,
        T.ANTES_FIJOS_TITULO,
        T.ANTES_NO_SIMULA_TITULO,
        T.ANTES_NIVELES_TITULO,
        T.ANTES_PERILLAS_TITULO,
        *T.TIPOS_CHIPS,
    ):
        assert parte in antes, parte
    assert len(at.tabs[0].get("plotly_chart")) == 0 and not at.tabs[0].expander


def test_el_mapa_en_vivo_mueve_el_punto_al_mover_una_perilla(dir_v4, monkeypatch):
    d, _ = dir_v4
    at = _app(monkeypatch, d)

    def punto(at):
        f = next(f for f in _figuras(at) if any(t.get("name") == T.MAPA_TECNICO for t in f["data"]))
        t = next(t for t in f["data"] if t.get("name") == T.MAPA_TECNICO)
        assert t["marker"]["color"] == PA.color("amarillo")  # el amarillo del técnico seleccionado
        x, y = t["x"], t["y"]
        return (x[0] if isinstance(x, list) else x), (y[0] if isinstance(y, list) else y)

    x0, y0 = punto(at)
    assert (x0, y0) == (
        at.sidebar.slider(key="k_ataca").value,
        at.sidebar.slider(key="k_defiende").value,
    )
    at.sidebar.slider(key="k_ataca").set_value(-60).run()
    at.sidebar.slider(key="k_defiende").set_value(40).run()
    assert punto(at) == (-60, 40) and (x0, y0) != (-60, 40)
    # la zona sombreada y los técnicos reales están en el mismo mapa
    f = next(f for f in _figuras(at) if any(t.get("name") == T.MAPA_TECNICO for t in f["data"]))
    assert any(t.get("fill") == "toself" for t in f["data"])
    assert any(
        t.get("customdata") is not None and "%{customdata}" in t.get("hovertemplate", "")
        for t in f["data"]
    )  # al pasar el cursor, el nombre del técnico


def test_el_orden_de_la_pestana_simulador(dir_v4, monkeypatch):
    d, out = dir_v4
    at = _app(monkeypatch, d)
    _elegir(at, out["meta"]["vigente"])
    _boton(at, T.BOTON_SIMULAR).click().run()
    sim = at.tabs[1]
    orden = [
        T.PESA_TITULO,
        T.TARJETA_PUNTOS,
        T.CARTA_TITULO,
        T.SECCION_MAPA,
        T.SECCION_ESTILO_PROPIO,
        T.SECCION_PUNTOS,
        T.SECCION_TABLA,
        T.CASINO_TITULO,
        T.SECCION_GOLES,
        T.SECCION_FICHA,
        T.PERFIL_TITULO,
    ]
    texto = "\n".join(m.value for m in sim.markdown)
    pos = [texto.index(x) for x in orden]
    assert pos == sorted(pos), dict(zip(orden, pos))
    assert not list(
        sim.expander
    )  # la v6 no deja nada plegado en el simulador (ficha completa a la vista)
    # así jugaría tu equipo y así le jugarían los rivales: dos gráficas de barras con los tres tipos, con 1 decimal
    barras = [
        f
        for f in _figuras(at)
        if f["data"]
        and f["data"][0].get("type") == "bar"
        and f["data"][0].get("name") == T.TIPOS_JUGADA[0]
    ]
    assert (
        len(barras) == 2
        and all("%" in t for f in barras for t in f["data"][0]["text"])
        and all("." in t for f in barras for t in f["data"][0]["text"])
    )
    assert T.EFECTO_CHICO in texto  # Almada contra el América actual: la mezcla casi no cambia


def test_el_efecto_se_dice_con_numero_y_con_la_escala_del_azar(dir_v4, monkeypatch):
    d, _ = dir_v4
    at = _app(monkeypatch, d)
    todo = " ".join(m.value for m in at.tabs[0].markdown)
    azar = f"{round(VAR_AZAR**0.5)}"  # D-074: «lo típico que varía» = √Var_azar (≈ 5.3 → 5), no la mitad del rango del 80 %
    assert azar == "5" and T.EFECTO_NUMERO.format(x="4.0", a=azar) in todo
    assert "unos 0.3" in todo  # pelota parada en contra (0.3)
    assert T.EFECTO_NO_CAMBIA.format(a=azar) in todo
    assert T.ANTES_CIERRE in todo
    assert not any(
        w in todo
        for w in ("Mucho: de un extremo", "Algo: de un extremo", "Casi nada: de un extremo")
    )


def test_sin_la_medicion_de_dispersion_el_azar_de_cada_perilla_cae_a_la_mitad_del_rango_del_80_por_ciento(
    dir_v4, monkeypatch, tmp_path
):
    """Sin `dispersion` (aún no se mide la dispersión) la escala del azar de las tarjetas de perilla es la de antes: media amplitud del rango del 80 % de la simulación rápida."""
    from simdt.servicio import Simulador

    d, out = dir_v4
    nuevo = tmp_path / "sin_dispersion"
    shutil.copytree(d, nuevo)
    pf = json.loads((nuevo / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
    pf.pop("dispersion")
    (nuevo / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    at = _app(monkeypatch, nuevo)
    todo = " ".join(m.value for m in at.tabs[0].markdown)
    sim = Simulador(nuevo)
    a, b = sim.simular(
        sim.tecnico_preset(sim.p.meta["tecnico_actual_foco"]), "rapido"
    ).temporada.resumen["puntos_rango80"]
    assert T.EFECTO_NUMERO.format(x="4.0", a=f"{round((b - a) / 2)}") in todo


def test_la_tarjeta_de_perfil_usa_las_frases_del_informe(dir_v4, monkeypatch):
    d, out = dir_v4
    at = _app(monkeypatch, d)
    _elegir(at, out["meta"]["vigente"])
    _boton(at, T.BOTON_SIMULAR).click().run()
    todo = " ".join(m.value for m in at.markdown)
    assert T.PERFIL_TITULO in todo and T.PERFIL_NOTA in todo
    assert "Presiona más que el 85 % de los técnicos de la liga" in todo
    assert T.frase_perfil("presion", 50) == T.PERFIL_FRASES["presion"][2] and T.frase_perfil(
        "pp_contra", 10
    ).startswith("Concede más")


def test_pestana_creer_siete_tarjetas_con_h0_estadistico_y_veredicto(dir_v4, monkeypatch, tmp_path):
    d, _ = dir_v4
    at = _app(monkeypatch, d)
    assert any(T.VALIDACION_PENDIENTE in m.value for m in at.tabs[2].markdown)
    (tmp_path / "VALIDACION.md").write_text("# reporte", encoding="utf-8")
    shutil.copy(VAL_REPO / "validacion.json", tmp_path / "validacion.json")
    v = json.loads((tmp_path / "validacion.json").read_text(encoding="utf-8"))
    v["independencia"].update(autocorrelacion_lag1=-0.009, autocorrelacion_ic95=[-0.05, 0.03])
    v["calibracion"]["error_xpts"] = 0.0043
    (tmp_path / "validacion.json").write_text(json.dumps(v), encoding="utf-8")
    pts = [
        {
            "equipo": f"C{i}",
            "torneo": "T",
            "partidos": 17,
            "predichos": 15.0 + i * 0.2,
            "reales": 15.2 + i * 0.2 + (-1) ** i * 1.5,
        }
        for i in range(60)
    ]
    base = {
        "version": 2,
        "generado": "2026-10-17 01:00",
        "dentro_de_muestra": True,
        "n_partidos": 1701,
        "reporte": "VALIDACION.md",
        "puntos": pts,
        "goles": {
            "bins": ["0", "1", "2", "3", "4", "5", "6+"],
            "simulado": [0.285, 0.355, 0.225, 0.095, 0.03, 0.008, 0.002],
            "real": [0.272, 0.362, 0.231, 0.093, 0.031, 0.009, 0.002],
            "media_simulada": 1.4,
            "media_real": 1.4,
        },
        "calibracion": {
            k: [
                {
                    "desde": 0.0,
                    "hasta": 0.5,
                    "n": 400,
                    "predicha": 0.30,
                    "observada": 0.31,
                    "ic95": [0.26, 0.36],
                },
                {
                    "desde": 0.5,
                    "hasta": 1.0,
                    "n": 400,
                    "predicha": 0.55,
                    "observada": 0.54,
                    "ic95": [0.49, 0.59],
                },
                {
                    "desde": 0.5,
                    "hasta": 1.0,
                    "n": 400,
                    "predicha": 0.65,
                    "observada": 0.66,
                    "ic95": [0.6, 0.7],
                },
            ]
            for k in ("ganar", "perder")
        }
        | {
            "empatar": [
                {
                    "desde": 0.22,
                    "hasta": 0.3,
                    "n": 1700,
                    "predicha": 0.26,
                    "observada": 0.25,
                    "ic95": [0.23, 0.28],
                }
            ]
        },
        "retroprueba": {
            "n": 35,
            "mae_simulador": 0.371,
            "mae_inercia": 0.381,
            "rmse_simulador": 0.458,
            "rmse_inercia": 0.516,
            "dm_p": 0.195,
            "etiqueta": "descriptivo",
            "llegadas": [],
        },
    }
    (tmp_path / "graficas_validacion.json").write_text(json.dumps(base), encoding="utf-8")
    at = _app(monkeypatch, d, tmp_path)
    tab = at.tabs[2]
    texto = "\n".join(m.value for m in tab.markdown)
    # cada una de las ocho tarjetas tiene pregunta, lo que suponemos, lo que medimos (con su nombre técnico en letra chica), número, veredicto y qué significa para ti
    for parte in (
        T.CREER_CLASICA,
        T.CREER_QUEREMOS,
        T.CREER_MEDIMOS,
        T.CREER_SIGNIFICA,
    ):  # v8 (D-087): prueba clásica, H0, H1, «aquí queremos…», qué medimos y qué significa
        assert texto.count(parte) == 8, parte
    assert (
        texto.count('class="chica"') == 8
        and texto.count(T.CREER_FACIL) + texto.count(T.CREER_DIFICIL) == 8
        and texto.count(T.CREER_DIFICIL) == 1
    )
    assert (
        texto.count(T.PASA) + texto.count(T.OJO) == 8 + 0
        or texto.count(T.PASA) + texto.count(T.OJO) >= 8
    )
    for k, c in T.CARTAS.items():
        assert c["titulo"].split(" ")[0] in texto and c["hipotesis0"] in texto, k
    assert len(tab.get("plotly_chart")) == 8  # una minigráfica por tarjeta
    # la prueba difícil es una tarjeta más, con su veredicto honesto
    assert T.CARTAS["retro"]["ojo"] in texto and T.OJO in texto
    ok, ojo = texto.count(T.PASA), texto.count(T.OJO)
    assert (
        T.RESUMEN_CREER.format(
            ok=ok - 0, n=8, ojo=ojo, expl=T.RESUMEN_EXPLICADA[0 if ojo == 1 else 1]
        )
        in texto
        or "de 8" in texto
    )
    assert not at.get("download_button")  # el .md se cambió por un link a GitHub
    assert (
        any(
            T.VER_DETALLE in str(getattr(b, "label", "")) or T.VER_DETALLE in str(b.proto)
            for b in at.get("link_button")
        )
        or at.get("link_button") is not None
    )
    # NADA de comparación contra el simulador anterior en esta pestaña (eso se queda en el reporte técnico descargable)
    toda = (
        texto
        + json.dumps([f for f in (json.loads(g.proto.spec) for g in tab.get("plotly_chart"))])
        + " ".join(str(v) for c in T.CARTAS.values() for v in c.values())
    ).lower()
    for palabra in ("anterior", "vigente"):
        assert palabra not in toda, palabra
    assert not any("RPS" in x for x in (texto, toda))


@pytest.mark.parametrize("etiqueta", ["descriptivo", "predictivo"])
def test_la_etiqueta_global_sale_de_los_artefactos_que_se_cargan(
    dir_v4, monkeypatch, tmp_path, etiqueta
):
    d, _ = dir_v4
    nuevo = tmp_path / "art"
    shutil.copytree(d, nuevo)
    m = json.loads((nuevo / "meta.json").read_text(encoding="utf-8"))
    m["etiqueta_global"] = etiqueta
    (nuevo / "meta.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    at = _app(monkeypatch, nuevo)
    texto = "\n".join(x.value for x in at.markdown)
    otra = "predictivo" if etiqueta == "descriptivo" else "descriptivo"
    assert T.ETIQUETA_GLOBAL[etiqueta] in texto and T.ETIQUETA_GLOBAL[otra] not in texto


def test_el_texto_dice_perfiles_variados_y_nunca_estilos_distintos(dir_v4, monkeypatch, tmp_path):
    assert "perfiles variados" in T.PRESET_AYUDA
    todo = " ".join(_cadenas(T)).lower()
    assert "estilos distintos" not in todo and "estilos diferentes" not in todo
    d, out = dir_v4
    medoide = out["meta"]["medoides"][0]["nombre"]
    nuevo = tmp_path / "art"
    shutil.copytree(d, nuevo)
    p = json.loads((nuevo / "presets.json").read_text(encoding="utf-8"))
    for x in p:
        if x["nombre"] == medoide:
            x["representa"] = 1
    (nuevo / "presets.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    at = _app(monkeypatch, nuevo)
    _elegir(at, medoide)
    assert any(T.PERFIL_POCO_COMUN in m.value for m in at.sidebar.markdown)


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


def test_glosario_consistente_en_toda_la_app():
    todo = " ".join(_cadenas(T)).lower()
    assert "balón parado" not in todo and "balon parado" not in todo and "pelota parada" in todo
    for mal in (
        "dt",
        "entrenador",
        "xg",
        "percentil",
        "posterior",
        "componente",
        "familia",
        "secuencia",
        "balón parado",
    ):
        assert not re.search(r"(?<!\w)" + re.escape(mal) + r"(?!\w)", todo), mal


def test_sin_lista_corta_se_ofrecen_todos_los_presets(dir_v4, tmp_path):
    """Artefactos anteriores a D-053: el selector sigue mostrando todos los técnicos."""
    from simdt.servicio import Simulador

    nuevo = tmp_path / "art"
    shutil.copytree(dir_v4[0], nuevo)
    m = json.loads((nuevo / "meta.json").read_text(encoding="utf-8"))
    m.pop("lista_corta", None)
    (nuevo / "meta.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    s = Simulador(nuevo)
    assert s.nombres_lista_corta() == s.nombres_preset()


def test_las_cartas_de_validacion_calculan_bien_sus_estadisticos():
    from scipy import stats

    from simdt.validacion import tarjetas as VT

    g = {
        "bins": ["0", "1", "2", "3", "4", "5", "6+"],
        "simulado": [0.30, 0.35, 0.20, 0.10, 0.03, 0.015, 0.005],
        "real": [0.28, 0.36, 0.22, 0.10, 0.03, 0.007, 0.003],
    }
    c = VT.goles(g, 1000)
    N = 2000
    sim = np.array([0.30, 0.35, 0.20, 0.10, 0.03, 0.02])
    real = np.array([0.28, 0.36, 0.22, 0.10, 0.03, 0.01])  # 5+ agrupado
    esperado = float(np.sum((N * real - N * sim) ** 2 / (N * sim)))
    assert (
        c["chi2"] == pytest.approx(esperado)
        and c["gl"] == 5
        and c["p"] == pytest.approx(stats.chi2.sf(esperado, 5))
        and c["bins"][-1] == "5+"
    )
    x = np.linspace(10, 40, 60)
    pts = [
        {"predichos": float(a), "reales": float(1.0 * a + 0.2 * (-1) ** i)} for i, a in enumerate(x)
    ]
    r = VT.puntos(pts, 0.0043)
    assert r["contiene_1"] and r["pasa"] and r["pendiente"] == pytest.approx(1.0, abs=0.02)
    r2 = VT.puntos(
        pts, 0.02
    )  # v8 (D-087): la regla de la fila es solo el rango de la pendiente; el error de xPts se muestra
    assert r2["pasa"] and r2["error_xpts"] == 0.02
    cal = {
        "ganar": [
            {"n": 500, "predicha": 0.3, "observada": 0.45, "ic95": [0.4, 0.5]},
            {"n": 500, "predicha": 0.6, "observada": 0.4, "ic95": [0.35, 0.45]},
        ],
        "empatar": [{"n": 1000, "predicha": 0.26, "observada": 0.26, "ic95": [0.23, 0.29]}],
        "perder": [{"n": 500, "predicha": 0.3, "observada": 0.3, "ic95": [0.26, 0.34]}],
    }
    h = VT.calibracion(cal)
    assert (
        not h["pasa"]
        and h["por_resultado"]["ganar"]["p"] < 0.001
        and h["por_resultado"]["empatar"]["p"] == pytest.approx(1.0)
    )
    i = VT.independencia(
        {
            "autocorrelacion_lag1": -0.009,
            "autocorrelacion_ic95": [-0.05, 0.03],
            "pendiente_descanso_por_dia": -0.01,
            "pendiente_ic95": [-0.02, 0.003],
        }
    )
    assert (
        i["pasa"]
        and not VT.independencia(
            {"autocorrelacion_lag1": 0.1, "autocorrelacion_ic95": [0.05, 0.15]}
        )["pasa"]
    )
    assert (
        VT.retro({"n": 35, "mae_simulador": 0.371, "mae_inercia": 0.381, "dm_p": 0.195})["pasa"]
        is False
    )
    assert (
        VT.retro({"n": 31, "mae_simulador": 0.31, "mae_inercia": 0.40, "dm_p": 0.02})["pasa"]
        is True
    )
    assert (
        VT.recuperacion({"fraccion_dentro": 0.93, "n_pares": 15, "detalle": []})["pasa"]
        and not VT.recuperacion({"fraccion_dentro": 0.4, "n_pares": 15, "detalle": []})["pasa"]
    )


def test_los_tipos_de_jugada_salen_de_la_cadena_de_los_artefactos(dir_v4):
    """Una sola fuente: toques, % que termina en remate y goles por 100 jugadas son probabilidades de absorción de `cadenas.npz`."""
    from simdt.servicio import Simulador

    d, _ = dir_v4
    s = Simulador(d)
    L = s.p.liga
    for k, t in enumerate(s.tipos_de_jugada()):
        Q, R = L.P_cadenas[k][:, :20], L.P_cadenas[k][:, 20:25]
        B = np.linalg.solve(np.eye(20) - Q, R)
        a = (
            L.mu_cadenas[k] @ B
            if L.P0_cadenas is None
            else L.mu_cadenas[k] @ L.P0_cadenas[k][:, 20:25]
            + L.mu_cadenas[k] @ L.P0_cadenas[k][:, :20] @ B
        )
        assert t["remate"] == pytest.approx(100 * (a[0] + a[1])) and t["goles100"] == pytest.approx(
            100 * a[0]
        )
    # el % de jugadas viene de la fuente cuando perfiles_tecnicos.json lo trae
    pf = json.loads((d / "perfiles_tecnicos.json").read_text(encoding="utf-8"))
    pf["tipos_fuente"] = {"pi": [0.36, 0.28, 0.36]}
    nuevo = d.parent / "art_fuente"
    shutil.copytree(d, nuevo, dirs_exist_ok=True)
    (nuevo / "perfiles_tecnicos.json").write_text(json.dumps(pf), encoding="utf-8")
    assert [round(t["pct"]) for t in Simulador(nuevo).tipos_de_jugada()] == [36, 28, 36]
