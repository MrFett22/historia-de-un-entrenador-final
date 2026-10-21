"""Organizacion defensiva de Pachuca via 360 (reto 5.1, ultima pieza).
Solo se usan los jugadores que el freeze_frame realmente reporta -- lo que
la camara no ve no se imputa (FRAMEWORK.md seccion 2). Se toman los frames
de eventos ejecutados por el RIVAL (Pachuca esta defendiendo); dentro de
esos frames, "teammate": false son los jugadores de Pachuca. Las
coordenadas estan en el marco de ataque del rival (x=0 su propio arco,
x=120 el arco de Pachuca) -- no hace falta espejear, solo hay que
interpretar la distancia a la porteria de Pachuca como 120-x.

Metricas por frame (solo con jugadores de campo, sin portero):
- altura_linea = 120 - max(x) del ultimo defensor -- que tan lejos de su
  propio arco esta la linea mas retrasada (mayor = linea mas alta/agresiva).
- ancho_bloque = max(y) - min(y)
- profundidad_bloque = max(x) - min(x)
- area_casco_convexo = area del poligono convexo de las posiciones (scipy)
- jugadores_por_delante_del_balon = cuenta de defensores de Pachuca con
  x < x_balon (x del evento) -- mas avanzados que el balon, hacia el arco
  rival, en el marco del rival.

Se requieren minimo 3 jugadores de campo visibles de Pachuca en el frame
para calcular casco convexo/ancho/profundidad (si hay menos, se descarta
el frame para esas metricas en vez de imputar).
"""

import json, time
import numpy as np
from scipy.spatial import ConvexHull, QhullError

SEASON_IDS = [351, 318, 317, 281, 235, 108]
MIN_JUGADORES = 3


def metricas_partido(events, frames, team_defendiendo):
    ev_by_id = {e["id"]: e for e in events}
    out = []
    for f in frames:
        ev = ev_by_id.get(f["event_uuid"])
        if ev is None or ev["period"] not in (1, 2):
            continue
        if ev["team"]["name"] == team_defendiendo:
            continue  # queremos frames donde el RIVAL ejecuta (team_defendiendo esta defendiendo)
        loc = ev.get("location")
        if loc is None:
            continue
        ball_x = loc[0]

        jugadores = [p for p in f["freeze_frame"] if not p["teammate"] and not p["keeper"]]
        if len(jugadores) == 0:
            continue
        xs = np.array([p["location"][0] for p in jugadores])
        ys = np.array([p["location"][1] for p in jugadores])

        altura_linea = 120.0 - xs.max()
        jugadores_delante = int((xs < ball_x).sum())

        ancho = profundidad = area_hull = np.nan
        if len(jugadores) >= MIN_JUGADORES:
            ancho = ys.max() - ys.min()
            profundidad = xs.max() - xs.min()
            try:
                pts = np.column_stack([xs, ys])
                hull = ConvexHull(pts)
                area_hull = hull.volume  # en 2D, ConvexHull.volume es el area
            except QhullError:
                area_hull = np.nan

        out.append((altura_linea, ancho, profundidad, area_hull, jugadores_delante, len(jugadores)))
    return out


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = set(m["match_id"] for m in almada if m["team"] == "Pachuca")

    all_matches_meta = {}
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    resultados_pachuca = []
    n_ok = 0
    for mid in pachuca_ids:
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
            frames = json.load(open(f"cache_events/frames_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        resultados_pachuca.extend(metricas_partido(events, frames, "Pachuca"))
        n_ok += 1
    print(
        f"Pachuca: {n_ok}/{len(pachuca_ids)} partidos, {len(resultados_pachuca):,} frames defensivos  ({time.time() - t0:.0f}s)"
    )

    resultados_liga = []
    n_procesados = 0
    for mid, meta in all_matches_meta.items():
        if meta.get("match_status_360") != "available" or mid in pachuca_ids:
            continue
        home = meta["home_team"]["home_team_name"]
        away = meta["away_team"]["away_team_name"]
        if home == "Pachuca" or away == "Pachuca":
            continue
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
            frames = json.load(open(f"cache_events/frames_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        resultados_liga.extend(metricas_partido(events, frames, home))
        resultados_liga.extend(metricas_partido(events, frames, away))
        n_procesados += 1
        if n_procesados % 300 == 0:
            print(
                f"  liga: {n_procesados} partidos, {len(resultados_liga):,} frames  ({time.time() - t0:.0f}s)"
            )

    print(
        f"\nLiga (sin Pachuca): {n_procesados} partidos, {len(resultados_liga):,} frames defensivos"
    )

    cols = [
        "altura_linea",
        "ancho_bloque",
        "profundidad_bloque",
        "area_hull",
        "jug_delante_balon",
        "n_jugadores",
    ]
    arr_p = np.array(resultados_pachuca, dtype=float)
    arr_l = np.array(resultados_liga, dtype=float)

    print(
        f"\n{'metrica':>22} {'Pachuca(media)':>15} {'Pachuca(mediana)':>17} {'Liga(media)':>13} {'Liga(mediana)':>15}"
    )
    for i, name in enumerate(cols[:5]):
        col_p = arr_p[:, i]
        col_l = arr_l[:, i]
        col_p = col_p[~np.isnan(col_p)]
        col_l = col_l[~np.isnan(col_l)]
        print(
            f"{name:>22} {col_p.mean():>15.2f} {np.median(col_p):>17.2f} {col_l.mean():>13.2f} {np.median(col_l):>15.2f}"
        )

    np.savez("organizacion_defensiva_360.npz", arr_p=arr_p, arr_l=arr_l, cols=cols)
    print(f"\nGuardado organizacion_defensiva_360.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
