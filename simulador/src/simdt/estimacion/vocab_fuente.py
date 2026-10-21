"""Vocabulario FIJO de dtcoach (`--vocab-dtcoach`): se usa la mezcla ya ajustada en la fuente en vez de reajustarla (D-048).

Por qué: el EM de simdt, aun con el paso inicial P⁰ (D-047), converge a otra solución que la mezcla publicada de dtcoach
(P(remate) 0.080 / 0.098 / 0.124 contra 0.140 / 0.025 / 0.122, prueba del script 2b). Mientras no se sepa por qué, el
vocabulario se toma tal cual de `mezcla_K3.npz` (π, μ, P, P0) y las responsabilidades r_sk salen de ahí.

Qué lee (carpeta `processed/mezcla` = 5 absorbentes, la de ADR-v2-72; o `processed/archivo_4abs/mezcla` = 4):
  - `mezcla_K3.npz`  (pi, mu, P, P0, lam, a0): malla 5×4 de 20 transitorios y 24 o 25 estados; se rellena a 25 con ceros
    (con 4 absorbentes la secuencia que simdt cierra en INTERRUPCIÓN se cuenta como PÉRDIDA, que es lo que la fuente hacía).
  - `responsabilidades_K3.parquet` (opcional): r_1..r_3 por secuencia, con `seq_uid`, `match_id`, `team`, `play_pattern`, `largo`.

Cómo se obtiene r_sk de cada secuencia de simdt (`modo_r`):
  - "modelo":  r = P(tipo | secuencia) con la mezcla de la fuente, aplicada a las transiciones de simdt. Está definido para TODAS
    las secuencias y no depende de ningún emparejamiento.
  - "parquet": para las secuencias que se emparejan con una de la fuente, r de la fuente; para el resto, "modelo".
    Se empareja DENTRO de cada (partido, equipo) alineando en orden cronológico las claves (largo, play_pattern) con
    `difflib.SequenceMatcher`; `seq_uid` = `<partido>_<posesión>_s<n>` da el orden de la fuente. Si se empareja menos de
    UMBRAL_EMPAREJADO o las r emparejadas no coinciden con las del modelo, se usa "modelo" y se avisa (decisión conservadora:
    un emparejamiento equivocado asigna la etiqueta de OTRA secuencia, el modelo nunca).
Siempre se reporta el porcentaje emparejado y cuánto difieren r de la fuente y r del modelo en las emparejadas.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

from . import mezcla as mz

UMBRAL_EMPAREJADO = (
    0.99  # fracción mínima de secuencias de simdt emparejadas para usar r del parquet
)
UMBRAL_ARGMAX = (
    0.97  # acuerdo mínimo de tipo (argmax) entre r de la fuente y r del modelo en las emparejadas
)
_RX_SEQ = re.compile(r"^(?P<partido>\d+)_(?P<pos>\d+)_s(?P<n>\d+)$")


def buscar(carpeta: Path) -> tuple[Path, Path | None]:
    """(mezcla_K3.npz, responsabilidades_K3.parquet | None) dentro de `carpeta` o de `carpeta/mezcla`."""
    carpeta = Path(carpeta)
    for base in (carpeta, carpeta / "mezcla"):
        npz = base / "mezcla_K3.npz"
        if npz.exists():
            resp = base / "responsabilidades_K3.parquet"
            return npz, (resp if resp.exists() else None)
    raise FileNotFoundError(f"no hay mezcla_K3.npz en {carpeta} ni en {carpeta / 'mezcla'}")


def cargar_mezcla(npz: Path) -> tuple[mz.Mezcla, int]:
    """La mezcla de la fuente como `Mezcla` de simdt (NS = 25) y su número de absorbentes (4 o 5)."""
    z = np.load(npz)
    K, nt, ns = z["P"].shape
    if nt != mz.NT:
        raise ValueError(
            f"{npz}: {nt} transitorios; simdt usa la malla 5×4 con una fase ({mz.NT}). Otra malla no se puede usar como vocabulario."
        )
    n_abs = ns - nt
    if n_abs not in (4, mz.NS - mz.NT):
        raise ValueError(f"{npz}: {n_abs} absorbentes; se esperan 4 o {mz.NS - mz.NT}")
    pad = ((0, 0), (0, 0), (0, mz.NS - ns))
    P = np.pad(z["P"], pad)
    P0 = np.pad(z["P0"], pad) if "P0" in z.files else None
    m = mz.Mezcla(
        z["pi"].astype(float),
        z["mu"].astype(float),
        P,
        float(z["lam"]),
        float(z["a0"]),
        list(z["objetivo"]) if "objetivo" in z.files else [],
        P0,
    )
    return m, n_abs


def _orden_fuente(seq_uid: pd.Series) -> np.ndarray:
    """Clave de orden cronológico de la fuente: (posesión, n) de `seq_uid`; si no se puede leer, el orden de las filas."""
    ex = seq_uid.astype(str).str.extract(_RX_SEQ)
    if ex.isna().any().any():
        return np.arange(len(seq_uid))
    return (ex["pos"].astype(np.int64) * 10_000 + ex["n"].astype(np.int64)).to_numpy()


def emparejar(s: pd.DataFrame, resp: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """Índice (fila de `resp`) de cada secuencia de simdt, -1 si no se empareja.

    `s`: columnas match_id, equipo, largo, pp (play_pattern), en el orden de aparición de simdt (cronológico por partido).
    `resp`: match_id, team, largo, play_pattern, seq_uid.
    """
    sk = pd.DataFrame(
        {
            "mid": s["match_id"].astype(np.int64).to_numpy(),
            "eq": s["equipo"].astype(str).to_numpy(),
            "clave": list(zip(s["largo"].astype(int), s["pp"].fillna("").astype(str))),
        }
    )
    sk["fila"] = np.arange(len(sk))
    rk = pd.DataFrame(
        {
            "mid": resp["match_id"].astype(np.int64).to_numpy(),
            "eq": resp["team"].astype(str).to_numpy(),
            "clave": list(
                zip(resp["largo"].astype(int), resp["play_pattern"].fillna("").astype(str))
            ),
            "ord": _orden_fuente(resp["seq_uid"]),
        }
    )
    rk["fila"] = np.arange(len(rk))
    rk = rk.sort_values(["mid", "eq", "ord", "fila"], kind="stable")
    codigos: dict = {}
    sk["cod"] = [codigos.setdefault(c, len(codigos)) for c in sk["clave"]]
    rk["cod"] = [codigos.setdefault(c, len(codigos)) for c in rk["clave"]]
    gr = {k: g for k, g in rk.groupby(["mid", "eq"], sort=False)}
    par = np.full(len(sk), -1, dtype=np.int64)
    for k, g in sk.groupby(["mid", "eq"], sort=False):
        h = gr.get(k)
        if h is None:
            continue
        a, b = g["cod"].tolist(), h["cod"].tolist()
        fa, fb = g["fila"].to_numpy(), h["fila"].to_numpy()
        for bl in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
            if bl.size:
                par[fa[bl.a : bl.a + bl.size]] = fb[bl.b : bl.b + bl.size]
    n_par = int((par >= 0).sum())
    sin_par_fuente = len(rk) - n_par
    peor = sk.assign(par=par)[par < 0].groupby("mid").size().sort_values(ascending=False).head(5)
    return par, {
        "n_simdt": len(sk),
        "n_fuente": len(rk),
        "emparejadas": n_par,
        "pct_emparejadas": n_par / max(len(sk), 1),
        "pct_fuente_emparejada": n_par / max(len(rk), 1),
        "sin_par_simdt": len(sk) - n_par,
        "sin_par_fuente": sin_par_fuente,
        "partidos_con_mas_sin_par": {int(i): int(v) for i, v in peor.items()},
    }


def aplicar(
    carpeta: Path,
    s: pd.DataFrame,
    t: pd.DataFrame,
    abierto: np.ndarray,
    modo_r: str = "parquet",
    verbose: bool = True,
) -> tuple[mz.Mezcla, np.ndarray, dict]:
    """(mezcla de la fuente, r de las secuencias `abierto`, informe). `s`/`t`: secuencias y transiciones de `repo.extraer`."""
    if modo_r not in ("modelo", "parquet"):
        raise ValueError("modo_r debe ser 'modelo' o 'parquet'")
    npz, ruta_resp = buscar(carpeta)
    m, n_abs = cargar_mezcla(npz)
    hacia = t.hacia.to_numpy()
    if n_abs == 4:  # la fuente no tiene INTERRUPCIÓN: allí era PÉRDIDA
        hacia = np.where(hacia == mz.NS - 1, mz.NT + 2, hacia)
    d = mz.datos_desde(t.sid.to_numpy(), t.desde.to_numpy(), hacia, len(s), s.inicio.to_numpy())
    r_modelo = mz.responsabilidades(m, d)  # todas las secuencias (abiertas y de balón parado)
    res = mz.resumen(m)
    info = {
        "npz": str(npz),
        "n_absorbentes": n_abs,
        "lam": m.lam,
        "a0": m.a0,
        "tiene_P0": m.P0 is not None,
        "ordenado_por_E_T": bool(np.all(np.diff([x["E_T"] for x in res]) > 0)),
        "pi": [x["pi"] for x in res],
        "E_T": [x["E_T"] for x in res],
        "p_remate": [x["p_remate"] for x in res],
        "pi_en_secuencias_simdt": r_modelo.mean(0).tolist(),
        "modo_r_pedido": modo_r,
        "modo_r_usado": "modelo",
    }
    r = r_modelo
    if ruta_resp is None:
        info["parquet"] = "no hay responsabilidades_K3.parquet en la carpeta: r sale del modelo"
    elif modo_r == "parquet":
        cols = [
            "seq_uid",
            "match_id",
            "team",
            "play_pattern",
            "largo",
            *[f"r_{k + 1}" for k in range(m.K)],
        ]
        resp = pd.read_parquet(ruta_resp, columns=cols)
        par, est = emparejar(s, resp)
        info["emparejamiento"] = est
        ok = par >= 0
        if ok.any():
            rf = resp[[f"r_{k + 1}" for k in range(m.K)]].to_numpy(float)[par[ok]]
            dif = np.abs(rf - r_modelo[ok])
            info["r_fuente_vs_modelo"] = {
                "dif_abs_media": float(dif.mean()),
                "dif_abs_p99": float(np.quantile(dif.max(1), 0.99)),
                "acuerdo_tipo": float((rf.argmax(1) == r_modelo[ok].argmax(1)).mean()),
            }
        if est["pct_emparejadas"] < UMBRAL_EMPAREJADO:
            info["parquet"] = (
                f"emparejadas {100 * est['pct_emparejadas']:.2f} % < {100 * UMBRAL_EMPAREJADO:.0f} %: r sale del modelo"
            )
        elif info["r_fuente_vs_modelo"]["acuerdo_tipo"] < UMBRAL_ARGMAX:
            info["parquet"] = (
                f"r de la fuente y del modelo coinciden en el tipo en {100 * info['r_fuente_vs_modelo']['acuerdo_tipo']:.1f} % "
                f"< {100 * UMBRAL_ARGMAX:.0f} %: ¿emparejamiento o etiquetas distintas? r sale del modelo"
            )
        else:
            r = r_modelo.copy()
            r[ok] = rf
            info["modo_r_usado"] = "parquet"
            info["parquet"] = "r de la fuente en las emparejadas, r del modelo en el resto"
    if verbose:
        print(
            f"  vocabulario FIJO de dtcoach ({n_abs} absorbentes, lam={m.lam:g}, a0={m.a0:g}, P0={'sí' if m.P0 is not None else 'no'}): "
            f"π {np.round(info['pi'], 3).tolist()} · r: {info['modo_r_usado']}",
            flush=True,
        )
        if "emparejamiento" in info:
            e = info["emparejamiento"]
            print(
                f"  emparejadas {e['emparejadas']:,}/{e['n_simdt']:,} ({100 * e['pct_emparejadas']:.2f} %); sin par: simdt {e['sin_par_simdt']:,} · fuente {e['sin_par_fuente']:,}",
                flush=True,
            )
        if "parquet" in info:
            print(f"  {info['parquet']}", flush=True)
    return m, r[abierto], info


def datos_publicados(carpeta_4abs: Path):
    """(Datos, n de secuencias de hoy, hay responsabilidades): las transiciones de dtcoach (4 absorbentes) restringidas a las secuencias
    PUBLICADAS (las `seq_uid` de `mezcla/responsabilidades_K3.parquet`), en el orden que pide `datos_desde`. Para comparar el EM de simdt
    con `mezcla_K3.npz` sobre la misma muestra con la que la fuente la ajustó."""
    import pyarrow.parquet as pq

    carpeta_4abs = Path(carpeta_4abs)
    trans, resp = (
        carpeta_4abs / "transitions.parquet",
        carpeta_4abs / "mezcla" / "responsabilidades_K3.parquet",
    )
    cols = [
        c
        for c in ("seq_uid", "poss_uid", "event_index", "from_state", "to_state", "is_absorbing")
        if c in pq.read_schema(trans).names
    ]
    t = pd.read_parquet(trans, columns=cols)
    if "seq_uid" not in t.columns:
        t = t.sort_values(["poss_uid", "event_index"])
        a = t["is_absorbing"].astype(int)
        t["seq_uid"] = (
            t["poss_uid"].astype(str) + "_s" + (a.groupby(t["poss_uid"]).cumsum() - a).astype(str)
        )
    n_hoy = int(t["seq_uid"].nunique())
    if resp.exists():
        t = t[t["seq_uid"].isin(set(pd.read_parquet(resp, columns=["seq_uid"])["seq_uid"]))]
    t = t.sort_values(["seq_uid", "event_index"], kind="stable")
    sid, uniq = pd.factorize(t["seq_uid"], sort=False)
    primero = t.groupby(sid, sort=True)["from_state"].first().to_numpy().astype(np.int64)
    d = mz.datos_desde(
        sid.astype(np.int64),
        t["from_state"].to_numpy().astype(np.int64),
        t["to_state"].to_numpy().astype(np.int64),
        len(uniq),
        primero,
    )
    return d, n_hoy, resp.exists()
