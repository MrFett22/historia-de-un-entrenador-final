"""Parámetros de la liga m (04_ESPECIFICACION §1) a partir de las tablas comunes."""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from ..tipos import BP_CAPA1, K, REF, U, Liga
from . import frac


def correr_elo(partidos: pd.DataFrame, K_elo: float, h: float, inicial: float = 1500.0):
    """Elo previo a cada partido (procedencia: dtcoach/elo.py@77b720b, sin polars).

    Devuelve (elo_local, elo_visitante) por fila en el orden dado y los ratings finales.
    """
    p = partidos.sort_values(["fecha", "match_id"])
    R: dict[str, float] = {}
    el, ev = {}, {}
    for mid, loc, vis, gl, gv in p[
        ["match_id", "local", "visitante", "goles_local", "goles_visitante"]
    ].itertuples(index=False):
        ra, rb = R.get(loc, inicial), R.get(vis, inicial)
        el[mid], ev[mid] = ra, rb
        if pd.isna(gl) or pd.isna(gv):
            continue
        E = 1.0 / (1.0 + 10 ** ((rb - ra - h) / 400.0))
        S = 1.0 if gl > gv else (0.5 if gl == gv else 0.0)
        R[loc] = ra + K_elo * (S - E)
        R[vis] = rb - K_elo * (S - E)
    return partidos["match_id"].map(el).to_numpy(), partidos["match_id"].map(ev).to_numpy(), R


def elo_dif_por_equipo(partidos: pd.DataFrame) -> pd.DataFrame:
    a = pd.DataFrame(
        {
            "match_id": partidos.match_id,
            "equipo": partidos.local,
            "elo_dif": partidos.elo_local - partidos.elo_visitante,
        }
    )
    b = pd.DataFrame(
        {
            "match_id": partidos.match_id,
            "equipo": partidos.visitante,
            "elo_dif": partidos.elo_visitante - partidos.elo_local,
        }
    )
    return pd.concat([a, b], ignore_index=True)


def tabla_contexto(tablas: dict) -> pd.DataFrame:
    """Una fila por (partido, equipo, tramo, m) con conteos por tipo de jugada y covariables."""
    j = tablas["juego"]
    piv = j.pivot_table(
        index=["match_id", "equipo", "rival", "local", "tramo", "m"],
        columns="k",
        values=["n", "remates", "xg", "goles"],
        aggfunc="sum",
        fill_value=0.0,
    )
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    piv = piv.reset_index()
    for k in range(K):
        for c in ("n", "remates", "xg", "goles"):
            if f"{c}_{k}" not in piv:
                piv[f"{c}_{k}"] = 0.0
    piv = piv.merge(elo_dif_por_equipo(tablas["partidos"]), on=["match_id", "equipo"], how="left")
    piv["elo_dif"] = piv["elo_dif"].fillna(0.0)
    expo = tablas["exposicion"]
    piv = piv.merge(expo, on=["match_id", "equipo", "tramo", "m"], how="left")
    piv["minutos"] = piv["minutos"].fillna(0.0)
    return piv


def diseno_x(t: pd.DataFrame) -> np.ndarray:
    """x = (1, pierde, gana, tramo_final, local, ΔElo/100)."""
    return np.column_stack(
        [
            np.ones(len(t)),
            (t.m == 0).astype(float),
            (t.m == 2).astype(float),
            (t.tramo == 5).astype(float),
            t.local.astype(float),
            t.elo_dif / 100.0,
        ]
    )


def _ritmo(conteo: pd.DataFrame, valor: str) -> tuple[np.ndarray, float]:
    """Poisson con exposición: log E[n] = log(min) + a_τ + h·(2·local − 1)."""
    c = conteo[conteo.minutos > 0]
    X = np.column_stack([np.eye(6)[c.tramo.to_numpy()], 2 * c.local.to_numpy() - 1.0])
    mod = sm.GLM(
        c[valor].to_numpy(), X, family=sm.families.Poisson(), offset=np.log(c.minutos.to_numpy())
    ).fit()
    return np.exp(mod.params[:6]), float(mod.params[6])


