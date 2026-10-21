"""Pruebas de la fase A en sintético: T-A1 a T-A4 (07_PRUEBAS.md).

La corrida completa (32 componentes, NUTS) tarda ~10 min; se guarda en simulador/_cache/ y las
pruebas la reutilizan. Para recalcular: borrar _cache/fase_a_sintetico.pkl.
"""

import numpy as np
import pytest
from scipy.stats import binom

from simdt.datos import sintetico
from simdt.estimacion import cruzado, fase_a
from simdt.tipos import COMPONENTES

pytestmark = pytest.mark.lento


@pytest.fixture(scope="module")
def faseA():
    tablas, verdad = sintetico.generar()
    res = fase_a.correr(
        tablas,
        P_cadenas=verdad.liga.P_cadenas,
        mu_cadenas=verdad.liga.mu_cadenas,
        cache="fase_a_sintetico.pkl",
        verbose=False,
    )
    return res, verdad


def test_TA1_cobertura_theta(faseA):
    res, v = faseA
    cubre, total, por_comp = 0, 0, {}
    for q, n in enumerate(COMPONENTES):
        p = res.posteriores[n]
        tru = v.theta[[v.tecnicos.index(t) for t in res.ix.tecnicos], q]
        lo, hi = np.quantile(p.theta, [0.025, 0.975], axis=0)
        c = (tru >= lo) & (tru <= hi)
        por_comp[n] = c.mean()
        cubre += c.sum()
        total += c.size
    cob = cubre / total
    print(f"cobertura global de θ (95 %): {cob:.3f}")
    assert 0.85 <= cob <= 1.0
    # Por componente se REPORTA (D-026): dentro de una componente los 30 intervalos comparten
    # σ_θ, así que no son ensayos binomiales independientes; cuando la componente tiene poca
    # información σ_θ queda baja y todos se encogen juntos.
    minimo = binom.ppf(0.005, 30, 0.95) / 30
    malas = {n: round(c, 2) for n, c in por_comp.items() if c < minimo}
    print("componentes bajo la tolerancia binomial:", malas)
    import json
    from simdt import config

    config.VALIDACION.mkdir(parents=True, exist_ok=True)
    (config.VALIDACION / "TA1_cobertura_por_componente.json").write_text(
        json.dumps(
            {
                "_nota": "Salida de la prueba T-A1 sobre datos SINTÉTICOS con verdad conocida (cobertura de θ). No depende de los artefactos reales ni de la publicación: "
                "cambia solo si cambia el código de la fase A.",
                "global": cob,
                "por_componente": por_comp,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )


def test_TA2_sigmas(faseA):
    res, v = faseA
    dentro, total = 0, 0
    for q, n in enumerate(COMPONENTES):
        p = res.posteriores[n]
        for j in range(3):  # theta, phi, int
            lo, hi = np.quantile(p.sigma[:, j], [0.025, 0.975])
            dentro += lo <= v.sigmas[q, j] <= hi
            total += 1
    frac = dentro / total
    print(f"σ verdaderas dentro del 95 %: {dentro}/{total}")
    assert frac >= binom.ppf(0.005, total, 0.95) / total


def test_TA3_regla_de_atribucion(faseA):
    res, v = faseA
    ceros = [n for q, n in enumerate(COMPONENTES) if v.sigmas[q, 0] == 0]
    assert ceros
    for n in ceros:
        assert res.decisiones[n] == "plantel", n


def test_TA4_diagnosticos(faseA):
    res, _ = faseA
    for n in COMPONENTES:
        d = res.posteriores[n].diag
        assert d["metodo"] == "NUTS", (n, d)
        assert d["rhat_max"] < 1.01 and d["ess_min"] > 400, (n, d)
