import json, math
from collections import defaultdict
import numpy as np

SEASON_IDS = [351, 318, 317, 281, 235, 108]
INIT_RATING = 1500.0


def load_matches_chrono():
    all_matches = []
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            if m.get("match_status") == "available" and m.get("home_score") is not None:
                all_matches.append(m)
    all_matches.sort(key=lambda m: (m["match_date"], m["match_id"]))
    return all_matches


def run_elo(matches, K, h, record_history=False):
    ratings = defaultdict(lambda: INIT_RATING)
    loglik = 0.0
    history = [] if record_history else None
    pre_match_elo = {}

    for m in matches:
        home_id = m["home_team"]["home_team_id"]
        away_id = m["away_team"]["away_team_id"]
        rh, ra = ratings[home_id], ratings[away_id]

        e_home = 1.0 / (1.0 + 10 ** ((ra - rh - h) / 400.0))

        hs, aws = m["home_score"], m["away_score"]
        if hs > aws:
            s_home = 1.0
        elif hs < aws:
            s_home = 0.0
        else:
            s_home = 0.5

        eps = 1e-9
        loglik += s_home * math.log(e_home + eps) + (1 - s_home) * math.log(1 - e_home + eps)

        if record_history:
            pre_match_elo[m["match_id"]] = {"home_elo": rh, "away_elo": ra, "e_home": e_home}

        ratings[home_id] = rh + K * (s_home - e_home)
        ratings[away_id] = ra + K * ((1 - s_home) - (1 - e_home))

    return loglik, ratings, pre_match_elo


def main():
    matches = load_matches_chrono()
    print(f"Partidos con resultado, orden cronologico: {len(matches)}")

    best = None
    for K in [10, 15, 20, 25, 30, 40, 50]:
        for h in [0, 25, 50, 75, 100]:
            ll, _, _ = run_elo(matches, K, h)
            if best is None or ll > best[0]:
                best = (ll, K, h)

    ll, K, h = best
    print(f"Mejor por verosimilitud: K={K}, h={h} (log-lik={ll:.1f})")

    _, ratings_final, pre_match = run_elo(matches, K, h, record_history=True)

    team_names = {}
    for m in matches:
        team_names[m["home_team"]["home_team_id"]] = m["home_team"]["home_team_name"]
        team_names[m["away_team"]["away_team_id"]] = m["away_team"]["away_team_name"]

    ranking = sorted(ratings_final.items(), key=lambda kv: -kv[1])
    print("\nRanking Elo final (top 10):")
    for tid, r in ranking[:10]:
        print(f"  {team_names.get(tid, '?'):<20} {r:.0f}")

    json.dump(
        {
            "K": K,
            "h": h,
            "ratings_final": {team_names.get(tid, str(tid)): r for tid, r in ratings_final.items()},
            "pre_match_elo": pre_match,
        },
        open("elo_resultados.json", "w", encoding="utf-8"),
        indent=2,
        ensure_ascii=False,
    )
    print(
        "\nGuardado elo_resultados.json (incluye Elo previo al partido para cada uno, usable como covariable en M1)"
    )


if __name__ == "__main__":
    main()
