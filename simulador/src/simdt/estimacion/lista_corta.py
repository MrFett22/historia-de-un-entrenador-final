"""Lista corta de técnicos de la app (D-053): se calcula al calibrar y se guarda en los artefactos; parámetros en `simulador.yaml: lista_corta`.

  - FIJOS: el técnico vigente del América y su antecesor en el América, detectados con los datos (no a mano). Un interino con menos de
    `min_partidos_antecesor` partidos no cuenta como antecesor.
  - ELEGIBLES para los demás: al menos `min_partidos` partidos y al menos `min_celdas` celdas técnico × club × temporada en la fase A.
  - `n_medoides` MÁS por k-medoides (PAM, determinista; semilla fija para los empates) sobre la media posterior de θ de las 32 componentes, cada una
    dividida entre la mediana posterior de su σ_θ (distancia euclidiana). Se reportan la silueta y, por cada medoide, cuántos técnicos representa.
  - Cada técnico lleva sus `n_rasgos` rasgos más marcados (mayor |θ̄ / σ_θ|, de bloques distintos); la frase en lenguaje común la arma la app (`textos.frase_rasgo`).
Uso sin repetir NUTS:  python -m simdt.estimacion.lista_corta --artefactos DIR --cache DIR_DE_CACHE   (lee fase_a_real.pkl y tablas_reales.pkl)
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .. import config
from ..tipos import COMPONENTES, bloque_de


def detectar_vigente_y_antecesor(
    partidos: pd.DataFrame, club: str, vigente: str | None = None, min_partidos: int = 10
) -> tuple[str | None, str | None]:
    """(técnico vigente, antecesor) del `club` a partir de los partidos jugados, en orden de fecha. El vigente es el del último partido (o `vigente` si se da);
    el antecesor, el técnico de la racha anterior distinta con al menos `min_partidos` partidos (un interino no cuenta)."""
    a = partidos[["fecha", "match_id", "local", "tecnico_local"]].set_axis(
        ["fecha", "match_id", "club", "tecnico"], axis=1
    )
    b = partidos[["fecha", "match_id", "visitante", "tecnico_visitante"]].set_axis(
        ["fecha", "match_id", "club", "tecnico"], axis=1
    )
    x = pd.concat([a, b])
    x = x[x.club == club].dropna(subset=["tecnico"]).sort_values(["fecha", "match_id"])
    if x.empty:
        return vigente, None
    rachas: list[list] = []  # [técnico, n partidos]
    for t in x.tecnico:
        if rachas and rachas[-1][0] == t:
            rachas[-1][1] += 1
        else:
            rachas.append([t, 1])
    vig = vigente or rachas[-1][0]
    # la racha vigente es la última de `vig`; el antecesor sale de las anteriores
    ult = (
        max(i for i, (t, _) in enumerate(rachas) if t == vig)
        if any(t == vig for t, _ in rachas)
        else len(rachas)
    )
    for t, n in reversed(rachas[:ult]):
        if t != vig and n >= min_partidos:
            return vig, t
    return vig, None


def rasgos(theta_media: np.ndarray, sigma: np.ndarray, n: int = 2) -> list[dict]:
    """Los `n` rasgos más marcados: mayor |θ̄ / σ_θ|, un solo rasgo por bloque (int_at, u_co, rho, …)."""
    z = theta_media / np.maximum(sigma, 1e-9)
    out, usados = [], set()
    for q in np.argsort(-np.abs(z)):
        b = bloque_de(COMPONENTES[q])
        if b in usados:
            continue
        usados.add(b)
        out.append(
            {"componente": COMPONENTES[q], "signo": int(np.sign(z[q])) or 1, "z": float(z[q])}
        )
        if len(out) == n:
            break
    return out


def pam(
    D: np.ndarray, k: int, semilla: int = 0, max_iter: int = 100
) -> tuple[np.ndarray, np.ndarray]:
    """K-medoides (PAM: BUILD voraz + SWAP) sobre una matriz de distancias. Determinista; la semilla solo ordena los candidatos (desempates)."""
    n = len(D)
    orden = np.random.default_rng(semilla).permutation(n)
    Dp = D[np.ix_(orden, orden)]
    med = [int(np.argmin(Dp.sum(1)))]
    while len(med) < k:  # BUILD
        cerca = Dp[:, med].min(1)
        ganancia = np.maximum(cerca[:, None] - Dp, 0).sum(0)
        ganancia[med] = -1
        med.append(int(np.argmax(ganancia)))
    costo = Dp[:, med].min(1).sum()
    for _ in range(max_iter):  # SWAP
        mejor = (costo, None, None)
        for i in range(k):
            for h in range(n):
                if h in med:
                    continue
                m2 = med.copy()
                m2[i] = h
                c = Dp[:, m2].min(1).sum()
                if c < mejor[0] - 1e-12:
                    mejor = (c, i, h)
        if mejor[1] is None:
            break
        med[mejor[1]] = mejor[2]
        costo = mejor[0]
    etiquetas = np.argmin(Dp[:, med], axis=1)
    medoides = orden[np.array(med)]
    lab = np.empty(n, dtype=int)
    lab[orden] = etiquetas
    return medoides, lab


def calcular(
    presets: list,
    theta_media: dict,
    sigma_theta: np.ndarray,
    partidos_por_tecnico: dict,
    celdas_por_tecnico: dict | None,
    vigente: str | None,
    antecesor: str | None,
    cfg: dict | None = None,
) -> dict:
    """Devuelve {"lista": {nombre: {rol, rasgos, representa}}, "meta": {...}}. `celdas_por_tecnico` None = no se exige el mínimo de celdas (se avisa en meta)."""
    c = {**config.cargar().get("lista_corta", {}), **(cfg or {})}
    min_p, min_c, k_med, sem, n_r = (
        c["min_partidos"],
        c["min_celdas"],
        c["n_medoides"],
        c["semilla"],
        c["n_rasgos"],
    )
    nombres = [p["nombre"] for p in presets]
    fijos = [t for t in (vigente, antecesor) if t]
    elegibles = [
        t
        for t in nombres
        if t not in fijos
        and t in theta_media
        and partidos_por_tecnico.get(t, 0) >= min_p
        and (celdas_por_tecnico is None or celdas_por_tecnico.get(t, 0) >= min_c)
    ]
    lista: dict = {}
    for t, rol in ((vigente, "vigente"), (antecesor, "antecesor")):
        if t and t in theta_media:
            lista[t] = {
                "rol": rol,
                "rasgos": rasgos(theta_media[t], sigma_theta, n_r),
                "representa": 1,
            }
    silueta, medoides_info = None, []
    if len(elegibles) > k_med:
        X = np.array([theta_media[t] / np.maximum(sigma_theta, 1e-9) for t in elegibles])
        D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(2))
        med, lab = pam(D, k_med, sem)
        try:
            from sklearn.metrics import silhouette_score

            silueta = float(silhouette_score(D, lab, metric="precomputed"))
        except Exception:  # noqa: BLE001
            silueta = None
        for j, m in enumerate(med):
            t = elegibles[int(m)]
            n_rep = int((lab == j).sum())
            lista[t] = {
                "rol": "medoide",
                "rasgos": rasgos(theta_media[t], sigma_theta, n_r),
                "representa": n_rep,
            }
            medoides_info.append(
                {
                    "nombre": t,
                    "representa": n_rep,
                    "representados": [elegibles[i] for i in np.flatnonzero(lab == j) if i != m],
                }
            )
    else:
        for t in elegibles:
            lista[t] = {
                "rol": "medoide",
                "rasgos": rasgos(theta_media[t], sigma_theta, n_r),
                "representa": 1,
            }
            medoides_info.append({"nombre": t, "representa": 1, "representados": []})
    meta = {
        "parametros": {
            "min_partidos": min_p,
            "min_celdas": min_c,
            "n_medoides": k_med,
            "semilla": sem,
            "n_rasgos": n_r,
            "min_partidos_antecesor": c["min_partidos_antecesor"],
        },
        "vigente": vigente,
        "antecesor": antecesor,
        "n_elegibles": len(elegibles),
        "silueta": silueta,
        "medoides": medoides_info,
        "celdas_exigidas": celdas_por_tecnico is not None,
        "n_lista": len(lista),
    }
    return {"lista": lista, "meta": meta}


def aplicar(presets: list, res: dict) -> list:
    """Marca cada preset con `lista_corta`, `rol`, `rasgos` y `representa` (los que no están en la lista quedan con lista_corta = False)."""
    for p in presets:
        x = res["lista"].get(p["nombre"])
        p["lista_corta"] = x is not None
        p["rol"] = x["rol"] if x else None
        p["rasgos"] = x["rasgos"] if x else []
        p["representa"] = x["representa"] if x else 0
    return presets


def desde_fase_a(
    res_fase_a, partidos: pd.DataFrame, piezas, presets: list, vigentes: dict, foco_club: str
) -> dict:
    """La lista corta a partir de lo que ya calcula `calibrar` (fase A, partidos que entran, fichas)."""
    cfg = config.cargar()["lista_corta"]
    vig, ant = detectar_vigente_y_antecesor(
        partidos, foco_club, vigentes.get(foco_club), cfg["min_partidos_antecesor"]
    )
    n = {}
    for col_t in ("tecnico_local", "tecnico_visitante"):
        for t, v in partidos[col_t].dropna().value_counts().items():
            n[t] = n.get(t, 0) + int(v)
    cel = res_fase_a.celdas.groupby("tecnico").size().to_dict() if res_fase_a is not None else None
    th = {t: v.mean(0) for t, v in piezas.theta_tec.items()}
    return calcular(presets, th, np.median(piezas.sigma[:, :, 0], axis=0), n, cel, vig, ant)


def recalcular(directorio: Path, cache: Path, verbose: bool = True) -> dict:
    """Agrega la lista corta a unos artefactos YA calibrados sin repetir NUTS: usa `fase_a_real.pkl` y `tablas_reales.pkl` de la caché de su calibración."""
    from .. import artefactos

    d = Path(directorio)
    p = artefactos.cargar(d)
    foco = p.meta["foco"]
    f_a, f_t = Path(cache) / "fase_a_real.pkl", Path(cache) / "tablas_reales.pkl"
    if f_a.exists() and f_t.exists():
        with open(f_a, "rb") as f:
            res = pickle.load(f)
        tablas = pd.read_pickle(f_t)[0]
        out = desde_fase_a(
            res, tablas["partidos"], p.piezas, p.presets, p.meta.get("tecnicos_vigentes", {}), foco
        )
    else:  # sin la caché de la calibración: sin antecesor ni mínimo de celdas (se avisa)
        if verbose:
            print(
                f"⚠ no hay {f_a.name} / {f_t.name} en {cache}: la lista corta sale SIN antecesor y SIN el mínimo de celdas"
            )
        cfg = config.cargar()["lista_corta"]
        th = {t: v.mean(0) for t, v in p.piezas.theta_tec.items()}
        out = calcular(
            p.presets,
            th,
            np.median(p.piezas.sigma[:, :, 0], axis=0),
            {x["nombre"]: x["partidos"] for x in p.presets},
            None,
            p.meta.get("tecnicos_vigentes", {}).get(foco),
            None,
            cfg,
        )
    presets = aplicar(p.presets, out)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    meta["lista_corta"] = out["meta"]
    (d / "presets.json").write_text(
        json.dumps(presets, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )
    (d / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1, default=float), encoding="utf-8"
    )
    if verbose:
        m = out["meta"]
        for rol, t in (("vigente", m["vigente"]), ("antecesor", m["antecesor"])):
            if t is None or t not in out["lista"]:
                print(
                    f"⚠ el {rol} ({t}) no está en la lista: sin posterior de θ en los artefactos (menos de {m['parametros']['min_partidos'] // 2} partidos) o no detectado"
                )
        print(
            f"lista corta: {m['n_lista']} técnicos (vigente {m['vigente']}, antecesor {m['antecesor']}; {m['n_elegibles']} elegibles; "
            f"silueta {m['silueta'] if m['silueta'] is None else round(m['silueta'], 3)}; medoides {[(x['nombre'], x['representa']) for x in m['medoides']]})"
        )
    return out["meta"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--artefactos", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    a = ap.parse_args(argv)
    recalcular(a.artefactos, a.cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
