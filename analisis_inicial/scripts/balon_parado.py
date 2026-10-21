"""Balon parado (reto 5.4) -- segunda pieza de la Semana 3, otro hueco del
rubro sin cobertura hasta ahora. Se reutiliza el mismo framework M0
(clasificacion de absorbentes G/R/P/D ya validada) pero restringido a
posesiones que arrancan de un tiro de esquina o tiro libre
(`play_pattern` = "From Corner" / "From Free Kick"). Se mide, para
Pachuca-Almada y para la referencia de liga (sin Pachuca):
  - ofensivo: como termina Pachuca sus propios balones parados.
  - defensivo: como termina el rival los balones parados que cobra contra
    Pachuca (misma logica que defensa_vulnerabilidad.py pero filtrando por
    origen de la posesion, no por toda la posesion del rival).
"""

import json, time
from collections import defaultdict
import numpy as np
from m0_cadena_absorbente import possession_to_secuencias, ABS

SEASON_IDS = [351, 318, 317, 281, 235, 108]
TIPOS_BP = {"From Corner", "From Free Kick"}


def posesiones_balon_parado(events, team_name, mid):
    """Devuelve lista de (match_id, play_pattern, absorbente) para las
    posesiones de team_name que arrancan de corner o tiro libre. Usa solo
    la PRIMERA secuencia de cada posesion (el resultado de la entrega
    inmediata) -- si el balon parado produce un rebote que sigue
    jugandose, eso ya es una fase distinta (juego abierto), no parte de
    la "calidad" del balon parado en si (fix C1, ver m0_cadena_absorbente.py)."""
    events = sorted(events, key=lambda e: e["index"])
    poss = defaultdict(list)
    for e in events:
        if e["period"] in (1, 2):
            poss[e["possession"]].append(e)

    resultados = []
    for pid, evs in poss.items():
        owner = evs[0]["possession_team"]["name"]
        if owner != team_name:
            continue
        pp = evs[0].get("play_pattern", {}).get("name")
        if pp not in TIPOS_BP:
            continue
        secuencias = possession_to_secuencias(evs, owner)
        if not secuencias:
            continue
        _, absorb, _, _ = secuencias[0]
        resultados.append((mid, pp, absorb))
    return resultados


def tabla(resultados):
    n = len(resultados)
    counts = {a: sum(1 for _, _, ab in resultados if ab == a) for a in ABS}
    return n, counts


def tasa(resultados, cnt_fn):
    """Proporcion de una condicion (ej. termina en gol) sobre una lista de
    (match_id, play_pattern, absorbente)."""
    n = len(resultados)
    if n == 0:
        return np.nan
    x = sum(1 for _, _, ab in resultados if cnt_fn(ab))
    return x / n


