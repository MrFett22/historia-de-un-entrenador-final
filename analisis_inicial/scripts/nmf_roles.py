"""NMF de roles de jugador (reto 5.3, Uso de Jugadores) -- primera pieza de
la Semana 3, cubre la parte del rubro que hasta ahora no se habia tocado
(todo lo de la Semana 1-2 fue estilo/consistencia/defensa a nivel equipo).

Matriz V (jugadores x 20 zonas) = conteo de toques (Pass+Carry+Shot) de
cada jugador de Pachuca en los 139 partidos de Almada. Se factoriza
V ~= W @ H con NMF: H (k x 20) son los "roles" como perfiles de zona,
W (jugadores x k) es cuanto de cada rol tiene cada jugador. Se valida
contra la posicion registrada por StatsBomb en cada toque (independiente
del NMF) -- si el rol dominante de un jugador coincide con su posicion
habitual, es evidencia de que el NMF esta recuperando estructura real,
no ruido.
"""

import json, time
from collections import defaultdict, Counter
import numpy as np
from sklearn.decomposition import NMF
import sys

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import zone, N_ZONES

K_ROLES = 5
MIN_TOQUES = 150
SEED = 31


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = [m["match_id"] for m in almada if m["team"] == "Pachuca"]

    toques = defaultdict(lambda: np.zeros(N_ZONES))
    nombres = {}
    posiciones = defaultdict(Counter)

    for mid in pachuca_ids:
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        for e in events:
            if e["period"] not in (1, 2):
                continue
            if e["team"]["name"] != "Pachuca":
                continue
            if e["type"]["name"] not in ("Pass", "Carry", "Shot"):
                continue
            player = e.get("player")
            loc = e.get("location")
            if player is None or loc is None:
                continue
            pid = player["id"]
            nombres[pid] = player["name"]
            toques[pid][zone(loc)] += 1
            pos = e.get("position")
            if pos:
                posiciones[pid][pos["name"]] += 1

    print(f"Jugadores de Pachuca detectados: {len(toques)}  ({time.time() - t0:.0f}s)")

    pids = [pid for pid, v in toques.items() if v.sum() >= MIN_TOQUES]
    pids.sort(key=lambda pid: -toques[pid].sum())
    print(f"Jugadores con >= {MIN_TOQUES} toques: {len(pids)}")

    V = np.array([toques[pid] for pid in pids])

    nmf = NMF(n_components=K_ROLES, init="nndsvda", random_state=SEED, max_iter=2000)
    W = nmf.fit_transform(V)
    H = nmf.components_

    # normalizar H por fila para verla como "distribucion de toques del rol" (perfil)
    H_norm = H / H.sum(axis=1, keepdims=True)
    # normalizar W por fila para ver la mezcla de roles de cada jugador (composicion, no escala)
    W_norm = W / W.sum(axis=1, keepdims=True)

    print(
        f"\nPerfil de cada rol por franja de x (promediando los 4 carriles de cada banda, 0=propia 4=rival):"
    )
    GRID_X, GRID_Y = 5, 4
    for k in range(K_ROLES):
        perfil_x = H_norm[k].reshape(GRID_X, GRID_Y).sum(axis=1)
        perfil_y = H_norm[k].reshape(GRID_X, GRID_Y).sum(axis=0)
        banda_dominante = np.argmax(perfil_x)
        carril_dominante = np.argmax(perfil_y)
        print(
            f"  rol {k}: banda_x dominante={banda_dominante} (perfil_x={np.round(perfil_x, 2)})  "
            f"carril_y dominante={carril_dominante} (perfil_y={np.round(perfil_y, 2)})"
        )

    print(f"\nRol dominante por jugador (top 25 por volumen de toques):")
    print(
        f"{'jugador':<32} {'toques':>7} {'rol_dom':>8} {'mezcla_W':>28} {'posicion_frecuente':>25}"
    )
    for pid in pids[:25]:
        idx = pids.index(pid)
        rol_dom = int(np.argmax(W_norm[idx]))
        mezcla = " ".join(f"{w:.2f}" for w in W_norm[idx])
        pos_frecuente = posiciones[pid].most_common(1)[0][0] if posiciones[pid] else "?"
        print(
            f"{nombres[pid]:<32} {int(toques[pid].sum()):>7} {rol_dom:>8} [{mezcla:>26}] {pos_frecuente:>25}"
        )

    np.savez(
        "nmf_roles.npz",
        V=V,
        W=W,
        H=H,
        W_norm=W_norm,
        H_norm=H_norm,
        pids=pids,
        nombres=[nombres[p] for p in pids],
    )
    print(f"\nGuardado nmf_roles.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
