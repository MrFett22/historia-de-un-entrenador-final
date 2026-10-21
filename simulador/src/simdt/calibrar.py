"""Calibración de punta a punta → artefactos/ (lo que lee la app).

    python -m simdt.calibrar --datos <ruta>      # ruta = raíz con cache_events/ y matches_*.json
                                                 #   o una carpeta con las tablas comunes en parquet
    python -m simdt.calibrar --sintetico         # datos de demostración con verdad conocida
    python -m simdt.calibrar --exportar-sintetico <carpeta>   # escribe tablas sintéticas en parquet
    python -m simdt.calibrar --datos <ruta> --vocab-dtcoach <processed/mezcla>   # vocabulario de dtcoach en vez del EM propio (D-048)

Pasos: (1) tablas comunes (extracción de eventos + mezcla K = 3, o lectura directa);
(2) liga m; (3) fase A (celdas + efectos cruzados); (4) fichas de los 18 equipos vigentes;
(5) presets, escalas de perillas y pares para el aviso de coherencia; (6) artefactos y caché de
rivales para el modo rápido.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import artefactos, config
from .datos import esquema, inventario
from .datos.corte import cortar_por_fecha
from .estimacion import fase_a, lista_corta
from .estimacion.fichas import armar
from .estimacion.liga import correr_elo
from .motor import calendario as mcal
from .motor.temporada import muestras_replicas, precalcular
from .perillas.mapeo import Escalas, rango_plausible, tecnico_a_perillas
from .tipos import COMPONENTES

TABLAS = tuple(esquema.ESQUEMA)


def exportar_tablas(tablas: dict, carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for n in TABLAS:
        tablas[n].to_parquet(carpeta / f"{n}.parquet", index=False)


def leer_tablas(carpeta: Path) -> dict:
    return {n: pd.read_parquet(carpeta / f"{n}.parquet") for n in TABLAS}


def _cache_con_clave(nombre: str, tablas: dict, cadenas, contexto: dict) -> str:
    """El caché de la fase A depende de los partidos que entran, de las cadenas y del corte: sin esto, recalibrar con otro corte reutiliza el resultado anterior."""
    import hashlib

    h = hashlib.md5()
    h.update(np.sort(tablas["partidos"]["match_id"].to_numpy()).tobytes())
    h.update(str(contexto.get("corte_fecha")).encode())
    for c in cadenas:
        if c is not None:
            h.update(np.ascontiguousarray(c).tobytes())
    stem, _, ext = nombre.rpartition(".")
    return f"{stem}_{h.hexdigest()[:10]}.{ext}"


def _enlazar_cache(clave: str, original: str) -> None:
    """`fase_a_real.pkl` apunta al resultado más reciente (validacion.reporte lo lee con ese nombre)."""
    import os
    import shutil

    d = config.cache_dir()
    dst, src = d / original, d / clave
    if not src.exists() or dst == src:
        return
    try:
        if dst.is_symlink() or dst.exists():
            dst.unlink()
        os.symlink(src.name, dst)
    except OSError:
        shutil.copyfile(src, dst)


def _vigentes(partidos: pd.DataFrame, temp_obj: int, equipos: list) -> dict:
    """Técnico del último partido jugado de cada equipo (en la temporada objetivo si hay)."""
    a = partidos[["fecha", "match_id", "temporada", "local", "tecnico_local"]].set_axis(
        ["fecha", "match_id", "temporada", "equipo", "tecnico"], axis=1
    )
    b = partidos[["fecha", "match_id", "temporada", "visitante", "tecnico_visitante"]].set_axis(
        ["fecha", "match_id", "temporada", "equipo", "tecnico"], axis=1
    )
    x = pd.concat([a, b]).dropna(subset=["tecnico"]).sort_values(["fecha", "match_id"])
    return {e: x[x.equipo == e].tecnico.iloc[-1] for e in equipos if (x.equipo == e).any()}


def _conteo_partidos(partidos: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    a = partidos[["tecnico_local", "local"]].set_axis(["tecnico", "club"], axis=1)
    b = partidos[["tecnico_visitante", "visitante"]].set_axis(["tecnico", "club"], axis=1)
    x = pd.concat([a, b]).dropna()
    return x.groupby("tecnico").size(), x.groupby(["tecnico", "club"]).size()


def preparar_real(raiz: Path, verbose=True, vocab=None, vocab_r="parquet"):
    from .datos import repo

    ext = repo.extraer(raiz=raiz, verbose=verbose)
    cfg = config.cargar()["torneo"]
    archivo = None
    for f in sorted(glob.glob(str(raiz / config.cargar()["datos"]["partidos_glob"]))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if d and d[0]["season"]["season_name"] == cfg["temporada_statsbomb"]:
            archivo = f
    equipos, cal, jornada, info = mcal.calendario_real(archivo)
    inicio = min(pd.Timestamp(i["fecha"]) for i in info)
    corte = (
        inicio if cfg.get("corte_antes_de_inicio", True) else None
    )  # D-050: nada del torneo objetivo entra a la estimación
    m, abierto, r = repo.ajustar_mezcla(
        ext, verbose=verbose, vocab=vocab, vocab_r=vocab_r, corte=corte
    )
    tablas, todos = repo.tablas_comunes(ext, abierto, r)
    temp_obj = int(todos[todos.match_id.isin([i["match_id"] for i in info])].temporada.max())
    previos = todos[(todos.fecha < inicio) & todos.goles_local.notna()]
    _, _, R = correr_elo(
        previos,
        config.cargar()["elo"]["K"],
        config.cargar()["elo"]["h"],
        config.cargar()["elo"]["inicial"],
    )
    elo = np.array([R.get(e, config.cargar()["elo"]["inicial"]) for e in equipos])
    contexto = {
        "modo": inventario.MODO_REAL_PIPELINE,
        "equipos": equipos,
        "calendario": cal.tolist(),
        "jornada": jornada.tolist(),
        "elo": elo.tolist(),
        "temp_obj": temp_obj,
        "torneo": cfg["nombre"],
        "partidos_calendario": info,
        "corte_fecha": None if corte is None else str(corte.date()),
        "mezcla": {
            "pi": m.pi.tolist(),
            "resumen": __import__("simdt.estimacion.mezcla", fromlist=["resumen"]).resumen(m),
        },
    }
    if ext.get("multiarranque"):
        contexto["mezcla"]["multiarranque"] = ext["multiarranque"]
    if ext.get("vocab_dtcoach"):
        contexto["mezcla"]["fuente_dtcoach"] = ext["vocab_dtcoach"]
    return tablas, contexto, (m.P, m.mu, m.P0)


def preparar_sintetico():
    from .datos import sintetico

    tablas, v = sintetico.generar()
    p = tablas["partidos"]
    nt = int(p.temporada.max())
    equipos = list(v.clubes)
    _, _, R = correr_elo(p, config.cargar()["elo"]["K"], config.cargar()["elo"]["h"])
    contexto = {
        "modo": inventario.MODO_SINTETICO,
        "equipos": equipos,
        "calendario": mcal.todos_contra_todos(len(equipos)).tolist(),
        "elo": [R.get(e, 1500.0) for e in equipos],
        "temp_obj": nt,
        "torneo": "Torneo de demostración",
    }
    return tablas, contexto, (v.liga.P_cadenas, v.liga.mu_cadenas, v.liga.P0_cadenas)


def calibrar(
    tablas: dict,
    contexto: dict,
    cadenas,
    salida: Path,
    cache_fase_a: str | None,
    verbose: bool = True,
    precalculo_completo: bool = True,
) -> dict:
    cfg = config.cargar()
    errores = esquema.validar(tablas)
    if errores:
        raise ValueError(f"tablas inválidas: {errores}")
    foco = cfg["torneo"]["club_foco"]
    equipos = contexto["equipos"]
    vig = _vigentes(
        tablas["partidos"], contexto["temp_obj"], equipos
    )  # el técnico vigente se lee ANTES del corte
    if contexto.get("corte_fecha"):
        tablas, corte = cortar_por_fecha(tablas, contexto["corte_fecha"])
        contexto["corte"] = corte
        if verbose:
            print(
                f"Corte por fecha {corte['fecha_corte']}: {corte['partidos_quitados']} partidos del torneo objetivo quedan fuera de la estimación "
                f"({corte['partidos_despues']} de {corte['partidos_antes']} entran).",
                flush=True,
            )
    nombre_cache = cache_fase_a
    if cache_fase_a:
        cache_fase_a = _cache_con_clave(cache_fase_a, tablas, cadenas, contexto)
    if (
        contexto["modo"] != inventario.MODO_SINTETICO
    ):  # lo lee validacion.reporte (junto con el pickle de la fase A)
        pd.to_pickle((tablas, contexto.get("corte")), config.cache_dir() / "tablas_reales.pkl")
    if verbose:
        print("Fase A...", flush=True)
    res = fase_a.correr(
        tablas,
        P_cadenas=cadenas[0],
        mu_cadenas=cadenas[1],
        P0_cadenas=cadenas[2] if len(cadenas) > 2 else None,
        cache=cache_fase_a,
        n_temp=max(int(tablas["partidos"].temporada.max()) + 1, contexto["temp_obj"] + 1),
        verbose=verbose,
    )
    if cache_fase_a:
        _enlazar_cache(cache_fase_a, nombre_cache)
    partidos = tablas["partidos"]
    n_tec, n_par = _conteo_partidos(partidos)
    minimo = cfg["estimacion"]["min_partidos_preset"]
    candidatos = [t for t in n_tec.index if n_tec[t] >= minimo and t in res.ix.tecnicos]
    atribucion = cfg["estimacion"].get("atribucion", "continua")  # D-051
    piezas = armar(
        res,
        equipos,
        vig,
        contexto["temp_obj"],
        foco,
        M=cfg["estimacion"]["n_muestras_fichas"],
        semilla=cfg["semilla"],
        tecnicos_guardar=candidatos,
        atribucion=atribucion,
    )
    tab = res.tabla()
    esc = Escalas(
        b0=tab.set_index("componente").loc[list(COMPONENTES), "b0"].to_numpy(),
        sigma_theta=np.median(piezas.sigma[:, :, 0], axis=0),
        decisiones=res.decisiones,
        atribucion=atribucion,
    )
    if esc.continua:
        esc.theta_lo, esc.theta_hi = rango_plausible(piezas.sigma[:, :, 0])
    presets = []
    for t in sorted(candidatos, key=lambda x: -n_tec[x]):
        clubes = sorted(c for (tt, c) in n_par.index if tt == t)
        presets.append(
            {
                "nombre": t,
                "partidos": int(n_tec[t]),
                "clubes": clubes,
                "perillas": tecnico_a_perillas(piezas.theta_tec[t].mean(0), res.liga, esc),
            }
        )
    lc = lista_corta.desde_fase_a(res, partidos, piezas, presets, vig, foco)  # D-053
    presets = lista_corta.aplicar(presets, lc)
    # pares técnico-club con ≥ 30 partidos: θ + ε medios (para el aviso de coherencia)
    filas = []
    for (t, c), n in n_par.items():
        if n >= minimo and t in res.ix.tecnicos and (t, c) in res.ix.pares:
            it, ip = res.ix.tecnicos.index(t), res.ix.pares.index((t, c))
            v = [
                float(np.mean(res.posteriores[q].theta[:, it] + res.posteriores[q].eps[:, ip]))
                for q in COMPONENTES
            ]
            filas.append([t, c, int(n)] + v)
    pares = pd.DataFrame(filas, columns=["tecnico", "club", "partidos"] + list(COMPONENTES))
    j = tablas["juego"]
    nk = j.groupby("k").n.sum()
    meta = {k: v for k, v in contexto.items()}
    meta.update(
        {
            "fecha_calibracion": str(date.today()),
            "mezcla_liga": (nk / nk.sum()).tolist(),
            "n_celdas": int(len(res.celdas)),
            "tecnicos_vigentes": vig,
            "corte": contexto.get("corte"),
            "etiqueta_global": "descriptivo",
            "perillas_solo_estilo": [],
            "factor_gol": res.liga.factor_gol,
            "diag_liga": res.diag_liga,
            "lista_corta": lc["meta"],
            "inflacion_etapa1": cfg["estimacion"]["inflacion_etapa1"],
        }
    )  # D-055
    meta.pop("partidos_calendario", None)
    artefactos.escribir(salida, res.liga, piezas, meta, presets, pares, cadenas, tab)
    titulo = (
        "Fase A con datos reales"
        if contexto["modo"] != inventario.MODO_SINTETICO
        else "Fase A (datos de demostración)"
    )
    nombre = {
        inventario.MODO_SINTETICO: "fase_A_demo.md",
        inventario.MODO_REAL: "fase_A_tablas_externas.md",
    }.get(contexto["modo"], "fase_A.md")
    fase_a.escribir_reporte(res, config.VALIDACION / nombre, titulo)
    # caché de rivales (modo rápido y preciso): desde los artefactos YA escritos (float32), que es lo que lee la app; la clave del caché
    # depende de las fichas y por eso no puede calcularse con las de doble precisión de antes de escribir (D-052)
    paq = artefactos.cargar(salida)
    R = cfg["simulacion"]["rapido"]["R"]
    idx = muestras_replicas(paq.piezas.fichas.shape[0], R, cfg["semilla"])
    cal, elo, foco_i = (
        np.asarray(paq.meta["calendario"]),
        np.asarray(paq.meta["elo"], dtype=float),
        paq.piezas.foco,
    )
    if verbose:
        print("Precálculo de rivales (modo rápido)...", flush=True)
    precalcular(
        paq.liga,
        paq.piezas.fichas,
        cal,
        elo,
        foco_i,
        indices=idx,
        ruta=Path(salida) / f"cache_rivales_R{R}.npz",
    )
    if precalculo_completo:
        if verbose:
            print("Precálculo de rivales (todas las muestras, modo preciso)...", flush=True)
        precalcular(
            paq.liga,
            paq.piezas.fichas,
            cal,
            elo,
            foco_i,
            ruta=Path(salida) / f"cache_rivales_R{cfg['simulacion']['preciso']['R']}.npz",
            indices=muestras_replicas(
                paq.piezas.fichas.shape[0], cfg["simulacion"]["preciso"]["R"], cfg["semilla"]
            ),
        )
    return {"fase_a": res, "piezas": piezas, "presets": presets}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--datos",
        type=Path,
        help="raíz con cache_events/ y matches_*.json, o carpeta con tablas parquet",
    )
    ap.add_argument("--sintetico", action="store_true")
    ap.add_argument("--exportar-sintetico", type=Path)
    ap.add_argument("--salida", type=Path, default=config.ARTEFACTOS)
    ap.add_argument(
        "--vocab-dtcoach",
        type=Path,
        metavar="CARPETA",
        help="usa el vocabulario de dtcoach (mezcla_K3.npz de CARPETA o CARPETA/mezcla) en vez de reajustar la mezcla (D-048)",
    )
    ap.add_argument(
        "--vocab-r",
        choices=("parquet", "modelo"),
        default="parquet",
        help="con --vocab-dtcoach: r_sk de responsabilidades_K3.parquet donde se empareje (parquet) o siempre del modelo",
    )
    a = ap.parse_args(argv)
    if a.vocab_dtcoach and (a.sintetico or a.exportar_sintetico):
        print(
            "AVISO: --vocab-dtcoach solo aplica a datos reales (--datos con eventos); se ignora.",
            file=sys.stderr,
        )
    if a.exportar_sintetico:
        tablas, _, _ = preparar_sintetico()
        exportar_tablas(tablas, a.exportar_sintetico)
        print(f"tablas sintéticas en {a.exportar_sintetico}")
        return 0
    if a.sintetico:
        tablas, ctx, cad = preparar_sintetico()
        calibrar(tablas, ctx, cad, a.salida, "fase_a_demo.pkl")
    elif a.datos and (a.datos / "partidos.parquet").exists():
        tablas = leer_tablas(a.datos)
        p = tablas["partidos"]
        equipos = sorted(set(p.local) | set(p.visitante))
        _, _, R = correr_elo(p, config.cargar()["elo"]["K"], config.cargar()["elo"]["h"])
        ctx = {
            "modo": inventario.MODO_REAL,
            "equipos": equipos,
            "calendario": mcal.todos_contra_todos(len(equipos)).tolist(),
            "elo": [R.get(e, 1500.0) for e in equipos],
            "temp_obj": int(p.temporada.max()),
            "torneo": "Torneo (tablas externas)",
        }
        from .datos.sintetico import liga_sintetica

        L = liga_sintetica()
        calibrar(tablas, ctx, (L.P_cadenas, L.mu_cadenas), a.salida, None)
    else:
        raiz = a.datos or config.RAIZ_REPO
        tablas, ctx, cad = preparar_real(Path(raiz), vocab=a.vocab_dtcoach, vocab_r=a.vocab_r)
        calibrar(tablas, ctx, cad, a.salida, "fase_a_real.pkl")
    print(f"artefactos escritos en {a.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
