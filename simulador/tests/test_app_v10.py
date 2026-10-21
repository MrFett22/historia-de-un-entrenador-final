"""App v10 (D-090 en adelante): gráficas que no cambian fuera, ficha completa con cambio significativo, qué torneo se simula y momentum con las dos presiones."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from simdt import analisis as A
from simdt import config
from simdt.app import textos as T

SIN_ARTEFACTOS = not (config.ARTEFACTOS / "meta.json").exists()
pytestmark = pytest.mark.skipif(SIN_ARTEFACTOS, reason="sin artefactos")

from test_app_v6 import _app as _app6  # noqa: E402  (el mismo montaje: artefactos con atribución continua, lista corta, perfiles y dispersión)
from test_app_v6 import _boton, _elegir, _texto, dir_v6, sim6  # noqa: E402,F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "herramientas"))


@pytest.fixture(scope="module")
def piezas(sim6):
    from simdt import analisis as A

    t = sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"])
    Ci, Cj, _ = A.componentes_partido(sim6, t, 3, True, 5)
    return t, Ci, Cj


@pytest.fixture
def app10(dir_v6, monkeypatch):
    return _app6(monkeypatch, dir_v6)


def _simulado(at, sim):
    _elegir(at, sim.p.meta["tecnico_actual_foco"])
    _boton(at, T.BOTON_SIMULAR).click().run()
    assert not at.exception
    return at


# ================================================================ Fase A: gráficas que no cambian (D-090)
def test_la_pestana_simulador_ya_no_trae_el_mapa_de_zonas_ni_los_goles_en_la_cancha(sim6, app10):
    at = _simulado(app10, sim6)
    todo = _texto(at) + "\n" + "\n".join(str(getattr(e, "value", "")) for e in at.tabs[1].markdown)
    for titulo in ("¿Por dónde movería el balón?", "¿De dónde vienen sus goles?"):
        assert titulo not in todo, titulo
    for nombre in (
        "SECCION_ZONAS",
        "SECCION_GOLES_CANCHA",
        "NOTA_ZONAS",
        "GOLES_NOTA",
        "ESCALA_ZONAS",
        "GOLES_HOVER",
    ):
        assert not hasattr(T, nombre), nombre
    from simdt.app import graficas as G

    assert not any(hasattr(G, n) for n in ("cancha_calor", "cancha_goles", "cancha_zonas"))
    assert "zonas" not in sim6.simular(sim6.tecnico_promedio(), "rapido").estilo


def _con_perfiles(sim, v):
    class Falso:
        def perfiles(self):
            return v

    return Falso()


def test_la_barra_de_goles_por_tipo_se_muestra_salvo_que_la_medicion_diga_que_no_cambia():
    from simdt.app.principal import barras_goles_visibles

    assert barras_goles_visibles(_con_perfiles(None, None))  # sin medición: se muestra
    assert barras_goles_visibles(
        _con_perfiles(None, {"variacion_graficas": {"barras_se_quedan": True}})
    )
    assert not barras_goles_visibles(
        _con_perfiles(None, {"variacion_graficas": {"barras_se_quedan": False}})
    )


def test_el_titulo_de_goles_por_tipo_aparece_si_cambia_entre_tecnicos(sim6, app10):
    at = _simulado(app10, sim6)
    assert T.SECCION_GOLES in _texto(at)


def test_la_variacion_entre_tecnicos_confirma_que_zonas_y_goles_en_la_cancha_son_el_mismo_dibujo(
    sim6,
):
    """H3: el técnico no cambia cómo se mueve el balón dentro de cada tipo de jugada; solo cambia la mezcla, y esa se mueve poco."""
    import variacion_graficas as V

    nombres = list(sim6.ejes.nombres)[:6]
    r = V.medir(sim6, nombres, extremos=False)
    assert r["n_reales"] == 6 and r["real"]["zonas_pp"] < 1.0 and r["real"]["zonas_rel"] < 0.05
    assert isinstance(r["barras_se_quedan"], bool) and r["real"]["barras_rel"] == max(
        f["barras_rel"] for f in r["filas"]
    )


# ================================================================ Fase B: ficha completa, solo lo que cambia de verdad (D-091)
def test_cambio_con_dos_valores_identicos_siempre_dice_igual():
    from simdt import analisis as A

    for tipo in ("pp", "conteo", "minutos"):
        assert A.cambio(35.4, 35.4, tipo)["estado"] == "igual"
    assert (
        A.cambio(26.5, 26.5, "mc", 0.0, 0.0)["estado"] == "igual"
    )  # sin error estándar, Δ = 0 no es un cambio


def test_el_cambio_debajo_del_umbral_no_se_colorea_y_encima_si_con_el_signo_correcto():
    from simdt import analisis as A

    c = config.cargar()["ficha_cambio"]
    # exactas: hacen falta el cambio relativo Y el absoluto
    assert (
        A.cambio(10.0, 10.0 + 0.9, "pp")["estado"] == "igual"
    )  # 9 % relativo, pero menos de 1 punto porcentual
    assert A.cambio(40.0, 41.5, "pp")["estado"] == "igual"  # 1.5 puntos, pero solo 3.7 % relativo
    assert A.cambio(35.0, 33.0, "pp")["estado"] == "sube"  # tu técnico 35 contra 33 de hoy: sube
    assert A.cambio(33.0, 35.0, "pp")["estado"] == "baja"
    assert A.cambio(1.0, 1.0 + 0.04, "conteo")["estado"] == "igual"  # menos de 0.05 por partido
    assert (
        A.cambio(0.30, 0.20, "conteo")["estado"] == "sube"
        and A.cambio(0.20, 0.30, "conteo")["estado"] == "baja"
    )
    assert (
        A.cambio(0.06, 0.0, "conteo")["de_cero"]
        and A.cambio(0.06, 0.0, "conteo")["estado"] == "sube"
    )
    assert A.cambio(0.04, 0.0, "conteo")["estado"] == "igual"
    # Monte Carlo: |Δ| ≥ k · EE combinado
    ee = 0.1
    umbral = c["k_ee"] * (2 * ee**2) ** 0.5
    assert A.cambio(26.0 + 0.95 * umbral, 26.0, "mc", ee, ee)["estado"] == "igual"
    assert A.cambio(26.0 + 1.05 * umbral, 26.0, "mc", ee, ee)["estado"] == "sube"
    assert A.cambio(26.0 - 1.05 * umbral, 26.0, "mc", ee, ee)["estado"] == "baja"
    assert A.cambio(5.0, 5.0 - 0.9 * c["rel_min"] * 5.0, "mc", 0.0, 0.0)["estado"] in (
        "sube",
        "baja",
    )  # con error 0, cualquier Δ ≠ 0 es un cambio


def test_los_decimales_hacen_que_dos_numeros_distintos_se_vean_distintos():
    from simdt import analisis as A

    assert A.decimales_distintos(26.50, 26.53, 1) == 2
    assert A.decimales_distintos(26.50, 26.90, 1) == 1
    assert A.decimales_distintos(3.0, 3.0, 1) == 1


def test_dos_fichas_identicas_dicen_todas_igual(sim6, app10):
    from simdt.app import principal

    r = sim6.simular(sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"]), "rapido")
    grupos = principal.ficha_filas(sim6, r, r)
    filas = [f for _, fs in grupos for f in fs]
    assert len(filas) > 20 and all(
        f["estado"] == "igual" and f["cambio"] == T.FICHA_IGUAL and f["ancho"] == 0 for f in filas
    )
    html = __import__("simdt.app.componentes", fromlist=["x"]).ficha_html(
        grupos, T.FICHA_COLUMNAS, T.FICHA_TABLA_TITULO
    )
    assert (
        "▲" not in html
        and "▼" not in html
        and "cb-barra" not in html
        and T.FICHA_TABLA_TITULO in html
    )


def test_ninguna_fila_de_la_ficha_muestra_flecha_con_valores_redondeados_iguales(sim6):
    from simdt.app import principal

    base = sim6.simular(sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"]), "rapido")
    otros = [n for n in sim6.ejes.nombres if n != sim6.p.meta["tecnico_actual_foco"]][:5]
    con_flecha = 0
    for n in otros:
        r = sim6.simular(sim6.tecnico_preset(n), "rapido")
        for _, filas in principal.ficha_filas(sim6, r, base):
            for f in filas:
                if f["estado"] in ("sube", "baja"):
                    con_flecha += 1
                    assert f["tu"] != f["actual"], (n, f)
                    assert f["ancho"] > 0 and f["cambio"] not in (T.FICHA_IGUAL, "+0 %", "−0 %"), (
                        n,
                        f,
                    )
                else:
                    assert f["ancho"] == 0 and f["estado"] in ("igual", "distinto"), (n, f)
    assert con_flecha > 0  # con técnicos distintos, algo sí cambia


def test_la_ficha_de_la_app_trae_titulo_columnas_y_grupo_de_resultado(sim6, app10):
    at = _simulado(app10, sim6)
    t = _texto(at)
    assert (
        T.FICHA_TABLA_TITULO in t
        and "Comparado con el América de hoy (estilo de Almada y plantel actual)" in t
    )
    assert (
        all(c in t for c in ("Tu técnico", "América hoy", "Cambio"))
        and "Lo normal en la liga" not in t.split(T.SECCION_FICHA)[-1]
    )
    assert (
        T.FICHA_GRUPOS["resultado"] in t and T.FICHA_IGUAL in t
    )  # Almada contra el América de hoy: "≈ igual" en casi todo
    assert 'class="der cambio igual"' in t


# ================================================================ Fase C: qué torneo se simula y qué es «América hoy» (D-092)
@pytest.fixture
def dir_corte(dir_v6, tmp_path):
    """Artefactos de la v6 con el corte por fecha que guarda la calibración E (`meta.json["corte"]`)."""
    import json
    import shutil

    d = tmp_path / "art_corte"
    shutil.copytree(dir_v6, d)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    meta["corte"] = {
        "fecha_corte": "2026-07-17",
        "partidos_antes": 1789,
        "partidos_quitados": 88,
        "partidos_despues": 1701,
        "temporadas_quitadas": [10],
        "fechas_quitadas": ["2026-07-17", "2026-09-28"],
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return d


def test_el_torneo_anterior_sale_del_nombre_del_torneo():
    from simdt import analisis as A

    assert (
        A.torneo_anterior("Apertura 2026") == "Clausura 2026"
        and A.torneo_anterior("Clausura 2026") == "Apertura 2025"
    )
    assert A.torneo_anterior("otro") is None and A.torneo_anterior(None) is None


def test_el_bloque_del_torneo_aparece_en_las_dos_pestanas_y_sus_datos_son_los_de_meta_json(
    dir_corte, monkeypatch
):
    import json
    from simdt.servicio import Simulador

    meta = json.loads((dir_corte / "meta.json").read_text(encoding="utf-8"))
    at = _app6(monkeypatch, dir_corte)
    sim = Simulador(dir_corte)
    lineas = __import__("simdt.app.principal", fromlist=["x"]).lineas_torneo(sim)
    assert (
        lineas[0]
        == f"Simulamos el {meta['torneo']} completo, desde la jornada 1, con su calendario real (local y visita): {len(meta['calendario'])} partidos."
    )
    assert (
        "Clausura 2026" in lineas[1] and "17 de julio de 2026" in lineas[1]
    )  # torneo anterior y fecha de corte, de meta.json
    assert "NO se usan (son 88, del 17 de julio de 2026 al 28 de septiembre de 2026)" in lineas[2]
    assert "«América hoy»" in lineas[3] and "Almada" in meta["tecnico_actual_foco"]
    for pestana in (0, 1):  # «Antes de jugar» y «Simulador», antes de simular
        t = _texto(at, pestana)
        assert T.TORNEO_TITULO in t and all(
            l in t.replace("&quot;", '"') or l.replace("«", "").replace("»", "") in t
            for l in lineas[:3]
        ), pestana
    assert _texto(at, 1).index(T.TORNEO_TITULO) < _texto(at, 1).index(
        T.PESA_TITULO
    )  # fijo ARRIBA de la pestaña


def test_sin_corte_en_meta_el_bloque_no_inventa_fechas(dir_v6, tmp_path):
    """Arma SU PROPIO meta.json sin `corte` (v11): no depende de si los artefactos que encuentre (los de prueba o los reales de E) lo traen."""
    import json
    import shutil
    from simdt.app.principal import lineas_torneo
    from simdt.servicio import Simulador

    d = tmp_path / "art_sin_corte"
    shutil.copytree(dir_v6, d)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    meta.pop("corte", None)
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    l = lineas_torneo(Simulador(d))
    assert "jugados antes del" not in l[1] and "(son " not in l[2] and "Clausura 2026" in l[1]


def test_las_tarjetas_dicen_contra_el_america_de_hoy():
    assert (
        T.TARJETA_VS == "Contra el América de hoy (Almada)"
        and T.SERIE_RIVAL_ACTUAL == "Contra el América de hoy (Almada)"
    )
    assert "América actual" not in " ".join(
        v for k, v in vars(T).items() if isinstance(v, str) and k.isupper()
    )


# ================================================================ Fase D: presión de cada equipo, suavizada (D-093)
@pytest.fixture(scope="module")
def partidos_d(sim6):
    """1,000 partidos del técnico vigente en casa contra el rival de fuerza mediana, con las mismas piezas de la app."""
    import diagnostico_presion as D

    return D.diagnostico(sim6, 1000)


def test_las_barras_se_ven_llenas_en_al_menos_95_por_ciento_de_los_minutos(partidos_d):
    v = partidos_d["v10"]
    assert v["las_dos_visibles"] >= 0.95 and v["visibles"] >= 0.95, (
        v
    )  # las dos barras de cada minuto por encima del 3 % del eje
    assert (
        partidos_d["v8"]["bajo_eje_max"] > 0.5 > 1 - v["visibles"]
    )  # y la v8 las dejaba casi todas por debajo: el diagnóstico de D-093
    assert v["presion_negativa"] == 0


def test_la_media_de_la_presion_coincide_con_la_media_de_mu_a_menos_de_3_errores_estandar(
    partidos_d,
):
    m = partidos_d["v10"]["media_S_menos_mu"]
    assert abs(m["america"]) < 3 * m["america_ee"] and abs(m["rival"]) < 3 * m["rival_ee"], m


def test_la_amenaza_y_los_remates_tienen_la_misma_media_que_mu(piezas):
    """E[T] = E[Y] = μ minuto a minuto (con el marcador fijado): la presión P = T + s (Y − T) conserva la media."""
    from simdt.motor import jugadas as J

    _, Ci, Cj = piezas
    n = 40000
    for t_, m in ((10, 1), (70, 0)):
        r = J.minuto(Ci, Cj, t_, np.full(n, m), np.random.default_rng(50 + t_))
        mu = Ci.mu[t_, m]
        for x in (r["amenaza_i"], Ci.f * r["peligro_i"]):
            assert abs(x.mean() - mu) < 3 * x.std(ddof=1) / np.sqrt(n), (x.mean(), mu)


def test_la_presion_con_peso_cero_es_la_amenaza_con_uno_son_los_remates_y_nunca_es_negativa():
    from simdt.motor import jugadas as J

    T_, Y_ = np.array([[0.02, 0.03]]), np.array([[0.0, 0.2]])
    assert np.allclose(J.presion(T_, Y_, 0.0), T_) and np.allclose(J.presion(T_, Y_, 1.0), Y_)
    for s in (0.0, 0.3, 0.5, 1.0):
        assert (J.presion(T_, Y_, s) >= 0).all()


def test_la_media_movil_conserva_la_media_y_no_tiene_rampa_si_arranca_en_la_expectativa():
    from simdt.motor import jugadas as J

    x = np.full((3, 90), 0.02)
    assert np.allclose(J.ema(x, 4.0, 0.02), 0.02)  # constante → constante: sin rampa al inicio
    imp = np.zeros((1, 90))
    imp[0, 10] = 1.0
    y = J.ema(imp, 4.0, 0.0)[0]
    assert y[10] == pytest.approx(1 - 0.5 ** (1 / 4.0)) and y[14] == pytest.approx(
        y[10] * 0.5 ** (4 / 4.0)
    )  # a los 4 minutos (la vida media) queda la mitad


def test_la_diferencia_de_presion_sube_con_la_ventaja_de_elo_en_partidos_con_favorito_claro(sim6):
    from simdt.motor import jugadas as J

    t = sim6.tecnico_preset(sim6.p.meta["tecnico_actual_foco"])
    rng = np.random.default_rng(1)
    de, dif = [], []
    for rv in (e for e in range(len(sim6.elo)) if e != sim6.foco):
        Ci, Cj, _ = A.componentes_partido(sim6, t, rv, True, 5)
        r = J.simular_partidos(Ci, Cj, 200, rng)
        dif.append((r["suave_i"] - r["suave_j"]).mean(1))
        de.append(np.full(200, sim6.elo[sim6.foco] - sim6.elo[rv]))
    de, dif = np.concatenate(de), np.concatenate(dif)
    claro = (
        np.abs(de) >= config.cargar()["elo"]["h"]
    )  # favorito claro: más de una ventaja de local de diferencia
    assert claro.sum() > 500 and np.corrcoef(de[claro], dif[claro])[0, 1] > 0


def test_los_goles_no_cambian_con_la_presion(piezas):
    """La presión solo se calcula DESPUÉS de sortear: la misma semilla da los mismos goles con cualquier peso de sorpresa o vida media."""
    from simdt.motor import jugadas as J

    _, Ci, Cj = piezas
    a = J.simular_partidos(Ci, Cj, 300, np.random.default_rng(9))
    b = J.simular_partidos(Ci, Cj, 300, np.random.default_rng(9), vida_media=9.0)
    assert (
        (a["goles_i"] == b["goles_i"]).all()
        and (a["goles_j"] == b["goles_j"]).all()
        and (a["remates_i"] == b["remates_i"]).all()
    )