def estimar_liga(
    tablas: dict,
    minutos: int = 90,
    P_cadenas=None,
    mu_cadenas=None,
    usar_factor_gol: bool = True,
    P0_cadenas=None,
) -> tuple[Liga, dict]:
    t = tabla_contexto(tablas)
    Y = t[[f"n_{k}" for k in range(K)]].to_numpy()
    t["n_tot"] = Y.sum(1)
    # M1: ritmo por tramo (exposición: minutos de cada equipo en cada tramo)
    por_tramo = t.groupby(["match_id", "equipo", "local", "tramo"], as_index=False)[
        ["n_tot", "minutos"]
    ].sum()
    lam_bar, h = _ritmo(por_tramo, "n_tot")
    # M2: logit fraccional con el diseño x
    X = diseno_x(t)
    A = frac.diseno_liga(X, K, REF)
    aj = frac.ajustar(Y, A, t.match_id.to_numpy())
    b = np.zeros((K, 6))
    libres = [k for k in range(K) if k != REF]
    for r, k in enumerate(libres):
        b[k] = aj.beta[r * 6 : (r + 1) * 6]
    # M3
    n_k = Y.sum(0)
    rem = t[[f"remates_{k}" for k in range(K)]].to_numpy().sum(0)
    xg = t[[f"xg_{k}" for k in range(K)]].to_numpy().sum(0)
    p_bar, g_bar = rem / n_k, xg / np.maximum(rem, 1e-12)
    # M4
    s = tablas["saques"]
    expo = (
        tablas["exposicion"]
        .groupby(["match_id", "equipo", "tramo"], as_index=False)["minutos"]
        .sum()
    )
    loc = t[["match_id", "equipo", "local"]].drop_duplicates()
    expo = expo.merge(loc, on=["match_id", "equipo"], how="left")
    r_bar = np.zeros((U, 6))
    h_bps = []
    for u in range(U):
        su = s[s.u == u].groupby(["match_id", "equipo", "tramo"], as_index=False)["n"].sum()
        c = expo.merge(su, on=["match_id", "equipo", "tramo"], how="left").fillna({"n": 0.0})
        r_bar[u], hu = _ritmo(c, "n")
        h_bps.append((hu, c.n.sum()))
    h_bp = float(sum(hh * w for hh, w in h_bps) / sum(w for _, w in h_bps))
    tot = s.groupby("u")[["n", "remates", "xg"]].sum().reindex(range(U), fill_value=0.0)
    q_bar = np.ones(U)
    q_bar[list(BP_CAPA1)] = (tot.remates / tot.n.clip(lower=1e-12)).to_numpy()[list(BP_CAPA1)]
    kappa = (tot.xg / tot.remates.clip(lower=1e-12)).to_numpy()
    # cambios
    hb, hm = _hazard(tablas["panel"])
    tb = _tipo_base(tablas["cambios"])
    pa = tablas["partidos"]
    xg_tot = float(xg.sum() + tot.xg.sum())
    goles_tot = float((pa.goles_local + pa.goles_visitante).sum())
    factor = goles_tot / xg_tot if usar_factor_gol else 1.0
    liga = Liga(
        factor_gol=factor,
        lam_bar=lam_bar,
        h_ritmo=h,
        b_liga=b,
        p_bar=p_bar,
        g_bar=g_bar,
        r_bar=r_bar,
        h_bp=h_bp,
        q_bar=q_bar,
        kappa=kappa,
        hazard_base=hb,
        hazard_m=hm,
        tipo_base=tb,
        P_cadenas=P_cadenas,
        mu_cadenas=mu_cadenas,
        P0_cadenas=P0_cadenas,
        minutos=minutos,
    )
    diag = {
        "b_liga_se": np.sqrt(np.diag(aj.cov)).tolist(),
        "b_convergio": aj.convergio,
        "xg_total_obs": xg_tot,
        "goles_total_obs": goles_tot,
        "factor_gol": factor,
    }
    return liga, diag


def _hazard(panel: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    from ..modelos.cambios import MIN_INICIO, N_MIN

    p = panel[(panel.minuto >= MIN_INICIO) & (panel.minuto < MIN_INICIO + N_MIN)]
    if len(p) == 0 or p.cambio.sum() == 0:
        return np.full(N_MIN, -4.0), np.zeros(3)
    tt = (p.minuto - MIN_INICIO).to_numpy()
    X = np.column_stack([np.eye(N_MIN)[tt], (p.m == 0).astype(float), (p.m == 2).astype(float)])
    mod = sm.GLM(p.cambio.to_numpy(), X, family=sm.families.Binomial()).fit()
    return mod.params[:N_MIN].copy(), np.array([mod.params[N_MIN], 0.0, mod.params[N_MIN + 1]])


def _tipo_base(cambios: pd.DataFrame) -> np.ndarray:
    tb = np.zeros((3, 3))
    for m in range(3):
        c = np.bincount(cambios[cambios.m == m].tipo.astype(int), minlength=3) + 0.5
        tb[m] = np.log(c / c.sum())
    return tb


def xg_predicho_liga(liga: Liga, tablas: dict) -> float:
    """xG total que implican M1 + M4 con la exposición observada (T-P6)."""
    from ..modelos.familias import softmax

    t = tabla_contexto(tablas)
    X = diseno_x(t)
    pi = softmax(X @ liga.b_liga.T)  # (n, K)
    lam = liga.lam_bar[t.tramo.to_numpy()] * np.exp(liga.h_ritmo * (2 * t.local.to_numpy() - 1))
    open_play = (t.minutos.to_numpy() * lam * (pi @ (liga.p_bar * liga.g_bar))).sum()
    expo = tablas["exposicion"].merge(
        t[["match_id", "equipo", "local"]].drop_duplicates(), on=["match_id", "equipo"], how="left"
    )
    rate = (
        liga.r_bar[:, expo.tramo.to_numpy()].T
        * np.exp(liga.h_bp * (2 * expo.local.to_numpy() - 1))[:, None]
    )
    bp = (expo.minutos.to_numpy()[:, None] * rate * (liga.q_bar * liga.kappa)[None]).sum()
    return float(open_play + bp)
