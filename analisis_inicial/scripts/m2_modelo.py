"""M2 vs M1 con validacion fuera de muestra (roadmap: "cada escalon se
acepta solo si predice mejor en partidos que no vio"). Split 80/20 por
PARTIDO completo (no por fila) para no filtrar informacion entre train y
test. Se compara la log-verosimilitud promedio por fila en el conjunto de
prueba entre M1 (sin historia) y M2 (con historia: n acumulado, tipo de
accion previa, presion, inicio por recuperacion). M2 solo se adopta si
mejora la prediccion fuera de muestra -- "se anade historia hasta que
pase, y no mas".
"""

import time
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression

N_ZONES = 20
N_ABS = 4
N_CLASSES = N_ZONES + N_ABS
SEED = 13
TEST_FRAC = 0.2


def build_features_m1(origen, x, is_pachuca):
    n = len(origen)
    onehot = sparse.csr_matrix((np.ones(n), (np.arange(n), origen)), shape=(n, N_ZONES))
    x_int = x * is_pachuca[:, None]
    return sparse.hstack([onehot, sparse.csr_matrix(x), sparse.csr_matrix(x_int)]).tocsr()


def build_h(h_raw):
    n_acum, tipo_previo, presion, recuperacion = h_raw[:, 0], h_raw[:, 1], h_raw[:, 2], h_raw[:, 3]
    es_inicio = (tipo_previo == -1).astype(np.float32)
    previo_carry = (tipo_previo == 1).astype(np.float32)
    return np.column_stack([n_acum / 10.0, es_inicio, previo_carry, presion, recuperacion])


def build_features_m2(origen, x, h_raw, is_pachuca):
    n = len(origen)
    onehot = sparse.csr_matrix((np.ones(n), (np.arange(n), origen)), shape=(n, N_ZONES))
    x_int = x * is_pachuca[:, None]
    h = build_h(h_raw)
    h_int = h * is_pachuca[:, None]
    return sparse.hstack(
        [
            onehot,
            sparse.csr_matrix(x),
            sparse.csr_matrix(x_int),
            sparse.csr_matrix(h),
            sparse.csr_matrix(h_int),
        ]
    ).tocsr()


def loglik_held_out(model, X, y):
    proba = model.predict_proba(X)
    class_to_col = {c: j for j, c in enumerate(model.classes_)}
    cols = np.array([class_to_col.get(val, -1) for val in y])
    ok = cols >= 0  # por si en test aparece una clase que no estaba en train
    p_true = np.full(len(y), 1e-12)
    p_true[ok] = proba[np.arange(len(y))[ok], cols[ok]]
    p_true = np.clip(p_true, 1e-12, 1.0)
    return np.log(p_true).sum(), ok.mean()


def main():
    t0 = time.time()
    data = np.load("m2_dataset.npz", allow_pickle=True)
    origen = data["origen"].astype(np.int64)
    destino = data["destino"].astype(np.int64)
    x = data["x"]
    h_raw = data["h"]
    is_pachuca = data["is_pachuca"]
    match_id = data["match_id"]
    print(f"Filas: {len(origen):,}  (Pachuca: {is_pachuca.sum():,})")

    rng = np.random.default_rng(SEED)
    unique_matches = np.unique(match_id)
    rng.shuffle(unique_matches)
    n_test = int(len(unique_matches) * TEST_FRAC)
    test_matches = set(unique_matches[:n_test])
    is_test = np.array([m in test_matches for m in match_id])
    print(f"Partidos: {len(unique_matches)}  train={len(unique_matches) - n_test}  test={n_test}")
    print(f"Filas train={(~is_test).sum():,}  filas test={is_test.sum():,}")

    y = destino
    tr, te = ~is_test, is_test

    # ---- M1 (sin historia) ----
    print("\nM1: ajustando en train...")
    X1_tr = build_features_m1(origen[tr], x[tr], is_pachuca[tr])
    X1_te = build_features_m1(origen[te], x[te], is_pachuca[te])
    m1 = LogisticRegression(solver="lbfgs", max_iter=300, C=10.0)
    m1.fit(X1_tr, y[tr])
    ll1_test, cov1 = loglik_held_out(m1, X1_te, y[te])
    print(
        f"  M1 loglik test = {ll1_test:.1f}  (avg/fila = {ll1_test / is_test.sum():.4f})  ({time.time() - t0:.0f}s)"
    )

    # ---- M2 (con historia) ----
    print("\nM2: ajustando en train...")
    X2_tr = build_features_m2(origen[tr], x[tr], h_raw[tr], is_pachuca[tr])
    X2_te = build_features_m2(origen[te], x[te], h_raw[te], is_pachuca[te])
    m2 = LogisticRegression(solver="lbfgs", max_iter=300, C=10.0)
    m2.fit(X2_tr, y[tr])
    ll2_test, cov2 = loglik_held_out(m2, X2_te, y[te])
    print(
        f"  M2 loglik test = {ll2_test:.1f}  (avg/fila = {ll2_test / is_test.sum():.4f})  ({time.time() - t0:.0f}s)"
    )

    delta_ll = ll2_test - ll1_test
    print(
        f"\nMejora de M2 sobre M1 en TEST (fuera de muestra): {delta_ll:+.1f} log-lik total, "
        f"{delta_ll / is_test.sum():+.5f} por fila"
    )
    if delta_ll > 0:
        print("  -> M2 predice mejor partidos que no vio. Se adopta M2 segun la regla del roadmap.")
    else:
        print("  -> M2 NO mejora la prediccion fuera de muestra. Se mantiene M1 (no se adopta M2),")
        print("     aunque M0 haya fallado la bondad de ajuste -- el roadmap solo pide historia")
        print("     si de verdad ayuda a predecir, no solo porque la nula del KS se rechazo.")

    classes = m2.classes_
    coef = m2.coef_
    n_alpha = N_ZONES
    kappa = np.zeros((N_CLASSES, 5))  # efecto de liga de h
    mu = np.zeros((N_CLASSES, 5))  # efecto especifico Pachuca de h
    for row_idx, cls in enumerate(classes):
        kappa[cls] = coef[row_idx, n_alpha + 8 : n_alpha + 13]
        mu[cls] = coef[row_idx, n_alpha + 13 : n_alpha + 18]

    h_names = [
        "n_acumulado/10",
        "es_inicio_posesion",
        "previo_fue_carry",
        "bajo_presion",
        "inicio_recuperacion",
    ]
    print("\nkappa_j (efecto de liga, historia) y mu_j (especifico Pachuca) para absorbentes:")
    for j in range(N_ZONES, N_CLASSES):
        label = ["G", "R", "P", "D"][j - N_ZONES]
        for f, name in enumerate(h_names):
            print(f"  {label} / {name}: kappa={kappa[j, f]:+.4f}  mu={mu[j, f]:+.4f}")

    np.savez(
        "m2_modelo.npz",
        kappa=kappa,
        mu=mu,
        ll1_test=ll1_test,
        ll2_test=ll2_test,
        delta_ll=delta_ll,
        n_test_rows=int(is_test.sum()),
        coef=coef,
        intercept=m2.intercept_,
        classes_presentes=classes,
    )
    print(f"\nGuardado m2_modelo.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
