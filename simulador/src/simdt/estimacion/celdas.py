"""Etapa 1: cada componente por celda técnico × club × temporada (≥ 8 partidos) con su varianza.

Todas las varianzas son agrupadas por PARTIDO (sandwich o método delta sobre sumas por partido).
Las componentes que dependen de r_sk se multiplican por `inflacion_etapa1` (regresor generado).
El rival se ignora en esta etapa (calendario balanceado: todos contra todos); la etapa 2 junta
las celdas con efectos cruzados.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from .. import config
from ..modelos.cambios import MIN_INICIO, N_MIN
from ..tipos import (
    FAMILIAS,
    REF,
    BLOQUES,
    BP_CAPA1,
    BP_CON_RHO,
    COMPONENTES,
    K,
    NO_REF,
    Q,
    Liga,
    bloque_de,
)
from . import frac
from .liga import diseno_x, tabla_contexto

V_SIN_DATOS = 25.0  # varianza para una componente sin información en la celda


def asignar_celdas(partidos: pd.DataFrame) -> pd.DataFrame:
    """(match_id, equipo) -> tecnico, temporada, celda; solo celdas con ≥ min_partidos."""
    a = partidos[["match_id", "local", "tecnico_local", "temporada"]].set_axis(
        ["match_id", "equipo", "tecnico", "temporada"], axis=1
    )
    b = partidos[["match_id", "visitante", "tecnico_visitante", "temporada"]].set_axis(
        ["match_id", "equipo", "tecnico", "temporada"], axis=1
    )
    x = pd.concat([a, b], ignore_index=True).dropna(subset=["tecnico"])
    n = x.groupby(["tecnico", "equipo", "temporada"]).match_id.transform("nunique")
    x["n_partidos"] = n
    minimo = config.cargar()["estimacion"]["min_partidos_celda"]
    x = x[x.n_partidos >= minimo].copy()
    x["celda"] = x.tecnico + " | " + x.equipo + " | " + x.temporada.astype(str)
    return x


def _ratio_log(y_g, e_g):
    """log(Σy/Σe) y su varianza delta agrupada."""
    Y, E = y_g.sum(), e_g.sum()
    if Y <= 0 or E <= 0:
        return 0.0, V_SIN_DATOS
    r = Y / E
    return float(np.log(r)), float(((y_g - r * e_g) ** 2).sum() / Y**2)


def _logit_prop(s_g, n_g, ref):
    """logit(Σs/Σn) − logit(ref) con varianza delta agrupada (corrección 0.5)."""
    S, N = s_g.sum(), n_g.sum()
    if N < 1:
        return 0.0, V_SIN_DATOS
    p = (S + 0.5) / (N + 1.0)
    var_p = ((s_g - p * n_g) ** 2).sum() / N**2 + p * (1 - p) / (N + 1) ** 2
    return float(logit(p) - logit(np.clip(ref, 1e-6, 1 - 1e-6))), float(var_p / (p * (1 - p)) ** 2)


def _mlogit_celda(t: pd.DataFrame, liga: Liga, con_pendientes: bool):
    """int (k ≠ ref) [+ s_marcador, s_rival] con offset de la liga."""
    Y = t[[f"n_{k}" for k in range(K)]].to_numpy()
    if Y.sum() < 20:
        return None
    X = diseno_x(t)
    off = X @ liga.b_liga.T  # (n, K)
    libres = list(NO_REF)
    P = len(libres) + (2 if con_pendientes else 0)
    A = np.zeros((len(t), K, P))
    for r, k in enumerate(libres):
        A[:, k, r] = 1.0
    if con_pendientes:
        b = liga.b_liga
        A[:, :, 2] = X[:, [1]] * b[None, :, 1] + X[:, [2]] * b[None, :, 2]
        A[:, :, 3] = X[:, [5]] * b[None, :, 5]
    aj = frac.ajustar(Y, A, t.match_id.to_numpy(), offset=off, ridge=1e-6)
    return aj.beta, np.diag(aj.cov)


def _alpha(p: pd.DataFrame, liga: Liga):
    p = p[(p.minuto >= MIN_INICIO) & (p.minuto < MIN_INICIO + N_MIN)]
    if len(p) == 0 or p.cambio.sum() == 0:
        return 0.0, V_SIN_DATOS
    off = liga.hazard_base[(p.minuto - MIN_INICIO).to_numpy()] + liga.hazard_m[p.m.to_numpy()]
    y = p.cambio.to_numpy().astype(float)
    a = 0.0
    for _ in range(30):
        pr = expit(off + a)
        g, h = (y - pr).sum(), -(pr * (1 - pr)).sum()
        paso = -g / h
        a += paso
        if abs(paso) < 1e-10:
            break
    pr = expit(off + a)
    s_g = pd.Series(y - pr).groupby(p.match_id.to_numpy()).sum().to_numpy()
    h = (pr * (1 - pr)).sum()
    return float(a), float((s_g**2).sum() / h**2)


def _gamma(c: pd.DataFrame, liga: Liga):
    if len(c) < 3:
        return 0.0, V_SIN_DATOS
    base = liga.tipo_base[c.m.to_numpy()]  # (n, 3)
    z = np.arange(3) - 1.0
    tipo = c.tipo.to_numpy().astype(int)
    g = 0.0
    for _ in range(50):
        lg = base + g * z
        pr = np.exp(lg - lg.max(1, keepdims=True))
        pr /= pr.sum(1, keepdims=True)
        ez = pr @ z
        grad = (z[tipo] - ez).sum()
        hess = -(pr @ z**2 - ez**2).sum()
        paso = -grad / min(hess, -1e-9)
        g += paso
        if abs(paso) < 1e-10:
            break
    lg = base + g * z
    pr = np.exp(lg - lg.max(1, keepdims=True))
    pr /= pr.sum(1, keepdims=True)
    ez = pr @ z
    s_g = pd.Series(z[tipo] - ez).groupby(c.match_id.to_numpy()).sum().to_numpy()
    h = (pr @ z**2 - ez**2).sum()
    if h < 1e-6:
        return 0.0, V_SIN_DATOS
    return float(np.clip(g, -5, 5)), float((s_g**2).sum() / h**2)


def factor_varianza(nombre: str, infl) -> float:
    """Factor que multiplica la VARIANZA de la etapa 1 de la componente `nombre` [D-055].

    `infl` es un número (v1: factor de varianza, ya sin elevar) o un dict {familia: f} con el factor medido
    por la fuente sobre el ERROR ESTÁNDAR (cociente de anchos de percentiles 2.5-97.5, dtcoach
    `regresor_generado.py`); la varianza se multiplica por f². Una componente de una familia usa el f de esa
    familia; las que comparan contra la referencia (int_*) o no tienen familia (s_marcador, s_rival) usan
    el máximo de las familias implicadas, porque dependen de r_sk de todas ellas.
    """
    if not isinstance(infl, dict):
        return float(infl)
    fam = _FAMILIA_DE.get(nombre)
    if fam is not None:
        return float(infl[fam]) ** 2
    b = bloque_de(nombre)
    if b in ("int_at", "int_co"):
        e = nombre[nombre.index("[") + 1 : -1]
        return max(float(infl[e]), float(infl[FAMILIAS[REF]])) ** 2
    return max(float(v) for v in infl.values()) ** 2


_FAMILIA_DE = {
    n: n[n.index("[") + 1 : -1]
    for n in COMPONENTES
    if bloque_de(n) in ("u_at", "u_co", "w_at", "w_co")
}


def estimar_celdas(tablas: dict, liga: Liga) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (y, v): una fila por celda, una columna por componente; y la info de la celda."""
    cfg = config.cargar()
    asig = asignar_celdas(tablas["partidos"])
    t = tabla_contexto(tablas)
    clave = asig[["match_id", "equipo", "celda"]]
    t_at = t.merge(clave, on=["match_id", "equipo"], how="inner")
    t_co = t.merge(clave.rename(columns={"equipo": "rival"}), on=["match_id", "rival"], how="inner")
    tr = t.tramo.to_numpy()
    for tt in (t_at, t_co):
        tt["esperado"] = (
            tt.minutos
            * liga.lam_bar[tt.tramo.to_numpy()]
            * np.exp(liga.h_ritmo * (2 * tt.local - 1))
        )
        tt["n_tot"] = tt[[f"n_{k}" for k in range(K)]].sum(1)
    del tr
    # balón parado: exposición por (partido, equipo, tramo)
    expo = (
        tablas["exposicion"].groupby(["match_id", "equipo", "tramo"], as_index=False).minutos.sum()
    )
    loc = t[["match_id", "equipo", "local"]].drop_duplicates()
    expo = expo.merge(loc, on=["match_id", "equipo"]).merge(clave, on=["match_id", "equipo"])
    s = tablas["saques"]
    s_at = s.merge(clave, on=["match_id", "equipo"])
    s_co = s.merge(clave.rename(columns={"equipo": "rival"}), on=["match_id", "rival"])
    panel = tablas["panel"].merge(clave, on=["match_id", "equipo"])
    camb = tablas["cambios"].merge(clave, on=["match_id", "equipo"])
    infl = cfg["estimacion"]["inflacion_etapa1"]
    dep_r = set(cfg["componentes"]["dependen_de_r"])

    celdas = asig.groupby("celda").agg(
        tecnico=("tecnico", "first"),
        club=("equipo", "first"),
        temporada=("temporada", "first"),
        n_partidos=("match_id", "nunique"),
    )
    Yc = np.zeros((len(celdas), Q))
    Vc = np.full((len(celdas), Q), V_SIN_DATOS)
    g_at = dict(tuple(t_at.groupby("celda")))
    g_co = dict(tuple(t_co.groupby("celda")))
    g_ex = dict(tuple(expo.groupby("celda")))
    g_sa = dict(tuple(s_at.groupby("celda")))
    g_sc = dict(tuple(s_co.groupby("celda")))
    g_pa = dict(tuple(panel.groupby("celda")))
    g_ca = dict(tuple(camb.groupby("celda")))
    vacio_s = s.iloc[:0]
    for i, c in enumerate(celdas.index):
        ta, tc = g_at.get(c), g_co.get(c)
        if ta is not None and len(ta):
            r = _mlogit_celda(ta, liga, con_pendientes=True)
            if r is not None:
                b, v = r
                Yc[i, BLOQUES["int_at"]], Vc[i, BLOQUES["int_at"]] = b[:2], v[:2]
                Yc[i, BLOQUES["s_marcador"]], Vc[i, BLOQUES["s_marcador"]] = b[2], v[2]
                Yc[i, BLOQUES["s_rival"]], Vc[i, BLOQUES["s_rival"]] = b[3], v[3]
            pm = ta.groupby("match_id")
            sums = pm[
                ["n_tot", "esperado"]
                + [f"{a}_{k}" for a in ("n", "remates", "xg") for k in range(K)]
            ].sum()
            Yc[i, BLOQUES["l_at"]], Vc[i, BLOQUES["l_at"]] = _ratio_log(
                sums.n_tot.to_numpy(), sums.esperado.to_numpy()
            )
            for k in range(K):
                q = BLOQUES["u_at"][k]
                Yc[i, q], Vc[i, q] = _logit_prop(
                    sums[f"remates_{k}"].to_numpy(), sums[f"n_{k}"].to_numpy(), liga.p_bar[k]
                )
                q = BLOQUES["w_at"][k]
                y_, v_ = _ratio_log(
                    sums[f"xg_{k}"].to_numpy(), liga.g_bar[k] * sums[f"remates_{k}"].to_numpy()
                )
                Yc[i, q], Vc[i, q] = y_, v_
        if tc is not None and len(tc):
            r = _mlogit_celda(tc, liga, con_pendientes=False)
            if r is not None:
                Yc[i, BLOQUES["int_co"]], Vc[i, BLOQUES["int_co"]] = r[0], r[1]
            pm = tc.groupby("match_id")
            sums = pm[
                ["n_tot", "esperado"]
                + [f"{a}_{k}" for a in ("n", "remates", "xg") for k in range(K)]
            ].sum()
            Yc[i, BLOQUES["l_co"]], Vc[i, BLOQUES["l_co"]] = _ratio_log(
                sums.n_tot.to_numpy(), sums.esperado.to_numpy()
            )
            for k in range(K):
                q = BLOQUES["u_co"][k]
                Yc[i, q], Vc[i, q] = _logit_prop(
                    sums[f"remates_{k}"].to_numpy(), sums[f"n_{k}"].to_numpy(), liga.p_bar[k]
                )
                q = BLOQUES["w_co"][k]
                Yc[i, q], Vc[i, q] = _ratio_log(
                    sums[f"xg_{k}"].to_numpy(), liga.g_bar[k] * sums[f"remates_{k}"].to_numpy()
                )
        ex = g_ex.get(c)
        sa = g_sa.get(c, vacio_s)
        sc = g_sc.get(c, vacio_s)
        if ex is not None:
            for r_, u in enumerate(BP_CON_RHO):
                esp = (
                    ex.minutos
                    * liga.r_bar[u, ex.tramo.to_numpy()]
                    * np.exp(liga.h_bp * (2 * ex.local - 1))
                )
                esp_g = esp.groupby(ex.match_id).sum()
                obs_g = (
                    sa[sa.u == u].groupby("match_id").n.sum().reindex(esp_g.index, fill_value=0.0)
                )
                q = BLOQUES["rho"][r_]
                Yc[i, q], Vc[i, q] = _ratio_log(obs_g.to_numpy(), esp_g.to_numpy())
        for nombre, tabla in (("nu_at", sa), ("nu_co", sc)):
            for r_, u in enumerate(BP_CAPA1):
                su = tabla[tabla.u == u].groupby("match_id")[["n", "remates"]].sum()
                q = BLOQUES[nombre][r_]
                Yc[i, q], Vc[i, q] = _logit_prop(
                    su.remates.to_numpy(), su.n.to_numpy(), liga.q_bar[u]
                )
        pa = g_pa.get(c)
        if pa is not None:
            Yc[i, BLOQUES["alpha"]], Vc[i, BLOQUES["alpha"]] = _alpha(pa, liga)
        ca = g_ca.get(c)
        if ca is not None:
            Yc[i, BLOQUES["gamma"]], Vc[i, BLOQUES["gamma"]] = _gamma(ca, liga)
    for q, nombre in enumerate(COMPONENTES):
        if bloque_de(nombre) in dep_r:
            Vc[:, q] *= factor_varianza(nombre, infl)
    Vc = np.where(np.isfinite(Vc) & (Vc > 0), Vc, V_SIN_DATOS)
    Vc = np.minimum(Vc, V_SIN_DATOS)
    y = pd.DataFrame(Yc, index=celdas.index, columns=COMPONENTES)
    v = pd.DataFrame(Vc, index=celdas.index, columns=COMPONENTES)
    return celdas.assign(**{}), pd.concat({"y": y, "v": v}, axis=1)
