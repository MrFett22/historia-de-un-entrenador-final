import json, sys
import numpy as np

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import process_match_for_team, N_ZONES

pachuca = np.load("m0_pachuca_almada.npz")
liga = np.load("m0_liga_referencia.npz")

counts_pachuca = pachuca["counts"]  # (20, 24): 20 zonas transitorias + 4 absorbentes
counts_liga = liga["counts"]

n_i = counts_pachuca.sum(axis=1)  # observaciones por zona de origen, Pachuca
p_hat = counts_pachuca / n_i[:, None]
q = counts_liga / counts_liga.sum(axis=1, keepdims=True)


def shrink(lam):
    return (n_i[:, None] * p_hat + lam * q) / (n_i[:, None] + lam)


print("Observaciones (n_i) por zona de origen, Pachuca:")
for z in range(N_ZONES):
    print(f"  z{z:>2}: n={int(n_i[z])}")

print(f"\nCon lambda=0 (magnitudes reportadas): P_tilde = P_hat (sin cambio)")
print("Verificacion:", np.allclose(shrink(0), p_hat))

print("\n--- Cuanto moveria el encogimiento a la zona con MENOS datos (referencia) ---")
z_min = int(np.argmin(n_i))
print(f"Zona con menos observaciones: z{z_min} (n={int(n_i[z_min])})")
for lam in [0, 5, 20, 50, 100]:
    pt = shrink(lam)[z_min]
    # distancia L1 entre p_hat cruda y la version encogida, solo para esa fila
    dist = np.abs(pt - p_hat[z_min]).sum()
    print(f"  lambda={lam:>4}: distancia L1 vs. crudo = {dist:.4f}")

# --- validacion cruzada por partido para elegir lambda ---
print("\nValidacion cruzada por partido para elegir lambda...")
almada = json.load(open("almada_matches.json", encoding="utf-8"))
pachuca_ids = [m["match_id"] for m in almada if m["team"] == "Pachuca"]

per_match_trans = []
for mid in pachuca_ids:
    events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
    trans, _, _ = process_match_for_team(events, "Pachuca")
    per_match_trans.append(trans)

rng = np.random.default_rng(3)
idx = rng.permutation(len(per_match_trans))
n_folds = 5
folds = np.array_split(idx, n_folds)

lambdas = [0, 1, 5, 10, 20, 50, 100, 200]
avg_loglik = {lam: 0.0 for lam in lambdas}

for f in range(n_folds):
    test_idx = set(folds[f].tolist())
    train_trans = []
    test_trans = []
    for i, trans in enumerate(per_match_trans):
        (test_trans if i in test_idx else train_trans).extend(trans)

    counts_train = np.zeros((N_ZONES, N_ZONES + 4)) + 1e-6
    for i, j in train_trans:
        counts_train[i, j] += 1
    n_train = counts_train.sum(axis=1)
    p_train = counts_train / n_train[:, None]

    for lam in lambdas:
        p_shrunk = (n_train[:, None] * p_train + lam * q) / (n_train[:, None] + lam)
        ll = 0.0
        for i, j in test_trans:
            ll += np.log(max(p_shrunk[i, j], 1e-9))
        avg_loglik[lam] += ll / max(len(test_trans), 1)

print("\nlambda -> log-verosimilitud promedio por transicion (test, 5-fold CV):")
for lam in lambdas:
    print(f"  lambda={lam:>4}: {avg_loglik[lam] / n_folds:.4f}")

best_lambda = max(lambdas, key=lambda l: avg_loglik[l])
print(f"\nMejor lambda por CV: {best_lambda}")
print(
    "(las magnitudes del informe se reportan con lambda=0 de cualquier forma, "
    "por transparencia -- este resultado de CV documenta que tanto ayudaria encoger "
    "si se necesitara para una celda con poca muestra, p.ej. en M1 con el grid mas fino)"
)
