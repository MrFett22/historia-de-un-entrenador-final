"""Desglose del DiD de sustituciones (did_sustituciones.py): el promedio
agrupando TODAS las sustituciones es debil (DiD=+0.0051, IC roza el
cero). Aqui se prueba si ese promedio esconde senal real en dos
subgrupos:

1. Por MARCADOR al momento del cambio (perdiendo/empatado/ganando) --
   control emparejado por el mismo marcador (no el pool completo), para
   no confundir el efecto de la sustitucion con que el ritmo del partido
   ya cambia solo por el marcador en ese momento.
2. Por TIPO de sustitucion (ofensiva/defensiva/lateral), usando el id de
   posicion de StatsBomb de quien sale vs. quien entra -- el id corre de
   portero (1) a delantero (24) aproximadamente de atras a adelante, asi
   que compararlos da una linea razonable de "sale mas atras, entra mas
   adelante" = ofensiva. Control = pool completo (el tipo no aplica a
   ventanas sin sustitucion).

Misma metrica de valor que el original (1=gol, X_BAR_GR=remate sin gol,
0=nada, agregada por minuto) y misma ventana de 15 min pre/post. A
diferencia del original (que bootstrapea sustituciones sueltas), aqui se
bootstrapea por PARTIDO -- varias sustituciones del mismo partido no son
observaciones independientes.
"""

import json, time
from collections import defaultdict
import numpy as np
from statsmodels.stats.multitest import multipletests
import sys

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import possession_to_secuencias

VENTANA = 15
MIN_MINUTO, MAX_MINUTO = 15, 75
X_BAR_GR = 0.0690
B_REPS = 3000
SEED = 89


def reconstruct_scores(events, home_id, away_id):
    score = {home_id: 0, away_id: 0}
    per_index_score = {}
    for e in events:
        if e["period"] == 5:
            per_index_score[e["index"]] = (score[home_id], score[away_id])
            continue
        t = e["type"]["name"]
        if t == "Shot" and e.get("shot", {}).get("outcome", {}).get("name") == "Goal":
            score[e["team"]["id"]] += 1
        elif t == "Own Goal For":
            score[e["team"]["id"]] += 1
        per_index_score[e["index"]] = (score[home_id], score[away_id])
    return per_index_score


def marcador_bucket(my_s, ri_s):
    if my_s > ri_s:
        return "ganando"
    if my_s < ri_s:
        return "perdiendo"
    return "empatado"


def valor_por_minuto(events, team_name):
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


def marcador_en_minuto(per_index_score, events, is_home, minute):
    """Marcador (propio, rival) al final del minuto dado, buscando el
    ultimo evento con minute<=minute."""
    my_s, ri_s = 0, 0
    for e in events:
        if e.get("minute", 0) > minute:
            break
        s = per_index_score.get(e["index"])
        if s is not None:
            my_s, ri_s = s
    if not is_home:
        my_s, ri_s = ri_s, my_s
    return my_s, ri_s


def posicion_entrante(events, idx_sub, replacement_id):
    for e in events:
        if e["index"] <= idx_sub:
            continue
        if e.get("player", {}).get("id") != replacement_id:
            continue
        pos = e.get("position")
        if pos and pos["id"] != 0:
            return pos["id"]
    return None


def tipo_sub(pos_saliente, pos_entrante):
    if pos_saliente is None or pos_entrante is None:
        return None
    if pos_entrante > pos_saliente:
        return "ofensiva"
    if pos_entrante < pos_saliente:
        return "defensiva"
    return "lateral"


