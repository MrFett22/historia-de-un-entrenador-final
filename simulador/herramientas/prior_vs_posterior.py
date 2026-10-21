"""Compara f_θ posterior (artefactos/sigmas_posterior.parquet) con el prior Beta(1/2, 1) por componente.

    cd simulador && .venv/bin/python herramientas/prior_vs_posterior.py [carpeta_artefactos]

KS_vs_prior cerca de 0 = los datos casi no movieron la componente respecto del prior.
Nota: sigmas_posterior.parquet trae 1000 muestras remuestreadas de la posterior; el p2.5 puede diferir en
el 3.er decimal de fase_A.json (que usa todas las muestras de NUTS). Las decisiones coinciden.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "artefactos"
s = pd.read_parquet(d / "sigmas_posterior.parquet")
fa = pd.read_json(d / "fase_A.json", orient="records").set_index("componente")
comps = [c for c in s.columns if c not in ("muestra", "parametro")]
P = {p: s[s.parametro == p].sort_values("muestra")[comps].to_numpy() for p in s.parametro.unique()}
th, ph, it = P["s_theta"], P["s_phi"], P["s_int"]
f = th**2 / np.maximum(th**2 + ph**2 + it**2, 1e-300)
prior = stats.beta(0.5, 1)
filas = []
for j, c in enumerate(comps):
    x = f[:, j]
    filas.append(
        dict(
            componente=c,
            p2_5=np.quantile(x, 0.025),
            mediana=np.median(x),
            p97_5=np.quantile(x, 0.975),
            P_menor_005=(x < 0.05).mean(),
            KS_vs_prior=stats.kstest(x, prior.cdf).statistic,
            decision=("tecnico" if np.quantile(x, 0.025) >= 0.05 else "plantel"),
            json_p2_5=fa.loc[c, "f_theta_p2.5"],
            json_dec=fa.loc[c, "decision"],
        )
    )
t = pd.DataFrame(filas).sort_values("KS_vs_prior")
pd.set_option("display.width", 220)
pd.set_option("display.float_format", lambda v: f"{v:.4f}")
print(t.to_string(index=False))
print("\nPrior solo: p2.5=0.0006  mediana=0.25  P(f<0.05)=0.2237")
print("Componentes con p2.5 posterior > 0.0006:", int((t.p2_5 > 0.000625).sum()), "de", len(t))
print(
    "Componentes con P(f<0.05) < 0.2237 (los datos empujaron hacia f alta):",
    int((t.P_menor_005 < 0.2237).sum()),
)
print(
    "Componentes con P(f<0.05) < 0.025 (pasan la regla):", list(t[t.P_menor_005 < 0.025].componente)
)
print("Decisión recomputada == fase_A.json:", bool((t.decision == t.json_dec).all()))
print(
    "KS vs prior: mediana",
    round(t.KS_vs_prior.median(), 3),
    "· mín",
    round(t.KS_vs_prior.min(), 3),
    "· máx",
    round(t.KS_vs_prior.max(), 3),
)
