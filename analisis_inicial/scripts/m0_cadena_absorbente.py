import json, time
from collections import defaultdict
import numpy as np

GRID_X, GRID_Y = 5, 4  # 20 zonas, franjas en x: 0-24-48-72-96-120
N_ZONES = GRID_X * GRID_Y
ABS = ["G", "R", "P", "D"]
STOP_TYPES = {"Foul Committed", "Offside", "Injury Stoppage", "Half End", "Referee Ball-Drop"}
PERDIDA_PASS = {"Incomplete", "Out", "Pass Offside", "Unknown", "Injury Clearance"}
SEASON_IDS = [351, 318, 317, 281, 235, 108]


def zone(loc):
    x, y = loc[0], loc[1]
    zx = min(GRID_X - 1, max(0, int(x / (120 / GRID_X))))
    zy = min(GRID_Y - 1, max(0, int(y / (80 / GRID_Y))))
    return zx * GRID_Y + zy


def possession_to_secuencias(evs, owner):
    """Corta una posesion de StatsBomb en SECUENCIAS: cada una va desde su
    inicio (o desde la absorcion anterior) hasta su PRIMERA absorcion
    (tiro, o pase con resultado de perdida). Devuelve una lista de
    (zonas, absorbente, xg_no_gol_o_None) -- una entrada por secuencia.

    Correccion (2026-09-24, hallazgo C1 de una auditoria cruzada): antes
    del fix, toda la posesion de StatsBomb se trataba como una sola
    trayectoria, clasificada por su "mejor" resultado -- pero StatsBomb no
    cierra la posesion cuando el mismo equipo conserva el balon tras un
    tiro (rebote, cordner a favor) o una perdida que recupera al toque.
    Verificado en los propios datos: ~10% de las posesiones de Pachuca-
    Almada tienen mas de una absorcion real. Una cadena absorbente termina
    en la PRIMERA absorcion, no en la "mejor" de toda la posesion."""
    accion = [
        e
        for e in evs
        if e["team"]["name"] == owner and e["type"]["name"] in ("Pass", "Carry", "Shot")
    ]
    accion.sort(key=lambda e: e["index"])

    secuencias = []
    zonas = []
    primer_evento = None
    for e in accion:
        if primer_evento is None:
            primer_evento = e
        t = e["type"]["name"]
        loc = e.get("location")
        if t == "Shot":
            outcome = e.get("shot", {}).get("outcome", {}).get("name")
            if outcome == "Goal":
                absorb, xg = "G", None
            else:
                absorb, xg = "R", e["shot"].get("statsbomb_xg", 0.0)
            zseq = zonas if zonas else ([zone(loc)] if loc else [])
            if zseq:
                secuencias.append((zseq, absorb, xg, primer_evento))
            zonas, primer_evento = [], None
            continue
        if loc:
            zonas.append(zone(loc))
        if t == "Pass":
            outcome = e.get("pass", {}).get("outcome", {}).get("name")
            if outcome in PERDIDA_PASS:
                if zonas:
                    secuencias.append((zonas, "P", None, primer_evento))
                zonas, primer_evento = [], None

    if zonas:
        last = evs[-1]
        if last.get("out") or last["type"]["name"] in STOP_TYPES:
            secuencias.append((zonas, "D", None, primer_evento))
        else:
            secuencias.append((zonas, "P", None, primer_evento))
    return secuencias


def process_match_for_team(events, team_name):
    """Devuelve: lista de transiciones (i,j) entre zonas [0..N_ZONES-1],
    lista de (zona_final, absorbente), y lista de xg de tiros sin gol.
    Cada posesion puede producir MAS DE UNA transicion a absorbente si se
    cortó en varias secuencias (ver possession_to_secuencias)."""
    events = sorted(events, key=lambda e: e["index"])
    poss = defaultdict(list)
    for e in events:
        if e["period"] in (1, 2):
            poss[e["possession"]].append(e)

    trans = []
    final_abs = []
    xg_no_gol_list = []
    for pid, evs in poss.items():
        owner = evs[0]["possession_team"]["name"]
        if owner != team_name:
            continue
        for seq, absorb, xg, _primer_evento in possession_to_secuencias(evs, owner):
            for i in range(len(seq) - 1):
                trans.append((seq[i], seq[i + 1]))
            trans.append(
                (seq[-1], N_ZONES + ABS.index(absorb))
            )  # nodo absorbente codificado como N_ZONES+k
            final_abs.append((seq[-1], absorb))
            if xg is not None:
                xg_no_gol_list.append(xg)
    return trans, final_abs, xg_no_gol_list


