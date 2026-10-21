import json, time, sys

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import process_match_for_team, build_QR, N_ZONES

SEASON_IDS = [351, 318, 317, 281, 235, 108]


def main():
    t0 = time.time()
    all_matches = []
    for sid in SEASON_IDS:
        matches = json.load(open(f"matches_{sid}.json", encoding="utf-8"))
        for m in matches:
            if m.get("match_status_360") == "available":
                all_matches.append(m)

    print(f"Procesando liga completa (sin Pachuca): {len(all_matches)} partidos...")
    all_trans = []
    n_teams_procesados = 0
    for i, m in enumerate(all_matches):
        mid = m["match_id"]
        home = m["home_team"]["home_team_name"]
        away = m["away_team"]["away_team_name"]
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        for team_name in (home, away):
            if team_name == "Pachuca":
                continue
            trans, _, _ = process_match_for_team(events, team_name)
            all_trans.extend(trans)
            n_teams_procesados += 1
        if (i + 1) % 300 == 0:
            print(f"  {i + 1}/{len(all_matches)} partidos ({time.time() - t0:.0f}s)")

    print(f"Equipos-partido procesados: {n_teams_procesados}")
    print(f"Transiciones totales (liga, sin Pachuca): {len(all_trans):,}")

    Q_liga, R_liga, counts_liga = build_QR(all_trans)

    import numpy as np

    np.savez("m0_liga_referencia.npz", Q=Q_liga, R=R_liga, counts=counts_liga)
    print(f"Guardado m0_liga_referencia.npz ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
