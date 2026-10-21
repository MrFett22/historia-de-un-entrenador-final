"""Dataset M2: igual que M1 (contexto) mas features de historia dentro de la
posesion, sin expandir el espacio de estados (roadmap): n_acciones acumuladas,
tipo de accion previa, si la accion actual fue bajo presion, y si la posesion
nacio de una recuperacion en juego abierto (misma definicion operacional que
"Transicion ofensiva" en FRAMEWORK.md: la posesion no arranca de un reinicio
a balon parado Y el evento inmediatamente anterior en el partido es del rival).
"""

import json, time, sys, bisect
import numpy as np

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import zone, STOP_TYPES, PERDIDA_PASS, N_ZONES
from m1_dataset import reconstruct_scores, marcador_estado, periodo_frac

SEASON_IDS = [351, 318, 317, 281, 235, 108]
DEAD_BALL_PATTERNS = {
    "From Corner",
    "From Free Kick",
    "From Throw In",
    "From Kick Off",
    "From Goal Kick",
}


def possession_a_secuencias_con_historia(evs, owner):
    """Mismo criterio de corte que possession_to_secuencias (M0/M1): cada
    secuencia termina en su PRIMERA absorcion. Ademas retorna, por zona
    visitada, el tipo de accion (0=Pass,1=Carry) y si fue bajo presion --
    para las features de historia de M2. Devuelve una lista de
    (zonas, tipos, presion, absorbente, primer_evento) -- una por
    secuencia."""
    accion = [
        e
        for e in evs
        if e["team"]["name"] == owner and e["type"]["name"] in ("Pass", "Carry", "Shot")
    ]
    accion.sort(key=lambda e: e["index"])

    secuencias = []
    zonas, tipos, presion = [], [], []
    primer_evento = None
    for e in accion:
        if primer_evento is None:
            primer_evento = e
        t = e["type"]["name"]
        loc = e.get("location")
        if t == "Shot":
            outcome = e.get("shot", {}).get("outcome", {}).get("name")
            absorb = "G" if outcome == "Goal" else "R"
            if not zonas and loc:
                zonas, tipos, presion = [zone(loc)], [0], [1 if e.get("under_pressure") else 0]
            if zonas:
                secuencias.append((zonas, tipos, presion, absorb, primer_evento))
            zonas, tipos, presion, primer_evento = [], [], [], None
            continue
        if loc:
            zonas.append(zone(loc))
            tipos.append(0 if t == "Pass" else 1)
            presion.append(1 if e.get("under_pressure") else 0)
        if t == "Pass":
            outcome = e.get("pass", {}).get("outcome", {}).get("name")
            if outcome in PERDIDA_PASS:
                if zonas:
                    secuencias.append((zonas, tipos, presion, "P", primer_evento))
                zonas, tipos, presion, primer_evento = [], [], [], None

    if zonas:
        last = evs[-1]
        absorb = "D" if (last.get("out") or last["type"]["name"] in STOP_TYPES) else "P"
        secuencias.append((zonas, tipos, presion, absorb, primer_evento))
    return secuencias


