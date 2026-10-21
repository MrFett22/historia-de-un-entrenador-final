"""Vulnerabilidad defensiva de Pachuca-Almada (reto 5.1, lado defensivo).

Misma cadena absorbente M0, pero aplicada al RIVAL: se construye la cadena
de como progresa el equipo contrario cuando tiene el balon contra Pachuca
(139 partidos), y se compara con una cadena de referencia de como progresan
esos mismos rivales -- en general, contra el resto de la liga (excluyendo
cualquier partido contra Pachuca, para no contaminar la referencia). El
B_gol del rival por zona, encogido hacia la referencia de liga (mismo
lambda validado por CV en la Semana 1), muestra en que zonas Pachuca es
mas o menos vulnerable que una defensa promedio de liga.
"""

import json, time
import numpy as np
from m0_cadena_absorbente import process_match_for_team, build_QR, solve_absorbing, N_ZONES

LAMBDA_SHRINK = 1750  # punto medio del optimo de CV (1500-2000) hallado en Semana 1


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_matches = [m for m in almada if m["team"] == "Pachuca"]
    pachuca_ids = set(m["match_id"] for m in pachuca_matches)
    print(f"Partidos de Pachuca-Almada: {len(pachuca_ids)}")

    # --- cadena del rival CONTRA Pachuca ---
    all_matches_meta = {}
    import os

    for sid in [351, 318, 317, 281, 235, 108]:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    trans_riv_vs_pachuca = []
    for mid in pachuca_ids:
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        home = meta["home_team"]["home_team_name"]
        away = meta["away_team"]["away_team_name"]
        rival_name = away if home == "Pachuca" else home
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        trans, _, _ = process_match_for_team(events, rival_name)
        trans_riv_vs_pachuca.extend(trans)

    print(f"Transiciones del rival contra Pachuca: {len(trans_riv_vs_pachuca):,}")

    # --- cadena de referencia: todos los equipos, en partidos SIN Pachuca ---
    trans_liga_sin_pachuca = []
    n_partidos_liga = 0
    for mid, meta in all_matches_meta.items():
        if meta.get("match_status_360") != "available":
            continue
        if mid in pachuca_ids:
            continue
        home = meta["home_team"]["home_team_name"]
        away = meta["away_team"]["away_team_name"]
        if home == "Pachuca" or away == "Pachuca":
            continue  # excluir tambien partidos de Pachuca fuera de la ventana de Almada
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        for team_name in (home, away):
            trans, _, _ = process_match_for_team(events, team_name)
            trans_liga_sin_pachuca.extend(trans)
        n_partidos_liga += 1
        if n_partidos_liga % 400 == 0:
            print(
                f"  liga referencia: {n_partidos_liga} partidos, {len(trans_liga_sin_pachuca):,} transiciones ({time.time() - t0:.0f}s)"
            )

    print(f"Partidos de referencia de liga (sin Pachuca): {n_partidos_liga}")
    print(f"Transiciones de referencia de liga: {len(trans_liga_sin_pachuca):,}")

    Q_riv, R_riv, counts_riv = build_QR(trans_riv_vs_pachuca)
    Q_liga, R_liga, counts_liga = build_QR(trans_liga_sin_pachuca)

    N_riv, t_riv, B_riv = solve_absorbing(Q_riv, R_riv)
    N_liga, t_liga, B_liga = solve_absorbing(Q_liga, R_liga)

    # encogimiento de B_riv hacia B_liga, ponderado por conteo de fila (n. de veces que
    # se salio de esa zona en counts_riv), mismo lambda de la Semana 1
    n_riv_por_zona = counts_riv.sum(axis=1)
    B_riv_shrunk = np.zeros_like(B_riv)
    for z in range(N_ZONES):
        n = n_riv_por_zona[z]
        B_riv_shrunk[z] = (n * B_riv[z] + LAMBDA_SHRINK * B_liga[z]) / (n + LAMBDA_SHRINK)

    diff_gol = (
        B_riv_shrunk[:, 0] - B_liga[:, 0]
    )  # positivo = Pachuca MAS vulnerable que la liga en esa zona

    print(
        f"\nrho(Q_riv)={max(abs(np.linalg.eigvals(Q_riv))):.4f}  rho(Q_liga)={max(abs(np.linalg.eigvals(Q_liga))):.4f}"
    )
    print(f"\nVulnerabilidad por zona (B_gol del rival, encogido) vs. referencia de liga:")
    print(f"{'zona':>5} {'n_riv':>7} {'B_gol_riv':>10} {'B_gol_liga':>11} {'diff_pp':>9}")
    for z in range(N_ZONES):
        print(
            f"{z:>5} {int(n_riv_por_zona[z]):>7} {B_riv_shrunk[z, 0] * 100:>9.2f}% {B_liga[z, 0] * 100:>10.2f}% {diff_gol[z] * 100:>+8.2f}pp"
        )

    orden = np.argsort(-diff_gol)
    print(f"\nZonas donde Pachuca es MAS vulnerable que el promedio de liga (top 5):")
    for z in orden[:5]:
        print(f"  z{z}: +{diff_gol[z] * 100:.2f}pp  (n_riv={int(n_riv_por_zona[z])})")
    print(f"\nZonas donde Pachuca es MENOS vulnerable que el promedio de liga (top 5):")
    for z in orden[-5:]:
        print(f"  z{z}: {diff_gol[z] * 100:+.2f}pp  (n_riv={int(n_riv_por_zona[z])})")

    np.savez(
        "defensa_vulnerabilidad.npz",
        Q_riv=Q_riv,
        R_riv=R_riv,
        B_riv=B_riv,
        B_riv_shrunk=B_riv_shrunk,
        Q_liga=Q_liga,
        R_liga=R_liga,
        B_liga=B_liga,
        diff_gol=diff_gol,
        n_riv_por_zona=n_riv_por_zona,
        lambda_shrink=LAMBDA_SHRINK,
    )
    print(f"\nGuardado defensa_vulnerabilidad.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
