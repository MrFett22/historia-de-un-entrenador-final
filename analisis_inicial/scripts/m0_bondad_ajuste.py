"""Bondad de ajuste de M0 (cadena de Markov de orden 1) sobre la duracion de
posesion (numero de pasos hasta absorcion), para decidir si hace falta M2
(memoria). Regla del roadmap: se agrega historia solo si M0 falla esta
prueba -- "se anade historia hasta que pase, y no mas".

Metodo: se toma la Q, R ya ajustadas de Pachuca-Almada (m0_pachuca_almada.npz)
y se simulan posesiones desde ellas (misma distribucion de zona inicial que
las posesiones reales). Se compara la distribucion de duracion real vs.
simulada con un test de Kolmogorov-Smirnov de dos muestras.
"""

import json, time
import numpy as np
from scipy import stats
from m0_cadena_absorbente import zone, possession_to_secuencias, N_ZONES

SEED = 5
N_SIM = 50000
MAX_STEPS = 100


def duraciones_reales():
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = [m["match_id"] for m in almada if m["team"] == "Pachuca"]

    durations, initial_zones = [], []
    for mid in pachuca_ids:
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        events = sorted(events, key=lambda e: e["index"])
        from collections import defaultdict

        poss = defaultdict(list)
        for e in events:
            if e["period"] in (1, 2):
                poss[e["possession"]].append(e)
        for pid, evs in poss.items():
            owner = evs[0]["possession_team"]["name"]
            if owner != "Pachuca":
                continue
            for seq, absorb, xg, primer_evento in possession_to_secuencias(evs, owner):
                durations.append(
                    len(seq)
                )  # pasos: len(seq)-1 transiciones zona-zona + 1 a absorbente
                initial_zones.append(seq[0])
    return np.array(durations), np.array(initial_zones)


def simular(Q, R, initial_zones, rng, n_sim=N_SIM):
    P_full = np.hstack([Q, R])  # (20,24)
    init_probs = np.bincount(initial_zones, minlength=N_ZONES).astype(float)
    init_probs /= init_probs.sum()

    state = rng.choice(N_ZONES, size=n_sim, p=init_probs)
    steps = np.zeros(n_sim, dtype=np.int32)
    absorbed = np.zeros(n_sim, dtype=bool)

    for _ in range(MAX_STEPS):
        active_idx = np.where(~absorbed)[0]
        if len(active_idx) == 0:
            break
        probs = P_full[state[active_idx]]
        cum = np.cumsum(probs, axis=1)
        u = rng.random(len(active_idx))[:, None]
        next_state = (u < cum).argmax(axis=1)
        steps[active_idx] += 1
        newly_abs = next_state >= N_ZONES
        state[active_idx] = np.where(newly_abs, state[active_idx], next_state)
        absorbed[active_idx[newly_abs]] = True

    return steps, 1.0 - absorbed.mean()


def main():
    t0 = time.time()
    print("Recalculando duraciones reales de posesion (Pachuca-Almada)...")
    dur_real, init_zones = duraciones_reales()
    print(
        f"  {len(dur_real):,} posesiones reales. media={dur_real.mean():.2f} "
        f"mediana={np.median(dur_real):.0f} max={dur_real.max()}  ({time.time() - t0:.0f}s)"
    )

    data_m0 = np.load("m0_pachuca_almada.npz")
    Q, R = data_m0["Q"], data_m0["R"]

    rng = np.random.default_rng(SEED)
    print(f"\nSimulando {N_SIM:,} posesiones desde M0 (Q,R)...")
    dur_sim, frac_no_absorbida = simular(Q, R, init_zones, rng)
    print(f"  media={dur_sim.mean():.2f}  mediana={np.median(dur_sim):.0f}  max={dur_sim.max()}")
    if frac_no_absorbida > 0:
        print(
            f"  ADVERTENCIA: {frac_no_absorbida * 100:.2f}% de las cadenas no absorbieron en {MAX_STEPS} pasos"
        )

    ks_stat, p_value = stats.ks_2samp(dur_real, dur_sim)
    print(f"\nKolmogorov-Smirnov (duracion real vs. simulada M0):")
    print(f"  D = {ks_stat:.4f}")
    print(f"  p-valor = {p_value:.4f}")
    if p_value < 0.05:
        print("  -> Se RECHAZA que M0 (orden 1) explique bien la duracion de posesion.")
        print("     Justifica construir M2 (memoria) segun la regla del roadmap.")
    else:
        print("  -> NO se rechaza M0 (orden 1) para duracion de posesion.")
        print("     Segun la regla del roadmap, no hace falta M2 por este criterio.")

    # tabla de percentiles para inspeccion rapida
    for pct in [10, 25, 50, 75, 90, 95, 99]:
        print(
            f"  p{pct}: real={np.percentile(dur_real, pct):.1f}  sim={np.percentile(dur_sim, pct):.1f}"
        )

    np.savez(
        "m0_bondad_ajuste.npz", dur_real=dur_real, dur_sim=dur_sim, ks_stat=ks_stat, p_value=p_value
    )
    print(f"\nGuardado m0_bondad_ajuste.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
