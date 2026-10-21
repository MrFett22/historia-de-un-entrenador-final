"""Balon parado desglosado por tipo (reto 5.4, profundidad): en vez de
agrupar corner y tiro libre en un solo "balon parado" (balon_parado.py),
se analizan por separado tres tipos, cada uno ofensivo y defensivo:
  - CORNER: play_pattern = "From Corner".
  - TIRO LIBRE CERCA DEL AREA: play_pattern = "From Free Kick" y el saque
    arranca en el tercio de ataque (x>=80 en el marco del que cobra) --
    un tiro libre desde campo propio no es una amenaza directa de gol,
    uno cerca del area si.
  - SAQUE DE BANDA MUY OFENSIVO: play_pattern = "From Throw In" y arranca
    en el tercio de ataque (x>=80) -- un saque largo directo a zona de
    remate, no un saque de reinicio en campo propio.
Mismo umbral (x>=80, ultimos 40m) para los dos tipos con filtro de
ubicacion, por simplicidad y consistencia.

Misma maquinaria que balon_parado.py: M0 (clasificacion G/R/P/D de la
PRIMERA secuencia de la posesion, fix C1), bootstrap por PARTIDO (no por
balon parado suelto). A diferencia del original, aqui se corrige por
Benjamini-Hochberg DENTRO de cada metrica (termina en tiro, gol) a traves
de las 6 celdas (3 tipos x ofensivo/defensivo) -- familias de prueba
separadas por metrica, igual que el resto del proyecto.
"""

import json, time
from collections import defaultdict
import numpy as np
from statsmodels.stats.multitest import multipletests
import sys

sys.path.insert(0, "scripts")
from m0_cadena_absorbente import possession_to_secuencias, ABS

SEASON_IDS = [351, 318, 317, 281, 235, 108]
B_REPS = 2000
SEED = 151
X_TERCIO_ATAQUE = 80.0

TIPOS = {
    "corner": ("From Corner", None),
    "tiro_libre_cerca_area": ("From Free Kick", X_TERCIO_ATAQUE),
    "saque_banda_ofensivo": ("From Throw In", X_TERCIO_ATAQUE),
}
ETIQUETAS_TIPO = {
    "corner": "Tiro de esquina",
    "tiro_libre_cerca_area": "Tiro libre cerca del area (x>=80)",
    "saque_banda_ofensivo": "Saque de banda muy ofensivo (x>=80)",
}


def posesiones_tipo(events, team_name, mid, play_pattern, x_min):
    events = sorted(events, key=lambda e: e["index"])
    poss = defaultdict(list)
    for e in events:
        if e["period"] in (1, 2):
            poss[e["possession"]].append(e)

    resultados = []
    for pid, evs in poss.items():
        owner = evs[0]["possession_team"]["name"]
        if owner != team_name:
            continue
        if evs[0].get("play_pattern", {}).get("name") != play_pattern:
            continue
        if x_min is not None:
            loc = evs[0].get("location")
            if loc is None or loc[0] < x_min:
                continue
        secuencias = possession_to_secuencias(evs, owner)
        if not secuencias:
            continue
        _, absorb, _, _ = secuencias[0]
        resultados.append((mid, absorb))
    return resultados


def tasa(resultados, cnt_fn):
    n = len(resultados)
    if n == 0:
        return np.nan
    x = sum(1 for _, ab in resultados if cnt_fn(ab))
    return x / n


