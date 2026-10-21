"""Correccion por comparaciones multiples (Benjamini-Hochberg) para las 5
metricas de organizacion defensiva 360 (organizacion_defensiva_360.py).
Con un n tan grande (cientos de miles de frames), casi cualquier
diferencia sale "significativa" por construccion -- lo que importa es si
sobrevive la correccion por probar 5 metricas a la vez, y el tamano del
efecto (Cohen's d), no solo el p-valor.
"""

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

d = np.load("organizacion_defensiva_360.npz", allow_pickle=True)
arr_p, arr_l, cols = d["arr_p"], d["arr_l"], d["cols"]

nombres, diffs, cohend_list, p_list = [], [], [], []
for i, name in enumerate(cols[:5]):
    cp = arr_p[:, i]
    cl = arr_l[:, i]
    cp = cp[~np.isnan(cp)]
    cl = cl[~np.isnan(cl)]
    diff = cp.mean() - cl.mean()
    sd_pooled = np.sqrt(
        ((len(cp) - 1) * cp.var(ddof=1) + (len(cl) - 1) * cl.var(ddof=1)) / (len(cp) + len(cl) - 2)
    )
    cohend = diff / sd_pooled
    se = np.sqrt(cp.var(ddof=1) / len(cp) + cl.var(ddof=1) / len(cl))
    z = diff / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    nombres.append(name)
    diffs.append(diff)
    cohend_list.append(cohend)
    p_list.append(p)

p_arr = np.array(p_list)
rechaza_bh, q_bh, _, _ = multipletests(p_arr, alpha=0.05, method="fdr_bh")

print(f"{'metrica':>20} {'diff':>10} {'cohen_d':>9} {'p':>10} {'q_BH':>10} {'sig_BH?':>8}")
n_sig_bh = 0
for i, name in enumerate(nombres):
    sig = "SI" if rechaza_bh[i] else ""
    if rechaza_bh[i]:
        n_sig_bh += 1
    print(
        f"{name:>20} {diffs[i]:>+10.3f} {cohend_list[i]:>+9.4f} {p_list[i]:>10.2e} {q_bh[i]:>10.2e} {sig:>8}"
    )

print(f"\nMetricas que sobreviven Benjamini-Hochberg (FDR=0.05): {n_sig_bh}/5")
print("Nota: con n tan grande, la significancia estadistica esta casi garantizada -- ")
print("la lectura relevante es el tamano del efecto (Cohen's d), reportado arriba.")

np.savez(
    "organizacion_defensiva_360_significancia.npz",
    nombres=nombres,
    diffs=diffs,
    cohend=cohend_list,
    p=p_list,
    q_bh=q_bh,
    rechaza_bh=rechaza_bh,
)
print("\nGuardado organizacion_defensiva_360_significancia.npz")
