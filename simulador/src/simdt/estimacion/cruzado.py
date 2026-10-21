"""Etapa 2: modelo bayesiano de efectos cruzados por componente (fase A).

    y_c ~ N(b0 + φ[club, temp] + θ[técnico] + ε[técnico, club], v_c)
    φ[club, 1] ~ N(0, σ_φ);  φ[club, t] ~ N(φ[club, t−1], σ_Δ)        (caminata aleatoria)
    θ ~ N(0, σ_θ);  ε ~ N(0, σ_int);  σ_* ~ HalfNormal(2·sd(y));  b0 ~ N(0, sd(y))
Parametrización no centrada; NUTS de numpyro (4 cadenas, 1000 + 1000). Si R̂ ≥ 1.01 o
ESS ≤ 400: se reintenta con más ajuste y target_accept mayor; si sigue fallando, fallback REML.
Regla de atribución: f_θ = σ_θ² / (σ_θ² + σ_φ² + σ_int²); si su percentil 2.5 < 0.05 la
componente queda SOLO del plantel.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import config


@dataclass
class Indices:
    clubes: list
    tecnicos: list
    pares: list  # (tecnico, club)
    n_temp: int
    club_c: np.ndarray
    temp_c: np.ndarray
    tec_c: np.ndarray
    par_c: np.ndarray


def indices(celdas: pd.DataFrame, n_temp: int | None = None) -> Indices:
    clubes = sorted(celdas.club.unique())
    tecnicos = sorted(celdas.tecnico.unique())
    pares = sorted(set(zip(celdas.tecnico, celdas.club)))
    nt = int(celdas.temporada.max()) + 1 if n_temp is None else n_temp
    return Indices(
        clubes,
        tecnicos,
        pares,
        nt,
        celdas.club.map({c: i for i, c in enumerate(clubes)}).to_numpy(),
        celdas.temporada.to_numpy().astype(int),
        celdas.tecnico.map({t: i for i, t in enumerate(tecnicos)}).to_numpy(),
        np.array([pares.index(p) for p in zip(celdas.tecnico, celdas.club)]),
    )


@dataclass
class Posterior:
    componente: str
    b0: np.ndarray  # (D,)
    sigma: np.ndarray  # (D, 4): theta, phi, int, delta
    theta: np.ndarray  # (D, n_tec)
    phi: np.ndarray  # (D, n_club, n_temp)
    eps: np.ndarray  # (D, n_pares)
    diag: dict = field(default_factory=dict)

    @property
    def f_theta(self) -> np.ndarray:
        s = self.sigma**2
        return s[:, 0] / np.maximum(s[:, 0] + s[:, 1] + s[:, 2], 1e-300)


def _modelo(y, v, ix: Indices):
    import pymc as pm

    sd = float(np.std(y)) if np.std(y) > 1e-6 else 1.0
    nc, nt = len(ix.clubes), ix.n_temp
    with pm.Model() as m:
        b0 = pm.Normal("b0", 0.0, sd)
        s_theta = pm.HalfNormal("s_theta", 2 * sd)
        s_phi = pm.HalfNormal("s_phi", 2 * sd)
        s_int = pm.HalfNormal("s_int", 2 * sd)
        s_delta = pm.HalfNormal("s_delta", 2 * sd)
        z_th = pm.Normal("z_th", 0, 1, shape=len(ix.tecnicos))
        z_ep = pm.Normal("z_ep", 0, 1, shape=len(ix.pares))
        z0 = pm.Normal("z0", 0, 1, shape=nc)
        zw = pm.Normal("zw", 0, 1, shape=(nc, max(nt - 1, 1)))
        import pytensor.tensor as pt

        camino = (
            pt.concatenate([(s_phi * z0)[:, None], s_delta * zw[:, : nt - 1]], axis=1)
            if nt > 1
            else (s_phi * z0)[:, None]
        )
        phi = pm.Deterministic("phi", pt.cumsum(camino, axis=1))
        theta = pm.Deterministic("theta", s_theta * z_th)
        eps = pm.Deterministic("eps", s_int * z_ep)
        media = b0 + phi[ix.club_c, ix.temp_c] + theta[ix.tec_c] + eps[ix.par_c]
        pm.Normal("y", media, np.sqrt(v), observed=y)
    return m


def ajustar_componente(
    nombre: str,
    y: np.ndarray,
    v: np.ndarray,
    ix: Indices,
    semilla: int,
    intento: int = 0,
    mcmc: dict | None = None,
) -> Posterior:
    import arviz as az
    import pymc as pm

    cfg = config.cargar()["estimacion"]
    mc = {**cfg["mcmc"], **(mcmc or {})}
    tune = mc["tune"] * (1 + intento)
    draws = mc["draws"] * (1 + intento)
    ta = min(mc["target_accept"] + 0.02 * intento, 0.995)
    logging.getLogger("pymc").setLevel(logging.ERROR)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with _modelo(y, v, ix):
            idata = pm.sample(
                draws=draws,
                tune=tune,
                chains=mc["chains"],
                nuts_sampler=mc["sampler"],
                target_accept=ta,
                random_seed=semilla,
                progressbar=False,
            )
    vars_ = ["b0", "s_theta", "s_phi", "s_int", "s_delta", "z_th", "z_ep", "z0", "zw"]
    rhat = az.rhat(idata, var_names=vars_)
    ess = az.ess(idata, var_names=vars_)
    rmax = max(float(np.nanmax(rhat[k].values)) for k in vars_)
    emin = min(float(np.nanmin(ess[k].values)) for k in vars_)
    div = int(idata.sample_stats["diverging"].values.sum())
    post = idata.posterior

    def f(k):  # se adelgaza a `draws` × cadenas muestras
        a = post[k].values[:, :: (1 + intento)]
        return a.reshape(-1, *a.shape[2:])

    sig = np.column_stack([f("s_theta"), f("s_phi"), f("s_int"), f("s_delta")])
    return Posterior(
        nombre,
        f("b0"),
        sig,
        f("theta"),
        f("phi"),
        f("eps"),
        {
            "rhat_max": rmax,
            "ess_min": emin,
            "divergencias": div,
            "intento": intento,
            "metodo": "NUTS",
        },
    )


def ajustar_reml(
    nombre: str, y: np.ndarray, v: np.ndarray, ix: Indices, D: int, semilla: int
) -> Posterior:
    """Fallback: componentes de varianza por REML (MixedLM) y aproximación normal."""
    import statsmodels.formula.api as smf

    df = pd.DataFrame(
        {
            "y": y,
            "tec": ix.tec_c.astype(str),
            "clubtemp": [f"{a}_{b}" for a, b in zip(ix.club_c, ix.temp_c)],
            "par": ix.par_c.astype(str),
            "g": 1,
        }
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = smf.mixedlm(
            "y ~ 1",
            df,
            groups="g",
            vc_formula={"tec": "0 + C(tec)", "clubtemp": "0 + C(clubtemp)", "par": "0 + C(par)"},
            re_formula="0",
        ).fit(reml=True)
    vc = dict(zip(mod.model.exog_vc.names, np.maximum(mod.vcomp, 0)))
    s_th, s_ph, s_in = (np.sqrt(vc.get(k, 0.0)) for k in ("tec", "clubtemp", "par"))
    rng = np.random.default_rng(semilla)
    re = next(iter(mod.random_effects.values())) if len(mod.random_effects) else {}
    nt, nc = len(ix.tecnicos), len(ix.clubes)
    th_mean = np.zeros(nt)
    for i in range(nt):
        th_mean[i] = re.get(f"tec[C(tec)[{i}]]", 0.0)
    sd_th = s_th / np.sqrt(1 + np.bincount(ix.tec_c, minlength=nt))
    theta = th_mean[None] + rng.normal(size=(D, nt)) * sd_th[None]
    phi = np.zeros((D, nc, ix.n_temp))
    for c_, t_ in set(zip(ix.club_c, ix.temp_c)):
        phi[:, c_, t_] = (
            re.get(f"clubtemp[C(clubtemp)[{c_}_{t_}]]", 0.0) + rng.normal(size=D) * s_ph / 2
        )
    eps = rng.normal(size=(D, len(ix.pares))) * s_in / 2
    sig = np.column_stack(
        [np.full(D, s_th), np.full(D, s_ph), np.full(D, s_in), np.full(D, s_ph / 3)]
    )
    return Posterior(
        nombre,
        np.full(D, float(mod.fe_params.iloc[0])),
        sig,
        theta,
        phi,
        eps,
        {
            "rhat_max": np.nan,
            "ess_min": np.nan,
            "divergencias": 0,
            "intento": 3,
            "metodo": "REML ⚠️",
        },
    )


def ajustar_todas(
    celdas: pd.DataFrame,
    yv: pd.DataFrame,
    semilla: int,
    n_temp: int | None = None,
    verbose: bool = True,
    componentes: list | None = None,
    mcmc: dict | None = None,
) -> tuple[dict, Indices]:
    cfg = dict(config.cargar()["estimacion"])
    if mcmc:
        cfg["mcmc"] = {**cfg["mcmc"], **mcmc}
        cfg["ess_min"] = mcmc.get("ess_min", cfg["ess_min"])
    ix = indices(celdas, n_temp)
    out = {}
    nombres = componentes or list(yv["y"].columns)
    for q, nombre in enumerate(yv["y"].columns):
        if nombre not in nombres:
            continue
        y = yv["y"][nombre].to_numpy()
        v = yv["v"][nombre].to_numpy()
        post = None
        for intento in range(3):
            try:
                post = ajustar_componente(
                    nombre, y, v, ix, semilla + 97 * q + intento, intento, cfg["mcmc"]
                )
            except Exception as e:  # noqa: BLE001
                if verbose:
                    print(f"  {nombre}: error en NUTS ({e}); intento {intento + 1}")
                post = None
                continue
            if post.diag["rhat_max"] < cfg["rhat_max"] and post.diag["ess_min"] > cfg["ess_min"]:
                break
            if verbose:
                print(
                    f"  {nombre}: intento {intento + 1} sin converger (R̂={post.diag['rhat_max']:.4f}, "
                    f"ESS={post.diag['ess_min']:.0f}, divergencias={post.diag['divergencias']})",
                    flush=True,
                )
        if post is None or not (
            post.diag["rhat_max"] < cfg["rhat_max"] and post.diag["ess_min"] > cfg["ess_min"]
        ):
            D = cfg["mcmc"]["draws"] * cfg["mcmc"]["chains"]
            try:
                post = ajustar_reml(nombre, y, v, ix, D, semilla + q)
            except Exception as e:  # noqa: BLE001
                if verbose:
                    print(f"  {nombre}: REML también falló ({e}); queda en la liga ⚠️")
                post = Posterior(
                    nombre,
                    np.zeros(D),
                    np.zeros((D, 4)),
                    np.zeros((D, len(ix.tecnicos))),
                    np.zeros((D, len(ix.clubes), ix.n_temp)),
                    np.zeros((D, len(ix.pares))),
                    {"metodo": "liga ⚠️", "rhat_max": np.nan, "ess_min": np.nan, "intento": 3},
                )
        out[nombre] = post
        if verbose:
            f = post.f_theta
            print(
                f"  {nombre:28s} R̂={post.diag['rhat_max']:.4f} ESS={post.diag['ess_min']:.0f} "
                f"f_θ={np.median(f):.2f} [{np.quantile(f, 0.025):.3f}, {np.quantile(f, 0.975):.2f}] "
                f"{post.diag['metodo']}",
                flush=True,
            )
    return out, ix


def decision(post: Posterior) -> str:
    """'tecnico' o 'plantel' según la regla pre-registrada."""
    umbral = config.cargar()["estimacion"]["umbral_f_theta"]
    if post.diag.get("metodo", "").startswith("liga"):
        return "liga"
    return "plantel" if np.quantile(post.f_theta, 0.025) < umbral else "tecnico"
