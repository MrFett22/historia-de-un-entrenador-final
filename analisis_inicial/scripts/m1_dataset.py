import json, time, sys
import numpy as np

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import zone, possession_to_secuencias, N_ZONES

SEASON_IDS = [351, 318, 317, 281, 235, 108]


def reconstruct_scores(events, home_id, away_id):
    score = {home_id: 0, away_id: 0}
    per_index_score = {}
    for e in events:
        if e["period"] == 5:
            per_index_score[e["index"]] = (score[home_id], score[away_id])
            continue
        t = e["type"]["name"]
        if t == "Shot" and e.get("shot", {}).get("outcome", {}).get("name") == "Goal":
            score[e["team"]["id"]] += 1
        elif t == "Own Goal For":
            score[e["team"]["id"]] += 1
        per_index_score[e["index"]] = (score[home_id], score[away_id])
    return per_index_score


def marcador_estado(my_s, ri_s):
    if my_s > ri_s:
        return 1
    elif my_s < ri_s:
        return -1
    return 0


def periodo_frac(minute):
    # minuto normalizado 0-1 sobre un partido de 90, recortado a [0,1]
    return min(1.0, minute / 90.0)


def main():
    t0 = time.time()
    elo_data = json.load(open("elo_resultados.json", encoding="utf-8"))
    pre_match_elo = elo_data["pre_match_elo"]

    all_matches = []
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            if m.get("match_status_360") == "available":
                all_matches.append(m)

    print(f"Construyendo dataset M1 sobre {len(all_matches)} partidos...")

    rows_i, rows_dest, rows_x, rows_is_pachuca, rows_equipo, rows_match = [], [], [], [], [], []
    n_procesados = 0

    for idx_m, m in enumerate(all_matches):
        mid = m["match_id"]
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        events.sort(key=lambda e: e["index"])
        home_id, away_id = m["home_team"]["home_team_id"], m["away_team"]["away_team_id"]
        home_name, away_name = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
        per_index_score = reconstruct_scores(events, home_id, away_id)

        elo_info = pre_match_elo.get(str(mid)) or pre_match_elo.get(mid)
        if elo_info is None:
            continue
        elo_home, elo_away = elo_info["home_elo"], elo_info["away_elo"]

        from collections import defaultdict

        poss = defaultdict(list)
        for e in events:
            if e["period"] in (1, 2):
                poss[e["possession"]].append(e)

        for pid, evs in poss.items():
            owner = evs[0]["possession_team"]["name"]
            is_home = owner == home_name
            if not is_home and owner != away_name:
                continue
            team_id = home_id if is_home else away_id
            local_visita = 1 if is_home else 0  # 1=local, 0=visita
            elo_own = elo_home if is_home else elo_away
            elo_riv = elo_away if is_home else elo_home
            elo_diff = (elo_own - elo_riv) / 400.0  # escalado

            is_pachuca = 1 if owner == "Pachuca" else 0

            for seq, absorb, xg_val, primer_evento in possession_to_secuencias(evs, owner):
                start_idx = primer_evento["index"]
                my_s, ri_s = per_index_score.get(start_idx, (0, 0))
                if not is_home:
                    my_s, ri_s = ri_s, my_s
                marcador = marcador_estado(my_s, ri_s)
                minute = primer_evento.get("minute", 0)
                per_frac = periodo_frac(minute)

                for k in range(len(seq) - 1):
                    rows_i.append(seq[k])
                    rows_dest.append(seq[k + 1])
                    rows_x.append([marcador, per_frac, local_visita, elo_diff])
                    rows_is_pachuca.append(is_pachuca)
                    rows_equipo.append(owner)
                    rows_match.append(mid)
                rows_i.append(seq[-1])
                rows_dest.append(N_ZONES + {"G": 0, "R": 1, "P": 2, "D": 3}[absorb])
                rows_x.append([marcador, per_frac, local_visita, elo_diff])
                rows_is_pachuca.append(is_pachuca)
                rows_equipo.append(owner)
                rows_match.append(mid)

        n_procesados += 1
        if (idx_m + 1) % 300 == 0:
            print(
                f"  {idx_m + 1}/{len(all_matches)} partidos ({time.time() - t0:.0f}s, {len(rows_i):,} filas)"
            )

    print(f"\nPartidos procesados: {n_procesados}")
    print(f"Filas totales: {len(rows_i):,}")

    np.savez_compressed(
        "m1_dataset.npz",
        origen=np.array(rows_i, dtype=np.int16),
        destino=np.array(rows_dest, dtype=np.int16),
        x=np.array(rows_x, dtype=np.float32),
        is_pachuca=np.array(rows_is_pachuca, dtype=np.int8),
        equipo=np.array(rows_equipo, dtype="<U30"),
        match_id=np.array(rows_match, dtype=np.int32),
    )
    print(f"Guardado m1_dataset.npz ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
