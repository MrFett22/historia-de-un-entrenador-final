"""Test de razon de verosimilitudes para M1: hay efecto especifico de Pachuca (delta)?

H0 (modelo restringido, "pooled"): solo alpha_ij (onehot origen) + beta_j (contexto liga).
H1 (modelo completo, ya ajustado en m1_modelo.py): alpha_ij + beta_j + delta_j (interaccion
con is_pachuca).

G2 = 2*(loglik_H1 - loglik_H0), observado sobre los datos reales.

Nula por bootstrap: bajo H0 no existe efecto especifico de ningun equipo. Para construir la
distribucion nula de G2 se re-muestrean PARTIDOS completos con reemplazo (bloque, respeta
correlacion dentro de partido) y se simula el destino de cada fila desde las probabilidades
ajustadas por el modelo restringido (generativo bajo H0), manteniendo las X y la etiqueta
is_pachuca reales. Se reajustan ambos modelos (restringido y completo) sobre cada dataset
simulado y se calcula G2_boot. p = P(G2_boot >= G2_observado).
"""

import time
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression

N_ZONES = 20
N_ABS = 4
N_CLASSES = N_ZONES + N_ABS
X_NAMES = ["marcador", "periodo_frac", "local", "elo_diff"]
N_BOOT = 30
SEED = 7


def build_features_full(origen, x, is_pachuca):
    n = len(origen)
    onehot = sparse.csr_matrix((np.ones(n), (np.arange(n), origen)), shape=(n, N_ZONES))
    x_int = x * is_pachuca[:, None]
    return sparse.hstack([onehot, sparse.csr_matrix(x), sparse.csr_matrix(x_int)]).tocsr()


def build_features_restringido(origen, x):
    n = len(origen)
    onehot = sparse.csr_matrix((np.ones(n), (np.arange(n), origen)), shape=(n, N_ZONES))
    return sparse.hstack([onehot, sparse.csr_matrix(x)]).tocsr()


def fit_and_loglik(X, y, n_classes_dataset):
    model = LogisticRegression(solver="lbfgs", max_iter=300, C=10.0)
    model.fit(X, y)
    proba = model.predict_proba(X)  # (n, n_clases_presentes) en orden model.classes_
    # log-verosimilitud: log p_i(y_i)
    class_to_col = {c: j for j, c in enumerate(model.classes_)}
    cols = np.array([class_to_col[val] for val in y])
    p_true = proba[np.arange(len(y)), cols]
    p_true = np.clip(p_true, 1e-12, 1.0)
    ll = np.log(p_true).sum()
    return model, ll


def simulate_y_bajo_h0(model_h0, X_h0, rng):
    proba = model_h0.predict_proba(X_h0)
    classes = model_h0.classes_
    cum = np.cumsum(proba, axis=1)
    u = rng.random(X_h0.shape[0])[:, None]
    idx = (u < cum).argmax(axis=1)
    return classes[idx]


def main():
    t0 = time.time()
    data = np.load("m1_dataset.npz", allow_pickle=True)
    origen = data["origen"].astype(np.int64)
    destino = data["destino"].astype(np.int64)
    x = data["x"]
    is_pachuca = data["is_pachuca"]
    match_id = data["match_id"]
    print(f"Filas: {len(origen):,}  (Pachuca: {is_pachuca.sum():,})")

    X_full = build_features_full(origen, x, is_pachuca)
    X_h0 = build_features_restringido(origen, x)
    y = destino

    print("Ajustando modelo H0 (restringido, sin delta)...")
    model_h0, ll0 = fit_and_loglik(X_h0, y, N_CLASSES)
    print(f"  loglik_H0 = {ll0:.1f}  ({time.time() - t0:.0f}s)")

    print("Ajustando modelo H1 (completo, con delta)...")
    model_h1, ll1 = fit_and_loglik(X_full, y, N_CLASSES)
    g2_obs = 2 * (ll1 - ll0)
    print(f"  loglik_H1 = {ll1:.1f}  ({time.time() - t0:.0f}s)")
    print(f"\nG2 observado = {g2_obs:.2f}  (28-24=4 grados de libertad extra)")

    # partidos unicos y sus filas, para resampleo por bloque de partido
    unique_matches = np.unique(match_id)
    rows_by_match = {m: np.where(match_id == m)[0] for m in unique_matches}
    rng = np.random.default_rng(SEED)

    g2_boot = np.zeros(N_BOOT)
    print(f"\nBootstrap nulo (H0), {N_BOOT} repeticiones, remuestreo por partido:")
    for b in range(N_BOOT):
        tb = time.time()
        sampled_matches = rng.choice(unique_matches, size=len(unique_matches), replace=True)
        idx = np.concatenate([rows_by_match[m] for m in sampled_matches])

        origen_b, x_b, is_pachuca_b = origen[idx], x[idx], is_pachuca[idx]
        X_h0_b = build_features_restringido(origen_b, x_b)
        y_b = simulate_y_bajo_h0(model_h0, X_h0_b, rng)

        X_full_b = build_features_full(origen_b, x_b, is_pachuca_b)
        _, ll0_b = fit_and_loglik(X_h0_b, y_b, N_CLASSES)
        _, ll1_b = fit_and_loglik(X_full_b, y_b, N_CLASSES)
        g2_boot[b] = 2 * (ll1_b - ll0_b)
        print(f"  rep {b + 1}/{N_BOOT}: G2_boot={g2_boot[b]:.2f}  ({time.time() - tb:.0f}s)")

    p_value = (g2_boot >= g2_obs).mean()
    print(f"\nG2 observado = {g2_obs:.2f}")
    print(
        f"G2 bootstrap nulo: media={g2_boot.mean():.2f}  p95={np.percentile(g2_boot, 95):.2f}  max={g2_boot.max():.2f}"
    )
    print(f"p-valor (bootstrap) = {p_value:.4f}")

    np.savez(
        "m1_g2_resultado.npz", g2_obs=g2_obs, g2_boot=g2_boot, p_value=p_value, ll0=ll0, ll1=ll1
    )
    print(f"\nGuardado m1_g2_resultado.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
