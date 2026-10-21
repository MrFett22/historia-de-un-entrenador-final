import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = np.load("kalman_estilo.npz", allow_pickle=True)
y, x_smooth, P_smooth = d["y"], d["x_smooth"], d["P_smooth"]
temporadas = d["temporadas"]

n = len(y)
lo = x_smooth - 1.96 * np.sqrt(P_smooth)
hi = x_smooth + 1.96 * np.sqrt(P_smooth)

fig, ax = plt.subplots(figsize=(12, 5.5))
ax.scatter(range(n), y, color="#c8102e", s=14, alpha=0.5, label="PPDA observado (por partido)")
ax.plot(range(n), x_smooth, color="#1a1a1a", lw=2, label="Nivel de presión suavizado (Kalman)")
ax.fill_between(range(n), lo, hi, color="#1a1a1a", alpha=0.15, label="IC 95% (suavizado)")

# lineas de temporada
temps_unicas = []
for i, t in enumerate(temporadas):
    if t not in temps_unicas:
        temps_unicas.append(t)
        if i > 0:
            ax.axvline(i - 0.5, color="gray", linestyle=":", lw=1)
        ax.text(
            i,
            ax.get_ylim()[1] if False else y.max() + 0.15,
            str(t),
            fontsize=8,
            color="gray",
            rotation=0,
        )

ax.set_xlabel("Partido (orden cronológico, 2021/22 → 2024/25)")
ax.set_ylabel("PPDA (más bajo = presión más intensa)")
ax.set_title(
    "Evolución temporal del estilo de presión de Pachuca-Almada\nFiltro de Kalman (nivel local) sobre PPDA por partido"
)
ax.legend(loc="upper right", fontsize=9)
ax.invert_yaxis()  # PPDA mas bajo = mas presion, invertir para que "arriba" = mas intenso
plt.tight_layout()
plt.savefig("kalman_estilo.png", dpi=150, facecolor="white")
print("saved kalman_estilo.png")
