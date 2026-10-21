"""Evolucion temporal del estilo (Semana 3, pieza de profundidad): filtro
de Kalman sobre PPDA por partido, ordenado cronologicamente a lo largo de
las 4 temporadas de Almada en Pachuca (2021/22 - 2024/25). Modelo de nivel
local (random walk + ruido):
    x_t = x_{t-1} + w_t,   w_t ~ N(0, Q)   (el "verdadero" nivel de presion evoluciona)
    y_t = x_t + v_t,       v_t ~ N(0, R)   (PPDA observado en cada partido es ruidoso)
Q y R se ajustan por maxima verosimilitud (grid search), igual que K y h
en el Elo de la Semana 1. Se corre filtro + suavizador (RTS) para tener
la mejor estimacion del nivel real de presion en cada punto del tiempo,
con banda de incertidumbre.
"""

import json, time, sys
import numpy as np

sys.path.insert(0, "scripts")
from ppda import ppda_equipo_en_partido

SEASON_IDS = [351, 318, 317, 281, 235, 108]


def kalman_filtro(y, Q, R, x0, P0):
    n = len(y)
    x_filt, P_filt = np.zeros(n), np.zeros(n)
    x_pred_l, P_pred_l = np.zeros(n), np.zeros(n)
    x_prev, P_prev = x0, P0
    loglik = 0.0
    for t in range(n):
        x_pred = x_prev
        P_pred = P_prev + Q
        innov = y[t] - x_pred
        innov_var = P_pred + R
        loglik += -0.5 * np.log(2 * np.pi * innov_var) - 0.5 * innov**2 / innov_var
        K = P_pred / innov_var
        x_t = x_pred + K * innov
        P_t = (1 - K) * P_pred
        x_filt[t], P_filt[t] = x_t, P_t
        x_pred_l[t], P_pred_l[t] = x_pred, P_pred
        x_prev, P_prev = x_t, P_t
    return x_filt, P_filt, x_pred_l, P_pred_l, loglik


def kalman_suavizador(x_filt, P_filt, x_pred_l, P_pred_l, Q):
    n = len(x_filt)
    x_smooth, P_smooth = np.zeros(n), np.zeros(n)
    x_smooth[-1], P_smooth[-1] = x_filt[-1], P_filt[-1]
    for t in range(n - 2, -1, -1):
        J = P_filt[t] / P_pred_l[t + 1]
        x_smooth[t] = x_filt[t] + J * (x_smooth[t + 1] - x_pred_l[t + 1])
        P_smooth[t] = P_filt[t] + J**2 * (P_smooth[t + 1] - P_pred_l[t + 1])
    return x_smooth, P_smooth


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_matches = sorted([m for m in almada if m["team"] == "Pachuca"], key=lambda m: m["date"])

    all_matches_meta = {}
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    fechas, ppda_vals, temporadas = [], [], []
    for m in pachuca_matches:
        mid = m["match_id"]
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        home, away = meta["home_team"]["home_team_name"], meta["away_team"]["away_team_name"]
        rival = away if home == "Pachuca" else home
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        d, p = ppda_equipo_en_partido(events, "Pachuca", rival)
        if d > 0:
            fechas.append(m["date"])
            ppda_vals.append(p / d)
            temporadas.append(m["season"])

    y = np.array(ppda_vals)
    n = len(y)
    print(f"Partidos con PPDA (ordenados por fecha): {n}  ({time.time() - t0:.0f}s)")
    print(f"PPDA: media={y.mean():.2f}  sd={y.std():.2f}")

    x0, P0 = y[0], y.var()

    # grid search de Q, R por maxima verosimilitud (parametrizado por razon senal/ruido)
    var_total = y.var()
    mejor = None
    for frac_q in np.linspace(0.02, 0.95, 40):
        Q = frac_q * var_total
        R = (1 - frac_q) * var_total
        if Q <= 0 or R <= 0:
            continue
        _, _, _, _, ll = kalman_filtro(y, Q, R, x0, P0)
        if mejor is None or ll > mejor[0]:
            mejor = (ll, Q, R, frac_q)

    ll, Q, R, frac_q = mejor
    print(
        f"\nOptimo por MLE: Q={Q:.4f}  R={R:.4f}  (fraccion de varianza atribuida a deriva real={frac_q:.3f})  loglik={ll:.2f}"
    )

    x_filt, P_filt, x_pred_l, P_pred_l, _ = kalman_filtro(y, Q, R, x0, P0)
    x_smooth, P_smooth = kalman_suavizador(x_filt, P_filt, x_pred_l, P_pred_l, Q)

    print(
        f"\nNivel de presion (PPDA) suavizado -- inicio vs. fin de la ventana de Almada en Pachuca:"
    )
    print(f"  primeros 5 partidos: {x_smooth[:5].round(2)}")
    print(f"  ultimos 5 partidos:  {x_smooth[-5:].round(2)}")
    print(f"  cambio neto (fin - inicio): {x_smooth[-1] - x_smooth[0]:+.2f}")

    # promedio suavizado por temporada, para lectura rapida
    temporadas_arr = np.array(temporadas)
    print(f"\nNivel suavizado promedio por temporada:")
    for temp in sorted(set(temporadas)):
        mask = temporadas_arr == temp
        print(
            f"  {temp}: PPDA_suavizado_promedio={x_smooth[mask].mean():.2f}  (n={mask.sum()} partidos)"
        )

    np.savez(
        "kalman_estilo.npz",
        y=y,
        x_filt=x_filt,
        x_smooth=x_smooth,
        P_smooth=P_smooth,
        fechas=np.array(fechas),
        temporadas=temporadas_arr,
        Q=Q,
        R=R,
    )
    print(f"\nGuardado kalman_estilo.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
