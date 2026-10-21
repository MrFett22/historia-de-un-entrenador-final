"""Como cambian los patrones de juego de Pachuca-Almada segun el contexto
del partido: marcador (perdiendo/empatado/ganando), fuerza del rival (Elo
pre-partido) y minuto (primeros/medios/ultimos 30'). No basta con ver si
Pachuca cambia -- CUALQUIER equipo cambia algo con el marcador. Lo que
importa es si Pachuca cambia MAS o MENOS que la liga (mismo espiritu que
did_sustituciones.py: una diferencia neta de una referencia, no un antes/
despues suelto).

Unidad de analisis: la SECUENCIA (M0, fix C1 -- una posesion de StatsBomb
puede tener varias). Dos metricas, cada una con su propio bootstrap+BH:
"termina en tiro" (gol o remate, G+R, ya usada en balon_parado.py) y
"pierde el balon" (P). Gol (G) solo no se prueba aparte: muy pocas
secuencias por celda de contexto (30-170) para un IC util, y queda
incluido dentro de "tiro". El desglose G/R/P/D completo se reporta crudo
para contexto cualitativo.

Bootstrap por PARTIDO para toda la incertidumbre (secuencias del mismo
partido estan correlacionadas), con correccion Benjamini-Hochberg DENTRO
de cada combinacion (eje, metrica) -- familias de prueba separadas, igual
que zonas y metricas 360 se corrigen por separado. Las dos metricas
comparten el mismo remuestreo de partidos por replica (mismo bootstrap,
dos lecturas), no se remuestrea dos veces.
"""

import json, time, sys
from collections import defaultdict
import numpy as np
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import possession_to_secuencias

SEASON_IDS = [351, 318, 317, 281, 235, 108]
B_REPS = 2000
SEED = 131

EJES = {
    "marcador": ["perdiendo", "empatado", "ganando"],
    "minuto": ["0-30", "30-60", "60-90"],
    "rival": ["rival_mas_fuerte", "rival_mas_debil_o_similar"],
}
EXTREMOS = {
    "marcador": ("perdiendo", "ganando"),
    "minuto": ("0-30", "60-90"),
    "rival": ("rival_mas_fuerte", "rival_mas_debil_o_similar"),
}
METRICAS = {
    "tiro": lambda absorb: np.isin(absorb, ["G", "R"]),
    "perdida": lambda absorb: absorb == "P",
}


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


def minuto_bucket(minute):
    if minute < 30:
        return "0-30"
    if minute < 60:
        return "30-60"
    return "60-90"


def registros_equipo(events, team_name, home_id, away_id, home_name, elo_own, elo_riv, mid):
    events = sorted(events, key=lambda e: e["index"])
    per_index_score = reconstruct_scores(events, home_id, away_id)
    poss = defaultdict(list)
    for e in events:
        if e["period"] in (1, 2):
            poss[e["possession"]].append(e)

    is_home = team_name == home_name
    rival = "rival_mas_fuerte" if elo_riv > elo_own else "rival_mas_debil_o_similar"
    out = []
    for pid, evs in poss.items():
        owner = evs[0]["possession_team"]["name"]
        if owner != team_name:
            continue
        for seq, absorb, xg_val, primer_evento in possession_to_secuencias(evs, owner):
            idx = primer_evento["index"]
            my_s, ri_s = per_index_score.get(idx, (0, 0))
            if not is_home:
                my_s, ri_s = ri_s, my_s
            marcador = marcador_bucket(my_s, ri_s)
            minuto = minuto_bucket(primer_evento.get("minute", 0))
            out.append((mid, marcador, minuto, rival, absorb))
    return out


def tasas_obs(sub):
    """Devuelve {metrica: tasa} sobre el sub-array completo (sin bootstrap)."""
    if len(sub) == 0:
        return {m: np.nan for m in METRICAS}
    return {m: fn(sub["absorb"]).mean() for m, fn in METRICAS.items()}


