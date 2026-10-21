"""Modelo propio de xG (Semana 3, pieza de profundidad) -- logit
interpretable sobre features geometricas, entrenado con TODOS los tiros
de las 6 temporadas (no solo Pachuca, para tener volumen suficiente).
Se valida por AUC en un split 80/20 por partido, comparado contra el AUC
que logra el propio `statsbomb_xg` en el mismo conjunto de prueba -- si
nuestro modelo transparente logra un AUC comparable, valida que usar
`statsbomb_xg` en el resto del proyecto (ej. x_bar en M0) es razonable
sin depender de una caja negra propietaria.

Features: distancia y angulo geometricos al arco, parte del cuerpo,
tecnica, bajo presion, tipo (penal / tiro libre directo / juego abierto),
y numero de defensores en la trayectoria tiro-arco (via freeze_frame del
propio tiro).
"""

import json, time
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

SEASON_IDS = [351, 318, 317, 281, 235, 108]
GOAL = np.array([120.0, 40.0])
POST1, POST2 = np.array([120.0, 36.0]), np.array([120.0, 44.0])


def angulo_tiro(loc):
    a = POST1 - np.array(loc[:2])
    b = POST2 - np.array(loc[:2])
    cos_ang = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
    cos_ang = np.clip(cos_ang, -1, 1)
    return np.arccos(cos_ang)


def defensores_en_trayectoria(loc, freeze_frame, umbral=1.5):
    S = np.array(loc[:2])
    SG = GOAL - S
    denom = np.dot(SG, SG) + 1e-9
    n = 0
    for p in freeze_frame or []:
        if p.get("teammate") or p.get("player", {}).get("position", {}).get("name") == "Goalkeeper":
            continue
        P = np.array(p["location"][:2])
        t = np.dot(P - S, SG) / denom
        if 0.15 <= t <= 0.98:
            closest = S + t * SG
            d = np.linalg.norm(P - closest)
            if d <= umbral:
                n += 1
    return n


def extraer_features(e):
    shot = e["shot"]
    loc = e["location"]
    dist = np.linalg.norm(GOAL - np.array(loc[:2]))
    ang = angulo_tiro(loc)
    body = shot.get("body_part", {}).get("name", "")
    es_cabeza = 1 if body == "Head" else 0
    tipo = shot.get("type", {}).get("name", "")
    es_penal = 1 if tipo == "Penalty" else 0
    es_falta = 1 if tipo == "Free Kick" else 0
    bajo_presion = 1 if e.get("under_pressure") else 0
    n_def = defensores_en_trayectoria(loc, shot.get("freeze_frame"))
    gol = 1 if shot.get("outcome", {}).get("name") == "Goal" else 0
    xg_sb = shot.get("statsbomb_xg", np.nan)
    return [dist, ang, es_cabeza, es_penal, es_falta, bajo_presion, n_def], gol, xg_sb


def main():
    t0 = time.time()
    all_matches = []
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            if m.get("match_status_360") == "available":
                all_matches.append(m)
    print(f"Procesando tiros sobre {len(all_matches)} partidos...")

    X, y, xg_sb_list, match_ids = [], [], [], []
    for idx_m, m in enumerate(all_matches):
        mid = m["match_id"]
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        for e in events:
            if e["type"]["name"] != "Shot" or e["period"] not in (1, 2):
                continue
            if e["shot"].get("type", {}).get("name") == "Penalty":
                continue  # penales se excluyen del modelo geometrico (todos a la misma distancia)
            loc = e.get("location")
            if loc is None:
                continue
            feats, gol, xg_sb = extraer_features(e)
            X.append(feats)
            y.append(gol)
            xg_sb_list.append(xg_sb)
            match_ids.append(mid)
        if (idx_m + 1) % 400 == 0:
            print(
                f"  {idx_m + 1}/{len(all_matches)} partidos, {len(X):,} tiros  ({time.time() - t0:.0f}s)"
            )

    X = np.array(X)
    y = np.array(y)
    xg_sb_arr = np.array(xg_sb_list)
    match_ids = np.array(match_ids)
    print(f"\nTiros totales (sin penales): {len(X):,}  goles={y.sum():,} ({y.mean() * 100:.2f}%)")

    rng = np.random.default_rng(41)
    unique_matches = np.unique(match_ids)
    rng.shuffle(unique_matches)
    n_test = int(len(unique_matches) * 0.2)
    test_matches = set(unique_matches[:n_test])
    is_test = np.array([m in test_matches for m in match_ids])

    Xtr, Xte = X[~is_test], X[is_test]
    ytr, yte = y[~is_test], y[is_test]
    xg_sb_te = xg_sb_arr[is_test]

    model = LogisticRegression(max_iter=1000)
    model.fit(Xtr, ytr)
    proba_te = model.predict_proba(Xte)[:, 1]

    auc_propio = roc_auc_score(yte, proba_te)
    ok_sb = ~np.isnan(xg_sb_te)
    auc_sb = roc_auc_score(yte[ok_sb], xg_sb_te[ok_sb])

    print(f"\nTiros en test: {is_test.sum():,}  (train: {(~is_test).sum():,})")
    print(f"AUC modelo propio (logit geometrico): {auc_propio:.4f}")
    print(f"AUC statsbomb_xg (referencia, mismo test):        {auc_sb:.4f}")

    feat_names = [
        "distancia",
        "angulo",
        "es_cabeza",
        "es_penal(excl)",
        "es_falta_libre",
        "bajo_presion",
        "n_defensores_trayectoria",
    ]
    print("\nCoeficientes (logit, features estandarizadas NO -- crudas):")
    for name, coef in zip(feat_names, model.coef_[0]):
        print(f"  {name:>25}: {coef:+.4f}")
    print(f"  intercepto: {model.intercept_[0]:+.4f}")

    # comparacion agregada: xg propio promedio vs xg statsbomb promedio vs tasa de gol real (calibracion global)
    print(
        f"\nCalibracion global (test): xg_propio_promedio={proba_te.mean():.4f}  "
        f"xg_statsbomb_promedio={np.nanmean(xg_sb_te):.4f}  tasa_gol_real={yte.mean():.4f}"
    )

    np.savez(
        "xg_propio.npz",
        coef=model.coef_,
        intercept=model.intercept_,
        auc_propio=auc_propio,
        auc_sb=auc_sb,
        feat_names=feat_names,
    )
    print(f"\nGuardado xg_propio.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
