"""Temporada completa con Monte Carlo de dos niveles.

Externo (r = 1..R): una muestra posterior de las fichas de los 18 equipos (+ la ficha del
América con el técnico simulado). Interno (s = 1..S): marcadores por inversión de la CDF de P_T
con uniformes de un generador con semilla (semilla, r) → números aleatorios comunes.
Los 136 partidos ajenos no dependen del técnico del América: se precalculan una vez por muestra
posterior (`Precalculo`) y se guardan en caché.
Los puntos esperados por réplica son exactos (Σ xPts, sin Monte Carlo interno).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .. import config
from ..tipos import ResultadoTemporada
from .partido import partido_lote
from .tabla import acumular, posiciones

GS = 10  # goles por lado al muestrear (la masa > 10 es < 1e-6 y se renormaliza)


@dataclass
class Precalculo:
    """P_T de los partidos ajenos para cada muestra posterior disponible."""

    P: np.ndarray  # (n_muestras, n_ajenos, (GS+1)²) float32, filas normalizadas
    ajenos: np.ndarray  # índices en el calendario
    propios: np.ndarray  # índices de los partidos del foco
    clave: str


def _clave(fichas, calendario, elo, foco) -> str:
    h = hashlib.sha1()
    for a in (fichas, calendario, elo, np.array([foco])):
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()[:16]


def _recortar(P: np.ndarray) -> np.ndarray:
    p = P[:, : GS + 1, : GS + 1].reshape(P.shape[0], -1)
    return (p / p.sum(1, keepdims=True)).astype(np.float32)


def precalcular(
    liga,
    fichas: np.ndarray,
    calendario: np.ndarray,
    elo: np.ndarray,
    foco: int,
    lote: int = 400,
    usar_cache: bool = True,
    verbose: bool = False,
    indices: np.ndarray | None = None,
    ruta: str | None = None,
) -> Precalculo:
    """fichas: (n_muestras, 18, Q). Calcula los ajenos de las muestras `indices` (todas si None).

    Las filas no calculadas quedan en NaN; `simular_temporada` falla si una réplica las usa.
    """
    ajenos = np.flatnonzero((calendario[:, 0] != foco) & (calendario[:, 1] != foco))
    propios = np.flatnonzero((calendario[:, 0] == foco) | (calendario[:, 1] == foco))
    n = fichas.shape[0]
    idx = np.arange(n) if indices is None else np.unique(indices)
    clave = _clave(fichas, calendario, elo, foco)
    ruta = config.cache_dir() / f"cache_rivales_{clave}.npz" if ruta is None else ruta
    C = (GS + 1) ** 2
    P = np.full((n, len(ajenos), C), np.nan, dtype=np.float32)
    if usar_cache and Path(ruta).exists():
        z = np.load(ruta)
        if (
            "clave" in z.files and str(z["clave"]) != clave
        ):  # caché de OTRAS fichas (D-052): no se usa; los archivos antiguos no traen clave
            z = None
        if z is not None:
            Pz = z["P"].astype(np.float32)
            P[z["idx"]] = Pz / Pz.sum(2, keepdims=True)  # el caché puede venir en float16
    faltan = idx[np.isnan(P[idx, 0, 0])]
    if len(faltan):
        loc, vis = calendario[ajenos, 0], calendario[ajenos, 1]
        zi = fichas[faltan][:, loc].reshape(-1, fichas.shape[2])
        zj = fichas[faltan][:, vis].reshape(-1, fichas.shape[2])
        de = np.tile(elo[loc] - elo[vis], len(faltan))
        out = np.empty((len(zi), C), dtype=np.float32)
        for a in range(0, len(zi), lote):
            d = partido_lote(liga, zi[a : a + lote], zj[a : a + lote], 1.0, de[a : a + lote])
            out[a : a + lote] = _recortar(d.P)
            if verbose and a % (lote * 20) == 0:
                print(f"  ajenos {a}/{len(zi)}", flush=True)
        P[faltan] = out.reshape(len(faltan), len(ajenos), C)
        if usar_cache:
            hechos = np.flatnonzero(~np.isnan(P[:, 0, 0]))
            np.savez_compressed(ruta, P=P[hechos], idx=hechos, clave=clave)
    return Precalculo(P, ajenos, propios, clave)


def muestras_replicas(n_muestras: int, R: int, semilla: int) -> np.ndarray:
    """Índices de la muestra posterior usada en cada réplica (iguales para cualquier técnico)."""
    rng = np.random.default_rng([semilla, 101])
    return rng.choice(
        n_muestras, R, replace=True
    )  # con reemplazo: el EE de dos etapas es exacto (D-022)


def _muestrear(cdf: np.ndarray, U: np.ndarray) -> np.ndarray:
    """cdf: (M, C) filas crecientes; U: (M, S). Índice de celda por inversión, en bloque."""
    M, C = cdf.shape
    off = np.arange(M, dtype=float)[:, None]
    plano = (cdf + off).ravel()
    q = (np.minimum(U, 1 - 1e-12) + off).ravel()
    idx = np.searchsorted(plano, q, side="right").reshape(U.shape) - np.arange(M)[:, None] * C
    return np.clip(idx, 0, C - 1)


def _bloque(
    liga,
    entorno_fichas: np.ndarray,
    fichas_foco: np.ndarray,
    calendario: np.ndarray,
    elo: np.ndarray,
    foco: int,
    idx_muestras: np.ndarray,
    S: int,
    semilla: int,
    pre: Precalculo,
    con_estilo: bool,
    r0: int,
    sel: np.ndarray,
) -> ResultadoTemporada:
    """UN bloque de réplicas consecutivas (la primera es la número `r0` del total): los uniformes de cada réplica salen de la semilla (semilla, r global), así que partir en
    bloques no cambia ningún número. Devuelve los arreglos de sus réplicas y sumas parciales; `_combinar` los junta (D-084)."""
    R = len(idx_muestras)
    nE = entorno_fichas.shape[1]
    prop = pre.propios
    loc, vis = calendario[prop, 0], calendario[prop, 1]
    es_local = loc == foco
    rival = np.where(es_local, vis, loc)
    zr = entorno_fichas[idx_muestras][:, rival]  # (R, 17, Q)
    zf = np.repeat(fichas_foco[:, None], len(prop), 1)  # (R, 17, Q)
    de = np.tile(elo[foco] - elo[rival], R)
    d = partido_lote(
        liga,
        zf.reshape(-1, zf.shape[2]),
        zr.reshape(-1, zr.shape[2]),
        np.tile(es_local.astype(float), R),
        de,
        con_detalle=con_estilo,
    )
    xpts = d.xpts_i.reshape(R, len(prop))
    puntos_exactos = xpts.sum(1)
    Pf = _recortar(d.P).reshape(R, len(prop), -1)  # desde el foco (i)
    # uniformes comunes por réplica: (S, 153) + sorteo (S, 18)
    U = np.empty((R, S, len(calendario)))
    sorteo = np.empty((R, S, nE))
    for r in range(R):
        g = np.random.default_rng([semilla, int(r) + r0])
        U[r] = g.random((S, len(calendario)))
        sorteo[r] = g.random((S, nE))
    C = (GS + 1) ** 2
    ga = np.empty((R, S, len(calendario)), dtype=np.int16)
    gb = np.empty_like(ga)
    # ajenos (precalculados por muestra posterior)
    Pa = pre.P[idx_muestras]  # (R, n_aj, C)
    if np.isnan(Pa[:, 0, 0]).any():
        raise ValueError(
            "faltan muestras en el precálculo de rivales: llama a precalcular(indices=...)"
        )
    cdf = np.cumsum(Pa, axis=2, dtype=np.float64).reshape(-1, C)
    Ua = np.transpose(U[:, :, pre.ajenos], (0, 2, 1)).reshape(-1, S)
    ia = _muestrear(cdf, Ua).reshape(R, len(pre.ajenos), S).transpose(0, 2, 1)
    ga[:, :, pre.ajenos], gb[:, :, pre.ajenos] = ia // (GS + 1), ia % (GS + 1)
    # propios: P_T está en la óptica del foco (a = goles del América)
    cdf = np.cumsum(Pf, axis=2, dtype=np.float64).reshape(-1, C)
    Up = np.transpose(U[:, :, prop], (0, 2, 1)).reshape(-1, S)
    ip = _muestrear(cdf, Up).reshape(R, len(prop), S).transpose(0, 2, 1)
    a_f, b_f = ip // (GS + 1), ip % (GS + 1)
    ga[:, :, prop] = np.where(es_local, a_f, b_f)
    gb[:, :, prop] = np.where(es_local, b_f, a_f)
    pts, gf, gc = acumular(
        calendario, ga.reshape(R * S, -1).astype(float), gb.reshape(R * S, -1).astype(float), nE
    )
    lugar = posiciones(pts, gf, gc, sorteo.reshape(R * S, nE))
    res = ResultadoTemporada(
        puntos_exactos=puntos_exactos,
        puntos=pts[:, foco].reshape(R, S).astype(np.int16),
        posicion=lugar[:, foco].reshape(R, S).astype(np.int8),
        gf=gf[:, foco].reshape(R, S).astype(np.int16),
        gc=gc[:, foco].reshape(R, S).astype(np.int16),
    )  # solo lo del foco, en tipos compactos: con 1,000,000 de torneos no se guarda nada más
    # salidas extra (no cambian el modelo): las filas de la muestra global de torneos que caen en este bloque, y sumas para la tabla esperada de los 18 equipos
    N = pts.shape[0]
    ini = r0 * S
    dentro = np.flatnonzero((sel >= ini) & (sel < ini + N))
    loc = sel[dentro] - ini
    res.interno["torneos_muestra"] = {
        "pos": dentro,
        "ga": ga.reshape(N, -1)[loc].astype(np.int8),
        "gb": gb.reshape(N, -1)[loc].astype(np.int8),
        "pts": pts[loc].astype(np.int16),
        "gf": gf[loc].astype(np.int16),
        "gc": gc[loc].astype(np.int16),
        "lugar": lugar[loc].astype(np.int8),
    }
    nl = config.cargar()["torneo"]["liguilla_directa"]
    res.interno["_sumas"] = {
        "n": N,
        "pts": pts.sum(0),
        "lug_liga": (lugar <= nl).sum(0),
        "lugar": lugar.sum(0),
    }
    res.interno["suma_puntos_liga"] = pts.sum(1).reshape(R, S).astype(np.int16)
    res.interno.update(_victorias_empates(ga.reshape(R * S, -1), gb.reshape(R * S, -1)))
    res.interno["xpts"] = xpts
    if con_estilo:
        ex = d.extra
        # promedios por partido (sobre réplicas y los 17 partidos)
        res.estilo = {
            k: np.asarray(v).reshape(R, len(prop), -1).mean((0, 1))
            for k, v in ex.items()
            if k != "ocupacion_m"
        }
        res.estilo["ocupacion_m"] = ex["ocupacion_m"].reshape(R, len(prop), 3).mean((0, 1))
        res.estilo["ocupacion_t"] = d.ocupacion.reshape(R, len(prop), -1, 3).mean((0, 1))
        res.estilo["eg_favor"] = float(d.eg_i.reshape(R, -1).sum(1).mean())
        res.estilo["eg_contra"] = float(d.eg_j.reshape(R, -1).sum(1).mean())
        res.estilo["_R"] = R
    return res


class Cancelado(Exception):
    """La simulación se canceló entre dos bloques (D-084)."""


def _combinar(partes: list[ResultadoTemporada], S: int, sel: np.ndarray) -> ResultadoTemporada:
    """Junta los bloques en el MISMO resultado que daría un solo bloque (mismas réplicas en el mismo orden)."""
    cat = lambda f: np.concatenate([f(p) for p in partes], axis=0)
    res = ResultadoTemporada(
        puntos_exactos=cat(lambda p: p.puntos_exactos),
        puntos=cat(lambda p: p.puntos),
        posicion=cat(lambda p: p.posicion),
        gf=cat(lambda p: p.gf),
        gc=cat(lambda p: p.gc),
    )
    res.resumen = resumir(res)
    # muestra global de torneos, en el orden de `sel`
    tm = {
        k: np.concatenate([p.interno["torneos_muestra"][k] for p in partes], axis=0)
        for k in ("pos", "ga", "gb", "pts", "gf", "gc", "lugar")
    }
    orden = np.argsort(tm["pos"], kind="stable")
    res.interno["torneos_muestra"] = {
        k: tm[k][orden] for k in ("ga", "gb", "pts", "gf", "gc", "lugar")
    }
    N = sum(p.interno["_sumas"]["n"] for p in partes)
    sm = {k: sum(p.interno["_sumas"][k] for p in partes) for k in ("pts", "lug_liga", "lugar")}
    res.interno["tabla_esperada"] = {
        "puntos": (sm["pts"] / N).tolist(),
        "p_liguilla": (sm["lug_liga"] / N).tolist(),
        "lugar_medio": (sm["lugar"] / N).tolist(),
    }
    xpts = cat(lambda p: p.interno["xpts"])
    res.resumen["xpts_partido"] = xpts.mean(0).tolist()
    res.interno["suma_puntos_liga"] = cat(lambda p: p.interno["suma_puntos_liga"])
    res.interno["victorias"] = cat(lambda p: p.interno["victorias"])
    res.interno["empates"] = cat(lambda p: p.interno["empates"])
    res.interno["xpts"] = xpts
    if partes[0].estilo:
        R = sum(p.estilo["_R"] for p in partes)
        res.estilo = {}
        for k in partes[0].estilo:
            if k == "_R":
                continue
            res.estilo[k] = sum(np.asarray(p.estilo[k]) * (p.estilo["_R"] / R) for p in partes)
            if np.ndim(res.estilo[k]) == 0:
                res.estilo[k] = float(res.estilo[k])
    return res


def simular_temporada(
    liga,
    entorno_fichas: np.ndarray,
    fichas_foco: np.ndarray,
    calendario: np.ndarray,
    elo: np.ndarray,
    foco: int,
    idx_muestras: np.ndarray,
    S: int,
    semilla: int,
    pre: Precalculo,
    con_estilo: bool = True,
    tam_bloque: int | None = None,
    progreso=None,
    cancelar=None,
) -> ResultadoTemporada:
    """entorno_fichas: (n_muestras, 18, Q); fichas_foco: (R, Q) ficha del América por réplica; idx_muestras: (R,) muestra posterior de cada réplica.
    `tam_bloque`: réplicas por bloque (None = todas en uno). Con la misma semilla, el resultado es EXACTAMENTE el mismo para cualquier tamaño de bloque. `progreso(hechos, total)`
    se llama al terminar cada bloque; `cancelar()` devuelve True para parar entre bloques (levanta `Cancelado`)."""
    R = len(idx_muestras)
    tam = R if not tam_bloque else max(1, int(tam_bloque))
    rangos = [(a, min(a + tam, R)) for a in range(0, R, tam)]
    N = R * S
    sel = np.random.default_rng([semilla, 909]).choice(
        N, min(int(config.cargar()["simulacion"]["muestra_torneos"]), N), replace=False
    )
    partes = []
    for k, (a, b) in enumerate(rangos):
        if cancelar is not None and cancelar():
            raise Cancelado()
        partes.append(
            _bloque(
                liga,
                entorno_fichas,
                fichas_foco[a:b],
                calendario,
                elo,
                foco,
                idx_muestras[a:b],
                S,
                semilla,
                pre,
                con_estilo,
                a,
                sel,
            )
        )
        if progreso is not None:
            progreso(k + 1, len(rangos))
    return _combinar(partes, S, sel)


def _victorias_empates(ga, gb):
    return {
        "victorias": (ga != gb).sum(1).astype(np.int16),
        "empates": (ga == gb).sum(1).astype(np.int16),
    }


def error_dos_etapas(x: np.ndarray) -> dict:
    """x: (R, S). Error estándar de la media con dos niveles y descomposición σ_b², σ_w²."""
    R, S = x.shape
    m_r = x.mean(1)
    var_dentro = x.var(1, ddof=1).mean() if S > 1 else 0.0
    var_medias = m_r.var(ddof=1) if R > 1 else 0.0
    sigma_b2 = max(var_medias - var_dentro / S, 0.0)
    return {
        "media": float(x.mean()),
        "ee": float(np.sqrt(var_medias / R)),
        "sigma_b2": float(sigma_b2),
        "sigma_w2": float(var_dentro),
    }


def resumir(res: ResultadoTemporada) -> dict:
    cfg = config.cargar()["torneo"]
    nl, npi = cfg["liguilla_directa"], cfg["play_in"]
    pos = res.posicion
    p_lig = (pos <= nl).astype(float)
    p_pi = ((pos > nl) & (pos <= nl + npi)).astype(float)
    R = len(res.puntos_exactos)
    lugares = np.bincount(pos.ravel(), minlength=19)[1:] / pos.size
    lo, hi = np.quantile(res.puntos, [0.1, 0.9])
    return {
        "puntos_esperados": float(res.puntos_exactos.mean()),
        "puntos_esperados_ee": float(res.puntos_exactos.std(ddof=1) / np.sqrt(R)) if R > 1 else 0.0,
        "puntos_rango80": [float(lo), float(hi)],
        "puntos_exactos_rango80": [float(x) for x in np.quantile(res.puntos_exactos, [0.1, 0.9])],
        "p_liguilla": error_dos_etapas(p_lig),
        "p_play_in": error_dos_etapas(p_pi),
        "p_top": error_dos_etapas((pos <= config.cargar()["exigencia"]["top"]).astype(float)),
        "p_fuera": float(1 - p_lig.mean() - p_pi.mean()),
        "lugar_mas_probable": int(np.argmax(lugares) + 1),
        "p_lugar": lugares.tolist(),
        "puntos_hist": np.bincount(res.puntos.astype(int).ravel(), minlength=52)[:52].tolist(),
        "gf": error_dos_etapas(res.gf),
        "gc": error_dos_etapas(res.gc),
        "posicion": error_dos_etapas(pos.astype(float)),
        "puntos_mc": error_dos_etapas(res.puntos),
    }