def bootstrap_tasas_por_partido(sub, rng, b_reps=B_REPS):
    """Bootstrap por partido; devuelve {metrica: array(b_reps)}, remuestreando
    los partidos UNA vez por replica y leyendo las dos metricas del mismo
    remuestreo (no se resamplea por separado para cada una)."""
    matches = np.unique(sub["mid"])
    if len(matches) == 0:
        return {m: np.full(b_reps, np.nan) for m in METRICAS}
    idx_por_partido = {m: np.where(sub["mid"] == m)[0] for m in matches}
    out = {m: np.zeros(b_reps) for m in METRICAS}
    for b in range(b_reps):
        sampled = rng.choice(matches, size=len(matches), replace=True)
        rows = np.concatenate([idx_por_partido[m] for m in sampled])
        absorb_b = sub["absorb"][rows] if len(rows) else np.array([], dtype=sub["absorb"].dtype)
        for m, fn in METRICAS.items():
            out[m][b] = fn(absorb_b).mean() if len(absorb_b) else np.nan
    return out


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = set(m["match_id"] for m in almada if m["team"] == "Pachuca")
    elo_data = json.load(open("elo_resultados.json", encoding="utf-8"))
    pre_match_elo = elo_data["pre_match_elo"]

    all_matches_meta = {}
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    registros_pachuca = []
    for mid in pachuca_ids:
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        elo_info = pre_match_elo.get(str(mid)) or pre_match_elo.get(mid)
        if elo_info is None:
            continue
        home_id, away_id = meta["home_team"]["home_team_id"], meta["away_team"]["away_team_id"]
        home_name = meta["home_team"]["home_team_name"]
        is_home = home_name == "Pachuca"
        elo_own = elo_info["home_elo"] if is_home else elo_info["away_elo"]
        elo_riv = elo_info["away_elo"] if is_home else elo_info["home_elo"]
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        registros_pachuca.extend(
            registros_equipo(events, "Pachuca", home_id, away_id, home_name, elo_own, elo_riv, mid)
        )

    print(f"Secuencias de Pachuca-Almada: {len(registros_pachuca):,}  ({time.time() - t0:.0f}s)")

    registros_liga = []
    n_procesados = 0
    for mid, meta in all_matches_meta.items():
        if meta.get("match_status_360") != "available" or mid in pachuca_ids:
            continue
        home, away = meta["home_team"]["home_team_name"], meta["away_team"]["away_team_name"]
        if home == "Pachuca" or away == "Pachuca":
            continue
        elo_info = pre_match_elo.get(str(mid)) or pre_match_elo.get(mid)
        if elo_info is None:
            continue
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        home_id, away_id = meta["home_team"]["home_team_id"], meta["away_team"]["away_team_id"]
        registros_liga.extend(
            registros_equipo(
                events,
                home,
                home_id,
                away_id,
                home,
                elo_info["home_elo"],
                elo_info["away_elo"],
                mid,
            )
        )
        registros_liga.extend(
            registros_equipo(
                events,
                away,
                home_id,
                away_id,
                home,
                elo_info["away_elo"],
                elo_info["home_elo"],
                mid,
            )
        )
        n_procesados += 1
        if n_procesados % 400 == 0:
            print(f"  liga: {n_procesados} partidos  ({time.time() - t0:.0f}s)")

    print(f"\nPartidos de liga de referencia: {n_procesados}")
    print(f"Secuencias de liga: {len(registros_liga):,}")

    dt = np.dtype(
        [
            ("mid", np.int32),
            ("marcador", "U10"),
            ("minuto", "U6"),
            ("rival", "U25"),
            ("absorb", "U1"),
        ]
    )
    arr_p = np.array(registros_pachuca, dtype=dt)
    arr_l = np.array(registros_liga, dtype=dt)

    rng = np.random.default_rng(SEED)
    resultado = {}
    to_save = {}

    for eje, categorias in EJES.items():
        print(f"\n=== Eje: {eje} ===")

        subs_p, subs_l, boot_p, boot_l = {}, {}, {}, {}
        for cat in categorias:
            subs_p[cat] = arr_p[arr_p[eje] == cat]
            subs_l[cat] = arr_l[arr_l[eje] == cat]
            boot_p[cat] = bootstrap_tasas_por_partido(subs_p[cat], rng)
            boot_l[cat] = bootstrap_tasas_por_partido(subs_l[cat], rng)

        for metrica in METRICAS:
            print(f"\n  --- métrica: {metrica} ---")
            p_vals = []
            filas = []
            for cat in categorias:
                sub_p, sub_l = subs_p[cat], subs_l[cat]
                n_p, n_l = len(sub_p), len(sub_l)
                t_p = tasas_obs(sub_p)[metrica]
                t_l = tasas_obs(sub_l)[metrica]

                diff_boot = boot_p[cat][metrica] - boot_l[cat][metrica]
                lo, hi = np.nanpercentile(diff_boot, [2.5, 97.5])
                p_boot = min(1.0, 2 * min(np.nanmean(diff_boot <= 0), np.nanmean(diff_boot >= 0)))
                p_vals.append(p_boot)

                counts_p = {a: (sub_p["absorb"] == a).sum() for a in "GRPD"}
                print(
                    f"  {cat:<28} Pachuca: n={n_p:>5}  G={counts_p['G']:>3} R={counts_p['R']:>4} "
                    f"P={counts_p['P']:>4} D={counts_p['D']:>4}  {metrica}={t_p * 100:5.1f}%   "
                    f"Liga: n={n_l:>6} {metrica}={t_l * 100:5.1f}%   diff={(t_p - t_l) * 100:+5.1f}pp "
                    f"IC95%=[{lo * 100:+.1f},{hi * 100:+.1f}]pp  p_boot={p_boot:.4f}"
                )
                filas.append((cat, n_p, t_p, n_l, t_l, lo, hi, p_boot))

            rechaza_bh, q_bh, _, _ = multipletests(p_vals, alpha=0.05, method="fdr_bh")
            print(f"  -> sobreviven BH ({eje}/{metrica}): {rechaza_bh.sum()}/{len(categorias)}")
            for i, cat in enumerate(categorias):
                sig = "SI" if rechaza_bh[i] else ""
                print(f"     {cat:<28} q_BH={q_bh[i]:.4f}  {sig}")

            cat_a, cat_b = EXTREMOS[eje]
            did_boot = (boot_p[cat_b][metrica] - boot_p[cat_a][metrica]) - (
                boot_l[cat_b][metrica] - boot_l[cat_a][metrica]
            )
            did_obs = (tasas_obs(subs_p[cat_b])[metrica] - tasas_obs(subs_p[cat_a])[metrica]) - (
                tasas_obs(subs_l[cat_b])[metrica] - tasas_obs(subs_l[cat_a])[metrica]
            )
            lo_did, hi_did = np.nanpercentile(did_boot, [2.5, 97.5])
            p_did = min(1.0, 2 * min(np.nanmean(did_boot <= 0), np.nanmean(did_boot >= 0)))
            print(
                f"\n  DiD ({cat_b} vs {cat_a}, Pachuca menos liga, {metrica}): {did_obs * 100:+.1f}pp  "
                f"IC95%=[{lo_did * 100:+.1f},{hi_did * 100:+.1f}]pp  p_boot={p_did:.4f}"
            )
            if lo_did > 0 or hi_did < 0:
                print(
                    f"     -> Pachuca reacciona {'MAS' if did_obs > 0 else 'MENOS'} que la liga en {metrica}."
                )
            else:
                print(
                    f"     -> no hay evidencia de que Pachuca reaccione distinto a la liga en {metrica}."
                )

            key = f"{eje}_{metrica}"
            resultado[key] = dict(
                filas=filas,
                q_bh=q_bh,
                rechaza_bh=rechaza_bh,
                did_obs=did_obs,
                did_ci=[lo_did, hi_did],
                did_p=p_did,
            )
            to_save[f"{key}_categorias"] = np.array([f[0] for f in filas])
            to_save[f"{key}_n_p"] = np.array([f[1] for f in filas])
            to_save[f"{key}_tasa_p"] = np.array([f[2] for f in filas])
            to_save[f"{key}_n_l"] = np.array([f[3] for f in filas])
            to_save[f"{key}_tasa_l"] = np.array([f[4] for f in filas])
            to_save[f"{key}_lo"] = np.array([f[5] for f in filas])
            to_save[f"{key}_hi"] = np.array([f[6] for f in filas])
            to_save[f"{key}_p_boot"] = np.array([f[7] for f in filas])
            for campo in ("q_bh", "rechaza_bh", "did_obs", "did_ci", "did_p"):
                to_save[f"{key}_{campo}"] = resultado[key][campo]

    np.savez("contexto_patrones.npz", **to_save, allow_pickle=True)
    print(f"\nGuardado contexto_patrones.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
