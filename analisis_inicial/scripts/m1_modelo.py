import time
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

N_ZONES = 20
N_ABS = 4
N_CLASSES = N_ZONES + N_ABS
X_NAMES = ["marcador", "periodo_frac", "local", "elo_diff"]


def build_features(origen, x, is_pachuca):
    """Disenio: [one-hot(origen) (20)] + [x (4)] + [x*is_pachuca (4)] -> 28 columnas.
    Los coeficientes de one-hot(origen) por clase = alpha_ij.
    Los coeficientes de x por clase = beta_j (efecto de liga).
    Los coeficientes de x*is_pachuca por clase = delta_j (efecto especifico Pachuca)."""
    n = len(origen)
    onehot_origen = sparse.csr_matrix((np.ones(n), (np.arange(n), origen)), shape=(n, N_ZONES))
    x_interact = x * is_pachuca[:, None]
    X = sparse.hstack([onehot_origen, sparse.csr_matrix(x), sparse.csr_matrix(x_interact)]).tocsr()
    return X


def main():
    t0 = time.time()
    data = np.load("m1_dataset.npz")
    origen, destino, x, is_pachuca = data["origen"], data["destino"], data["x"], data["is_pachuca"]
    print(f"Filas: {len(origen):,}")
    print(f"Filas de Pachuca: {is_pachuca.sum():,}")

    X = build_features(origen.astype(np.int64), x, is_pachuca)
    y = destino.astype(np.int64)

    print(
        f"Ajustando regresion logistica multinomial ({X.shape[1]} features, {N_CLASSES} clases)..."
    )
    model = LogisticRegression(solver="lbfgs", max_iter=300, C=10.0, n_jobs=-1)
    model.fit(X, y)
    print(f"Ajuste listo en {time.time() - t0:.0f}s")

    classes = model.classes_
    coef = model.coef_  # (n_classes, n_features) -- ojo: si una clase no aparece, sklearn la omite
    n_feat_alpha = N_ZONES
    beta = np.zeros((N_CLASSES, len(X_NAMES)))
    delta = np.zeros((N_CLASSES, len(X_NAMES)))
    for row_idx, cls in enumerate(classes):
        beta[cls] = coef[row_idx, n_feat_alpha : n_feat_alpha + 4]
        delta[cls] = coef[row_idx, n_feat_alpha + 4 : n_feat_alpha + 8]

    print("\nbeta_j (efecto de liga por destino) para 'marcador' (ir ganando -> +1):")
    for j in range(N_CLASSES):
        label = f"z{j}" if j < N_ZONES else ["G", "R", "P", "D"][j - N_ZONES]
        print(f"  {label:>4}: beta={beta[j, 0]:+.4f}  delta_pachuca={delta[j, 0]:+.4f}")

    np.savez(
        "m1_modelo.npz",
        beta=beta,
        delta=delta,
        classes_presentes=classes,
        coef=coef,
        intercept=model.intercept_,
    )
    print(f"\nGuardado m1_modelo.npz")


if __name__ == "__main__":
    main()
