"""Grafica de contexto_patrones.py: como cambian dos metricas de Pachuca-
Almada (termina en tiro, pierde el balon) segun marcador, minuto y fuerza
del rival, comparado contra la liga. Barras = tasa observada (Pachuca vs.
liga); el error mostrado es el binomial estandar de cada barra (para
lectura visual rapida); la significancia real (bootstrap por partido +
Benjamini-Hochberg) viene de contexto_patrones.py y se anota arriba de
cada par."""

import numpy as np

d = np.load("contexto_patrones.npz", allow_pickle=True)

EJES = ["marcador", "minuto", "rival"]
METRICAS = ["tiro", "perdida"]
TITULOS_EJE = {"marcador": "Marcador", "minuto": "Minuto", "rival": "Fuerza del rival"}
TITULOS_METRICA = {"tiro": "Termina en tiro\n(gol o remate)", "perdida": "Pierde el balón"}
ETIQUETAS_CAT = {
    "perdiendo": "Perdiendo",
    "empatado": "Empatado",
    "ganando": "Ganando",
    "0-30": "0-30'",
    "30-60": "30-60'",
    "60-90": "60-90'",
    "rival_mas_fuerte": "Rival más\nfuerte",
    "rival_mas_debil_o_similar": "Rival más\ndébil/similar",
}

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 3, figsize=(14, 9))
bar_p = bar_l = None

for row, metrica in enumerate(METRICAS):
    for col, eje in enumerate(EJES):
        ax = axes[row, col]
        key = f"{eje}_{metrica}"
        cats = d[f"{key}_categorias"]
        n_p, t_p = d[f"{key}_n_p"].astype(float), d[f"{key}_tasa_p"]
        n_l, t_l = d[f"{key}_n_l"].astype(float), d[f"{key}_tasa_l"]
        rechaza_bh = d[f"{key}_rechaza_bh"]

        x = np.arange(len(cats))
        w = 0.35
        sem_p = np.sqrt(t_p * (1 - t_p) / n_p)
        sem_l = np.sqrt(t_l * (1 - t_l) / n_l)
        bar_p = ax.bar(
            x - w / 2,
            t_p * 100,
            width=w,
            yerr=sem_p * 100,
            capsize=3,
            color="#c8102e",
            label="Pachuca",
        )
        bar_l = ax.bar(
            x + w / 2,
            t_l * 100,
            width=w,
            yerr=sem_l * 100,
            capsize=3,
            color="#555555",
            label="Liga",
        )

        ymax = max((t_p + sem_p).max(), (t_l + sem_l).max()) * 100
        for i, cat in enumerate(cats):
            diff_pp = (t_p[i] - t_l[i]) * 100
            marca = "*" if rechaza_bh[i] else "ns"
            ax.text(
                x[i],
                ymax * 1.08,
                f"{diff_pp:+.1f}pp {marca}",
                ha="center",
                fontsize=8.5,
                color="#222222",
            )

        ax.set_xticks(x)
        ax.set_xticklabels([ETIQUETAS_CAT.get(str(c), str(c)) for c in cats], fontsize=9)
        ax.set_ylim(0, ymax * 1.22)
        ax.set_xlim(x[0] - 0.75, x[-1] + 0.75)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if col == 0:
            ax.set_ylabel(f"{TITULOS_METRICA[metrica]}\n(% de secuencias)", fontsize=9.5)
        if row == 0:
            ax.set_title(TITULOS_EJE[eje], fontsize=11)
fig.suptitle(
    "Pachuca-Almada vs. Liga MX: cómo cambian los patrones de juego según el contexto\n"
    "barras = tasa observada ± error binomial; etiqueta = diferencia Pachuca−liga\n"
    "(* = sobrevive Benjamini-Hochberg dentro de su eje, ns = no significativo)",
    fontsize=10.5,
    y=0.99,
)
fig.legend(
    [bar_p, bar_l],
    ["Pachuca", "Liga"],
    loc="upper center",
    bbox_to_anchor=(0.5, 0.855),
    fontsize=9.5,
    framealpha=0.9,
    ncol=2,
)
plt.tight_layout(rect=[0, 0, 1, 0.86])
plt.savefig("contexto_patrones.png", dpi=130)
print("Guardado contexto_patrones.png")
