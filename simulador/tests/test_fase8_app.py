"""Pruebas de interfaz T-U1 a T-U5 (07_PRUEBAS.md)."""

import ast
import re
import time
from pathlib import Path

import pytest

from simdt import config
from simdt.app import textos as T

APP = config.RAIZ_SIM / "src" / "simdt" / "app"
SIN_ARTEFACTOS = not (config.ARTEFACTOS / "meta.json").exists()


def _cadenas_visibles_de_textos() -> list[str]:
    out = []
    for nombre, v in vars(T).items():
        if nombre.startswith("_") or nombre == "PALABRAS_PROHIBIDAS" or callable(v):
            continue
        out += _aplana(v)
    return out


def _aplana(v) -> list[str]:
    if isinstance(v, str):
        return [v]
    if isinstance(v, (tuple, list)):
        return [s for x in v for s in _aplana(x)]
    if isinstance(v, dict):
        return [s for x in v.values() for s in _aplana(x)]
    return []


def _palabra(p: str):
    return re.compile(r"(?<!\w)" + re.escape(p.lower()) + r"(?!\w)")


def test_TU1_sin_palabras_prohibidas():
    textos = " ".join(_cadenas_visibles_de_textos()).lower()
    for p in T.PALABRAS_PROHIBIDAS:
        assert not _palabra(p).search(textos), (
            p
        )  # palabra completa: «consecuencias» no es «secuencia»
    # textos de las gráficas: plantillas de hover y títulos en graficas.py
    fuente = (APP / "graficas.py").read_text(encoding="utf-8").lower()
    lits = [
        n.value
        for n in ast.walk(ast.parse(fuente))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    for p in T.PALABRAS_PROHIBIDAS:
        assert not any(_palabra(p).search(s) for s in lits), p


_VISIBLE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúñÑ¿¡]{3,}\s+[A-Za-zÁÉÍÓÚáéíóúñÑ]{2,}")


def test_TU2_cadenas_solo_en_textos():
    malas = []
    for f in APP.glob("*.py"):
        if f.name in ("textos.py", "__init__.py"):
            continue
        arbol = ast.parse(f.read_text(encoding="utf-8"))
        docs = {
            id(n.body[0].value)
            for n in ast.walk(arbol)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
            and n.body
            and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
        }
        for n in ast.walk(arbol):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
                s = n.value
                if any(c in s for c in "<{=_/#") or s.strip().startswith("%"):
                    continue  # HTML, formato, CSS, rutas
                if _VISIBLE.search(s):
                    malas.append((f.name, s))
    assert malas == [], malas


@pytest.fixture(scope="module")
def app():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=180)
    at.run()
    return at


@pytest.mark.skipif(SIN_ARTEFACTOS, reason="sin artefactos")
def test_TU3_arranca(app):
    assert not app.exception
    assert any(T.TITULO in m.value for m in app.markdown)


@pytest.mark.skipif(SIN_ARTEFACTOS, reason="sin artefactos")
def test_TU4_simular_rapido(app):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(config.RAIZ_SIM / "app.py"), default_timeout=180)
    at.run()
    boton = next(b for b in at.button if b.label == T.BOTON_SIMULAR)
    t0 = time.perf_counter()
    boton.click().run()
    dt = time.perf_counter() - t0
    print(f"Simular torneo (rápido): {dt:.2f} s")
    assert not at.exception
    assert any(T.TARJETA_PUNTOS in m.value for m in at.markdown)
    assert dt < 10


@pytest.mark.skipif(SIN_ARTEFACTOS, reason="sin artefactos")
def test_TU5_pie_completo(app):
    todo = "\n".join(m.value for m in app.markdown)
    for parte in (
        T.ANTES_NO_SIMULA_TITULO,
        *T.ANTES_NO_SIMULA,
        T.ANTES_CIERRE,
        T.ANTES_QUE_NO_TITULO,
        *T.ANTES_QUE_NO,
    ):  # el pie del spec, en frases cortas (D-070)
        assert parte in todo, parte
    assert any(v in todo for v in T.ETIQUETA_GLOBAL.values())