def bootstrap_por_partido(resultados, cnt_fn, rng, b_reps=B_REPS):
    por_partido = defaultdict(list)
    for mid, ab in resultados:
        por_partido[mid].append(ab)
    matches = list(por_partido.keys())
    n_matches = len(matches)
    if n_matches == 0:
        return np.full(b_reps, np.nan)
    tasas = np.zeros(b_reps)
    for b in range(b_reps):
        idx = rng.integers(0, n_matches, size=n_matches)
        absorbs_b = [ab for i in idx for ab in por_partido[matches[i]]]
        n_b = len(absorbs_b)
        tasas[b] = sum(1 for ab in absorbs_b if cnt_fn(ab)) / n_b if n_b > 0 else np.nan
    return tasas


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = set(m["match_id"] for m in almada if m["team"] == "Pachuca")

    all_matches_meta = {}
    for sid in SEASON_IDS:
        for m in json.load(open(f"matches_{sid}.json", encoding="utf-8")):
            all_matches_meta[m["match_id"]] = m

    # ---- referencia de liga, ofensivo por tipo (se reutiliza tambien
    # como referencia defensiva, igual que balon_parado.py) ----
    res_liga_por_tipo = {t: [] for t in TIPOS}
    n_procesados = 0
    for mid, meta in all_matches_meta.items():
        if meta.get("match_status_360") != "available" or mid in pachuca_ids:
            continue
        home, away = meta["home_team"]["home_team_name"], meta["away_team"]["away_team_name"]
        if home == "Pachuca" or away == "Pachuca":
            continue
        try:
            events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        except FileNotFoundError:
            continue
        for tipo, (pp, xmin) in TIPOS.items():
            res_liga_por_tipo[tipo].extend(posesiones_tipo(events, home, mid, pp, xmin))
            res_liga_por_tipo[tipo].extend(posesiones_tipo(events, away, mid, pp, xmin))
        n_procesados += 1
        if n_procesados % 400 == 0:
            print(f"  liga: {n_procesados} partidos  ({time.time() - t0:.0f}s)")

    print(f"\nPartidos de liga de referencia: {n_procesados}")
    for tipo in TIPOS:
        print(f"  {ETIQUETAS_TIPO[tipo]:<38} liga n={len(res_liga_por_tipo[tipo])}")

    # ---- Pachuca: ofensivo (propio) y defensivo (del rival contra Pachuca) ----
    res_of_pachuca = {t: [] for t in TIPOS}
    res_def_pachuca = {t: [] for t in TIPOS}
    for mid in pachuca_ids:
        meta = all_matches_meta.get(mid)
        if meta is None:
            continue
        home, away = meta["home_team"]["home_team_name"], meta["away_team"]["away_team_name"]
        rival = away if home == "Pachuca" else home
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        for tipo, (pp, xmin) in TIPOS.items():
            res_of_pachuca[tipo].extend(posesiones_tipo(events, "Pachuca", mid, pp, xmin))
            res_def_pachuca[tipo].extend(posesiones_tipo(events, rival, mid, pp, xmin))

    print(f"\nPachuca-Almada, por tipo:")
    for tipo in TIPOS:
        print(
            f"  {ETIQUETAS_TIPO[tipo]:<38} ofensivo n={len(res_of_pachuca[tipo])}  "
            f"defensivo n={len(res_def_pachuca[tipo])}"
        )

    rng = np.random.default_rng(SEED)
    metricas = {"tiro": lambda ab: ab in ("G", "R"), "gol": lambda ab: ab == "G"}
    filas = {
        metrica: [] for metrica in metricas
    }  # (etiqueta, n_p, tasa_p, n_l, tasa_l, lo, hi, p_boot)

    resultados_guardar = {}
    for lado, res_pachuca in [("ofensivo", res_of_pachuca), ("defensivo", res_def_pachuca)]:
        for tipo in TIPOS:
            res_p = res_pachuca[tipo]
            res_l = res_liga_por_tipo[tipo]
            n_p, n_l = len(res_p), len(res_l)
            counts_p = {a: sum(1 for _, ab in res_p if ab == a) for a in ABS}
            print(f"\n--- {ETIQUETAS_TIPO[tipo]} ({lado}) ---")
            print(f"  Pachuca: n={n_p}  " + "  ".join(f"{a}={counts_p[a]}" for a in ABS))
            for metrica, cnt_fn in metricas.items():
                t_p, t_l = tasa(res_p, cnt_fn), tasa(res_l, cnt_fn)
                boot_p = bootstrap_por_partido(res_p, cnt_fn, rng)
                boot_l = bootstrap_por_partido(res_l, cnt_fn, rng)
                diff_boot = boot_p - boot_l
                lo, hi = np.nanpercentile(diff_boot, [2.5, 97.5])
                p_boot = min(1.0, 2 * min(np.nanmean(diff_boot <= 0), np.nanmean(diff_boot >= 0)))
                print(
                    f"    {metrica:<6} Pachuca={t_p * 100:5.1f}%  Liga={t_l * 100:5.1f}%  "
                    f"diff={(t_p - t_l) * 100:+5.1f}pp  IC95%=[{lo * 100:+.1f},{hi * 100:+.1f}]pp  p_boot={p_boot:.4f}"
                )
                filas[metrica].append((f"{tipo}_{lado}", n_p, t_p, n_l, t_l, lo, hi, p_boot))

    print("\n=== Correccion Benjamini-Hochberg (dentro de cada métrica, 6 celdas) ===")
    for metrica in metricas:
        p_vals = [f[7] for f in filas[metrica]]
        rechaza_bh, q_bh, _, _ = multipletests(p_vals, alpha=0.05, method="fdr_bh")
        print(f"\n  métrica: {metrica}")
        for i, f in enumerate(filas[metrica]):
            print(f"    {f[0]:<30} q_BH={q_bh[i]:.4f}  {'SI' if rechaza_bh[i] else ''}")
        resultados_guardar[f"{metrica}_etiquetas"] = np.array([f[0] for f in filas[metrica]])
        resultados_guardar[f"{metrica}_n_p"] = np.array([f[1] for f in filas[metrica]])
        resultados_guardar[f"{metrica}_tasa_p"] = np.array([f[2] for f in filas[metrica]])
        resultados_guardar[f"{metrica}_n_l"] = np.array([f[3] for f in filas[metrica]])
        resultados_guardar[f"{metrica}_tasa_l"] = np.array([f[4] for f in filas[metrica]])
        resultados_guardar[f"{metrica}_lo"] = np.array([f[5] for f in filas[metrica]])
        resultados_guardar[f"{metrica}_hi"] = np.array([f[6] for f in filas[metrica]])
        resultados_guardar[f"{metrica}_p_boot"] = np.array([f[7] for f in filas[metrica]])
        resultados_guardar[f"{metrica}_q_bh"] = q_bh
        resultados_guardar[f"{metrica}_rechaza_bh"] = rechaza_bh

    np.savez("balon_parado_desglose.npz", **resultados_guardar)
    print(f"\nGuardado balon_parado_desglose.npz ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
