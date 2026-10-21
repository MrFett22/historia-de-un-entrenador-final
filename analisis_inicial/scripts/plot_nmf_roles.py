import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe

GRID_X, GRID_Y = 5, 4
data = np.load("nmf_roles.npz", allow_pickle=True)
H_norm = data["H_norm"]
K = H_norm.shape[0]

ETIQUETAS = {
    0: "Rol 0: banda ancha ofensiva\n(laterales que se proyectan)",
    1: "Rol 1: portero",
    2: "Rol 2: costado izquierdo",
    3: "Rol 3: ataque central",
    4: "Rol 4: zaga y mediocampo\ndefensivo (bloque profundo)",
}


def draw_pitch(ax):
    ax.set_facecolor("#0b6e2f")
    ax.add_patch(patches.Rectangle((0, 0), 120, 80, fill=False, color="white", lw=2))
    ax.plot([60, 60], [0, 80], color="white", lw=1.0, alpha=0.5)
    for x0 in [0, 120]:
        ax.add_patch(
            patches.Rectangle(
                (x0 - 18 if x0 else 0, 18), 18, 44, fill=False, color="white", lw=1.0, alpha=0.5
            )
        )
    ax.set_xlim(-2, 122)
    ax.set_ylim(-2, 82)
    ax.set_aspect("equal")
    ax.axis("off")


def heat(ax, values, title):
    draw_pitch(ax)
    vmin, vmax = 0, values.max()
    cell_w, cell_h = 120 / GRID_X, 80 / GRID_Y
    cmap_fn = plt.get_cmap("YlOrRd")
    for zx in range(GRID_X):
        for zy in range(GRID_Y):
            z = zx * GRID_Y + zy
            v = values[z]
            norm = (v - vmin) / (vmax - vmin + 1e-9)
            color = cmap_fn(norm)
            cx, cy = zx * cell_w, zy * cell_h
            ax.add_patch(
                patches.Rectangle(
                    (cx, cy), cell_w, cell_h, facecolor=color, alpha=0.85, edgecolor="white", lw=1
                )
            )
            ax.text(
                cx + cell_w / 2,
                cy + cell_h / 2,
                f"{v * 100:.0f}%",
                color="black",
                fontsize=8,
                ha="center",
                va="center",
                weight="bold",
                path_effects=[pe.withStroke(linewidth=2, foreground="white")],
            )
    ax.set_title(title, fontsize=10)


fig, axes = plt.subplots(1, K, figsize=(5 * K, 5.5))
for k in range(K):
    heat(axes[k], H_norm[k], ETIQUETAS.get(k, f"Rol {k}"))

fig.suptitle(
    "NMF de roles: perfil de zona de cada rol latente (139 partidos de Pachuca-Almada)\n"
    "arco de Pachuca a la izquierda (x=0), arco rival a la derecha (x=120)",
    fontsize=12,
)
plt.tight_layout()
plt.savefig("nmf_roles.png", dpi=150, facecolor="white")
print("saved nmf_roles.png")