def build_QR(trans_list):
    """trans_list: lista de (i,j) con i en [0,N_ZONES), j en [0,N_ZONES) (transitorio) o
    [N_ZONES, N_ZONES+4) (absorbente). Devuelve Q (NxN) y R (Nx4) en probabilidades, mas los conteos."""
    counts = np.zeros((N_ZONES, N_ZONES + 4))
    for i, j in trans_list:
        counts[i, j] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    probs = counts / row_sums
    Q = probs[:, :N_ZONES]
    R = probs[:, N_ZONES:]
    return Q, R, counts


def solve_absorbing(Q, R):
    I = np.eye(N_ZONES)
    N = np.linalg.inv(I - Q)
    t = N @ np.ones(N_ZONES)
    B = N @ R
    return N, t, B


def main():
    t0 = time.time()
    almada = json.load(open("almada_matches.json", encoding="utf-8"))
    pachuca_ids = [m["match_id"] for m in almada if m["team"] == "Pachuca"]

    print(f"Procesando {len(pachuca_ids)} partidos de Pachuca (Almada)...")
    all_trans, all_final, all_xg = [], [], []
    duraciones_reales, inicios = [], []
    for mid in pachuca_ids:
        events = json.load(open(f"cache_events/events_{mid}.json", encoding="utf-8"))
        trans, final_abs, xg = process_match_for_team(events, "Pachuca")
        all_trans.extend(trans)
        all_final.extend(final_abs)
        all_xg.extend(xg)
        # duracion y zona inicial de cada secuencia (para la prueba de cierre)
        poss = defaultdict(list)
        for e in sorted(events, key=lambda e: e["index"]):
            if e["period"] in (1, 2):
                poss[e["possession"]].append(e)
        for pid, evs in poss.items():
            owner = evs[0]["possession_team"]["name"]
            if owner != "Pachuca":
                continue
            for seq, absorb, xg_val, primer_evento in possession_to_secuencias(evs, owner):
                duraciones_reales.append(len(seq))
                inicios.append(seq[0])

    Q, R, counts = build_QR(all_trans)
    N, t, B = solve_absorbing(Q, R)

    x_bar_gr = float(np.mean(all_xg)) if all_xg else 0.0
    r_vec = np.array([1.0, x_bar_gr, 0.0, 0.0])
    V = B @ r_vec

    print(
        f"Secuencias totales (Pachuca): {len(all_final):,}  (antes del fix C1 eran posesiones completas, menos en numero)"
    )
    print(f"Transiciones totales (Pachuca): {len(all_trans):,}")
    print(f"x_bar (xG promedio de tiros sin gol, para R): {x_bar_gr:.4f}")
    print(f"rho(Q) = {max(abs(np.linalg.eigvals(Q))):.4f} (debe ser <1 para que converja)")
    print(
        f"\nt (acciones esperadas hasta absorcion) -- min={t.min():.2f} max={t.max():.2f} media={t.mean():.2f}"
    )
    print(f"B[:,0] (prob de gol) -- min={B[:, 0].min():.4f} max={B[:, 0].max():.4f}")
    print(f"V (valor de zona, goles esperados) -- min={V.min():.4f} max={V.max():.4f}")

    # ---- prueba de cierre: alpha^T N 1 (duracion media predicha desde la
    # distribucion real de zonas iniciales) contra la duracion media empirica ----
    alpha = np.zeros(N_ZONES)
    for z in inicios:
        alpha[z] += 1
    alpha /= alpha.sum()
    t_pred_medio = alpha @ t
    dur_media_empirica = float(np.mean(duraciones_reales))
    diff_pct = abs(t_pred_medio - dur_media_empirica) / dur_media_empirica * 100
    print(
        f"\nPrueba de cierre: alpha^T N 1 = {t_pred_medio:.3f}  vs. duracion media empirica = {dur_media_empirica:.3f}"
        f"  (diferencia = {diff_pct:.2f}%, debe ser <1%)"
    )
    if diff_pct >= 1.0:
        print(
            "  ADVERTENCIA: la prueba de cierre NO paso, hay trayectorias invalidas en la cadena."
        )
    else:
        print("  OK: la cadena cierra correctamente.")

    np.savez(
        "m0_pachuca_almada.npz",
        Q=Q,
        R=R,
        N=N,
        t=t,
        B=B,
        V=V,
        counts=counts,
        x_bar_gr=x_bar_gr,
        n_transiciones=len(all_trans),
        n_secuencias=len(all_final),
        cierre_diff_pct=diff_pct,
    )

    print(f"\nGuardado m0_pachuca_almada.npz ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
