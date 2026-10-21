"""Simulador validado (Semana 3, pieza de profundidad): usa el M1 ya
ajustado (softmax con onehot(origen)+x+x*is_pachuca) para simular
posesiones completas de Pachuca partido por partido, manteniendo fijo el
contexto real de cada posesion (marcador, periodo, local/visita,
diferencia de Elo) y la zona inicial real, pero dejando que el destino
de cada paso se muestree del modelo. Se compara, a nivel partido, el
numero de posesiones que terminan en gol simuladas vs. las reales -- si
el simulador reproduce bien la macro-estadistica (goles por partido), es
evidencia de que el modelo M1 no solo ajusta bien en el sentido de
verosimilitud sino que genera partidos "jugables" razonables.
"""

import json, time, sys
import numpy as np

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import zone, possession_to_secuencias, N_ZONES
from m1_dataset import reconstruct_scores, marcador_estado, periodo_frac

N_ABS = 4
N_CLASSES = N_ZONES + N_ABS
MAX_STEPS = 100
N_SIM_POR_PARTIDO = 20  # cuantas veces se simula cada partido completo, para promediar ruido
SEED = 53


def softmax_probs(feat_row, coef, intercept):
    logits = coef @ feat_row + intercept
    logits -= logits.max()
    p = np.exp(logits)
    return p / p.sum()


def build_feat(zona, x, is_pachuca=1):
    onehot = np.zeros(N_ZONES)
    onehot[zona] = 1
    x_int = np.array(x) * is_pachuca
    return np.concatenate([onehot, x, x_int])


def simular_posesion(zona_inicial, x, coef, intercept, rng):
    z = zona_inicial
    for _ in range(MAX_STEPS):
        feat = build_feat(z, x)
        probs = softmax_probs(feat, coef, intercept)
        dest = rng.choice(N_CLASSES, p=probs)
        if dest >= N_ZONES:
            return ["G", "R", "P", "D"][dest - N_ZONES]
        z = dest
    return "D"  # no absorbio en MAX_STEPS, se cuenta como detencion


