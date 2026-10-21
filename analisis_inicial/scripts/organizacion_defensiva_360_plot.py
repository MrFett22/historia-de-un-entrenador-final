"""Grafica de organizacion defensiva 360: las 5 metricas de
organizacion_defensiva_360.py (Pachuca vs. liga) con su tamano de efecto
(Cohen's d) y significancia BH de organizacion_defensiva_360_significancia.py."""

import numpy as np

d1 = np.load("organizacion_defensiva_360.npz", allow_pickle=True)
arr_p, arr_l, cols = d1["arr_p"], d1["arr_l"], d1["cols"]

d2 = np.load("organizacion_defensiva_360_significancia.npz", allow_pickle=True)
nombres, cohend, rechaza_bh = d2["nombres"], d2["cohend"], d2["rechaza_bh"]

ETIQUETAS = {
    "altura_linea": "Línea defensiva\n(m desde su arco)",
    "ancho_bloque": "Ancho del bloque\n(m)",
    "profundidad_bloque": "Profundidad del bloque\n(m)",
    "area_hull": "Área del bloque\n(m²)",
    "jug_delante_balon": "Jugadores por delante\ndel balón (cont.)",
}

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 5, figsize=(15, 4.5))

for i, name in enumerate(cols[:5]):
    ax = axes[i]
    cp = arr_p[:, i]
    cl = arr_l[:, i]
    cp = cp[~np.isnan(cp)]
    cl = cl[~np.isnan(cl)]
    mean_p, mean_l = cp.mean(), cl.mean()
    sem_p, sem_l = cp.std(ddof=1) / np.sqrt(len(cp)), cl.std(ddof=1) / np.sqrt(len(cl))

    ax.bar(
        [0, 1],
        [mean_p, mean_l],
        yerr=[sem_p, sem_l],
        capsize=4,
        color=["#c8102e", "#555555"],
        width=0.6,
    )
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Pachuca", "Liga"], fontsize=9)
    ax.set_title(ETIQUETAS.get(str(name), str(name)), fontsize=10)

    j = list(nombres).index(name)
    marca = "*" if rechaza_bh[j] else "ns"
    ax.text(
        0.5,
        0.97,
        f"d={cohend[j]:+.3f} {marca}",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        color="#333333",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.suptitle(
    "Organización defensiva (360): Pachuca-Almada vs. Liga MX (sin Pachuca)\n"
    "media ± error estándar; d = Cohen's d, * = sobrevive Benjamini-Hochberg (FDR 5%)",
    fontsize=11,
)
plt.tight_layout(rect=[0, 0, 1, 0.90])
plt.savefig("organizacion_defensiva_360.png", dpi=130)
print("Guardado organizacion_defensiva_360.png")
