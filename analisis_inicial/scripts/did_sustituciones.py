"""DiD (diferencias en diferencias) para el impacto de las sustituciones
de Pachuca (Semana 3, ultima pieza de profundidad).

Metrica de valor por posesion, consistente con el vector de recompensa
r=(1, x_bar_GR, 0, 0) ya usado en M0: valor=1 si termina en gol,
valor=x_bar_GR (xG promedio de tiros sin gol, ~0.069) si termina en
remate sin gol, 0 si pierde o se detiene. Se agrega por minuto de
partido para tener una serie fina de "valor generado por Pachuca".

Diseno: para cada sustitucion real de Pachuca en el minuto m (con
15<=m<=75 para tener ventana completa antes/despues), TRATADO =
valor_post15 - valor_pre15 alrededor de esa sustitucion. CONTROL = la
misma diferencia post-pre, pero en ventanas de minutos SIN sustitucion
(de Pachuca) cercana, tomadas de todos los partidos -- para descontar la
tendencia normal del partido (cansancio, marcador) que no tiene nada que
ver con la sustitucion en si. DiD = media(tratado) - media(control), con
bootstrap para el intervalo de confianza.
"""

import json, time, sys
from collections import defaultdict
import numpy as np

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import zone, possession_to_secuencias

VENTANA = 15
MIN_MINUTO, MAX_MINUTO = 15, 75
X_BAR_GR = 0.0690  # de m0_pachuca_almada.npz, Semana 1
SEED = 61


def valor_por_minuto(events, team_name):
    """Devuelve un array de 96 minutos (0-95) con el valor generado por
    team_name en cada minuto (suma de valores de posesiones que arrancan
    en ese minuto)."""
    events = sorted(events, key=lambda e: e["index"])
    poss = defaultdict(list)
    for e in events:
        if e["period"] in (1, 2):
            poss[e["possession"]].append(e)

    valor = np.zeros(96)
    for pid, evs in poss.items():
        owner = evs[0]["possession_team"]["name"]
        if owner != team_name:
            continue
        for seq, absorb, xg_val, primer_evento in possession_to_secuencias(evs, owner):
            v = 1.0 if absorb == "G" else (X_BAR_GR if absorb == "R" else 0.0)
            minuto = min(95, primer_evento.get("minute", 0))
            valor[minuto] += v
    return valor


def tasa_ventana(valor, m, ventana=VENTANA):
    pre = valor[max(0, m - ventana) : m].sum() / ventana
    post = valor[m : m + ventana].sum() / ventana
    return post - pre


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_matches = [m for m in almada if m["team"] == "Pachuca"]

    valores_por_partido = {}
    subs_por_partido = defaultdict(list)

    for m in pachuca_matches:
        mid = m["match_id"]
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        valores_por_partido[mid] = valor_por_minuto(events, "Pachuca")
        for e in events:
            if (
                e["period"] in (1, 2)
                and e["type"]["name"] == "Substitution"
                and e["team"]["name"] == "Pachuca"
            ):
                minuto = e.get("minute", 0)
                if MIN_MINUTO <= minuto <= MAX_MINUTO:
                    subs_por_partido[mid].append(minuto)

    print(f"Partidos con datos: {len(valores_por_partido)}  ({time.time() - t0:.0f}s)")
    n_subs_total = sum(len(v) for v in subs_por_partido.values())
    print(
        f"Sustituciones de Pachuca en ventana valida (min {MIN_MINUTO}-{MAX_MINUTO}): {n_subs_total}"
    )

    tratado = []
    for mid, minutos in subs_por_partido.items():
        for m in minutos:
            tratado.append(tasa_ventana(valores_por_partido[mid], m))
    tratado = np.array(tratado)

    # control: minutos SIN sustitucion (ni propia ni cerca), cada 5 min, en todos los partidos
    control = []
    for mid, valor in valores_por_partido.items():
        subs_mid = subs_por_partido.get(mid, [])
        for m in range(MIN_MINUTO, MAX_MINUTO + 1, 5):
            if any(abs(m - sm) <= VENTANA for sm in subs_mid):
                continue  # muy cerca de una sustitucion real, no sirve de control limpio
            control.append(tasa_ventana(valor, m))
    control = np.array(control)

    print(
        f"\nTratado (alrededor de sustitucion): n={len(tratado)}  media(post-pre)={tratado.mean():+.4f}  sd={tratado.std():.4f}"
    )
    print(
        f"Control (ventanas sin sustitucion cercana): n={len(control)}  media(post-pre)={control.mean():+.4f}  sd={control.std():.4f}"
    )

    did = tratado.mean() - control.mean()
    print(
        f"\nDiD = {did:+.4f}  (valor esperado extra por minuto en los 15 min tras una sustitucion, "
        f"neto de la tendencia normal del partido)"
    )

    rng = np.random.default_rng(SEED)
    diffs_boot = []
    for _ in range(5000):
        t_b = rng.choice(tratado, size=len(tratado), replace=True)
        c_b = rng.choice(control, size=len(control), replace=True)
        diffs_boot.append(t_b.mean() - c_b.mean())
    diffs_boot = np.array(diffs_boot)
    lo, hi = np.percentile(diffs_boot, [2.5, 97.5])
    print(f"IC bootstrap 95% del DiD: [{lo:+.4f}, {hi:+.4f}]")
    if lo > 0 or hi < 0:
        print(
            "  -> significativo: las sustituciones de Pachuca se asocian a un cambio real en el valor generado."
        )
    else:
        print(
            "  -> no significativo: no hay evidencia de que las sustituciones, en promedio, cambien el valor generado "
            "mas alla de la variacion normal del partido."
        )

    np.savez("did_sustituciones.npz", tratado=tratado, control=control, did=did, ci=[lo, hi])
    print(f"\nGuardado did_sustituciones.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
