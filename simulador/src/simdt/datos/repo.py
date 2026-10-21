"""Adaptador de SOLO LECTURA a los datos del repo (MODO_REAL_PIPELINE).

Lee `cache_events/events_<id>.json` y `matches_*.json` de la raíz, y produce:
  - secuencias (nivel secuencia, a simulador/_cache/, NUNCA al repo): una fila por secuencia de
    juego abierto o de balón parado, con sus transiciones entre zonas de la malla 5×4.
  - las tablas comunes de `datos/esquema.py` (agregadas por partido, equipo, tramo y marcador)
    una vez que la mezcla asigna responsabilidades r_sk.

Definiciones (copiadas de dtcoach con sus reglas; ver INVENTARIO.md):
  Procedencia: dtcoach_revision/dtcoach_revision_20260925_0951/src/dtcoach/possessions.py@77b720b
    - acción = Pass, Carry o Shot del equipo en posesión; una transición por acción (inicio → fin);
    - desenlace: remate con gol → GOL; remate sin gol → REMATE; pase Out → FUERA;
      pase Incomplete / Pass Offside / Unknown / Injury Clearance → PÉRDIDA;
    - la posesión se corta en SECUENCIAS en la primera absorción (ADR-v2-14);
    - absorción terminal si la secuencia muere en una zona: INTERRUPCIÓN si la siguiente posesión
      es del mismo equipo (falta, balón detenido), PÉRDIDA si no (5.º absorbente, ADR-v2-72).
  Procedencia: .../dtcoach/grid.py@77b720b (zone_of, malla 5×4 sobre 120×80)
  Procedencia: .../dtcoach/decisiones.py@77b720b (nivel_puesto)
"""

from __future__ import annotations

import glob
import json
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from .. import config

MOVING = ("Pass", "Carry", "Shot")
LOSS_OUT = ("Incomplete", "Pass Offside", "Unknown", "Injury Clearance")
GOL, REMATE, PERDIDA, FUERA, INTERRUPCION = 20, 21, 22, 23, 24  # índices globales de estado
ETAPAS_REGULARES = ("Apertura", "Clausura", "Regular Season")


# Procedencia: dtcoach/grid.py@77b720b (StateSpace.zone_of con nx=5, ny=4)
def zona(
    x: float, y: float, nx: int = 5, ny: int = 4, largo: float = 120.0, ancho: float = 80.0
) -> int:
    x = min(max(float(x), 0.0), largo - 1e-9)
    y = min(max(float(y), 0.0), ancho - 1e-9)
    return int(x / largo * nx) * ny + int(y / ancho * ny)


# Procedencia: dtcoach/decisiones.py@77b720b
def nivel_puesto(p: str | None) -> int | None:
    """Portero 0, defensa 1, contención 2, medio 3, mediapunta/extremo 4, delantero 5."""
    if p is None:
        return None
    if "Goalkeeper" in p:
        return 0
    if "Back" in p:
        return 1
    if "Defensive Midfield" in p:
        return 2
    if "Attacking Midfield" in p or "Wing" in p:
        return 4
    if "Midfield" in p:
        return 3
    if "Forward" in p or "Striker" in p:
        return 5
    return None


def normaliza(s: str | None) -> str | None:
    if s is None:
        return None
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def _en_area(x, y, cfg_bp) -> bool:
    return (
        x is not None and x >= cfg_bp["area_x"] and cfg_bp["area_y"][0] <= y <= cfg_bp["area_y"][1]
    )


def _minuto_nominal(ev) -> int | None:
    p, m = ev.get("period"), ev.get("minute", 0)
    if p == 1:
        return min(m, 44)
    if p == 2:
        return min(max(m, 45), 89)
    return None  # tiempo extra y penales: fuera