def bootstrap_diff_por_partido(
    treated_vals, treated_mid, control_vals, control_mid, rng, b_reps=B_REPS
):
    m_t = np.unique(treated_mid) if len(treated_mid) else np.array([])
    m_c = np.unique(control_mid) if len(control_mid) else np.array([])
    if len(m_t) == 0 or len(m_c) == 0:
        return np.full(b_reps, np.nan)
    idx_t = {m: np.where(treated_mid == m)[0] for m in m_t}
    idx_c = {m: np.where(control_mid == m)[0] for m in m_c}
    out = np.zeros(b_reps)
    for b in range(b_reps):
        samp_t = rng.choice(m_t, size=len(m_t), replace=True)
        samp_c = rng.choice(m_c, size=len(m_c), replace=True)
        rows_t = np.concatenate([idx_t[m] for m in samp_t])
        rows_c = np.concatenate([idx_c[m] for m in samp_c])
        out[b] = treated_vals[rows_t].mean() - control_vals[rows_c].mean()
    return out


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_matches = [m for m in almada if m["team"] == "Pachuca"]

    all_matches_meta = {}
    for sid in [351, 318, 317, 281, 235, 108]:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    tratado = []  # (mid, valor, marcador, tipo)
    control = []  # (mid, valor, marcador)

    for m in pachuca_matches:
        mid = m["match_id"]
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        events = sorted(events, key=lambda e: e["index"])
        home_id, away_id = meta["home_team"]["home_team_id"], meta["away_team"]["away_team_id"]
        home_name = meta["home_team"]["home_team_name"]
        is_home = home_name == "Pachuca"
        per_index_score = reconstruct_scores(events, home_id, away_id)

        valor = valor_por_minuto(events, "Pachuca")

        subs_mid = []
        for e in events:
            if (
                e["period"] in (1, 2)
                and e["type"]["name"] == "Substitution"
                and e["team"]["name"] == "Pachuca"
            ):
                minuto = e.get("minute", 0)
                if not (MIN_MINUTO <= minuto <= MAX_MINUTO):
                    continue
                subs_mid.append(minuto)
                my_s, ri_s = marcador_en_minuto(per_index_score, events, is_home, minuto)
                marcador = marcador_bucket(my_s, ri_s)

                pos_saliente = e.get("position", {}).get("id")
                replacement_id = e.get("substitution", {}).get("replacement", {}).get("id")
                pos_entrante = (
                    posicion_entrante(events, e["index"], replacement_id)
                    if replacement_id
                    else None
                )
                tipo = tipo_sub(pos_saliente, pos_entrante)

                tratado.append((mid, tasa_ventana(valor, minuto), marcador, tipo))

        for m5 in range(MIN_MINUTO, MAX_MINUTO + 1, 5):
            if any(abs(m5 - sm) <= VENTANA for sm in subs_mid):
                continue
            my_s, ri_s = marcador_en_minuto(per_index_score, events, is_home, m5)
            marcador = marcador_bucket(my_s, ri_s)
            control.append((mid, tasa_ventana(valor, m5), marcador))

    print(
        f"Sustituciones tratadas: {len(tratado)}  |  ventanas de control: {len(control)}  ({time.time() - t0:.0f}s)"
    )

    dt_t = np.dtype([("mid", np.int32), ("valor", float), ("marcador", "U10"), ("tipo", "U10")])
    dt_c = np.dtype([("mid", np.int32), ("valor", float), ("marcador", "U10")])
    arr_t = np.array([(a, b, c, d or "") for a, b, c, d in tratado], dtype=dt_t)
    arr_c = np.array(control, dtype=dt_c)

    rng = np.random.default_rng(SEED)
    resultado = {}

    # --- eje 1: por marcador, control emparejado por marcador ---
    print("\n=== Por marcador al momento del cambio (control emparejado) ===")
    p_vals, filas = [], []
    for cat in ["perdiendo", "empatado", "ganando"]:
        sub_t = arr_t[arr_t["marcador"] == cat]
        sub_c = arr_c[arr_c["marcador"] == cat]
        n_t, n_c = len(sub_t), len(sub_c)
        did_obs = sub_t["valor"].mean() - sub_c["valor"].mean() if n_t and n_c else np.nan
        boot = bootstrap_diff_por_partido(
            sub_t["valor"], sub_t["mid"], sub_c["valor"], sub_c["mid"], rng
        )
        lo, hi = np.nanpercentile(boot, [2.5, 97.5])
        p_boot = min(1.0, 2 * min(np.nanmean(boot <= 0), np.nanmean(boot >= 0)))
        p_vals.append(p_boot)
        print(
            f"  {cat:<12} tratado n={n_t:>3} (media={sub_t['valor'].mean() if n_t else float('nan'):+.4f})  "
            f"control n={n_c:>3} (media={sub_c['valor'].mean() if n_c else float('nan'):+.4f})  "
            f"DiD={did_obs:+.4f}  IC95%=[{lo:+.4f},{hi:+.4f}]  p_boot={p_boot:.4f}"
        )
        filas.append((cat, n_t, n_c, did_obs, lo, hi, p_boot))
    rechaza_bh, q_bh, _, _ = multipletests(p_vals, alpha=0.05, method="fdr_bh")
    for i, cat in enumerate(["perdiendo", "empatado", "ganando"]):
        print(f"     {cat:<12} q_BH={q_bh[i]:.4f}  {'SI' if rechaza_bh[i] else ''}")
    resultado["marcador"] = dict(filas=filas, q_bh=q_bh, rechaza_bh=rechaza_bh)

    # --- eje 2: por tipo de sustitucion, control pooled ---
    print("\n=== Por tipo de sustitución (control = pool completo) ===")
    n_sin_tipo = (arr_t["tipo"] == "").sum()
    print(
        f"  (sin tipo determinable -- sin posicion de salida o de entrada: {n_sin_tipo}/{len(arr_t)})"
    )
    p_vals2, filas2 = [], []
    categorias_tipo = ["ofensiva", "defensiva", "lateral"]
    for cat in categorias_tipo:
        sub_t = arr_t[arr_t["tipo"] == cat]
        n_t, n_c = len(sub_t), len(arr_c)
        did_obs = sub_t["valor"].mean() - arr_c["valor"].mean() if n_t else np.nan
        boot = bootstrap_diff_por_partido(
            sub_t["valor"], sub_t["mid"], arr_c["valor"], arr_c["mid"], rng
        )
        lo, hi = np.nanpercentile(boot, [2.5, 97.5])
        p_boot = min(1.0, 2 * min(np.nanmean(boot <= 0), np.nanmean(boot >= 0)))
        p_vals2.append(p_boot)
        print(
            f"  {cat:<12} tratado n={n_t:>3} (media={sub_t['valor'].mean() if n_t else float('nan'):+.4f})  "
            f"control n={n_c:>3} (media={arr_c['valor'].mean():+.4f})  "
            f"DiD={did_obs:+.4f}  IC95%=[{lo:+.4f},{hi:+.4f}]  p_boot={p_boot:.4f}"
        )
        filas2.append((cat, n_t, n_c, did_obs, lo, hi, p_boot))
    rechaza_bh2, q_bh2, _, _ = multipletests(p_vals2, alpha=0.05, method="fdr_bh")
    for i, cat in enumerate(categorias_tipo):
        print(f"     {cat:<12} q_BH={q_bh2[i]:.4f}  {'SI' if rechaza_bh2[i] else ''}")
    resultado["tipo"] = dict(filas=filas2, q_bh=q_bh2, rechaza_bh=rechaza_bh2)

    to_save = {}
    for eje in resultado:
        filas = resultado[eje]["filas"]
        to_save[f"{eje}_categorias"] = np.array([f[0] for f in filas])
        to_save[f"{eje}_n_t"] = np.array([f[1] for f in filas])
        to_save[f"{eje}_n_c"] = np.array([f[2] for f in filas])
        to_save[f"{eje}_did"] = np.array([f[3] for f in filas])
        to_save[f"{eje}_lo"] = np.array([f[4] for f in filas])
        to_save[f"{eje}_hi"] = np.array([f[5] for f in filas])
        to_save[f"{eje}_p_boot"] = np.array([f[6] for f in filas])
        to_save[f"{eje}_q_bh"] = resultado[eje]["q_bh"]
        to_save[f"{eje}_rechaza_bh"] = resultado[eje]["rechaza_bh"]
    np.savez("did_sustituciones_desglose.npz", **to_save)
    print(f"\nGuardado did_sustituciones_desglose.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
