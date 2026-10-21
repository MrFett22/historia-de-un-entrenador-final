"""Kaplan-Meier + log-rank sobre transicion_defensiva.npz: recupera Pachuca
el balon mas rapido que el promedio de liga tras una perdida?
"""

import numpy as np
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

data = np.load("transicion_defensiva.npz")
dur_p, ev_p, dur_l, ev_l = data["dur_p"], data["ev_p"], data["dur_l"], data["ev_l"]

kmf_p = KaplanMeierFitter()
kmf_p.fit(dur_p, event_observed=ev_p, label="Pachuca-Almada")
kmf_l = KaplanMeierFitter()
kmf_l.fit(dur_l, event_observed=ev_l, label="Liga (sin Pachuca)")

print("Mediana de tiempo de recuperacion (KM, ajustado por censura):")
print(f"  Pachuca: {kmf_p.median_survival_time_:.1f}s")
print(f"  Liga:    {kmf_l.median_survival_time_:.1f}s")

for t in [5, 10, 15, 20, 30, 45, 60]:
    sp = kmf_p.survival_function_at_times(t).values[0]
    sl = kmf_l.survival_function_at_times(t).values[0]
    print(
        f"  P(no recuperado a los {t:>2}s): Pachuca={sp * 100:5.1f}%  Liga={sl * 100:5.1f}%  diff={(sp - sl) * 100:+.1f}pp"
    )

result = logrank_test(dur_p, dur_l, event_observed_A=ev_p, event_observed_B=ev_l)
print(
    f"\nLog-rank test (Pachuca vs. liga): estadistico={result.test_statistic:.2f}  p-valor={result.p_value:.6f}"
)
if result.p_value < 0.05:
    print("  -> Diferencia significativa en la velocidad de recuperacion del balon tras perdida.")
else:
    print("  -> No hay diferencia significativa.")

np.savez(
    "transicion_defensiva_km.npz",
    mediana_pachuca=kmf_p.median_survival_time_,
    mediana_liga=kmf_l.median_survival_time_,
    logrank_stat=result.test_statistic,
    logrank_p=result.p_value,
)
print("\nGuardado transicion_defensiva_km.npz")

# grafica
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5))
kmf_p.plot_survival_function(ax=ax, color="#c8102e")
kmf_l.plot_survival_function(ax=ax, color="#555555")
ax.set_xlabel("Segundos desde la pérdida")
ax.set_ylabel("P(balón aún no recuperado)")
ax.set_title(
    "Transición defensiva: tiempo hasta recuperar el balón\nPachuca-Almada vs. Liga MX (sin Pachuca)"
)
ax.set_xlim(0, 90)
ax.axvline(10, color="gray", linestyle=":", linewidth=1)
ax.text(10.5, 0.95, "10s (ventana de\ntransición defensiva)", fontsize=8, color="gray")
plt.tight_layout()
plt.savefig("transicion_defensiva_km.png", dpi=130)
print("Guardado transicion_defensiva_km.png")