def procesar_partido(args) -> dict:
    """Un partido → dict de listas (secuencias, transiciones, cambios, goles)."""
    ruta, mid, local, visitante = args
    cfg_bp = config.cargar()["balon_parado"]
    try:
        import orjson

        ev = orjson.loads(Path(ruta).read_bytes())
    except ImportError:  # pragma: no cover
        ev = json.loads(Path(ruta).read_text(encoding="utf-8"))
    ev.sort(key=lambda e: e["index"])
    # --- goles por minuto nominal (para el estado del marcador) ---
    goles = []  # (minuto, equipo, index)
    for e in ev:
        t = e["type"]["name"]
        es_gol = (
            t == "Shot" and e.get("shot", {}).get("outcome", {}).get("name") == "Goal"
        ) or t == "Own Goal For"
        mn = _minuto_nominal(e)
        if es_gol and mn is not None:
            goles.append((mn, e["team"]["name"], e["index"]))

    def marcador_en(index: int, equipo: str) -> int:
        """Diferencia de goles del equipo ANTES del evento con este índice."""
        d = 0
        for _, eq, ix in goles:
            if ix < index:
                d += 1 if eq == equipo else -1
        return d

    # --- posición de cada jugador (para el tipo de cambio) ---
    puesto = {}
    for e in ev:
        pl, po = e.get("player"), e.get("position")
        if pl and po and pl["id"] not in puesto:
            puesto[pl["id"]] = po["name"]
    # --- secuencias ---
    acciones = [
        e
        for e in ev
        if e["type"]["name"] in MOVING
        and e.get("possession_team")
        and e.get("team")
        and e["team"]["id"] == e["possession_team"]["id"]
        and e.get("location")
        and _minuto_nominal(e) is not None
    ]
    equipo_de_pos = {}
    for e in ev:
        equipo_de_pos.setdefault(e["possession"], e["possession_team"]["name"])
    pos_ids = sorted(equipo_de_pos)
    siguiente_pos = {
        p: (pos_ids[i + 1] if i + 1 < len(pos_ids) else None) for i, p in enumerate(pos_ids)
    }
    seqs, trans = [], []
    actual = None

    def cerrar(destino_terminal=None):
        nonlocal actual
        if actual is None:
            return
        if destino_terminal is not None:
            trans.append((actual["sid"], actual["ultimo"], destino_terminal))
            actual["fin"] = destino_terminal
            actual["largo"] += 1
        seqs.append(actual)
        actual = None

    sid = 0
    prev_pos = None
    for e in acciones:
        pos = e["possession"]
        if prev_pos is not None and pos != prev_pos and actual is not None:
            sig_eq = equipo_de_pos.get(siguiente_pos.get(prev_pos))
            cerrar(INTERRUPCION if sig_eq == actual["equipo"] else PERDIDA)
        prev_pos = pos
        t = e["type"]["name"]
        x, y = e["location"][:2]
        z0 = zona(x, y)
        if actual is None:
            eq = e["team"]["name"]
            u = -1
            if t == "Pass":
                pt = (e["pass"].get("type") or {}).get("name")
                ex, ey = (e["pass"].get("end_location") or [None, None])[:2]
                if pt == "Corner":
                    u = 0
                elif pt == "Free Kick" and _en_area(ex, ey, cfg_bp):
                    u = 1
                elif pt == "Throw-in" and _en_area(ex, ey, cfg_bp):
                    u = 2
            elif t == "Shot":
                st = (e["shot"].get("type") or {}).get("name")
                u = 3 if st == "Free Kick" else (4 if st == "Penalty" else -1)
            actual = {
                "sid": sid,
                "match_id": mid,
                "equipo": eq,
                "minuto": _minuto_nominal(e),
                "dif": marcador_en(e["index"], eq),
                "inicio": z0,
                "u": u,
                "largo": 0,
                "xg": 0.0,
                "remate": 0,
                "gol": 0,
                "fin": None,
                "ultimo": z0,
                "pp": e.get("play_pattern", {}).get("name"),
            }
            sid += 1
        # destino de la acción
        if t == "Shot":
            gol = (e["shot"].get("outcome") or {}).get("name") == "Goal"
            dest = GOL if gol else REMATE
            actual["xg"] += float(e["shot"].get("statsbomb_xg") or 0.0)
            actual["remate"] = 1
            actual["gol"] = int(gol)
        elif t == "Pass":
            oc = (e["pass"].get("outcome") or {}).get("name")
            if oc == "Out":
                dest = FUERA
            elif oc in LOSS_OUT:
                dest = PERDIDA
            else:
                el = e["pass"].get("end_location")
                dest = zona(*el[:2]) if el else PERDIDA
        else:
            el = (e.get("carry") or {}).get("end_location")
            dest = zona(*el[:2]) if el else PERDIDA
        trans.append((actual["sid"], z0, dest))
        actual["largo"] += 1
        actual["ultimo"] = dest
        if dest >= GOL:
            actual["fin"] = dest
            cerrar()
    if actual is not None:
        sig_eq = equipo_de_pos.get(siguiente_pos.get(prev_pos))
        cerrar(INTERRUPCION if sig_eq == actual["equipo"] else PERDIDA)
    # --- cambios ---
    cambios = []
    for e in ev:
        if e["type"]["name"] != "Substitution":
            continue
        mn = _minuto_nominal(e)
        if mn is None:
            continue
        sale = nivel_puesto((e.get("position") or {}).get("name"))
        rep = (e.get("substitution") or {}).get("replacement") or {}
        entra = nivel_puesto(puesto.get(rep.get("id")))
        eq = e["team"]["name"]
        tipo = None
        if sale and entra:  # sin porteros (nivel 0) ni desconocidos
            d = entra - sale
            tipo = 2 if d >= 1 else (0 if d <= -1 else 1)
        cambios.append((mid, eq, mn, marcador_en(e["index"], eq), tipo))
    # --- goles en minutos nominales (para la exposición) ---
    gl = [(mid, m_, eq) for m_, eq, _ in goles]
    for s in seqs:
        s.pop("ultimo", None)
    return {
        "seqs": seqs,
        "trans": trans,
        "cambios": cambios,
        "goles": gl,
        "match_id": mid,
        "local": local,
        "visitante": visitante,
    }


