"""Grafica de balon_parado_desglose.py: tasa de 'termina en tiro' por
tipo de balon parado (corner, tiro libre cerca del area, saque de banda
muy ofensivo), ofensivo y defensivo, Pachuca vs. liga."""

import numpy as np

d = np.load("balon_parado_desglose.npz", allow_pickle=True)

TIPOS = ["corner", "tiro_libre_cerca_area", "saque_banda_ofensivo"]
LADOS = ["ofensivo", "defensivo"]
TITULOS_TIPO = {
    "corner": "Tiro de esquina",
    "tiro_libre_cerca_area": "Tiro libre cerca\ndel área (x≥80)",
    "saque_banda_ofensivo": "Saque de banda\nmuy ofensivo (x≥80)",
}
TITULOS_LADO = {
    "ofensivo": "OFENSIVO (balón parado propio)",
    "defensivo": "DEFENSIVO (balón parado del rival)",
}

etiquetas = d["tiro_etiquetas"]
idx_por_clave = {e: i for i, e in enumerate(etiquetas)}

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 3, figsize=(14, 9.5))
bar_p = bar_l = None

for row, lado in enumerate(LADOS):
    for col, tipo in enumerate(TIPOS):
        ax = axes[row, col]
        clave = f"{tipo}_{lado}"
        i = idx_por_clave[clave]

        n_p, t_p = float(d["tiro_n_p"][i]), d["tiro_tasa_p"][i]
        n_l, t_l = float(d["tiro_n_l"][i]), d["tiro_tasa_l"][i]
        rechaza_bh = d["tiro_rechaza_bh"][i]
        n_p_gol, t_p_gol = float(d["gol_n_p"][i]), d["gol_tasa_p"][i]
        t_l_gol = d["gol_tasa_l"][i]
        rechaza_bh_gol = d["gol_rechaza_bh"][i]

        sem_p = np.sqrt(t_p * (1 - t_p) / n_p)
        sem_l = np.sqrt(t_l * (1 - t_l) / n_l)
        bar_p = ax.bar(0, t_p * 100, width=0.6, yerr=sem_p * 100, capsize=4, color="#c8102e")
        bar_l = ax.bar(1, t_l * 100, width=0.6, yerr=sem_l * 100, capsize=4, color="#555555")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Pachuca", "Liga"], fontsize=9.5)

        diff_pp = (t_p - t_l) * 100
        marca = "*" if rechaza_bh else "ns"
        diff_gol_pp = (t_p_gol - t_l_gol) * 100
        marca_gol = "*" if rechaza_bh_gol else "ns"
        ymax = max((t_p + sem_p), (t_l + sem_l)) * 100
        ax.text(
            0.5,
            ymax * 1.05,
            f"tiro: {diff_pp:+.1f}pp {marca}",
            transform=ax.transData,
            ha="center",
            fontsize=9,
            color="#222222",
        )
        ax.text(
            0.5,
            ymax * 1.18,
            f"gol: {diff_gol_pp:+.1f}pp {marca_gol}",
            transform=ax.transData,
            ha="center",
            fontsize=8,
            color="#666666",
        )
        ax.text(
            0.5,
            ymax * 1.34,
            f"n Pachuca={n_p:.0f}",
            transform=ax.transData,
            ha="center",
            fontsize=7.5,
            color="#888888",
        )

        ax.set_ylim(0, ymax * 1.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if col == 0:
            ax.set_ylabel(f"{TITULOS_LADO[lado]}\n% termina en tiro", fontsize=9.5)
        if row == 0:
            ax.set_title(TITULOS_TIPO[tipo], fontsize=10.5)

fig.suptitle(
    "Balón parado por tipo: Pachuca-Almada vs. Liga MX\n"
    "barras = tasa observada ± error binomial (* = sobrevive Benjamini-Hochberg dentro de su métrica)",
    fontsize=11,
)
plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig("balon_parado_desglose.png", dpi=130)
print("Guardado balon_parado_desglose.png")
