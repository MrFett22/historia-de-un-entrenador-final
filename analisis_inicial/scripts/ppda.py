"""PPDA (passes permitidos por accion defensiva) de Pachuca-Almada vs.
referencia de liga (excluyendo los partidos de Pachuca). Definicion
reconciliada con la exploracion inicial del proyecto: acciones defensivas =
Pressure + Duel + Interception + Foul Committed, contadas solo si
x>=40 en el marco propio del equipo que defiende (excluye su propio tercio
defensivo -- no cuenta como "presion" defenderse cerca del propio arco).
Los pases del rival se cuentan con x<=80 en el marco DEL RIVAL -- misma
zona fisica, sin necesidad de espejeo (team_x>=40 <=> rival_x<=80, porque
120-40=80 para la misma franja del campo).

PPDA = pases del rival (x<=80, su marco) / acciones defensivas propias
(x>=40, mi marco). PPDA mas bajo = presion mas intensa/alta.
"""

import json, time
import numpy as np
from scipy import stats

DEF_TYPES = {"Pressure", "Duel", "Interception", "Foul Committed"}


def ppda_equipo_en_partido(events, team_name, rival_name):
    def_actions = 0
    rival_passes = 0
    for e in events:
        if e["period"] not in (1, 2):
            continue
        loc = e.get("location")
        if loc is None:
            continue
        if e["team"]["name"] == team_name and e["type"]["name"] in DEF_TYPES and loc[0] >= 40:
            def_actions += 1
        elif e["team"]["name"] == rival_name and e["type"]["name"] == "Pass" and loc[0] <= 80:
            rival_passes += 1
    return def_actions, rival_passes


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_matches = [m for m in almada if m["team"] == "Pachuca"]
    pachuca_ids = set(m["match_id"] for m in pachuca_matches)

    all_matches_meta = {}
    for sid in [351, 318, 317, 281, 235, 108]:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    ppda_pachuca = []
    for mid in pachuca_ids:
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        home = meta["home_team"]["home_team_name"]
        away = meta["away_team"]["away_team_name"]
        rival = away if home == "Pachuca" else home
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        d, p = ppda_equipo_en_partido(events, "Pachuca", rival)
        if d > 0:
            ppda_pachuca.append(p / d)

    print(
        f"PPDA calculado en {len(ppda_pachuca)}/{len(pachuca_ids)} partidos de Pachuca-Almada  ({time.time() - t0:.0f}s)"
    )

    ppda_liga = []
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
        except FileNotFoundError:
            continue
        d_h, p_h = ppda_equipo_en_partido(events, home, away)
        if d_h > 0:
            ppda_liga.append(p_h / d_h)
        d_a, p_a = ppda_equipo_en_partido(events, away, home)
        if d_a > 0:
            ppda_liga.append(p_a / d_a)
        n_procesados += 1
        if n_procesados % 400 == 0:
            print(f"  liga: {n_procesados} partidos  ({time.time() - t0:.0f}s)")

    ppda_pachuca = np.array(ppda_pachuca)
    ppda_liga = np.array(ppda_liga)
    print(f"\nPartidos de liga de referencia: {n_procesados}  (equipo-partido: {len(ppda_liga)})")
    print(
        f"\nPPDA Pachuca-Almada: media={ppda_pachuca.mean():.2f}  mediana={np.median(ppda_pachuca):.2f}  "
        f"sd={ppda_pachuca.std():.2f}  n={len(ppda_pachuca)}"
    )
    print(
        f"PPDA liga (sin Pachuca): media={ppda_liga.mean():.2f}  mediana={np.median(ppda_liga):.2f}  "
        f"sd={ppda_liga.std():.2f}  n={len(ppda_liga)}"
    )

    u_stat, p_value = stats.mannwhitneyu(ppda_pachuca, ppda_liga, alternative="two-sided")
    print(f"\nMann-Whitney U (Pachuca vs. liga): U={u_stat:.0f}  p-valor={p_value:.5f}")

    rng = np.random.default_rng(23)
    diffs = []
    for _ in range(5000):
        s_p = rng.choice(ppda_pachuca, size=len(ppda_pachuca), replace=True)
        s_l = rng.choice(ppda_liga, size=len(ppda_liga), replace=True)
        diffs.append(s_p.mean() - s_l.mean())
    diffs = np.array(diffs)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    print(
        f"Diferencia de medias (Pachuca-liga), bootstrap 95% CI: {diffs.mean():+.2f}  [{lo:+.2f}, {hi:+.2f}]"
    )

    np.savez(
        "ppda_resultado.npz",
        ppda_pachuca=ppda_pachuca,
        ppda_liga=ppda_liga,
        u_stat=u_stat,
        p_value=p_value,
        diff_ci=[lo, hi],
    )
    print(f"\nGuardado ppda_resultado.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
