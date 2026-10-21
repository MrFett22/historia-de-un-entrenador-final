"""Grafica del desglose de did_sustituciones_desglose.py: DiD (valor
generado extra en los 15 min tras el cambio, neto de un control) por
marcador al momento del cambio y por tipo de sustitucion."""

import numpy as np

d = np.load("did_sustituciones_desglose.npz", allow_pickle=True)

ETIQUETAS = {
    "perdiendo": "Perdiendo",
    "empatado": "Empatado",
    "ganando": "Ganando",
    "ofensiva": "Ofensiva\n(entra más\nadelantado)",
    "defensiva": "Defensiva\n(entra más\natrasado)",
    "lateral": "Lateral\n(misma\nposición)",
}
TITULOS = {
    "marcador": "Por marcador al momento del cambio\n(control emparejado por marcador)",
    "tipo": "Por tipo de sustitución\n(control = pool completo)",
}

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))

for col, eje in enumerate(["marcador", "tipo"]):
    ax = axes[col]
    cats = d[f"{eje}_categorias"]
    n_t = d[f"{eje}_n_t"]
    did = d[f"{eje}_did"]
    lo = d[f"{eje}_lo"]
    hi = d[f"{eje}_hi"]
    rechaza_bh = d[f"{eje}_rechaza_bh"]

    x = np.arange(len(cats))
    colores = ["#c8102e" if r else "#999999" for r in rechaza_bh]
    for i in range(len(cats)):
        yerr_i = [[did[i] - lo[i]], [hi[i] - did[i]]]
        ax.errorbar(
            x[i],
            did[i],
            yerr=yerr_i,
            fmt="o",
            markersize=9,
            capsize=5,
            elinewidth=2,
            color=colores[i],
        )
    ax.axhline(0, color="#333333", linewidth=1, linestyle="--")

    for i, cat in enumerate(cats):
        marca = "*  sobrevive BH" if rechaza_bh[i] else "ns"
        ax.text(
            x[i],
            hi[i] + 0.002,
            f"{did[i]:+.4f}\n{marca}\n(n={n_t[i]})",
            ha="center",
            va="bottom",
            fontsize=8.5,
            color="#222222",
        )

    ax.set_xticks(x)
    ax.set_xticklabels([ETIQUETAS.get(str(c), str(c)) for c in cats], fontsize=9.5)
    ax.set_xlim(x[0] - 0.6, x[-1] + 0.6)
    ax.set_title(TITULOS[eje], fontsize=10.5)
    ax.set_ylim(min(lo.min(), 0) - 0.006, max(hi.max(), 0) + 0.013)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if col == 0:
        ax.set_ylabel(
            "DiD: valor extra generado por minuto\nen los 15' tras el cambio (neto de control)",
            fontsize=9.5,
        )

fig.suptitle(
    "Impacto de las sustituciones de Almada en Pachuca: el promedio general es débil,\n"
    "pero las sustituciones OFENSIVAS sí muestran un efecto real",
    fontsize=11.5,
)
plt.tight_layout(rect=[0, 0, 1, 0.90])
plt.savefig("did_sustituciones_desglose.png", dpi=130)
print("Guardado did_sustituciones_desglose.png")
