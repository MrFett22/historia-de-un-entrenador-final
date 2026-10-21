"""Grafica de incidencia acumulada (Aalen-Johansen) para transicion
defensiva -- reemplaza transicion_defensiva_km.png, que graficaba 1-KM
tratando el tiro rival como censura (ver correccion en FRAMEWORK.md,
seccion "Correcciones de inferencia (2026-09-26)")."""

import numpy as np
from lifelines import AalenJohansenFitter

d = np.load("transicion_defensiva.npz")
dur_p, ev_p, dur_l, ev_l = d["dur_p"], d["ev_p"], d["dur_l"], d["ev_l"]

ajf_p = AalenJohansenFitter()
ajf_p.fit(dur_p, ev_p, event_of_interest=1)
ajf_l = AalenJohansenFitter()
ajf_l.fit(dur_l, ev_l, event_of_interest=1)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5))
ajf_p.plot(ax=ax, color="#c8102e", label="Pachuca-Almada")
ajf_l.plot(ax=ax, color="#555555", label="Liga (sin Pachuca)")
ax.set_xlabel("Segundos desde la pérdida")
ax.set_ylabel("Incidencia acumulada de recuperación")
ax.set_title(
    "Transición defensiva: incidencia acumulada de recuperación\n"
    "(compitiendo contra el tiro rival) -- Pachuca-Almada vs. Liga MX"
)
ax.set_xlim(0, 90)
ax.axvline(10, color="gray", linestyle=":", linewidth=1)
ax.text(10.5, 0.05, "10s (ventana de\ntransición defensiva)", fontsize=8, color="gray")
ax.legend(loc="lower right")
plt.tight_layout()
plt.savefig("transicion_defensiva_riesgos_competidores.png", dpi=130)
print("Guardado transicion_defensiva_riesgos_competidores.png")
