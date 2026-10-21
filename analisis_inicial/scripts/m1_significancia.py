"""Correccion de C2: el test G^2 con nula por bootstrap (scripts/m1_g2_test.py)
resultaba invalido -- la nula dio varias repeticiones con G^2 negativo, algo
que no puede pasar si ambos modelos (restringido y completo) son un MLE
limpio sobre los mismos datos; senal de que la regularizacion L2 (C=10) o
la convergencia de lbfgs rompian la comparacion. Se reemplaza por el MISMO
criterio ya usado para validar M2: log-verosimilitud FUERA DE MUESTRA, con
split 80/20 por partido completo (no por fila). Si el modelo CON delta
(especifico de Pachuca) predice mejor en partidos que no vio que el modelo
SIN delta (pooled), el efecto es real -- mismo estandar que "cada escalon
se acepta solo si predice mejor en partidos que no vio" del roadmap.
"""

import time
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression

N_ZONES = 20
N_ABS = 4
N_CLASSES = N_ZONES + N_ABS
SEED = 71
TEST_FRAC = 0.2


def build_features_full(origen, x, is_pachuca):
    n = len(origen)
    onehot = sparse.csr_matrix((np.ones(n), (np.arange(n), origen)), shape=(n, N_ZONES))
    x_int = x * is_pachuca[:, None]
    return sparse.hstack([onehot, sparse.csr_matrix(x), sparse.csr_matrix(x_int)]).tocsr()


def build_features_pooled(origen, x):
    n = len(origen)
    onehot = sparse.csr_matrix((np.ones(n), (np.arange(n), origen)), shape=(n, N_ZONES))
    return sparse.hstack([onehot, sparse.csr_matrix(x)]).tocsr()


def loglik_held_out(model, X, y):
    proba = model.predict_proba(X)
    class_to_col = {c: j for j, c in enumerate(model.classes_)}
    cols = np.array([class_to_col.get(val, -1) for val in y])
    ok = cols >= 0
    p_true = np.full(len(y), 1e-12)
    p_true[ok] = proba[np.arange(len(y))[ok], cols[ok]]
    p_true = np.clip(p_true, 1e-12, 1.0)
    return np.log(p_true).sum()


def main():
    t0 = time.time()
    data = np.load("m1_dataset.npz", allow_pickle=True)
    origen = data["origen"].astype(np.int64)
    destino = data["destino"].astype(np.int64)
    x = data["x"]
    is_pachuca = data["is_pachuca"]
    match_id = data["match_id"]
    y = destino
    print(f"Filas: {len(origen):,}  (Pachuca: {is_pachuca.sum():,})")

    rng = np.random.default_rng(SEED)
    unique_matches = np.unique(match_id)
    rng.shuffle(unique_matches)
    n_test = int(len(unique_matches) * TEST_FRAC)
    test_matches = set(unique_matches[:n_test])
    is_test = np.array([m in test_matches for m in match_id])
    tr, te = ~is_test, is_test
    print(f"Partidos: {len(unique_matches)}  train={len(unique_matches) - n_test}  test={n_test}")
    print(f"Filas train={tr.sum():,}  filas test={te.sum():,}")

    print("\nModelo SIN delta (pooled, restringido): ajustando en train...")
    X0_tr = build_features_pooled(origen[tr], x[tr])
    X0_te = build_features_pooled(origen[te], x[te])
    m0 = LogisticRegression(solver="lbfgs", max_iter=300, C=10.0)
    m0.fit(X0_tr, y[tr])
    ll0_test = loglik_held_out(m0, X0_te, y[te])
    print(f"  loglik test (sin delta) = {ll0_test:.1f}  ({time.time() - t0:.0f}s)")

    print("\nModelo CON delta (completo): ajustando en train...")
    X1_tr = build_features_full(origen[tr], x[tr], is_pachuca[tr])
    X1_te = build_features_full(origen[te], x[te], is_pachuca[te])
    m1 = LogisticRegression(solver="lbfgs", max_iter=300, C=10.0)
    m1.fit(X1_tr, y[tr])
    ll1_test = loglik_held_out(m1, X1_te, y[te])
    print(f"  loglik test (con delta) = {ll1_test:.1f}  ({time.time() - t0:.0f}s)")

    delta_ll = ll1_test - ll0_test
    n_test_rows = te.sum()
    print(
        f"\nMejora de 'con delta' sobre 'sin delta' en TEST (fuera de muestra): "
        f"{delta_ll:+.1f} log-lik total, {delta_ll / n_test_rows:+.5f} por fila"
    )
    if delta_ll > 0:
        print("  -> El efecto especifico de Pachuca (delta) predice mejor partidos que no vio.")
        print(
            "     Es real segun el mismo criterio con el que se acepto M2, no un artefacto de ajuste in-sample."
        )
    else:
        print("  -> El efecto delta NO mejora la prediccion fuera de muestra.")
        print("     No se puede sostener como hallazgo con este criterio.")

    np.savez(
        "m1_significancia.npz",
        ll0_test=ll0_test,
        ll1_test=ll1_test,
        delta_ll=delta_ll,
        n_test_rows=int(n_test_rows),
    )
    print(f"\nGuardado m1_significancia.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
