import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe

GRID_X, GRID_Y = 5, 4
data = np.load("m0_pachuca_almada.npz")
t, B, V = data["t"], data["B"], data["V"]

outline = [pe.withStroke(linewidth=2, foreground="black")]


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


def heat(ax, values, title, fmt="{:.3f}", cmap="YlOrRd"):
    draw_pitch(ax)
    vmin, vmax = values.min(), values.max()
    cell_w, cell_h = 120 / GRID_X, 80 / GRID_Y
    cmap_fn = plt.get_cmap(cmap)
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
                fmt.format(v),
                color="black",
                fontsize=9,
                ha="center",
                va="center",
                weight="bold",
                path_effects=[pe.withStroke(linewidth=2, foreground="white")],
            )
    ax.set_title(title, fontsize=11)


fig, axes = plt.subplots(1, 3, figsize=(19, 7))
heat(axes[0], t, "t: acciones esperadas hasta\nque termine la posesion", fmt="{:.1f}", cmap="Blues")
heat(axes[1], B[:, 0], "B[:,G]: probabilidad de\nterminar en gol", fmt="{:.3f}", cmap="Reds")
heat(axes[2], V, "V: valor de zona\n(goles esperados que produce)", fmt="{:.3f}", cmap="YlOrRd")

fig.suptitle(
    f"M0 -- cadena absorbente, Pachuca (Almada), 139 partidos, {int(data['n_transiciones']):,} transiciones",
    fontsize=13,
)
plt.tight_layout()
plt.savefig("m0_pachuca_almada.png", dpi=160, facecolor="white")
print("saved m0_pachuca_almada.png")