def main():
    t0 = time.time()
    modelo = np.load("m1_modelo.npz", allow_pickle=True)
    coef, intercept = modelo["coef"], modelo["intercept"]

    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_matches = [m for m in almada if m["team"] == "Pachuca"]

    elo_data = json.load(open("elo_resultados.json", encoding="utf-8"))
    pre_match_elo = elo_data["pre_match_elo"]

    all_matches_meta = {}
    for sid in [351, 318, 317, 281, 235, 108]:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    rng = np.random.default_rng(SEED)
    goles_reales, goles_sim_media, goles_sim_todas_reps = [], [], []

    for idx_m, m in enumerate(pachuca_matches):
        mid = m["match_id"]
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        events.sort(key=lambda e: e["index"])
        home_id, away_id = meta["home_team"]["home_team_id"], meta["away_team"]["away_team_id"]
        home_name, away_name = (
            meta["home_team"]["home_team_name"],
            meta["away_team"]["away_team_name"],
        )
        per_index_score = reconstruct_scores(events, home_id, away_id)
        elo_info = pre_match_elo.get(str(mid)) or pre_match_elo.get(mid)
        if elo_info is None:
            continue
        elo_home, elo_away = elo_info["home_elo"], elo_info["away_elo"]
        is_home = home_name == "Pachuca"
        local_visita = 1 if is_home else 0
        elo_own = elo_home if is_home else elo_away
        elo_riv = elo_away if is_home else elo_home
        elo_diff = (elo_own - elo_riv) / 400.0

        from collections import defaultdict

        poss = defaultdict(list)
        for e in events:
            if e["period"] in (1, 2):
                poss[e["possession"]].append(e)

        secuencias_partido = []  # (zona_inicial, x)
        n_goles_real = 0
        for pid, evs in poss.items():
            owner = evs[0]["possession_team"]["name"]
            if owner != "Pachuca":
                continue
            for seq, absorb, xg_val, primer_evento in possession_to_secuencias(evs, owner):
                if absorb == "G":
                    n_goles_real += 1
                start_idx = primer_evento["index"]
                my_s, ri_s = per_index_score.get(start_idx, (0, 0))
                if not is_home:
                    my_s, ri_s = ri_s, my_s
                marcador = marcador_estado(my_s, ri_s)
                minute = primer_evento.get("minute", 0)
                per_frac = periodo_frac(minute)
                x = np.array([marcador, per_frac, local_visita, elo_diff], dtype=float)
                secuencias_partido.append((seq[0], x))

        goles_sim_reps = []
        for _ in range(N_SIM_POR_PARTIDO):
            n_g = 0
            for zona0, x in secuencias_partido:
                if simular_posesion(zona0, x, coef, intercept, rng) == "G":
                    n_g += 1
            goles_sim_reps.append(n_g)

        goles_reales.append(n_goles_real)
        goles_sim_media.append(np.mean(goles_sim_reps))
        goles_sim_todas_reps.append(goles_sim_reps)

        if (idx_m + 1) % 30 == 0:
            print(f"  {idx_m + 1}/{len(pachuca_matches)} partidos  ({time.time() - t0:.0f}s)")

    goles_reales = np.array(goles_reales)
    goles_sim_media = np.array(goles_sim_media)
    goles_sim_todas_reps = np.array(goles_sim_todas_reps)  # (n_partidos, N_SIM_POR_PARTIDO)

    print(f"\nPartidos simulados: {len(goles_reales)}")
    print(
        f"Goles reales por partido: media={goles_reales.mean():.3f}  sd={goles_reales.std():.3f}  total={goles_reales.sum()}"
    )
    print(
        f"Goles simulados por partido (promedio de {N_SIM_POR_PARTIDO} corridas, ESTE PROMEDIO tiene "
        f"menos varianza que una sola corrida por construccion): "
        f"media={goles_sim_media.mean():.3f}  sd={goles_sim_media.std():.3f}  total_esperado={goles_sim_media.sum():.1f}"
    )
    diff_pct_agregado = abs(goles_sim_media.sum() - goles_reales.sum()) / goles_reales.sum() * 100
    print(f"  -> diferencia agregada: {diff_pct_agregado:.2f}%")

    corr = np.corrcoef(goles_reales, goles_sim_media)[0, 1]
    print(f"Correlacion (goles reales vs. esperado simulado, a nivel partido): {corr:.3f}")

    from scipy import stats

    # comparacion JUSTA de variabilidad: una sola realizacion simulada por partido (no el promedio)
    una_rep = goles_sim_todas_reps[:, 0]
    ks_stat, ks_p = stats.ks_2samp(goles_reales, una_rep)
    print(
        f"\nKS (goles reales vs. UNA sola realizacion simulada por partido, comparacion justa de varianza): "
        f"D={ks_stat:.4f}  p={ks_p:.4f}"
    )
    print(
        f"  una_rep: media={una_rep.mean():.3f}  sd={una_rep.std():.3f}  (vs. reales sd={goles_reales.std():.3f})"
    )

    # calibracion: percentil del valor real dentro de las 20 corridas simuladas de su propio partido
    percentiles = np.array(
        [
            (goles_sim_todas_reps[i] < goles_reales[i]).mean()
            + 0.5 * (goles_sim_todas_reps[i] == goles_reales[i]).mean()
            for i in range(len(goles_reales))
        ]
    )
    print(
        f"\nCalibracion: percentil del valor real dentro de la distribucion simulada de su propio partido."
    )
    print(
        f"  Si el modelo esta bien calibrado, estos percentiles deberian ser ~uniformes en [0,1]."
    )
    print(
        f"  media={percentiles.mean():.3f} (ideal=0.5)  frac<0.1={(percentiles < 0.1).mean():.2f}  frac>0.9={(percentiles > 0.9).mean():.2f}"
    )

    np.savez(
        "simulador_validado.npz",
        goles_reales=goles_reales,
        goles_sim_media=goles_sim_media,
        goles_sim_todas_reps=goles_sim_todas_reps,
        corr=corr,
        ks_stat=ks_stat,
        ks_p=ks_p,
        percentiles=percentiles,
    )
    print(f"\nGuardado simulador_validado.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
