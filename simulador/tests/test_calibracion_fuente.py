"""D-055 (inflación por familia) y D-056 (técnico por id)."""

import numpy as np
import pandas as pd
import pytest

from simdt.datos.repo import homonimos, tecnicos_por_id
from simdt.estimacion.celdas import factor_varianza
from simdt.tipos import COMPONENTES

INFL = {"Directa": 1.68, "Circulación estéril": 4.94, "Ataque elaborado": 1.12}


def test_numero_suelto_es_varianza_como_en_E():
    assert factor_varianza("u_at[Directa]", 1.10) == 1.10


def test_familia_eleva_al_cuadrado_el_error_estandar():
    assert factor_varianza("u_at[Circulación estéril]", INFL) == pytest.approx(4.94**2)
    assert factor_varianza("w_co[Ataque elaborado]", INFL) == pytest.approx(1.12**2)


def test_int_y_s_usan_el_maximo():
    for n in COMPONENTES:
        b = n.split("[")[0]
        if b in ("int_at", "int_co", "s_marcador", "s_rival"):
            assert factor_varianza(n, INFL) == pytest.approx(4.94**2)


def test_tecnicos_por_id_separa_homonimos_y_une_variantes():
    p = pd.DataFrame(
        {
            "tecnico_local": ["Ruben Gomez", "Rubén G.", "Ruben Gomez", "Ana"],
            "tecnico_id_local": [1, 1, 2, 3],
            "tecnico_visitante": ["Ana", "Ana", "Ana", "Ruben Gomez"],
            "tecnico_id_visitante": [3, 3, 3, 2],
        }
    )
    q, t = tecnicos_por_id(p)
    # id 1 -> nombre más frecuente "Ruben Gomez" (2 de 3 ... empate resuelto por value_counts), id 2 mismo nombre => se desambiguan
    assert q.tecnico_local.nunique() == 3
    assert q.tecnico_local.iloc[0] == q.tecnico_local.iloc[1]
    assert q.tecnico_local.iloc[0] != q.tecnico_local.iloc[2]
    assert "(2)" in q.tecnico_local.iloc[2]
    assert set(t.id) == {1, 2, 3}


def test_homonimos_detecta_dos_ids_con_un_nombre():
    p = pd.DataFrame(
        {
            "tecnico_local": ["X", "X"],
            "tecnico_id_local": [10, 11],
            "tecnico_visitante": ["Y", "Y"],
            "tecnico_id_visitante": [5, 5],
        }
    )
    h = homonimos(p)
    assert set(h.id) == {10, 11} and set(h.nombre) == {"X"}


def test_tablas_sin_ids_conservan_el_nombre():
    p = pd.DataFrame({"tecnico_local": ["A"], "tecnico_visitante": ["B"]})
    q, t = tecnicos_por_id(p)
    assert q.equals(p) and t.empty
