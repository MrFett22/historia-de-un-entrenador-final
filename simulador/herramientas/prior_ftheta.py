"""p2.5 de f_θ bajo el prior SOLO (sin datos). Auditoría de la regla de atribución (spec 04 §2).

Según estimacion/cruzado.py:69-72 y :58-60:
    s_theta, s_phi, s_int ~ HalfNormal(2·sd(y)) independientes
    f_θ = s_theta² / (s_theta² + s_phi² + s_int²)
La escala 2·sd(y) se cancela en el cociente, así que el resultado no depende de los datos.
Analíticamente f_θ ~ Beta(1/2, 1): CDF(x) = √x → p2.5 = 0.025² = 0.000625.

    cd simulador && .venv/bin/python herramientas/prior_ftheta.py
"""

import numpy as np
from scipy import stats

Q = [0.025, 0.05, 0.5, 0.95, 0.975]


def mc(escala, n_total=20_000_000, trozo=2_000_000, semilla=20261008):
    rng = np.random.default_rng(semilla)
    out = []
    for _ in range(n_total // trozo):
        s = np.abs(rng.normal(0.0, escala, size=(3, trozo)))  # HalfNormal(sigma=escala)
        out.append(s[0] ** 2 / (s**2).sum(0))
    return np.concatenate(out)


if __name__ == "__main__":
    for sd in (0.05, 1.0, 37.0):  # 2·sd(y) debe cancelarse
        f = mc(2 * sd)
        q = np.quantile(f, Q)
        ee = np.sqrt(0.025 * 0.975 / len(f)) / stats.beta(0.5, 1).pdf(q[0])
        print(
            f"2·sd(y)={2 * sd:7.3f}  N={len(f):,}  p2.5={q[0]:.6f} (EE≈{ee:.1e})  p5={q[1]:.5f}  "
            f"mediana={q[2]:.4f}  p95={q[3]:.4f}  p97.5={q[4]:.4f}  P(f<0.05)={np.mean(f < 0.05):.4f}"
        )
    b = stats.beta(0.5, 1)
    print(
        f"analítico Beta(1/2,1): p2.5={b.ppf(0.025):.6f}  p5={b.ppf(0.05):.5f}  mediana={b.ppf(0.5):.4f}  "
        f"p95={b.ppf(0.95):.4f}  p97.5={b.ppf(0.975):.4f}  P(f<0.05)={b.cdf(0.05):.4f}"
    )
    print(
        f"regla: 'plantel' si p2.5 < 0.05 → bajo el prior solo p2.5 = {np.quantile(f, 0.025):.5f} → plantel"
    )