def bootstrap_por_partido(resultados, cnt_fn, rng, b_reps=2000):
    """Bootstrap de la proporcion, remuestreando PARTIDOS completos (no
    balones parados sueltos) -- respeta la correlacion dentro de partido
    (ej. un partido con muchos corners a favor pesa como un bloque, no
    como N observaciones independientes)."""
    por_partido = defaultdict(list)
    for mid, pp, ab in resultados:
        por_partido[mid].append(ab)
    matches = list(por_partido.keys())
    n_matches = len(matches)
    tasas = np.zeros(b_reps)
    for b in range(b_reps):
        idx = rng.integers(0, n_matches, size=n_matches)
        absorbs_b = [ab for i in idx for ab in por_partido[matches[i]]]
        n_b = len(absorbs_b)
        tasas[b] = sum(1 for ab in absorbs_b if cnt_fn(ab)) / n_b if n_b > 0 else np.nan
    return tasas


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = set(m["match_id"] for m in almada if m["team"] == "Pachuca")

    all_matches_meta = {}
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    # ---- ofensivo: balon parado propio de Pachuca ----
    res_of_pachuca = []
    for mid in pachuca_ids:
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        res_of_pachuca.extend(posesiones_balon_parado(events, "Pachuca", mid))

    # ---- defensivo: balon parado del rival contra Pachuca ----
    res_def_pachuca = []
    for mid in pachuca_ids:
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        home, away = meta["home_team"]["home_team_name"], meta["away_team"]["away_team_name"]
        rival = away if home == "Pachuca" else home
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        res_def_pachuca.extend(posesiones_balon_parado(events, rival, mid))

    print(
        f"Balon parado propio de Pachuca: {len(res_of_pachuca)}  "
        f"| del rival contra Pachuca: {len(res_def_pachuca)}  ({time.time() - t0:.0f}s)"
    )

    # ---- referencia de liga (sin Pachuca), ofensivo y defensivo combinados por equipo-partido ----
    res_of_liga, res_def_liga = [], []
    n_procesados = 0
    for mid, meta in all_matches_meta.items():
        if meta.get("match_status_360") != "available" or mid in pachuca_ids:
            continue
        home, away = meta["home_team"]["home_team_name"], meta["away_team"]["away_team_name"]
        if home == "Pachuca" or away == "Pachuca":
            continue
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        # cada equipo es "ofensivo" con sus propios balones parados y "defensivo" con los del rival
        res_of_liga.extend(posesiones_balon_parado(events, home, mid))
        res_of_liga.extend(posesiones_balon_parado(events, away, mid))
        n_procesados += 1
        if n_procesados % 400 == 0:
            print(f"  liga: {n_procesados} partidos  ({time.time() - t0:.0f}s)")

    print(f"\nPartidos de liga de referencia: {n_procesados}")

    rng = np.random.default_rng(83)
    B_REPS = 2000

    def reporta(nombre, res_p, res_l):
        n_p, c_p = tabla(res_p)
        n_l, c_l = tabla(res_l)
        print(f"\n--- {nombre} ---")
        print(
            f"Pachuca: n={n_p}  "
            + "  ".join(f"{a}={c_p[a]} ({c_p[a] / n_p * 100:.1f}%)" for a in ABS)
        )
        print(
            f"Liga:    n={n_l}  "
            + "  ".join(f"{a}={c_l[a]} ({c_l[a] / n_l * 100:.1f}%)" for a in ABS)
        )
        # bootstrap por PARTIDO (no por balon parado suelto) para la incertidumbre y el p-valor
        for etiqueta, cnt_fn in [
            ("gol", lambda ab: ab == "G"),
            ("termina en tiro (G+R)", lambda ab: ab in ("G", "R")),
        ]:
            p1 = tasa(res_p, cnt_fn)
            p2 = tasa(res_l, cnt_fn)
            boot_p = bootstrap_por_partido(res_p, cnt_fn, rng, B_REPS)
            boot_l = bootstrap_por_partido(res_l, cnt_fn, rng, B_REPS)
            diff_boot = boot_p - boot_l
            lo, hi = np.nanpercentile(diff_boot, [2.5, 97.5])
            p_boot = min(1.0, 2 * min(np.nanmean(diff_boot <= 0), np.nanmean(diff_boot >= 0)))
            print(
                f"  {etiqueta}: Pachuca={p1 * 100:.2f}%  Liga={p2 * 100:.2f}%  diff={(p1 - p2) * 100:+.2f}pp  "
                f"IC95%(partido)=[{lo * 100:+.2f}pp, {hi * 100:+.2f}pp]  p_boot={p_boot:.4f}"
            )
        return n_p, c_p, n_l, c_l

    of_stats = reporta("OFENSIVO (balon parado propio)", res_of_pachuca, res_of_liga)
    def_stats = reporta(
        "DEFENSIVO (balon parado del rival contra Pachuca, vs. referencia de liga)",
        res_def_pachuca,
        res_of_liga,
    )

    np.savez(
        "balon_parado.npz",
        res_of_pachuca=np.array(res_of_pachuca, dtype=object),
        res_def_pachuca=np.array(res_def_pachuca, dtype=object),
        res_of_liga=np.array(res_of_liga, dtype=object),
    )
    print(f"\nGuardado balon_parado.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
