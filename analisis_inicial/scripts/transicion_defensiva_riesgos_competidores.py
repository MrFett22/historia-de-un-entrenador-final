"""Correccion (2026-09-26, senalada por auditoria cruzada): el analisis de
transicion defensiva original usaba Kaplan-Meier tratando el remate rival
como censura -- pero es un RIESGO COMPETIDOR (evento informativo, no falta
de informacion). Se reemplaza por incidencia acumulada (Aalen-Johansen),
que sí maneja riesgos competidores correctamente: la probabilidad de
recuperar el balon en el tiempo t, compitiendo explicitamente contra la
probabilidad de que el rival remate primero.

Como lifelines no trae un test de Gray, la comparacion Pachuca vs. liga se
hace con bootstrap por PARTIDO (no por perdida suelta, para respetar la
correlacion dentro de partido) en varios tiempos de corte fijos, con
correccion Benjamini-Hochberg por probar varios tiempos a la vez.
"""

import time
import numpy as np
from lifelines import AalenJohansenFitter
from statsmodels.stats.multitest import multipletests

CHECKPOINTS = [5, 10, 15, 20, 30, 45, 60]
B_REPS = 300
SEED = 97


def cif_en_checkpoints(dur, ev, checkpoints):
    ajf = AalenJohansenFitter()
    ajf.fit(dur, ev, event_of_interest=1)
    return ajf.predict(checkpoints).values


def bootstrap_por_partido(mid, dur, ev, checkpoints, rng, b_reps):
    matches = np.unique(mid)
    n_matches = len(matches)
    idx_por_partido = {m: np.where(mid == m)[0] for m in matches}
    out = np.zeros((b_reps, len(checkpoints)))
    for b in range(b_reps):
        sampled = rng.choice(matches, size=n_matches, replace=True)
        idx = np.concatenate([idx_por_partido[m] for m in sampled])
        out[b] = cif_en_checkpoints(dur[idx], ev[idx], checkpoints)
    return out


def main():
    t0 = time.time()
    d = np.load("transicion_defensiva.npz")
    mid_p, dur_p, ev_p = d["mid_p"], d["dur_p"], d["ev_p"]
    mid_l, dur_l, ev_l = d["mid_l"], d["dur_l"], d["ev_l"]

    print(
        f"Pachuca: n={len(dur_p)}  ({(ev_p == 1).mean() * 100:.1f}% recuperacion, "
        f"{(ev_p == 2).mean() * 100:.1f}% tiro rival, {(ev_p == 0).mean() * 100:.1f}% censura)"
    )
    print(
        f"Liga:    n={len(dur_l)}  ({(ev_l == 1).mean() * 100:.1f}% recuperacion, "
        f"{(ev_l == 2).mean() * 100:.1f}% tiro rival, {(ev_l == 0).mean() * 100:.1f}% censura)"
    )

    cif_p_obs = cif_en_checkpoints(dur_p, ev_p, CHECKPOINTS)
    cif_l_obs = cif_en_checkpoints(dur_l, ev_l, CHECKPOINTS)
    diff_obs = cif_p_obs - cif_l_obs

    print(f"\nIncidencia acumulada de RECUPERACION (compitiendo contra el tiro rival):")
    print(f"{'t(s)':>6} {'Pachuca':>9} {'Liga':>9} {'diff':>9}")
    for i, t in enumerate(CHECKPOINTS):
        print(
            f"{t:>6} {cif_p_obs[i] * 100:>8.1f}% {cif_l_obs[i] * 100:>8.1f}% {diff_obs[i] * 100:>+8.1f}pp"
        )

    print(
        f"\nBootstrap por partido ({B_REPS} repeticiones cada lado, ~{6.5 * B_REPS / 60:.0f} min estimados)..."
    )
    rng = np.random.default_rng(SEED)
    boot_p = bootstrap_por_partido(mid_p, dur_p, ev_p, CHECKPOINTS, rng, B_REPS)
    print(f"  Pachuca listo  ({time.time() - t0:.0f}s)")
    boot_l = bootstrap_por_partido(mid_l, dur_l, ev_l, CHECKPOINTS, rng, B_REPS)
    print(f"  Liga lista  ({time.time() - t0:.0f}s)")

    diff_boot = boot_p - boot_l
    lo = np.percentile(diff_boot, 2.5, axis=0)
    hi = np.percentile(diff_boot, 97.5, axis=0)
    p_boot = np.array(
        [
            min(1.0, 2 * min((diff_boot[:, i] <= 0).mean(), (diff_boot[:, i] >= 0).mean()))
            for i in range(len(CHECKPOINTS))
        ]
    )
    rechaza_bh, q_bh, _, _ = multipletests(p_boot, alpha=0.05, method="fdr_bh")

    print(
        f"\n{'t(s)':>6} {'diff_obs':>10} {'IC 2.5%':>10} {'IC 97.5%':>10} {'p_boot':>8} {'q_BH':>8} {'sig_BH?':>8}"
    )
    n_sig_bh = 0
    for i, t in enumerate(CHECKPOINTS):
        sig = "SI" if rechaza_bh[i] else ""
        if rechaza_bh[i]:
            n_sig_bh += 1
        print(
            f"{t:>6} {diff_obs[i] * 100:>+9.2f}pp {lo[i] * 100:>+9.2f}pp {hi[i] * 100:>+9.2f}pp "
            f"{p_boot[i]:>8.4f} {q_bh[i]:>8.4f} {sig:>8}"
        )

    print(
        f"\nTiempos de corte donde Pachuca recupera mas que la liga, tras BH: {n_sig_bh}/{len(CHECKPOINTS)}"
    )

    np.savez(
        "transicion_defensiva_riesgos_competidores.npz",
        checkpoints=CHECKPOINTS,
        cif_p_obs=cif_p_obs,
        cif_l_obs=cif_l_obs,
        diff_obs=diff_obs,
        lo=lo,
        hi=hi,
        p_boot=p_boot,
        q_bh=q_bh,
        rechaza_bh=rechaza_bh,
    )
    print(
        f"\nGuardado transicion_defensiva_riesgos_competidores.npz ({time.time() - t0:.0f}s total)"
    )


if __name__ == "__main__":
    main()