def tecnicos_por_id(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """El técnico se identifica por `managers[0].id`, no por nombre [D-056].

    Nombre visible = el más frecuente de ese id; si dos ids distintos quedan con el mismo nombre
    visible, se desambigua como "nombre (id)". Devuelve (partidos con `tecnico_*` reescrito, tabla de
    ids con su nombre y los nombres con que aparece). Los partidos sin id conservan su nombre.
    """
    cols = [("tecnico_local", "tecnico_id_local"), ("tecnico_visitante", "tecnico_id_visitante")]
    if not all(
        i in p.columns for _, i in cols
    ):  # tablas sin ids (sintéticas o ya agregadas): se queda el nombre
        return p, pd.DataFrame(columns=["id", "nombre", "nombres", "partidos"])
    f = pd.concat([p[[n, i]].rename(columns={n: "nombre", i: "id"}) for n, i in cols]).dropna()
    f = f[f["id"].notna()]
    if f.empty:
        return p, pd.DataFrame(columns=["id", "nombre", "nombres", "partidos"])
    f["id"] = f["id"].astype(int)
    vis = f.groupby("id").nombre.agg(lambda x: x.value_counts().index[0])
    cuenta = vis.value_counts()
    vis = pd.Series({i: (n if cuenta[n] == 1 else f"{n} ({i})") for i, n in vis.items()})
    tabla = pd.DataFrame(
        {
            "id": vis.index,
            "nombre": vis.values,
            "nombres": [sorted(f[f["id"] == i].nombre.unique()) for i in vis.index],
            "partidos": [int((f["id"] == i).sum()) for i in vis.index],
        }
    )
    p = p.copy()
    for n, i in cols:
        m = p[i].notna()
        p.loc[m, n] = p.loc[m, i].astype(int).map(vis).to_numpy()
    return p, tabla


def homonimos(p: pd.DataFrame) -> pd.DataFrame:
    """Ids distintos que el código antiguo (por nombre) fusionaba en una sola persona."""
    cols = [("tecnico_local", "tecnico_id_local"), ("tecnico_visitante", "tecnico_id_visitante")]
    f = pd.concat([p[[n, i]].rename(columns={n: "nombre", i: "id"}) for n, i in cols]).dropna()
    g = f.groupby("nombre").id.nunique()
    return (
        f[f.nombre.isin(g[g > 1].index)]
        .groupby(["nombre", "id"])
        .size()
        .rename("partidos")
        .reset_index()
    )


def leer_partidos(raiz: Path | None = None) -> pd.DataFrame:
    cfg = config.cargar()
    raiz = Path(raiz) if raiz else config.RAIZ_REPO
    filas = []
    for f in sorted(glob.glob(str(raiz / cfg["datos"]["partidos_glob"]))):
        with open(f, encoding="utf-8") as fh:
            for m in json.load(fh):
                h, a = m["home_team"], m["away_team"]
                mh = (h.get("managers") or [{}])[0]
                ma = (a.get("managers") or [{}])[0]
                filas.append(
                    {
                        "match_id": m["match_id"],
                        "fecha": pd.Timestamp(m["match_date"]),
                        "temporada_sb": m["season"]["season_name"],
                        "etapa": m["competition_stage"]["name"],
                        "jornada": m.get("match_week"),
                        "estado": m["match_status"],
                        "local": h["home_team_name"],
                        "visitante": a["away_team_name"],
                        "goles_local": m["home_score"],
                        "goles_visitante": m["away_score"],
                        "tecnico_local": normaliza(mh.get("nickname") or mh.get("name")),
                        "tecnico_visitante": normaliza(ma.get("nickname") or ma.get("name")),
                        "tecnico_id_local": mh.get("id"),
                        "tecnico_id_visitante": ma.get("id"),
                    }
                )
    p = pd.DataFrame(filas)
    p, _ = tecnicos_por_id(p)
    # torneo corto: Apertura (jul–dic) o Clausura (ene–jun), en orden cronológico
    anio = p.fecha.dt.year.astype(str)
    p["torneo"] = np.where(p.fecha.dt.month >= 7, "Apertura " + anio, "Clausura " + anio)
    orden = p.groupby("torneo").fecha.min().sort_values().index.tolist()
    p["temporada"] = p.torneo.map({t: i for i, t in enumerate(orden)})
    p["regular"] = p.etapa.isin(ETAPAS_REGULARES)
    return p.sort_values(["fecha", "match_id"]).reset_index(drop=True)


def extraer(hilos: int = 6, verbose: bool = True, raiz: Path | None = None) -> dict:
    """Corre la extracción sobre todos los partidos jugados con eventos; cachea en _cache/."""
    cache = config.cache_dir() / "extraccion.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    cfg = config.cargar()
    raiz = Path(raiz) if raiz else config.RAIZ_REPO
    partidos = leer_partidos(raiz)
    ev_dir = raiz / cfg["datos"]["eventos_dir"]
    jugados = partidos[partidos.estado == "available"]
    args = [
        (str(ev_dir / f"events_{r.match_id}.json"), r.match_id, r.local, r.visitante)
        for r in jugados.itertuples()
        if (ev_dir / f"events_{r.match_id}.json").exists()
    ]
    out = []
    with ProcessPoolExecutor(hilos) as ex:
        for i, r in enumerate(ex.map(procesar_partido, args, chunksize=8)):
            out.append(r)
            if verbose and i % 200 == 0:
                print(f"  extracción {i}/{len(args)}", flush=True)
    seqs, trans, camb, goles = [], [], [], []
    base = 0
    for r in out:
        for s in r["seqs"]:
            s["sid"] += base
        seqs += r["seqs"]
        trans += [(a + base, b, c) for a, b, c in r["trans"]]
        base += len(r["seqs"])
        camb += r["cambios"]
        goles += r["goles"]
    res = {
        "partidos": partidos,
        "secuencias": pd.DataFrame(seqs),
        "transiciones": pd.DataFrame(trans, columns=["sid", "desde", "hacia"]),
        "cambios": pd.DataFrame(camb, columns=["match_id", "equipo", "minuto", "dif", "tipo"]),
        "goles": pd.DataFrame(goles, columns=["match_id", "minuto", "equipo"]),
        "con_eventos": [a[1] for a in args],
    }
    pd.to_pickle(res, cache)
    return res


# ----------------------------------------------------------------------------------------------
# De secuencias a tablas comunes
# ----------------------------------------------------------------------------------------------
def ajustar_mezcla(
    ext: dict, verbose: bool = True, vocab=None, vocab_r: str = "parquet", corte=None
):
    """Mezcla K = 3 sobre las secuencias de JUEGO ABIERTO (u = −1); r_sk para todas ellas.

    `vocab` (D-048): carpeta con `mezcla_K3.npz` de dtcoach; si se da, NO se ajusta nada: el vocabulario es el de la fuente y
    r_sk sale de ahí (`estimacion/vocab_fuente.py`). El informe del emparejamiento queda en `ext["vocab_dtcoach"]`.
    `corte` (D-050): el EM se ajusta solo con secuencias de partidos anteriores a esa fecha (r_sk se calcula para todas).
    """
    from ..estimacion import mezcla as mz

    if vocab:
        from ..estimacion import vocab_fuente as vf

        s, t = ext["secuencias"], ext["transiciones"]
        abierto = np.flatnonzero(s.u.to_numpy() < 0)
        m, r, ext["vocab_dtcoach"] = vf.aplicar(
            Path(vocab), s, t, abierto, modo_r=vocab_r, verbose=verbose
        )
        return m, abierto, r
    cfg = config.cargar()
    mc = cfg["mezcla"]
    n_arr = int(mc.get("n_arranques", 1))
    # _p0: la caché anterior (sin P⁰, D-047) no se reutiliza; _a<N>: depende del número de arranques (D-049)
    sufijo = "" if corte is None else "_c" + pd.Timestamp(corte).strftime("%Y%m%d")
    cache = config.cache_dir() / (
        f"mezcla_real_p0_a{n_arr}{sufijo}.npz" if n_arr > 1 else f"mezcla_real_p0{sufijo}.npz"
    )
    s, t = ext["secuencias"], ext["transiciones"]
    d = mz.datos_desde(
        t.sid.to_numpy(), t.desde.to_numpy(), t.hacia.to_numpy(), len(s), s.inicio.to_numpy()
    )
    abierto = np.flatnonzero(s.u.to_numpy() < 0)
    da = d.sub(abierto)
    dfit = d if mc.get("ajustar_con_balon_parado", True) else da
    if corte is not None:
        fecha = ext["partidos"].drop_duplicates("match_id").set_index("match_id")["fecha"]
        antes = (s.match_id.map(fecha) < pd.Timestamp(corte)).to_numpy()
        dfit = dfit.sub(
            np.flatnonzero(antes if mc.get("ajustar_con_balon_parado", True) else antes[abierto])
        )
    if cache.exists():
        z = np.load(cache)
        m = mz.Mezcla(
            z["pi"],
            z["mu"],
            z["P"],
            float(z["lam"]),
            float(z["a0"]),
            list(z["objetivo"]),
            z["P0"] if "P0" in z.files else None,
            json.loads(str(z["diagnostico"])) if "diagnostico" in z.files else {},
        )
    else:
        rng = np.random.default_rng([cfg["semilla"], 3])
        n_sub = mc["submuestra"] or dfit.n
        sub = (
            np.sort(rng.choice(dfit.n, min(n_sub, dfit.n), replace=False))
            if n_sub < dfit.n
            else np.arange(dfit.n)
        )
        if n_arr > 1:
            m = mz.ajustar_multi(
                dfit.sub(sub),
                3,
                mc["lam"],
                mc["a0"],
                mc["max_iter"],
                mc["tol"],
                seed=cfg["semilla"],
                n_corto=mc["n_corto"],
                n_arranques=n_arr,
                n_jobs=int(mc.get("n_jobs", 1)),
                verbose=verbose,
            )
        else:
            m = mz.ajustar(
                dfit.sub(sub),
                3,
                mc["lam"],
                mc["a0"],
                mc["max_iter"],
                mc["tol"],
                seed=cfg["semilla"],
                n_corto=mc["n_corto"],
                verbose=verbose,
            )
        extra = {} if m.P0 is None else {"P0": m.P0}
        np.savez_compressed(
            cache,
            pi=m.pi,
            mu=m.mu,
            P=m.P,
            lam=m.lam,
            a0=m.a0,
            objetivo=np.array(m.objetivo),
            diagnostico=json.dumps(m.diagnostico),
            **extra,
        )
    if m.diagnostico:
        ext["multiarranque"] = m.diagnostico
    r = mz.responsabilidades(m, da)
    return m, abierto, r


def _estado(dif) -> np.ndarray:
    dif = np.asarray(dif)
    return np.where(dif < 0, 0, np.where(dif == 0, 1, 2))


def tablas_comunes(ext: dict, abierto: np.ndarray, r: np.ndarray) -> dict:
    """Construye las tablas de `datos/esquema.py` a partir de la extracción y de r_sk."""
    from ..estimacion.liga import correr_elo

    cfg = config.cargar()
    p = ext["partidos"].copy()
    el, ev, _ = correr_elo(p, cfg["elo"]["K"], cfg["elo"]["h"], cfg["elo"]["inicial"])
    p["elo_local"], p["elo_visitante"] = el, ev
    p["etapa"] = np.where(p.regular, "regular", "liguilla")
    con_ev = set(ext["con_eventos"])
    partidos = p[p.match_id.isin(con_ev)].copy()
    lado = pd.concat(
        [
            pd.DataFrame(
                {
                    "match_id": partidos.match_id,
                    "equipo": partidos.local,
                    "rival": partidos.visitante,
                    "local": 1,
                }
            ),
            pd.DataFrame(
                {
                    "match_id": partidos.match_id,
                    "equipo": partidos.visitante,
                    "rival": partidos.local,
                    "local": 0,
                }
            ),
        ]
    )
    s = ext["secuencias"].merge(lado, on=["match_id", "equipo"], how="inner")
    s["tramo"] = np.minimum(s.minuto // 15, 5)
    s["m"] = _estado(s.dif)
    # juego abierto, ponderado por r_sk
    sa = ext["secuencias"].iloc[abierto][["sid"]].reset_index(drop=True)
    R = pd.DataFrame(r, columns=[0, 1, 2])
    R["sid"] = sa.sid
    j = s[s.u < 0].merge(R, on="sid")
    filas = []
    for k in range(3):
        g = j.assign(n=j[k], remates=j[k] * j.remate, xg=j[k] * j.xg, goles=j[k] * j.gol, k=k)
        filas.append(
            g.groupby(["match_id", "equipo", "rival", "local", "tramo", "m", "k"], as_index=False)[
                ["n", "remates", "xg", "goles"]
            ].sum()
        )
    juego = pd.concat(filas, ignore_index=True)
    sq = s[s.u >= 0].assign(
        n=1.0, remates=lambda x: x.remate.astype(float), goles=lambda x: x.gol.astype(float)
    )
    saques = sq.groupby(
        ["match_id", "equipo", "rival", "local", "tramo", "m", "u"], as_index=False
    )[["n", "remates", "xg", "goles"]].sum()
    # exposición: estado al inicio de cada minuto nominal
    goles = ext["goles"]
    gpm = {mid: g for mid, g in goles.groupby("match_id")}
    expo, panel = [], []
    camb = ext["cambios"]
    cpm = {k: g for k, g in camb.groupby(["match_id", "equipo"])}
    for row in lado.itertuples(index=False):
        g = gpm.get(row.match_id)
        dif_min = np.zeros(90)
        if g is not None:
            for mn, eq in zip(g.minuto, g.equipo):
                dif_min[mn + 1 :] += 1 if eq == row.equipo else -1
        m = _estado(dif_min)
        tr = np.minimum(np.arange(90) // 15, 5)
        cnt = np.zeros((6, 3))
        np.add.at(cnt, (tr, m), 1)
        for a in range(6):
            for b in range(3):
                if cnt[a, b]:
                    expo.append((row.match_id, row.equipo, a, b, cnt[a, b]))
        cs = cpm.get((row.match_id, row.equipo))
        minutos_c = (
            np.bincount(cs.minuto.to_numpy(), minlength=90) if cs is not None else np.zeros(90)
        )
        hechos = int(minutos_c[:45].sum())
        for t_ in range(45, 90):
            if hechos >= 5:
                break
            panel.append((row.match_id, row.equipo, t_, m[t_], int(minutos_c[t_] > 0)))
            hechos += int(minutos_c[t_])
    camb = camb.dropna(subset=["tipo"]).assign(
        m=lambda x: _estado(x.dif), tipo=lambda x: x.tipo.astype(int)
    )
    tablas = {
        "partidos": partidos[
            [
                "match_id",
                "temporada",
                "jornada",
                "fecha",
                "local",
                "visitante",
                "goles_local",
                "goles_visitante",
                "tecnico_local",
                "tecnico_visitante",
                "elo_local",
                "elo_visitante",
                "etapa",
                "torneo",
            ]
        ].reset_index(drop=True),
        "juego": juego,
        "exposicion": pd.DataFrame(expo, columns=["match_id", "equipo", "tramo", "m", "minutos"]),
        "saques": saques,
        "cambios": camb[["match_id", "equipo", "minuto", "m", "tipo"]],
        "panel": pd.DataFrame(panel, columns=["match_id", "equipo", "minuto", "m", "cambio"]),
    }
    return tablas, p
