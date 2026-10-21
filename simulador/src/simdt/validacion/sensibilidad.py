"""Sensibilidad global (Sobol) de los puntos esperados del América a cada perilla.

Muestreo de Saltelli con SALib (N ≥ 1024), salida = puntos esperados exactos en el torneo
(suma de xPts de los 17 partidos) con las fichas medias de los rivales y del plantel.
Regla (D-034): una perilla con índice total S_T < 0.05 (y su IC sin pasar de 0.05) se marca
"solo cambia el estilo, no los puntos".
"""

from __future__ import annotations

import numpy as np
from SALib.analyze import sobol
from SALib.sample import sobol as muestreo

from ..estimacion.fichas import ficha_foco
from ..motor.partido import partido_lote
from ..perillas import mapeo
from ..tipos import BLOQUES, Q

PERILLAS = (
    "mezcla",
    "rival",
    "reaccion_marcador",
    "reaccion_rival",
    "balon_parado",
    "cambios_momento",
    "cambios_tipo",
)
NOMBRES = [
    "mezcla_directa",
    "mezcla_elaborada",
    "rival_directa",
    "rival_elaborada",
    "reaccion_marcador",
    "reaccion_rival",
    "balon_parado",
    "cambios_momento",
    "cambios_tipo",
]
LIMITES = [
    [0.10, 0.45],
    [0.10, 0.45],
    [0.10, 0.45],
    [0.10, 0.45],
    [0.0, 2.0],
    [0.0, 2.0],
    [1, 99],
    [1, 99],
    [15, 85],
]
GRUPO = {
    "mezcla_directa": "mezcla",
    "mezcla_elaborada": "mezcla",
    "rival_directa": "rival",
    "rival_elaborada": "rival",
    "reaccion_marcador": "reaccion_marcador",
    "reaccion_rival": "reaccion_rival",
    "balon_parado": "balon_parado",
    "cambios_momento": "cambios_momento",
    "cambios_tipo": "cambios_tipo",
}


def theta_de_fila(x: np.ndarray, liga, esc) -> np.ndarray:
    from scipy.stats import norm

    th = mapeo.perillas_a_tecnico(
        {
            "mezcla": (x[0], x[1]),
            "rival": (x[2], x[3]),
            "balon_parado": x[6],
            "cambios_momento": x[7],
        },
        liga,
        esc,
    )
    for v, b in ((x[4], "s_marcador"), (x[5], "s_rival")):
        q = BLOQUES[b][0]
        th[q] = v - 1.0 - esc.b0[q]
    q = BLOQUES["gamma"][0]
    th[q] = esc.tau(q) * norm.ppf(x[8] / 100.0)
    return esc.limitar(th, [BLOQUES["s_marcador"][0], BLOQUES["s_rival"][0], q])


def puntos_esperados(sim, thetas: np.ndarray, G: int = 10, lote: int = 4000) -> np.ndarray:
    """Puntos esperados exactos para cada θ (filas) con fichas medias."""
    pz = sim.p.piezas
    cal, foco = sim.calendario, sim.foco
    prop = np.flatnonzero((cal[:, 0] == foco) | (cal[:, 1] == foco))
    es_local = cal[prop, 0] == foco
    rival = np.where(es_local, cal[prop, 1], cal[prop, 0])
    zr = pz.fichas.mean(0)[rival]  # (17, Q)
    de = sim.elo[foco] - sim.elo[rival]
    base_idx = np.arange(pz.fichas.shape[0])
    medias = []
    # ficha del foco: plantel medio + θ (ε nuevo de media cero → se usa su media, 0)
    piezas_media = type(pz)(
        pz.equipos,
        pz.fichas.mean(0, keepdims=True),
        pz.base_foco.mean(0, keepdims=True),
        {},
        {},
        pz.sigma.mean(0, keepdims=True) * 0.0,
        np.zeros((1, Q)),
        pz.decisiones,
        pz.foco,
        pz.tecnico_actual_foco,
        pz.atribucion,
    )
    zf = np.array([ficha_foco(piezas_media, th, np.array([0]))[0] for th in thetas])
    del base_idx
    n = len(zf)
    zi = np.repeat(zf, len(prop), 0)
    zj = np.tile(zr, (n, 1))
    loc = np.tile(es_local.astype(float), n)
    dd = np.tile(de, n)
    out = np.empty(len(zi))
    for a in range(0, len(zi), lote):
        d = partido_lote(
            sim.p.liga, zi[a : a + lote], zj[a : a + lote], loc[a : a + lote], dd[a : a + lote], G=G
        )
        out[a : a + lote] = d.xpts_i
    medias = out.reshape(n, len(prop)).sum(1)
    return medias


def limites(esc, liga) -> list:
    """Límites del muestreo: los de siempre con atribución binaria; con la continua, el rango de los técnicos plausibles de cada perilla (D-051)."""
    if not esc.continua or esc.theta_lo is None:
        return LIMITES
    r = mapeo.rangos_perillas(esc, liga)
    L = [list(LIMITES[i]) for i in range(len(LIMITES))]
    L[0], L[1] = (
        [r["mezcla"]["directa"][0] / 100, r["mezcla"]["directa"][1] / 100],
        [r["mezcla"]["elaborada"][0] / 100, r["mezcla"]["elaborada"][1] / 100],
    )
    L[2], L[3] = (
        [r["rival"]["directa"][0] / 100, r["rival"]["directa"][1] / 100],
        [r["rival"]["elaborada"][0] / 100, r["rival"]["elaborada"][1] / 100],
    )
    L[6], L[7] = list(r["balon_parado"]), list(r["cambios_momento"])
    return [[float(a), float(b)] if b > a else [float(a), float(a) + 1e-3] for a, b in L]


def evaluar(sim, N: int = 1024, semilla: int = 20261008, umbral: float = 0.05) -> dict:
    problema = {
        "num_vars": len(NOMBRES),
        "names": NOMBRES,
        "bounds": limites(sim.p.escalas, sim.p.liga),
    }
    X = muestreo.sample(problema, N, calc_second_order=False, seed=semilla)
    th = np.array([theta_de_fila(x, sim.p.liga, sim.p.escalas) for x in X])
    Y = puntos_esperados(sim, th)
    S = sobol.analyze(problema, Y, calc_second_order=False, seed=semilla)
    tabla = []
    for i, nnm in enumerate(NOMBRES):
        tabla.append(
            {
                "perilla": nnm,
                "S1": float(S["S1"][i]),
                "S1_ic": float(S["S1_conf"][i]),
                "ST": float(S["ST"][i]),
                "ST_ic": float(S["ST_conf"][i]),
            }
        )
    tabla.sort(key=lambda r: -r["ST"])
    grupos = {}
    for r in tabla:
        g = GRUPO[r["perilla"]]
        grupos[g] = max(grupos.get(g, 0.0), r["ST"] + r["ST_ic"])
    solo_estilo = sorted(g for g, v in grupos.items() if v < umbral)
    return {
        "N": N,
        "evaluaciones": int(len(X)),
        "puntos_media": float(Y.mean()),
        "puntos_sd": float(Y.std()),
        "puntos_rango": [float(Y.min()), float(Y.max())],
        "tabla": tabla,
        "solo_estilo": solo_estilo,
        "umbral_ST": umbral,
    }
