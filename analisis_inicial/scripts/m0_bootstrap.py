import json, time, sys
import numpy as np

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import process_match_for_team, build_QR, solve_absorbing, N_ZONES

B_REPS = 2000
SEED = 11


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = [m["match_id"] for m in almada if m["team"] == "Pachuca"]

    print(f"Cargando transiciones por partido ({len(pachuca_ids)} partidos)...")
    per_match_trans = []
    per_match_xg = []
    for mid in pachuca_ids:
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        trans, _, xg = process_match_for_team(events, "Pachuca")
        per_match_trans.append(trans)
        per_match_xg.append(xg)

    n_matches = len(per_match_trans)
    rng = np.random.default_rng(SEED)

    t_samples = np.zeros((B_REPS, N_ZONES))
    Bgoal_samples = np.zeros((B_REPS, N_ZONES))
    V_samples = np.zeros((B_REPS, N_ZONES))

    print(f"Bootstrap por partido, B={B_REPS}...")
    for b in range(B_REPS):
        idx = rng.integers(0, n_matches, size=n_matches)
        trans_b = []
        xg_b = []
        for i in idx:
            trans_b.extend(per_match_trans[i])
            xg_b.extend(per_match_xg[i])
        Q, R, counts = build_QR(trans_b)
        try:
            N, t, Bp = solve_absorbing(Q, R)
        except np.linalg.LinAlgError:
            continue
        x_bar = np.mean(xg_b) if xg_b else 0.0
        r_vec = np.array([1.0, x_bar, 0.0, 0.0])
        V = Bp @ r_vec
        t_samples[b] = t
        Bgoal_samples[b] = Bp[:, 0]
        V_samples[b] = V
        if (b + 1) % 500 == 0:
            print(f"  {b + 1}/{B_REPS} ({time.time() - t0:.0f}s)")

    def ci(samples):
        return np.percentile(samples, [2.5, 97.5], axis=0)

    t_ci = ci(t_samples)
    B_ci = ci(Bgoal_samples)
    V_ci = ci(V_samples)

    data0 = np.load("m0_pachuca_almada.npz")
    t_point, B_point, V_point = data0["t"], data0["B"][:, 0], data0["V"]

    print("\nZona | t (punto, IC95%) | B_gol (punto, IC95%) | V (punto, IC95%)")
    for z in range(N_ZONES):
        print(
            f"z{z:>2}: t={t_point[z]:.2f} [{t_ci[0, z]:.2f},{t_ci[1, z]:.2f}]  "
            f"Bgol={B_point[z]:.4f} [{B_ci[0, z]:.4f},{B_ci[1, z]:.4f}]  "
            f"V={V_point[z]:.4f} [{V_ci[0, z]:.4f},{V_ci[1, z]:.4f}]"
        )

    np.savez(
        "m0_bootstrap.npz",
        t_ci=t_ci,
        B_ci=B_ci,
        V_ci=V_ci,
        t_point=t_point,
        B_point=B_point,
        V_point=V_point,
        t_samples=t_samples,
        Bgoal_samples=Bgoal_samples,
        V_samples=V_samples,
    )
    print(f"\nGuardado m0_bootstrap.npz ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
