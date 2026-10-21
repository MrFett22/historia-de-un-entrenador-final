"""Generador sintético con verdad conocida (07_PRUEBAS.md).

Produce las MISMAS tablas que `datos/repo.py` saca de StatsBomb:
  partidos     match_id, temporada, jornada, fecha, local, visitante, goles_local, goles_visitante,
               tecnico_local, tecnico_visitante, elo_local, elo_visitante, etapa
  juego        match_id, equipo, rival, local, tramo, m, k, n, remates, xg, goles
               (n, remates, xg y goles ya vienen ponderados por r_sk: suma de responsabilidades)
  exposicion   match_id, equipo, tramo, m, minutos
  saques       match_id, equipo, rival, local, tramo, m, u, n, remates, xg, goles
  cambios      match_id, equipo, minuto, m, tipo
  panel        match_id, equipo, minuto, m, cambio        (minutos 45..89 con cambios disponibles)
Los partidos se generan con el mismo modelo de intensidad que usa el motor: conteos de
secuencias Poisson(λ π), remates Binomiales y goles Binomiales (la composición sigue siendo
Poisson con media μ por minuto, igual que en la recursión exacta).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import config
from ..modelos.balon_parado import balon_parado
from ..modelos.cambios import MIN_INICIO, N_MIN, hazard, prob_tipo
from ..modelos.eficiencia import eficiencia
from ..modelos.familias import mezcla
from ..modelos.llegada import ritmo, tramo_minuto
from ..tipos import BLOQUES, COMPONENTES, FAMILIAS, K, Q, REF, U, Liga, bloque_de

MAX_CAMBIOS = 5


@dataclass
class Verdad:
    liga: Liga
    theta: np.ndarray  # (n_tecnicos, Q)
    phi: np.ndarray  # (n_clubes, n_temporadas, Q)
    eps: dict  # (tecnico, club) -> (Q,)
    sigmas: np.ndarray  # (Q, 4): sigma_theta, sigma_phi, sigma_int, sigma_delta
    clubes: list
    tecnicos: list


def liga_sintetica(cfg: dict | None = None) -> Liga:
    cfg = cfg or config.cargar()
    s = cfg["sintetico"]
    pi = np.array(cfg["familias"]["pi"])
    perfil = np.array([1.00, 1.02, 1.01, 0.98, 1.00, 0.99])
    b = np.zeros((K, 6))
    filas = [k for k in range(K) if k != REF]
    for r, k in enumerate(filas):
        b[k, 0] = np.log(pi[k] / pi[REF])
        b[k, 1:] = s["b_liga"][r]
    T = cfg["partido"]["minutos"]
    r_bar = np.outer(np.array(s["saques_por_partido"]) / T, perfil)
    hb = -3.6 + 0.045 * np.arange(N_MIN)
    hb[0] += 2.0  # cambios en el descanso
    from ..modelos.cadena import cadenas_sinteticas

    Pc, muc = cadenas_sinteticas(cfg["familias"]["largo"], cfg["familias"]["p_remate"])
    return Liga(
        P_cadenas=Pc,
        mu_cadenas=muc,
        lam_bar=s["secuencias_por_minuto"] * perfil,
        h_ritmo=s["ventaja_local_ritmo"],
        b_liga=b,
        p_bar=np.array(cfg["familias"]["p_remate"]),
        g_bar=np.array(s["xg_por_remate"]),
        r_bar=r_bar,
        h_bp=0.05,
        q_bar=np.array(s["q_capa1"]),
        kappa=np.array(s["kappa"]),
        hazard_base=hb,
        hazard_m=np.array([0.3, 0.0, -0.1]),
        tipo_base=np.array([[-0.5, 0.0, 0.8], [0.0, 0.3, 0.2], [0.8, 0.3, -0.6]]),
        minutos=T,
    )


def _sigmas(cfg) -> np.ndarray:
    sg = cfg["sintetico"]["sigmas"]
    out = np.zeros((Q, 4))
    for q, nombre in enumerate(COMPONENTES):
        out[q] = sg.get(bloque_de(nombre), sg["defecto"])
    return out


def _round_robin(n: int, rng) -> list[list[tuple[int, int]]]:
    """Método del círculo: n−1 jornadas, localía alternada."""
    eq = list(rng.permutation(n))
    jornadas = []
    for j in range(n - 1):
        par = []
        for i in range(n // 2):
            a, b = eq[i], eq[n - 1 - i]
            par.append((a, b) if (j + i) % 2 == 0 else (b, a))
        jornadas.append(par)
        eq = [eq[0]] + [eq[-1]] + eq[1:-1]
    return jornadas


def _asignaciones(n_clubes, n_temp, n_tec, jornadas, cfg, rng):
    """tec[club, temporada, jornada] con cambios entre temporadas y a mitad de temporada."""
    s = cfg["sintetico"]
    for _ in range(200):
        tec = np.zeros((n_clubes, n_temp, jornadas), dtype=int)
        actual = list(range(n_clubes))
        libres_nuevos = list(range(n_clubes, n_tec))
        libres_usados: list[int] = []
        historial = {t: {c} for c, t in enumerate(actual)}
        mitad = 0

        def contratar(club):
            quedan = len(libres_nuevos)
            if quedan and (rng.random() < 0.5 or not libres_usados or quedan >= (n_temp - t) * 3):
                return libres_nuevos.pop(rng.integers(quedan))
            cand = [x for x in libres_usados if club not in historial[x]] or libres_usados
            x = cand[rng.integers(len(cand))]
            libres_usados.remove(x)
            return x

        for t in range(n_temp):
            if t > 0:
                for club in rng.choice(n_clubes, 5, replace=False):
                    libres_usados.append(actual[club])
                    nuevo = contratar(club)
                    historial.setdefault(nuevo, set()).add(club)
                    actual[club] = nuevo
            tec[:, t, :] = np.array(actual)[:, None]
            club = rng.integers(n_clubes)  # cambio a mitad de temporada
            libres_usados.append(actual[club])
            nuevo = contratar(club)
            historial.setdefault(nuevo, set()).add(club)
            actual[club] = nuevo
            tec[club, t, jornadas // 2 :] = nuevo
            mitad += 1
        usados = np.unique(tec)
        movers = sum(len(v) >= 2 for v in historial.values())
        completo = n_temp >= s["temporadas"]  # versiones cortas (pruebas) no exigen todo
        if not completo or (
            len(usados) == n_tec
            and movers >= s["min_cambian_club"]
            and mitad >= s["min_cambios_mitad"]
        ):
            return tec
    raise RuntimeError("no se logró una asignación sintética válida")


def generar(
    n_temporadas: int | None = None,
    semilla: int | None = None,
    cfg: dict | None = None,
    ruido_r: float = 0.05,
) -> tuple[dict[str, pd.DataFrame], Verdad]:
    cfg = cfg or config.cargar()
    s = cfg["sintetico"]
    semilla = cfg["semilla"] if semilla is None else semilla
    rng = np.random.default_rng([semilla, 7])
    nc, nt = s["clubes"], n_temporadas or s["temporadas"]
    ntec = s["tecnicos"]
    liga = liga_sintetica(cfg)
    T = liga.minutos
    sig = _sigmas(cfg)
    theta = rng.normal(size=(ntec, Q)) * sig[:, 0]
    phi = np.zeros((nc, nt, Q))
    phi[:, 0] = rng.normal(size=(nc, Q)) * sig[:, 1]
    for t in range(1, nt):
        phi[:, t] = phi[:, t - 1] + rng.normal(size=(nc, Q)) * sig[:, 3]
    eps: dict = {}
    clubes = ["América"] + [f"Club {c + 1:02d}" for c in range(1, nc)]  # el foco de la demo
    tecnicos = [f"Técnico {x + 1:02d}" for x in range(ntec)]
    jornadas = nc - 1
    asign = _asignaciones(nc, nt, ntec, jornadas, cfg, rng)

    def ficha(club, temp, tec):
        if (tec, club) not in eps:
            eps[(tec, club)] = rng.normal(size=Q) * sig[:, 2]
        return phi[club, temp] + theta[tec] + eps[(tec, club)]

    elo = np.full(nc, float(cfg["elo"]["inicial"]))
    Ke, he = cfg["elo"]["K"], cfg["elo"]["h"]
    tr = tramo_minuto(T)
    partidos, juego, expo, saq, camb, panel = [], [], [], [], [], []
    mid = 0
    hz_cache, pt_cache = {}, {}
    for temp in range(nt):
        cal = _round_robin(nc, rng)
        for j, par in enumerate(cal):
            B = len(par)
            loc = np.array([a for a, _ in par])
            vis = np.array([b for _, b in par])
            tl, tv = asign[loc, temp, j], asign[vis, temp, j]
            zl = np.array([ficha(c, temp, x) for c, x in zip(loc, tl)])
            zv = np.array([ficha(c, temp, x) for c, x in zip(vis, tv)])
            # lado 0..B-1: local ataca; B..2B-1: visitante ataca
            zi, zj = np.vstack([zl, zv]), np.vstack([zv, zl])
            local = np.r_[np.ones(B), np.zeros(B)]
            dE = np.r_[elo[loc] - elo[vis], elo[vis] - elo[loc]]
            lam = ritmo(liga, zi, zj, local)
            pi = mezcla(liga, zi, zj, local, dE)
            p, g = eficiencia(liga, zi, zj)
            sq, gps = balon_parado(liga, zi, zj, local)
            qcap = gps / liga.kappa[None]
            goles = np.zeros(2 * B, dtype=int)
            # acumuladores por (lado, tramo, m, k)
            Nk = np.zeros((2 * B, 6, 3, K))
            Sk = np.zeros_like(Nk)
            Gk = np.zeros_like(Nk)
            Xk = np.zeros_like(Nk)
            Ex = np.zeros((2 * B, 6, 3))
            Nu = np.zeros((2 * B, 6, 3, U))
            Su = np.zeros_like(Nu)
            Gu = np.zeros_like(Nu)
            Xu = np.zeros_like(Nu)
            ncamb = np.zeros(2 * B, dtype=int)
            alpha = zi[:, BLOQUES["alpha"][0]]
            gamma = zi[:, BLOQUES["gamma"][0]]
            lados = np.arange(2 * B)
            for t in range(T):
                rival_g = np.r_[goles[B:], goles[:B]]
                d = goles - rival_g
                m = np.where(d < 0, 0, np.where(d == 0, 1, 2))
                Ex[lados, tr[t], m] += 1
                n = rng.poisson(lam[:, t, None] * pi[lados, t, m])  # (2B, K)
                sh = rng.binomial(n, p)
                gl = rng.binomial(sh, g)
                xg = g * rng.gamma(2.0 * np.maximum(sh, 1e-9), 0.5) * (sh > 0)
                Nk[lados, tr[t], m] += n
                Sk[lados, tr[t], m] += sh
                Gk[lados, tr[t], m] += gl
                Xk[lados, tr[t], m] += xg
                nu = rng.poisson(sq[:, t])
                su = rng.binomial(nu, qcap)
                gu = rng.binomial(su, liga.kappa[None])
                xu = liga.kappa[None] * rng.gamma(2.0 * np.maximum(su, 1e-9), 0.5) * (su > 0)
                Nu[lados, tr[t], m] += nu
                Su[lados, tr[t], m] += su
                Gu[lados, tr[t], m] += gu
                Xu[lados, tr[t], m] += xu
                if t >= MIN_INICIO:
                    tt = t - MIN_INICIO
                    for lado in lados:
                        if ncamb[lado] >= MAX_CAMBIOS:
                            continue
                        a_ = float(alpha[lado])
                        if a_ not in hz_cache:
                            hz_cache[a_] = hazard(liga, a_)
                        hzv = hz_cache[a_][tt, m[lado]]
                        hubo = rng.random() < hzv
                        panel.append((mid + lado % B, lado, t, m[lado], int(hubo)))
                        if hubo:
                            g_ = float(gamma[lado])
                            if g_ not in pt_cache:
                                pt_cache[g_] = prob_tipo(liga, g_)
                            tipo = rng.choice(3, p=pt_cache[g_][m[lado]])
                            camb.append((mid + lado % B, lado, t, m[lado], tipo))
                            ncamb[lado] += 1
                goles += gl.sum(1) + gu.sum(1)
            # ruido de responsabilidades: r_sk = (1-ε)·verdad + ε·Dirichlet por celda
            ruido = rng.dirichlet(np.ones(K), size=Nk.shape[:3] + (K,))  # (.., k_verdad, k_obs)
            R = (1 - ruido_r) * np.eye(K) + ruido_r * ruido
            obs = lambda A: np.einsum("...k,...kj->...j", A, R)
            Nk_o, Sk_o, Gk_o, Xk_o = obs(Nk), obs(Sk), obs(Gk), obs(Xk)
            for b in range(B):
                mid_b = mid + b
                partidos.append(
                    (
                        mid_b,
                        temp,
                        j,
                        pd.Timestamp("2020-07-15") + pd.Timedelta(days=182 * temp + 7 * j),
                        clubes[loc[b]],
                        clubes[vis[b]],
                        int(goles[b]),
                        int(goles[B + b]),
                        tecnicos[tl[b]],
                        tecnicos[tv[b]],
                        elo[loc[b]],
                        elo[vis[b]],
                        "regular",
                    )
                )
            for lado in range(2 * B):
                b = lado % B
                eq = clubes[loc[b]] if lado < B else clubes[vis[b]]
                ri = clubes[vis[b]] if lado < B else clubes[loc[b]]
                es_loc = int(lado < B)
                for ti in range(6):
                    for mm in range(3):
                        if Ex[lado, ti, mm] == 0:
                            continue
                        expo.append((mid + b, eq, ti, mm, Ex[lado, ti, mm]))
                        for k in range(K):
                            juego.append(
                                (
                                    mid + b,
                                    eq,
                                    ri,
                                    es_loc,
                                    ti,
                                    mm,
                                    k,
                                    Nk_o[lado, ti, mm, k],
                                    Sk_o[lado, ti, mm, k],
                                    Xk_o[lado, ti, mm, k],
                                    Gk_o[lado, ti, mm, k],
                                )
                            )
                        for u in range(U):
                            if Nu[lado, ti, mm, u] > 0:
                                saq.append(
                                    (
                                        mid + b,
                                        eq,
                                        ri,
                                        es_loc,
                                        ti,
                                        mm,
                                        u,
                                        Nu[lado, ti, mm, u],
                                        Su[lado, ti, mm, u],
                                        Xu[lado, ti, mm, u],
                                        Gu[lado, ti, mm, u],
                                    )
                                )
            # Elo (K, h del config) después de la jornada
            gl_, gv_ = goles[:B], goles[B:]
            E = 1 / (1 + 10 ** ((elo[vis] - elo[loc] - he) / 400))
            S_ = np.where(gl_ > gv_, 1.0, np.where(gl_ == gv_, 0.5, 0.0))
            elo[loc] += Ke * (S_ - E)
            elo[vis] -= Ke * (S_ - E)
            mid += B
    tabla_partidos = pd.DataFrame(
        partidos,
        columns=[
            "match_id",
            "temporada",
            "jornada",
            "fecha",
            "local",
            "visitante",
            "goles_local",
            "goles_visitante",
            "tecnico_local",
            "tecnico_visitante",
            "elo_local",
            "elo_visitante",
            "etapa",
        ],
    )
    # equipo del lado en cambios/panel
    eq_lado = {}
    for r in tabla_partidos.itertuples():
        eq_lado[r.match_id] = (r.local, r.visitante)
    B = nc // 2

    def _eq(mid_, lado):
        return eq_lado[mid_][0 if lado < B else 1]

    cambios = pd.DataFrame(
        [(m_, _eq(m_, l_), t_, mm, tp) for m_, l_, t_, mm, tp in camb],
        columns=["match_id", "equipo", "minuto", "m", "tipo"],
    )
    panel_df = pd.DataFrame(
        [(m_, _eq(m_, l_), t_, mm, c_) for m_, l_, t_, mm, c_ in panel],
        columns=["match_id", "equipo", "minuto", "m", "cambio"],
    )
    tablas = {
        "partidos": tabla_partidos,
        "juego": pd.DataFrame(
            juego,
            columns=[
                "match_id",
                "equipo",
                "rival",
                "local",
                "tramo",
                "m",
                "k",
                "n",
                "remates",
                "xg",
                "goles",
            ],
        ),
        "exposicion": pd.DataFrame(expo, columns=["match_id", "equipo", "tramo", "m", "minutos"]),
        "saques": pd.DataFrame(
            saq,
            columns=[
                "match_id",
                "equipo",
                "rival",
                "local",
                "tramo",
                "m",
                "u",
                "n",
                "remates",
                "xg",
                "goles",
            ],
        ),
        "cambios": cambios,
        "panel": panel_df,
    }
    return tablas, Verdad(liga, theta, phi, eps, sig, clubes, tecnicos)


def ficha_verdadera(v: Verdad, club: str, temporada: int, tecnico: str) -> np.ndarray:
    c, x = v.clubes.index(club), v.tecnicos.index(tecnico)
    e = v.eps.get((x, c), np.zeros(Q))
    return v.phi[c, temporada] + v.theta[x] + e