def main():
    t0 = time.time()
    elo_data = json.load(open("elo_resultados.json", encoding="utf-8"))
    pre_match_elo = elo_data["pre_match_elo"]

    all_matches = []
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            if m.get("match_status_360") == "available":
                all_matches.append(m)

    print(f"Construyendo dataset M2 sobre {len(all_matches)} partidos...")

    rows_i, rows_dest, rows_x, rows_h, rows_is_pachuca, rows_equipo, rows_match = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    n_procesados = 0

    for idx_m, m in enumerate(all_matches):
        mid = m["match_id"]
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        events.sort(key=lambda e: e["index"])
        home_id, away_id = m["home_team"]["home_team_id"], m["away_team"]["away_team_id"]
        home_name, away_name = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
        per_index_score = reconstruct_scores(events, home_id, away_id)

        elo_info = pre_match_elo.get(str(mid)) or pre_match_elo.get(mid)
        if elo_info is None:
            continue
        elo_home, elo_away = elo_info["home_elo"], elo_info["away_elo"]

        from collections import defaultdict

        poss = defaultdict(list)
        for e in events:
            if e["period"] in (1, 2):
                poss[e["possession"]].append(e)

        # evento anterior (por indice global) al primer evento de cada posesion,
        # para saber si la posesion nace de una recuperacion (evento previo es del rival)
        sorted_idx = [e["index"] for e in events]
        all_events_by_index = {e["index"]: e for e in events}

        for pid, evs in poss.items():
            owner = evs[0]["possession_team"]["name"]
            is_home = owner == home_name
            if not is_home and owner != away_name:
                continue
            local_visita = 1 if is_home else 0
            elo_own = elo_home if is_home else elo_away
            elo_riv = elo_away if is_home else elo_home
            elo_diff = (elo_own - elo_riv) / 400.0

            is_pachuca = 1 if owner == "Pachuca" else 0

            for (
                zonas,
                tipos,
                presion,
                absorb,
                primer_evento,
            ) in possession_a_secuencias_con_historia(evs, owner):
                start_idx = primer_evento["index"]
                my_s, ri_s = per_index_score.get(start_idx, (0, 0))
                if not is_home:
                    my_s, ri_s = ri_s, my_s
                marcador = marcador_estado(my_s, ri_s)
                minute = primer_evento.get("minute", 0)
                per_frac = periodo_frac(minute)

                play_pattern = primer_evento.get("play_pattern", {}).get("name", "")
                pos_in_sorted = bisect.bisect_left(sorted_idx, start_idx)
                inicio_recuperacion = 0
                if pos_in_sorted > 0 and play_pattern not in DEAD_BALL_PATTERNS:
                    prev_ev = all_events_by_index[sorted_idx[pos_in_sorted - 1]]
                    if prev_ev["team"]["name"] != owner:
                        inicio_recuperacion = 1

                n = len(zonas)
                for k in range(n - 1):
                    rows_i.append(zonas[k])
                    rows_dest.append(zonas[k + 1])
                    rows_x.append([marcador, per_frac, local_visita, elo_diff])
                    tipo_previo = tipos[k - 1] if k > 0 else -1  # -1 = inicio de secuencia
                    rows_h.append([k + 1, tipo_previo, presion[k], inicio_recuperacion])
                    rows_is_pachuca.append(is_pachuca)
                    rows_equipo.append(owner)
                    rows_match.append(mid)
                rows_i.append(zonas[-1])
                rows_dest.append(N_ZONES + {"G": 0, "R": 1, "P": 2, "D": 3}[absorb])
                rows_x.append([marcador, per_frac, local_visita, elo_diff])
                tipo_previo = tipos[n - 2] if n > 1 else -1
                rows_h.append([n, tipo_previo, presion[-1], inicio_recuperacion])
                rows_is_pachuca.append(is_pachuca)
                rows_equipo.append(owner)
                rows_match.append(mid)

        n_procesados += 1
        if (idx_m + 1) % 300 == 0:
            print(
                f"  {idx_m + 1}/{len(all_matches)} partidos ({time.time() - t0:.0f}s, {len(rows_i):,} filas)"
            )

    print(f"\nPartidos procesados: {n_procesados}")
    print(f"Filas totales: {len(rows_i):,}")

    np.savez_compressed(
        "m2_dataset.npz",
        origen=np.array(rows_i, dtype=np.int16),
        destino=np.array(rows_dest, dtype=np.int16),
        x=np.array(rows_x, dtype=np.float32),
        h=np.array(rows_h, dtype=np.float32),
        is_pachuca=np.array(rows_is_pachuca, dtype=np.int8),
        equipo=np.array(rows_equipo, dtype="<U30"),
        match_id=np.array(rows_match, dtype=np.int32),
    )
    print(f"Guardado m2_dataset.npz ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
