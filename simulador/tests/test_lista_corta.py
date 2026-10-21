"""Lista corta de técnicos (D-053): vigente + antecesor detectados con los datos, elegibles y k-medoides (PAM), etiquetas en lenguaje común."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from simdt.app import textos as T
from simdt.estimacion import lista_corta as lc
from simdt.tipos import COMPONENTES, Q, bloque_de


def _partidos(rachas: list[tuple[str, int]], club: str = "América") -> pd.DataFrame:
    filas, mid = [], 0
    for tec, n in rachas:
        for _ in range(n):
            mid += 1
            filas.append(
                {
                    "match_id": mid,
                    "fecha": pd.Timestamp("2020-01-01") + pd.Timedelta(days=7 * mid),
                    "local": club,
                    "visitante": "Rival",
                    "tecnico_local": tec,
                    "tecnico_visitante": "Otro",
                }
            )
    return pd.DataFrame(filas)


def test_vigente_y_antecesor_con_datos_ignorando_interinos():
    p = _partidos([("Cocca", 40), ("Jardine", 60), ("Interino", 3), ("Almada", 30)])
    assert lc.detectar_vigente_y_antecesor(p, "América", None, 10) == ("Almada", "Jardine")
    assert (
        lc.detectar_vigente_y_antecesor(p, "América", "Almada", 2)[1] == "Interino"
    )  # con otro umbral sí cuenta
    assert lc.detectar_vigente_y_antecesor(_partidos([("Solo", 20)]), "América", None, 10) == (
        "Solo",
        None,
    )
    assert lc.detectar_vigente_y_antecesor(p, "Club inexistente", "X", 10) == ("X", None)


def test_pam_es_determinista_y_encuentra_los_grupos():
    rng = np.random.default_rng(4)
    X = np.vstack([rng.normal(c, 0.2, (15, 2)) for c in ((0, 0), (5, 5), (-5, 5), (5, -5))])
    D = np.sqrt(((X[:, None] - X[None]) ** 2).sum(2))
    m1, l1 = lc.pam(D, 4, 1)
    m2, l2 = lc.pam(D, 4, 1)
    assert np.array_equal(np.sort(m1), np.sort(m2)) and np.array_equal(l1, l2)
    assert sorted(np.bincount(l1)) == [15, 15, 15, 15]
    assert len({int(m) // 15 for m in m1}) == 4  # un medoide por grupo


def test_rasgos_de_bloques_distintos_y_frases_sin_palabras_prohibidas():
    th = np.zeros(Q)
    sig = np.full(Q, 0.1)
    th[COMPONENTES.index("int_at[Directa]")] = 0.3
    th[COMPONENTES.index("int_at[Ataque elaborado]")] = 0.25  # mismo bloque: no debe repetirse
    th[COMPONENTES.index("nu_co[corner]")] = -0.2
    r = lc.rasgos(th, sig, 2)
    assert (
        [bloque_de(x["componente"]) for x in r] == ["int_at", "nu_co"]
        and r[0]["signo"] == 1
        and r[1]["signo"] == -1
    )
    assert T.etiqueta_tecnico(r) == "Ataca más directo y defiende mejor los tiros de esquina."
    prohibidas = [w.lower() for w in T.PALABRAS_PROHIBIDAS]
    for c in COMPONENTES:
        for sg in (1, -1):
            f = T.frase_rasgo(c, sg)
            assert f and not any(w in f.lower() for w in prohibidas), (c, f)
    assert T.etiqueta_tecnico([]) == T.ETIQUETA_SIN_RASGOS


def _mundo(n_tec=14, seed=2):
    rng = np.random.default_rng(seed)
    sig = np.full(Q, 0.1)
    centros = rng.normal(0, 0.2, (4, Q))
    th = {f"T{i:02d}": centros[i % 4] + rng.normal(0, 0.03, Q) for i in range(n_tec)}
    presets = [
        {"nombre": t, "partidos": 100 + i, "clubes": ["X"], "perillas": {}}
        for i, t in enumerate(th)
    ]
    return presets, th, sig


def test_lista_corta_fijos_medoides_silueta_y_representados():
    presets, th, sig = _mundo()
    n = {p["nombre"]: p["partidos"] for p in presets}
    n["T05"] = 20  # no elegible por partidos
    cel = {t: 5 for t in th}
    cel["T06"] = 1  # no elegible por celdas
    out = lc.calcular(presets, th, sig, n, cel, "T00", "T01")
    L, m = out["lista"], out["meta"]
    assert L["T00"]["rol"] == "vigente" and L["T01"]["rol"] == "antecesor"
    meds = [t for t, x in L.items() if x["rol"] == "medoide"]
    assert len(meds) == 4 and "T05" not in L and "T06" not in L and not ({"T00", "T01"} & set(meds))
    assert (
        m["n_elegibles"] == 14 - 2 - 2
        and sum(x["representa"] for t, x in L.items() if x["rol"] == "medoide") == m["n_elegibles"]
    )
    assert (
        m["silueta"] is not None and -1 <= m["silueta"] <= 1 and m["silueta"] > 0.3
    )  # cuatro grupos bien separados
    assert len({x["nombre"] for x in m["medoides"]}) == 4 and all(
        len(x["rasgos"]) == 2 for x in L.values()
    )
    marcados = lc.aplicar(presets, out)
    assert sum(p["lista_corta"] for p in marcados) == 6 and [
        p["rol"] for p in marcados if p["nombre"] == "T00"
    ] == ["vigente"]
    assert all(p["rasgos"] == [] and p["representa"] == 0 for p in marcados if not p["lista_corta"])
    out2 = lc.calcular(presets, th, sig, n, cel, "T00", "T01")  # reproducible
    assert out2["meta"]["medoides"] == m["medoides"]


def test_con_pocos_elegibles_se_ofrecen_todos():
    presets, th, sig = _mundo(n_tec=5)
    out = lc.calcular(presets, th, sig, {p["nombre"]: 100 for p in presets}, None, "T00", "T01")
    assert (
        out["meta"]["silueta"] is None
        and out["meta"]["n_elegibles"] == 3
        and out["meta"]["n_lista"] == 5
    )
    assert out["meta"]["celdas_exigidas"] is False


def test_desde_la_fase_a_sintetica_detecta_al_vigente_y_exige_celdas():
    from simdt import calibrar, config
    from simdt.datos import sintetico
    from simdt.estimacion import fase_a
    from simdt.estimacion.fichas import armar

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
        M=50,
        semilla=1,
        tecnicos_guardar=cand,
        atribucion="continua",
    )
    n_tec, _ = calibrar._conteo_partidos(tablas["partidos"])
    presets = [
        {"nombre": t, "partidos": int(n_tec[t]), "clubes": [], "perillas": {}} for t in pz.theta_tec
    ]
    out = lc.desde_fase_a(res, tablas["partidos"], pz, presets, vig, foco)
    assert out["meta"]["vigente"] == vig[foco] and out["meta"]["celdas_exigidas"] is True
    assert out["meta"]["antecesor"] != out["meta"]["vigente"]
    assert out["lista"][vig[foco]]["rol"] == "vigente"
