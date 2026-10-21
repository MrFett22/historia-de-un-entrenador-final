"""Transicion defensiva (FRAMEWORK.md seccion 1: "los 10s posteriores a una
perdida propia"). Analisis de tiempo hasta que Pachuca recupera el balon
tras perderlo, con RIESGOS COMPETIDORES (correccion 2026-09-26, senalada
por auditoria cruzada): el remate del rival no es censura simple, es un
evento competidor -- si el rival tira, la "recuperacion" queda impedida por
una razon informativa (el rival ya organizo un ataque), no por falta de
informacion. Tratarlo como censura (Kaplan-Meier ingenuo) sesga hacia
arriba la probabilidad de recuperacion. Se codifican 3 desenlaces:
  0 = censura real (se acabo el periodo sin recuperacion ni tiro rival)
  1 = evento de interes (Pachuca recupera el balon)
  2 = riesgo competidor (el rival remata antes de que Pachuca recupere)
Se usa incidencia acumulada (Aalen-Johansen) en vez de 1-KM.
"""

import json, time
import numpy as np

SEASON_IDS = [351, 318, 317, 281, 235, 108]


def tiempo(e):
    return e.get("minute", 0) * 60 + e.get("second", 0)


def transiciones_defensivas_equipo(events, team_name):
    """Devuelve lista de (duracion, evento) para cada perdida del equipo:
    evento=1 si se observo recuperacion, 0 si se censuro (tiro rival o fin de periodo)."""
    events = sorted(events, key=lambda e: e["index"])
    resultados = []
    n = len(events)
    i = 0
    while i < n:
        e = events[i]
        if (
            e["team"]["name"] == team_name
            and e["type"]["name"] in ("Pass", "Carry")
            and e["period"] in (1, 2)
        ):
            # es esta la ULTIMA accion de una posesion de team_name que termina en perdida?
            pid = e["possession"]
            # buscar el siguiente evento con possession distinto
            j = i + 1
            while j < n and events[j]["possession"] == pid:
                j += 1
            if j >= n or events[j]["period"] != e["period"]:
                i = j if j > i else i + 1
                continue
            # confirmar que la posesion siguiente NO es de team_name (o sea, hubo perdida)
            # y que la posesion de team_name no termino en tiro propio (eso seria R/G, no P)
            propios_tiro = any(
                ev["team"]["name"] == team_name and ev["type"]["name"] == "Shot"
                for ev in events[i:j]
                if ev["possession"] == pid
            )
            siguiente_owner = events[j]["possession_team"]["name"]
            if propios_tiro or siguiente_owner == team_name:
                i = j
                continue
            t0 = tiempo(events[j - 1])  # momento de la ultima accion antes de perder el balon
            periodo = e["period"]
            k = j
            evento_obs = 0  # 0=censura, 1=recuperacion, 2=riesgo competidor (tiro rival)
            duracion = None
            while k < n and events[k]["period"] == periodo:
                ek = events[k]
                if ek["team"]["name"] == team_name and ek["possession_team"]["name"] == team_name:
                    duracion = tiempo(ek) - t0
                    evento_obs = 1
                    break
                if ek["team"]["name"] != team_name and ek["type"]["name"] == "Shot":
                    duracion = tiempo(ek) - t0
                    evento_obs = 2
                    break
                k += 1
            else:
                # se acabo el periodo sin recuperacion observada ni tiro rival
                duracion = tiempo(events[k - 1]) - t0 if k > j else 0
                evento_obs = 0
            if duracion is not None and duracion >= 0:
                resultados.append((duracion, evento_obs))
            i = j
        else:
            i += 1
    return resultados


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = set(m["match_id"] for m in almada if m["team"] == "Pachuca")

    all_matches_meta = {}
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    resultados_pachuca = []
    for mid in pachuca_ids:
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        resultados_pachuca.extend(
            (mid, dur, ev) for dur, ev in transiciones_defensivas_equipo(events, "Pachuca")
        )
    print(
        f"Transiciones defensivas de Pachuca-Almada: {len(resultados_pachuca):,}  ({time.time() - t0:.0f}s)"
    )

    resultados_liga = []
    n_procesados = 0
    for mid, meta in all_matches_meta.items():
        if meta.get("match_status_360") != "available" or mid in pachuca_ids:
            continue
        home = meta["home_team"]["home_team_name"]
        away = meta["away_team"]["away_team_name"]
        if home == "Pachuca" or away == "Pachuca":
            continue
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        resultados_liga.extend(
            (mid, dur, ev) for dur, ev in transiciones_defensivas_equipo(events, home)
        )
        resultados_liga.extend(
            (mid, dur, ev) for dur, ev in transiciones_defensivas_equipo(events, away)
        )
        n_procesados += 1
        if n_procesados % 400 == 0:
            print(
                f"  liga: {n_procesados} partidos, {len(resultados_liga):,} transiciones  ({time.time() - t0:.0f}s)"
            )

    print(f"\nPartidos de liga de referencia: {n_procesados}")
    print(f"Transiciones defensivas de liga (sin Pachuca): {len(resultados_liga):,}")

    mid_p = np.array([r[0] for r in resultados_pachuca], dtype=np.int32)
    dur_p = np.array([r[1] for r in resultados_pachuca], dtype=float)
    ev_p = np.array([r[2] for r in resultados_pachuca], dtype=int)
    mid_l = np.array([r[0] for r in resultados_liga], dtype=np.int32)
    dur_l = np.array([r[1] for r in resultados_liga], dtype=float)
    ev_l = np.array([r[2] for r in resultados_liga], dtype=int)

    print(
        f"\nPachuca: n={len(dur_p)}  recuperacion={(ev_p == 1).sum()} ({(ev_p == 1).mean() * 100:.1f}%)  "
        f"tiro rival (riesgo competidor)={(ev_p == 2).sum()} ({(ev_p == 2).mean() * 100:.1f}%)  "
        f"censura={(ev_p == 0).sum()} ({(ev_p == 0).mean() * 100:.1f}%)  "
        f"duracion media={dur_p.mean():.2f}s  mediana={np.median(dur_p):.1f}s"
    )
    print(
        f"Liga:    n={len(dur_l)}  recuperacion={(ev_l == 1).sum()} ({(ev_l == 1).mean() * 100:.1f}%)  "
        f"tiro rival (riesgo competidor)={(ev_l == 2).sum()} ({(ev_l == 2).mean() * 100:.1f}%)  "
        f"censura={(ev_l == 0).sum()} ({(ev_l == 0).mean() * 100:.1f}%)  "
        f"duracion media={dur_l.mean():.2f}s  mediana={np.median(dur_l):.1f}s"
    )

    np.savez(
        "transicion_defensiva.npz",
        mid_p=mid_p,
        dur_p=dur_p,
        ev_p=ev_p,
        mid_l=mid_l,
        dur_l=dur_l,
        ev_l=ev_l,
    )
    print(f"\nGuardado transicion_defensiva.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
