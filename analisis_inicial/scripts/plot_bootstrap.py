import numpy as np
import matplotlib.pyplot as plt

data = np.load("m0_bootstrap.npz")
t_point, B_point, V_point = data["t_point"], data["B_point"], data["V_point"]
t_ci, B_ci, V_ci = data["t_ci"], data["B_ci"], data["V_ci"]
N_ZONES = len(t_point)
zonas = np.arange(N_ZONES)

fig, axes = plt.subplots(3, 1, figsize=(13, 11), sharex=True)

for ax, point, ci, title, color in [
    (axes[0], t_point, t_ci, "t: acciones esperadas hasta que termine la posesion", "#1f6feb"),
    (axes[1], B_point, B_ci, "B[:,G]: probabilidad de terminar en gol", "#d63031"),
    (axes[2], V_point, V_ci, "V: valor de zona (goles esperados)", "#e67e22"),
]:
    err_low = point - ci[0]
    err_high = ci[1] - point
    ax.errorbar(
        zonas,
        point,
        yerr=[err_low, err_high],
        fmt="o",
        color=color,
        ecolor=color,
        alpha=0.85,
        capsize=3,
        markersize=5,
    )
    ax.set_title(title, fontsize=11)
    ax.grid(alpha=0.3)

axes[-1].set_xlabel("zona (0-19, grid 5x4)")
axes[-1].set_xticks(zonas)

fig.suptitle(
    "M0 con incertidumbre -- bootstrap por partido, B=2000, Pachuca (Almada) 139 partidos",
    fontsize=13,
)
plt.tight_layout()
plt.savefig("m0_bootstrap.png", dpi=150, facecolor="white")
print("saved m0_bootstrap.png")
