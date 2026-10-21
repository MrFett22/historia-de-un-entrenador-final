import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = np.load("simulador_validado.npz")
goles_reales = d["goles_reales"]
una_rep = d["goles_sim_todas_reps"][:, 0]

bins = np.arange(0, max(goles_reales.max(), una_rep.max()) + 2) - 0.5
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(
    goles_reales,
    bins=bins,
    alpha=0.55,
    label=f"Real (n={len(goles_reales)}, media={goles_reales.mean():.2f})",
    color="#c8102e",
)
ax.hist(
    una_rep,
    bins=bins,
    alpha=0.55,
    label=f"Simulado -- una corrida (media={una_rep.mean():.2f})",
    color="#1a1a1a",
)
ax.set_xlabel("Goles de Pachuca en el partido")
ax.set_ylabel("Número de partidos")
ax.set_title(
    "Simulador validado: goles reales vs. simulados por partido\nKS D=0.079, p=0.78 (no distinguible de la distribución real)"
)
ax.legend()
plt.tight_layout()
plt.savefig("simulador_validado.png", dpi=150, facecolor="white")
print("saved simulador_validado.png")
