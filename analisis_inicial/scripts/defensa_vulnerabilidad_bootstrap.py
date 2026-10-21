"""Bootstrap por partido (B=2000) para la incertidumbre de la vulnerabilidad
defensiva de Pachuca por zona (diff_gol = B_gol_riv_shrunk - B_gol_liga).
Se remuestrean los 139 partidos de Pachuca-Almada; B_liga (1564 partidos de
referencia) se deja fija -- su propia incertidumbre es mucho menor por
tener ~11x mas partidos.
"""

import json, time
import numpy as np
from statsmodels.stats.multitest import multipletests
from m0_cadena_absorbente import process_match_for_team, build_QR, solve_absorbing, N_ZONES

LAMBDA_SHRINK = 1750
B_REPS = 2000
SEED = 17


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = [m["match_id"] for m in almada if m["team"] == "Pachuca"]

    all_matches_meta = {}
    for sid in [351, 318, 317, 281, 235, 108]:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    # trans por partido (lista de listas), para remuestreo por bloque
    trans_por_partido = []
    for mid in pachuca_ids:
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        home = meta["home_team"]["home_team_name"]
        away = meta["away_team"]["away_team_name"]
        rival_name = away if home == "Pachuca" else home
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        trans, _, _ = process_match_for_team(events, rival_name)
        trans_por_partido.append(trans)
    print(f"Partidos cargados: {len(trans_por_partido)}  ({time.time() - t0:.0f}s)")

    data_vuln = np.load("defensa_vulnerabilidad.npz")
    B_liga = data_vuln["B_liga"]

    rng = np.random.default_rng(SEED)
    diff_boot = np.zeros((B_REPS, N_ZONES))
    n_partidos = len(trans_por_partido)
    for b in range(B_REPS):
        idx = rng.integers(0, n_partidos, size=n_partidos)
        trans_b = [t for i in idx for t in trans_por_partido[i]]
        Q_b, R_b, counts_b = build_QR(trans_b)
        _, _, B_b = solve_absorbing(Q_b, R_b)
        n_por_zona = counts_b.sum(axis=1)
        B_shrunk_b = np.zeros(N_ZONES)
        for z in range(N_ZONES):
            n = n_por_zona[z]
            B_shrunk_b[z] = (n * B_b[z, 0] + LAMBDA_SHRINK * B_liga[z, 0]) / (n + LAMBDA_SHRINK)
        diff_boot[b] = B_shrunk_b - B_liga[:, 0]
        if (b + 1) % 500 == 0:
            print(f"  {b + 1}/{B_REPS}  ({time.time() - t0:.0f}s)")

    lo = np.percentile(diff_boot, 2.5, axis=0)
    hi = np.percentile(diff_boot, 97.5, axis=0)
    diff_obs = data_vuln["diff_gol"]

    # p-valor bootstrap por zona (metodo de reflexion): 2*min(P(diff_boot<=0), P(diff_boot>=0)),
    # tope en 1. Es la version con p-valor de la misma prueba de "IC 95% no cruza 0".
    p_boot = np.array(
        [
            min(1.0, 2 * min((diff_boot[:, z] <= 0).mean(), (diff_boot[:, z] >= 0).mean()))
            for z in range(N_ZONES)
        ]
    )

    # correccion por comparaciones multiples (Benjamini-Hochberg, FDR=0.05) sobre las 20 zonas --
    # con 20 pruebas independientes al 5%, se espera ~1 falso positivo por puro azar sin corregir.
    rechaza_bh, q_bh, _, _ = multipletests(p_boot, alpha=0.05, method="fdr_bh")

    print(
        f"\n{'zona':>5} {'diff_obs':>10} {'IC 2.5%':>10} {'IC 97.5%':>10} {'p_boot':>8} {'q_BH':>8} {'sig?':>6} {'sig_BH?':>8}"
    )
    n_sig, n_sig_bh = 0, 0
    for z in range(N_ZONES):
        sig = "SI" if (lo[z] > 0 or hi[z] < 0) else ""
        sig_bh = "SI" if rechaza_bh[z] else ""
        if sig:
            n_sig += 1
        if rechaza_bh[z]:
            n_sig_bh += 1
        print(
            f"{z:>5} {diff_obs[z] * 100:>+9.2f}pp {lo[z] * 100:>+9.2f}pp {hi[z] * 100:>+9.2f}pp "
            f"{p_boot[z]:>8.4f} {q_bh[z]:>8.4f} {sig:>6} {sig_bh:>8}"
        )

    print(
        f"\nZonas con diferencia estadisticamente distinguible de cero (IC 95% no cruza 0, SIN corregir): {n_sig}/{N_ZONES}"
    )
    print(f"Zonas que sobreviven la correccion Benjamini-Hochberg (FDR=0.05): {n_sig_bh}/{N_ZONES}")

    np.savez(
        "defensa_vulnerabilidad_bootstrap.npz",
        diff_boot=diff_boot,
        lo=lo,
        hi=hi,
        p_boot=p_boot,
        q_bh=q_bh,
        rechaza_bh=rechaza_bh,
    )
    print(f"\nGuardado defensa_vulnerabilidad_bootstrap.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
