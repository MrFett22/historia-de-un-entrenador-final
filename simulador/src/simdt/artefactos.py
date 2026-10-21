"""Escritura y lectura de los artefactos agregados que usa la app (artefactos/).

Solo parámetros agregados por equipo, técnico o liga: nada a nivel de evento o secuencia.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .estimacion.fichas import PiezasFichas
from .perillas.mapeo import Escalas, rango_plausible
from .tipos import COMPONENTES, Liga

SIGMAS = ("s_theta", "s_phi", "s_int", "s_delta")


def _ancho(M: np.ndarray, **cols) -> pd.DataFrame:
    df = pd.DataFrame(M.astype(np.float32), columns=list(COMPONENTES))
    for k, v in reversed(list(cols.items())):
        df.insert(0, k, v)
    return df


def escribir(
    directorio: Path,
    liga: Liga,
    piezas: PiezasFichas,
    meta: dict,
    presets: list,
    pares: pd.DataFrame,
    cadenas: tuple | None,
    tabla_fase_a: pd.DataFrame,
) -> None:
    d = Path(directorio)
    d.mkdir(parents=True, exist_ok=True)
    M, E, _ = piezas.fichas.shape
    (d / "liga.json").write_text(json.dumps(liga.a_dict(), ensure_ascii=False), encoding="utf-8")
    filas = []
    for e, eq in enumerate(piezas.equipos):
        filas.append(_ancho(piezas.fichas[:, e], muestra=np.arange(M), equipo=eq))
    pd.concat(filas).to_parquet(d / "fichas_posterior.parquet", index=False)
    filas = [_ancho(th, muestra=np.arange(M), tecnico=t) for t, th in piezas.theta_tec.items()]
    pd.concat(filas).to_parquet(d / "tecnicos_posterior.parquet", index=False)
    filas = [
        _ancho(piezas.base_foco, muestra=np.arange(M), tipo="base"),
        _ancho(piezas.z_eps, muestra=np.arange(M), tipo="z_eps"),
    ]
    filas += [_ancho(v, muestra=np.arange(M), tipo=f"eps:{t}") for t, v in piezas.eps_foco.items()]
    pd.concat(filas).to_parquet(d / "plantel_america.parquet", index=False)
    filas = [
        _ancho(piezas.sigma[:, :, j], muestra=np.arange(M), parametro=s)
        for j, s in enumerate(SIGMAS)
    ]
    pd.concat(filas).to_parquet(d / "sigmas_posterior.parquet", index=False)
    pares.to_parquet(d / "coherencia_pares.parquet", index=False)
    if cadenas is not None:
        extra = {"P0": cadenas[2]} if len(cadenas) > 2 and cadenas[2] is not None else {}
        np.savez_compressed(d / "cadenas.npz", P=cadenas[0], mu=cadenas[1], **extra)
    tabla_fase_a.to_json(d / "fase_A.json", orient="records", force_ascii=False, indent=1)
    meta = dict(meta)
    meta.update(
        {
            "equipos": piezas.equipos,
            "foco": piezas.equipos[piezas.foco],
            "tecnico_actual_foco": piezas.tecnico_actual_foco,
            "decisiones": piezas.decisiones,
            "n_muestras": int(M),
            "atribucion": piezas.atribucion,
        }
    )
    (d / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )
    (d / "presets.json").write_text(
        json.dumps(presets, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )


@dataclass
class Paquete:
    liga: Liga
    piezas: PiezasFichas
    meta: dict
    presets: list
    pares: pd.DataFrame
    cadenas: tuple | None
    escalas: Escalas
    fase_a: pd.DataFrame


def cargar(directorio: Path | None = None) -> Paquete:
    d = Path(directorio or config.ARTEFACTOS)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    liga = Liga.de_dict(json.loads((d / "liga.json").read_text(encoding="utf-8")))
    comp = list(COMPONENTES)
    f = pd.read_parquet(d / "fichas_posterior.parquet")
    equipos = meta["equipos"]
    M = int(meta["n_muestras"])
    fichas = np.zeros((M, len(equipos), len(comp)))
    for e, eq in enumerate(equipos):
        fichas[:, e] = f[f.equipo == eq].sort_values("muestra")[comp].to_numpy()
    t = pd.read_parquet(d / "tecnicos_posterior.parquet")
    theta_tec = {
        n: g.sort_values("muestra")[comp].to_numpy().astype(float) for n, g in t.groupby("tecnico")
    }
    pl = pd.read_parquet(d / "plantel_america.parquet")
    base = pl[pl.tipo == "base"].sort_values("muestra")[comp].to_numpy().astype(float)
    z_eps = pl[pl.tipo == "z_eps"].sort_values("muestra")[comp].to_numpy().astype(float)
    eps = {
        k[4:]: g.sort_values("muestra")[comp].to_numpy().astype(float)
        for k, g in pl.groupby("tipo")
        if k.startswith("eps:")
    }
    s = pd.read_parquet(d / "sigmas_posterior.parquet")
    sigma = np.stack(
        [s[s.parametro == p].sort_values("muestra")[comp].to_numpy() for p in SIGMAS], axis=2
    )
    piezas = PiezasFichas(
        equipos,
        fichas,
        base,
        theta_tec,
        eps,
        sigma,
        z_eps,
        meta["decisiones"],
        equipos.index(meta["foco"]),
        meta.get("tecnico_actual_foco"),
        meta.get("atribucion", "binaria"),
    )
    fa = pd.read_json(d / "fase_A.json", orient="records")
    b0 = (
        fa.set_index("componente").loc[comp, "b0"].to_numpy() if "b0" in fa else np.zeros(len(comp))
    )
    esc = Escalas(
        b0=b0,
        sigma_theta=np.median(sigma[:, :, 0], axis=0),
        decisiones=meta["decisiones"],
        atribucion=piezas.atribucion,
    )
    if piezas.atribucion == "continua":
        esc.theta_lo, esc.theta_hi = rango_plausible(sigma[:, :, 0])
    cad = None
    if (d / "cadenas.npz").exists():
        z = np.load(d / "cadenas.npz")
        cad = (z["P"], z["mu"], z["P0"] if "P0" in z.files else None)
        liga.P_cadenas, liga.mu_cadenas = z["P"], z["mu"]
        liga.P0_cadenas = z["P0"] if "P0" in z.files else None
    presets = json.loads((d / "presets.json").read_text(encoding="utf-8"))
    pares = pd.read_parquet(d / "coherencia_pares.parquet")
    return Paquete(liga, piezas, meta, presets, pares, cad, esc, fa)
