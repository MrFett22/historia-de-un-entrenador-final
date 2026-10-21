"""Cálculos de las apps v5 y v6 (D-062 a D-069). Nada de esto cambia el modelo ni la calibración: solo lee lo que ya produce el motor.

escala_efectos / frase_pesa_mas   suerte, jugadores (medidos DIRECTO de las tablas reales) y técnico en la MISMA escala (lo típico que varía en un torneo), para «¿Qué pesa más?»
deltas_reales / calificaciones_reales / calificacion_de_delta   la calificación 0 a 10: Δ de puntos contra el estilo neutro, percentil entre los técnicos reales
carta / parecido                   la carta del técnico: seis atributos de 0 a 100 y el técnico real más parecido
densidad_tecnicos                  sombreado de dónde se juntan más técnicos en el mapa de estilos
tabla_final                        tabla esperada de la liga
girar_torneo                       UN torneo de los ya simulados, para «Gira un torneo»
partido_unico / autoverificacion_partido   UN partido minuto a minuto con el proceso del motor, y su comparación con el cálculo exacto
metricas                           todas las métricas del técnico para la ficha completa
"""

from __future__ import annotations

import re

import numpy as np
from scipy.stats import norm

from . import config
from .estimacion.fichas import ficha_foco
from .modelos.intensidad import intensidades_lote
from .motor.jugadas import componentes, simular_partidos
from .motor.partido import distribucion_partido
from .perillas import ejes as mejes
from .tipos import COMPONENTES, Q, Tecnico

NOMBRES_ATRIBUTOS = ("ataque", "presion", "pp_favor", "pp_contra", "plan", "cambios")


# ---------------------------------------------------------------- «¿Qué pesa más?» (D-066, D-074)
def _val(x):
    """Un valor que la medición de la dispersión guarda como {valor, ic95} (o, en pruebas, como número suelto)."""
    return (x.get("valor"), x.get("ic95")) if isinstance(x, dict) else (x, None)


def sd_entre_tecnicos(deltas, n_boot: int = 2000, semilla: int = 20261020) -> dict | None:
    """Lo típico que varía (desviación típica) el Δ medio de los técnicos reales contra el estilo neutro, con su rango del 95 % por bootstrap sobre los técnicos."""
    d = np.asarray([x for x in deltas if x is not None], float)
    if len(d) < 3:
        return None
    rng = np.random.default_rng(semilla)
    b = np.array([np.std(d[rng.integers(0, len(d), len(d))], ddof=1) for _ in range(n_boot)])
    return {
        "valor": float(np.std(d, ddof=1)),
        "ic95": [float(x) for x in np.quantile(b, [0.025, 0.975])],
        "n": int(len(d)),
    }


def escala_efectos(sim) -> dict:
    """Las tres barras en LA MISMA escala: lo típico que varía en un torneo, en puntos (desviación típica de cada fuente).
    suerte = √Var_azar (la varianza de los puntos de un equipo en un torneo según el motor; con su rango del 95 % del bootstrap);
    jugadores = SD_fuerza_real (medida DIRECTO de la tabla real; no sale del simulador porque el simulador acorta las diferencias entre equipos);
    técnico = desviación típica, entre los técnicos reales, de su Δ medio contra el estilo neutro (`calificacion`), con su rango del 95 % por bootstrap sobre los técnicos."""
    pf = sim.perfiles() or {}
    d = pf.get("dispersion") or {}
    va, va_ic = _val(d.get("var_azar"))
    jug, jug_ic = _val(d.get("sd_fuerza_real"))
    r, r_ic = _val(d.get("r"))
    azar_real, _ = _val(d.get("azar_sobre_real"))
    tec = sd_entre_tecnicos([v["delta"] for v in calificaciones_reales(sim).values()])
    return {
        "suerte": float(np.sqrt(va)) if va is not None else None,
        "suerte_ic": [float(np.sqrt(max(x, 0.0))) for x in va_ic] if va_ic else None,
        "jugadores": jug,
        "jugadores_ic": jug_ic,
        "tecnico": tec["valor"] if tec else None,
        "tecnico_ic": tec["ic95"] if tec else None,
        "n_tecnicos": tec["n"] if tec else 0,
        "r": r,
        "r_ic": r_ic,
        "azar_sobre_real": azar_real,
    }


def frase_pesa_mas(e: dict) -> str | None:
    """La frase que acompaña a las tres barras, según los números. 'parecidos': el menor de dos es al menos `parecidos` del mayor; 'mucho menos': el técnico es a lo más
    `mucho_menos` del menor de los otros dos (umbrales en el config, `pesa_mas`). None si falta alguna barra."""
    from .app import textos as T

    s, j, t = e.get("suerte"), e.get("jugadores"), e.get("tecnico")
    if s is None or j is None or t is None:
        return None
    c = config.cargar()["pesa_mas"]
    parecidos = min(s, j) >= c["parecidos"] * max(s, j)
    mucho_menos = t <= c["mucho_menos"] * min(s, j)
    if mucho_menos:
        return (
            T.PESA_FRASE_IGUALES
            if parecidos
            else T.PESA_FRASE_UNO["suerte" if s > j else "jugadores"]
        )
    m = mayor(e)
    return T.PESA_FRASE_TECNICO if m == "tecnico" else T.PESA_FRASE_NEUTRA.format(que=T.PESA_QUE[m])


def frase_suerte(f: float | None) -> str | None:
    """La línea de debajo: qué parte de lo que varían los puntos reales es pura suerte (Var_azar / Var_real)."""
    from .app import textos as T

    if f is None:
        return None
    c = config.cargar()["pesa_mas"]
    if f >= c["mas_de_la_mitad"]:
        medida = T.PESA_SUERTE_MAS
    elif f >= c["casi_mitad"]:
        medida = T.PESA_SUERTE_CASI
    elif f >= c["un_tercio"]:
        medida = T.PESA_SUERTE_TERCIO
    else:
        medida = T.PESA_SUERTE_POCO
    return T.PESA_SUERTE_LINEA.format(medida=medida, pct=round(100 * f))


def mayor(e: dict) -> str | None:
    """Lo que más pesa de los tres, entre los que están medidos: 'suerte', 'jugadores' o 'tecnico'."""
    xs = {k: e[k] for k in ("suerte", "jugadores", "tecnico") if e.get(k) is not None}
    return max(xs, key=xs.get) if xs else None


# ---------------------------------------------------------------- «Exigencia América» (D-083)
def peor_tecnico_real(exigencia: dict | None) -> dict | None:
    """El técnico real con la P(top N) más baja de `perfiles_tecnicos.json["exigencia"]`: {nombre, media, ee} (None si no se midió)."""
    t = (exigencia or {}).get("tecnicos") or {}
    if not t:
        return None
    n = min(t, key=lambda k: t[k]["p_top"]["media"])
    return {"nombre": n, "media": float(t[n]["p_top"]["media"]), "ee": float(t[n]["p_top"]["ee"])}


def nivel_exigencia(
    top: float,
    ee: float,
    top_actual: float,
    ee_actual: float,
    peor: dict | None = None,
    k: float | None = None,
) -> str:
    """'top' (🏆 a la altura del América), 'corto' (😬 se queda corto) o 'alerta' (🚨 no da el ancho), por la P(top N) del resultado.
    top: P(top N) ≥ la de Almada − k·EE combinado. alerta: por debajo del peor técnico real − k·EE combinado (nunca por encima del umbral de 'top': los niveles son monótonos);
    sin la medición del peor técnico real no hay nivel 'alerta'."""
    k = config.cargar()["exigencia"]["k_ee"] if k is None else k
    umbral_top = top_actual - k * float(np.hypot(ee, ee_actual))
    if top >= umbral_top:
        return "top"
    if peor is not None and top < min(
        peor["media"] - k * float(np.hypot(ee, peor["ee"])), umbral_top
    ):
        return "alerta"
    return "corto"


# ---------------------------------------------------------------- calificación 0 a 10 que no contradice al simulador (D-067)
CENTRO = 5.0


def seguridad(rango) -> str | None:
    """Qué tan segura es la calificación, por lo ancho de su rango probable (umbrales en el config, `calificacion`): ancho > 6 → «baja»; de 3 a 6 → «media»; menos de 3 → «alta».
    Sin rango (la calificación solo se estimó) no hay seguridad."""
    if not rango:
        return None
    c = config.cargar()["calificacion"]
    ancho = float(rango[1]) - float(rango[0])
    return "baja" if ancho > c["ancho_baja"] else ("alta" if ancho < c["ancho_alta"] else "media")


def deltas_reales(sim, nombres: list | None = None, modo: str = "rapido", progreso=None) -> dict:
    """Δ de puntos esperados de cada técnico real contra el América con un técnico neutro (θ = 0), con la posterior completa de θ de cada uno y el plantel del América,
    con los mismos números aleatorios, y su IC 90 % (`comparar`). {nombre: {delta, ic90}}."""
    from .motor.comparar import comparar

    nombres = list(nombres if nombres is not None else sim.ejes.nombres)
    neutro = sim.simular(sim.tecnico_promedio(), modo, con_estilo=False)
    out = {}
    for i, n in enumerate(nombres):
        if progreso:
            progreso(i, len(nombres))
        c = comparar(
            sim.simular(sim.tecnico_preset(n), modo, con_estilo=False).temporada, neutro.temporada
        )
        out[n] = {
            "delta": round(float(c.resumen["media"]), 4),
            "ic90": [
                round(float(c.resumen["int90"][0]), 4),
                round(float(c.resumen["int90"][1]), 4),
            ],
        }
    return out


def mapa_calificacion(deltas: list[float]):
    """Función Δ → 0 a 10. Percentil entre los técnicos reales DENTRO de cada lado del cero: el mejor técnico con Δ > 0 vale 10, el peor con Δ < 0 vale 0 y Δ = 0 vale 5.
    Es creciente (Spearman = 1 entre técnicos reales) y (calificación − 5) tiene el signo de Δ. Fuera del rango de los reales se queda en 0 o 10."""
    d = np.sort(np.asarray(deltas, float))
    pos, neg = d[d > 0], d[d < 0]
    xs, ys = [], []
    for i, v in enumerate(neg):  # el peor vale 0; el menos malo, cerca de 5
        xs.append(v)
        ys.append(CENTRO - CENTRO * (len(neg) - i) / len(neg))
    xs.append(0.0)
    ys.append(CENTRO)
    for i, v in enumerate(pos):  # el mejor vale 10
        xs.append(v)
        ys.append(CENTRO + CENTRO * (i + 1) / len(pos))
    xs, ys = np.array(xs), np.array(ys)
    if len(neg) == 0:
        xs, ys = (
            np.r_[xs.min() - 1e-9, xs],
            np.r_[0.0, ys],
        )  # sin técnicos peores que el neutro, lo de abajo se acota en 0
    return lambda x: float(np.interp(x, xs, ys, left=ys[0] if len(neg) else 0.0, right=10.0))


def calificaciones_reales(sim) -> dict:
    """{técnico real: {delta, ic90, calif, rango, cruza}}: de `perfiles_tecnicos.json["calificacion"]` (todos los técnicos con ≥ 30 partidos, los calcula
    la medición de la dispersión) o, si no vienen, de la lista corta (se calcula una vez en modo rápido y se guarda en el objeto)."""
    if hasattr(sim, "_calif"):
        return sim._calif
    base = ((sim.perfiles() or {}).get("calificacion") or {}).get("tecnicos")
    if not base:
        base = deltas_reales(
            sim, sim.nombres_lista_corta()[:8], "rapido"
        )  # sin lo que deja la medición de la dispersión: solo los técnicos del selector (unos segundos)
    f = mapa_calificacion([v["delta"] for v in base.values()])
    out = {}
    for n, v in base.items():
        lo, hi = f(v["ic90"][0]), f(v["ic90"][1])
        out[n] = {
            "delta": v["delta"],
            "ic90": v["ic90"],
            "calif": round(f(v["delta"]), 1),
            "rango": [round(lo, 1), round(hi, 1)],
            "cruza": bool(lo <= CENTRO <= hi),
            "seguridad": seguridad([lo, hi]),
        }
    sim._calif = out
    sim._calif_f = f
    return out


def calificacion_de_delta(sim, delta: float, ic90: list | None = None) -> dict:
    """La misma conversión para un técnico inventado: con su Δ (y su IC 90 % si se simuló) contra el técnico neutro."""
    calificaciones_reales(sim)
    f = sim._calif_f
    if ic90 is None:
        return {
            "delta": delta,
            "ic90": None,
            "calif": round(f(delta), 1),
            "rango": None,
            "cruza": True,
            "estimada": True,
            "seguridad": None,
        }
    lo, hi = f(ic90[0]), f(ic90[1])
    return {
        "delta": delta,
        "ic90": ic90,
        "calif": round(f(delta), 1),
        "rango": [round(lo, 1), round(hi, 1)],
        "cruza": bool(lo <= CENTRO <= hi),
        "estimada": False,
        "seguridad": seguridad([lo, hi]),
    }


def _pesos_sustituto(sim) -> dict | None:
    ef = (sim.perfiles() or {}).get("efecto_perillas")
    if not ef:
        return None
    w = {}
    for k in mejes.CLAVES_EJES:
        d = ef.get(k)
        e = sim.ejes[k]
        lo, hi = e.limites
        dz = e.z_de_posicion(hi) - e.z_de_posicion(lo)
        w[k] = float(d["delta"]) / dz if (d and abs(dz) > 1e-9) else 0.0
    return w


def delta_estimado(sim, perillas: dict, ilim: bool = False) -> float | None:
    """Δ estimado contra el técnico neutro SIN simular: Σ efecto_i · z_i, con efecto_i = lo que cada perilla mueve los puntos de extremo a extremo entre la distancia
    entre extremos (`efecto_perillas`); z_i = dónde está la perilla en su eje (0 = neutro). Al simular, la app usa el Δ de la simulación en su lugar."""
    w = _pesos_sustituto(sim)
    if w is None:
        return None
    return float(
        sum(w[k] * sim.ejes[k].z_de_posicion(perillas[k], ilim) for k in mejes.CLAVES_EJES)
    )


COLOR_NEUTRO = "gris"  # nombre del color en la paleta (D-097); `app/paleta.py` lo traduce a su hex


def color_calificacion(x: float, cruza: bool = False, seguridad: str | None = "media") -> str:
    """El color de la calificación 0 a 10 como NOMBRE de la paleta (D-097): «amarillo» (alta y segura), «gris» (no se separa del promedio) o «rojo» (baja y segura). Con el centro en 5.
    Solo lleva color si la seguridad no es «baja» y su rango no toca el centro (5); si no, no se puede separar del promedio y es gris."""
    if cruza or seguridad in ("baja", None):
        return COLOR_NEUTRO
    return "amarillo" if x >= CENTRO else "rojo"


# ---------------------------------------------------------------- la carta del técnico
def _pct_eje(sim, clave: str, pos: float, ilim: bool) -> float:
    """De cada 100 técnicos reales, a cuántos supera en esa perilla (0 a 100); en pelota parada en contra «más» es defender mejor."""
    e = sim.ejes[clave]
    p = e.pct(e.z_de_posicion(pos, ilim))
    return 100 - p if e.invertido else p


def atributos(sim, perillas: dict, ilim: bool = False) -> list[float]:
    """Los seis atributos de la carta, de 0 a 100, en el orden de NOMBRES_ATRIBUTOS."""
    ops = list(_opciones_reaccion())
    reac = perillas["reaccion"]
    plan = (
        (ops.index(reac) * 100 + 50) / len(ops) if reac in ops else 50.0
    )  # cinco opciones: 10, 30, 50, 70, 90
    return [
        _pct_eje(sim, "ataca", perillas["ataca"], ilim),
        _pct_eje(sim, "defiende", perillas["defiende"], ilim),
        _pct_eje(sim, "pp_favor", perillas["pp_favor"], ilim),
        _pct_eje(sim, "pp_contra", perillas["pp_contra"], ilim),
        float(plan),
        float(perillas["cambios_momento"]),
    ]


def _opciones_reaccion() -> tuple:
    return tuple(config.cargar()["perillas"]["reactividad"].keys())


def _atributos_reales(sim) -> np.ndarray:
    filas = []
    for n in sim.ejes.nombres:
        th = sim.p.piezas.theta_tec[n]
        th = th.mean(0) if th.ndim == 2 else th
        filas.append(atributos(sim, sim.ejes.posiciones(th), False))
    return np.array(filas)


def parecido(sim, attrs: list[float]) -> tuple[str, float]:
    """Técnico real más cercano a esos seis atributos (distancia entre atributos estandarizados con la desviación entre técnicos reales) y esa distancia."""
    M = _atributos_reales(sim)
    sd = np.maximum(M.std(0), 1e-6)
    d = np.sqrt((((M - np.asarray(attrs)) / sd) ** 2).sum(1))
    i = int(np.argmin(d))
    return sim.ejes.nombres[i], float(d[i])


def carta(sim, perillas: dict, ilim: bool = False) -> dict:
    """La carta del técnico. «Se parece a» solo existe si el punto cae DENTRO de la zona observada (el casco convexo del mapa de estilos); si cae fuera, `parecido` es None y
    nunca se nombra a un técnico real (D-082)."""
    a = atributos(sim, perillas, ilim)
    nombre, dist = parecido(sim, a)
    dentro = not sim.fuera_de_la_zona(perillas, ilim)
    return {
        "atributos": a,
        "parecido": nombre if dentro else None,
        "distancia": dist,
        "dentro": dentro,
        "es_el_mismo": bool(dentro and dist < 0.05),
    }


# ---------------------------------------------------------------- mapa de estilos
def densidad_tecnicos(puntos: np.ndarray, limite: int = 100, n: int = 60) -> tuple:
    """Sombreado suave de dónde se juntan más técnicos reales (densidad gaussiana sobre sus puntos del mapa), normalizado a 0–1. Sin grupos ni fronteras:
    la silueta de los técnicos es 0.06, así que no hay grupos de estilo que dibujar (D-068)."""
    from scipy.stats import gaussian_kde

    p = np.asarray(puntos, float)
    xs = np.linspace(-limite, limite, n)
    X, Y = np.meshgrid(xs, xs)
    Z = gaussian_kde(p.T)(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)
    return xs.tolist(), xs.tolist(), (Z / Z.max()).tolist()


def _fichas(sim, t: Tecnico, idx: np.ndarray):
    obs = t.nombre if t.observado else None
    return ficha_foco(sim.p.piezas, t.theta, idx, obs), sim.p.piezas.fichas[idx]


# ---------------------------------------------------------------- tabla final
def iniciales(nombre: str) -> str:
    palabras = [
        p
        for p in nombre.replace("-", " ").split()
        if p.lower() not in ("de", "del", "la", "los", "las", "fc", "club")
    ]
    if len(palabras) >= 2:
        return "".join(p[0] for p in palabras[:3]).upper()
    return (palabras[0] if palabras else nombre)[:3].upper()


def tabla_final(sim, res) -> list[dict]:
    te = res.temporada.interno["tabla_esperada"]
    nombres = sim.p.meta["equipos"]
    filas = [
        {
            "equipo": nombres[i],
            "iniciales": iniciales(nombres[i]),
            "puntos": te["puntos"][i],
            "p_liguilla": te["p_liguilla"][i],
            "lugar_medio": te["lugar_medio"][i],
            "foco": i == sim.foco,
        }
        for i in range(len(nombres))
    ]
    filas.sort(key=lambda f: (-f["puntos"], f["lugar_medio"]))
    for n, f in enumerate(filas, 1):
        f["lugar"] = n
    return filas


# ---------------------------------------------------------------- «Gira un torneo»
def n_torneos_muestra(res) -> int:
    return len(res.temporada.interno["torneos_muestra"]["pts"])


def girar_torneo(sim, res, i: int) -> dict:
    """El torneo número `i` de los YA simulados (no se vuelve a simular): tabla final de los 18 equipos y la racha del América partido por partido."""
    m = res.temporada.interno["torneos_muestra"]
    nombres = sim.p.meta["equipos"]
    cal = np.asarray(sim.calendario)
    lugar = m["lugar"][i].astype(int)
    filas = [
        {
            "equipo": nombres[e],
            "iniciales": iniciales(nombres[e]),
            "puntos": int(m["pts"][i][e]),
            "gf": int(m["gf"][i][e]),
            "gc": int(m["gc"][i][e]),
            "lugar": int(lugar[e]),
            "foco": e == sim.foco,
        }
        for e in range(len(nombres))
    ]
    filas.sort(key=lambda f: f["lugar"])
    propios = np.flatnonzero((cal[:, 0] == sim.foco) | (cal[:, 1] == sim.foco))
    racha, marcadores = [], []
    for p in propios:
        a, b = int(m["ga"][i][p]), int(m["gb"][i][p])
        if cal[p, 1] == sim.foco:
            a, b = b, a
        racha.append("G" if a > b else ("E" if a == b else "P"))
        marcadores.append((a, b))
    nl = config.cargar()["torneo"]["liguilla_directa"]
    lf = int(lugar[sim.foco])
    return {
        "tabla": filas,
        "racha": racha,
        "marcadores": marcadores,
        "lugar": lf,
        "clasifica": lf <= nl,
        "liguilla": nl,
    }


def tabla_valida(tabla: list[dict]) -> bool:
    """18 equipos, lugares 1 a 18 sin repetir, ordenados por lugar y por puntos (con los desempates de la liga)."""
    if len(tabla) != 18 or sorted(f["lugar"] for f in tabla) != list(range(1, 19)):
        return False
    return all(
        (a["puntos"], a["gf"] - a["gc"]) >= (b["puntos"], b["gf"] - b["gc"])
        or a["puntos"] > b["puntos"]
        for a, b in zip(tabla, tabla[1:])
    )


# ---------------------------------------------------------------- «Ver un partido» (D-069)
def _fichas_partido(sim, t: Tecnico, rival: int, local: bool, muestra: int | None, rng):
    n = sim.p.piezas.fichas.shape[0]
    if muestra is None:
        muestra = int((rng or np.random.default_rng()).integers(n))
    ff, ent = _fichas(sim, t, np.array([muestra]))
    zi, zj = ff[0][None], ent[0][rival][None]
    de = sim.elo[sim.foco] - sim.elo[rival]
    return zi, zj, de, muestra


def intensidades_partido(
    sim, t: Tecnico, rival: int, local: bool, muestra: int | None = None, rng=None
):
    """(μ del América, μ del rival, muestra usada) de un partido contra `rival`: de una muestra de la fase A (la dada o una al azar)."""
    zi, zj, de, muestra = _fichas_partido(sim, t, rival, local, muestra, rng)
    Ii = intensidades_lote(sim.p.liga, zi, zj, 1.0 if local else 0.0, de)
    Ij = intensidades_lote(sim.p.liga, zj, zi, 0.0 if local else 1.0, -de)
    return Ii.mu[0], Ij.mu[0], muestra


def componentes_partido(
    sim, t: Tecnico, rival: int, local: bool, muestra: int | None = None, rng=None
):
    """(piezas del América, piezas del rival, muestra usada): lo que `motor.jugadas` necesita para sortear las jugadas del partido (D-073)."""
    zi, zj, de, muestra = _fichas_partido(sim, t, rival, local, muestra, rng)
    Ci = componentes(sim.p.liga, zi, zj, 1.0 if local else 0.0, de)
    Cj = componentes(sim.p.liga, zj, zi, 0.0 if local else 1.0, -de)
    return Ci, Cj, muestra


def distribucion_exacta(mu_i, mu_j):
    """La distribución exacta del motor para ese partido (marcadores, G/E/P y goles esperados)."""
    return distribucion_partido(mu_i, mu_j)


def distribucion_resultado(mu_i, mu_j) -> tuple[float, float, float]:
    d = distribucion_partido(mu_i, mu_j)
    return float(d.p_gana[0]), float(d.p_empata[0]), float(d.p_pierde[0])


BP_CLAVES = (
    "corner",
    "tiro_libre_area",
    "lateral_largo",
    "tiro_libre_directo",
    "penal",
)  # el orden de los tipos de pelota parada de M4 (tipos.TIPOS_BP)


def estadisticas_partido(r: dict, lado: str, con_fin: bool) -> dict:
    """Conteos de UN lado de UN partido sorteado: remates, los cinco tipos de pelota parada (los saques, con o sin remate), las jugadas por tipo y cómo terminaron (gol y remate sin gol
    de juego abierto; pérdida; fuera o interrupción). `con_fin` es False si la liga no trae cadenas (no se sabe cómo terminaron)."""
    e = {"remates": int(r[f"remates_{lado}"][0].sum())}
    for u, clave in enumerate(BP_CLAVES):
        e[clave] = int(r[f"saques_{lado}"][0][u])
    e["directa"], e["toque"], e["elaborada"] = (int(x) for x in r[f"jugadas_{lado}"][0])
    if con_fin:
        per, fue, inte = (int(x) for x in r[f"fin_{lado}"][0])
        abiertos = (
            int(r[f"jugadas_{lado}"][0].sum()) - per - fue - inte
        )  # las jugadas de juego abierto que terminaron en remate
        e["gol_abierto"] = int(r[f"goles_abierto_{lado}"][0])
        e["remate_sin_gol"] = abiertos - e["gol_abierto"]
        e["perdidas"], e["fuera_interrupcion"] = per, fue + inte
    return e


def partido_unico(
    sim, t: Tecnico, rival: int, local: bool, semilla: int | None = None, muestra: int | None = None
) -> dict:
    """UN partido posible, sorteado jugada por jugada con la misma ley de goles del motor (D-073). Con la misma semilla, el mismo partido.
    Devuelve los goles minuto a minuto, los remates y el dominio M(t) de cada minuto (UNA serie con signo, en goles esperados por minuto: positivo, domina el América; negativo, el rival; D-096),
    con el tope del eje (percentil `percentil_eje` de |M|) y el marco. `peligro_*` es el de la v7: los remates sin suavizar."""
    rng = np.random.default_rng(semilla)
    Ci, Cj, muestra = componentes_partido(sim, t, rival, local, muestra, rng)
    r = simular_partidos(Ci, Cj, 1, rng)
    goles, a, b = [], 0, 0
    for minuto in range(Ci.T):
        for _ in range(int(r["goles_i"][0, minuto])):
            a += 1
            goles.append((minuto + 1, "i", a, b))
        for _ in range(int(r["goles_j"][0, minuto])):
            b += 1
            goles.append((minuto + 1, "j", a, b))
    mu_i, mu_j = Ci.mu, Cj.mu
    cfgj = config.cargar()["partido"]["jugadas"]
    dom = np.abs(r["dominio"][0])
    tope = float(
        np.percentile(dom, cfgj["percentil_eje"])
    )  # el eje simétrico: percentil 95 de |M| del partido
    techo = float(
        min(dom.max(), tope * (1 + cfgj["margen_eje"]))
    )  # el marco llega hasta el pico, sin pasar de tope · (1 + margen)
    pg, pe, pp = distribucion_resultado(mu_i, mu_j)
    nombres = sim.p.meta["equipos"]
    return {
        "america": int(r["a"][0]),
        "rival": int(r["b"][0]),
        "goles": goles,
        "minutos": int(Ci.T),
        "local": local,
        "nombre_rival": nombres[rival],
        "iniciales_rival": iniciales(nombres[rival]),
        "peligro_america": [round(float(x), 5) for x in r["peligro_i"][0]],
        "peligro_rival": [round(float(x), 5) for x in r["peligro_j"][0]],
        "remates_america": int(r["remates_i"].sum()),
        "remates_rival": int(r["remates_j"].sum()),
        "dominio": [round(float(x), 6) for x in r["dominio"][0]],
        "tope": round(tope, 6),
        "techo": round(techo, 6),
        "estadisticas": {
            "america": estadisticas_partido(r, "i", Ci.fin_k is not None),
            "rival": estadisticas_partido(r, "j", Ci.fin_k is not None),
        },
        "p_gana": pg,
        "p_empata": pe,
        "p_pierde": pp,
        "muestra": muestra,
        "semilla": semilla,
    }


def autoverificacion_partido(
    sim,
    t: Tecnico,
    rival: int,
    local: bool = True,
    n: int = 5000,
    semilla: int = 20261020,
    muestra: int = 0,
) -> dict:
    """¿El partido sorteado se parece al cálculo exacto? Sortea `n` partidos jugada por jugada (los mismos de «Ver un partido») con la misma muestra de la fase A y los compara con la
    distribución exacta del motor: frecuencias de ganar / empatar / perder y goles medios de cada lado (a ≤ 3 errores estándar) y χ² de bondad de ajuste de los marcadores (4+ goles
    agrupados; las celdas con menos de 5 esperados se juntan en «otros»)."""
    from scipy import stats

    Ci, Cj, _ = componentes_partido(sim, t, rival, local, muestra)
    d = distribucion_partido(Ci.mu, Cj.mu)
    P = d.P[0]
    K = 4
    exact = np.zeros((K + 1, K + 1))
    G1 = P.shape[0]
    for x in range(G1):
        for y in range(G1):
            exact[min(x, K), min(y, K)] += P[x, y]
    rng = np.random.default_rng(semilla)
    r = simular_partidos(Ci, Cj, n, rng)
    a, b = r["a"], r["b"]
    obs = np.zeros((K + 1, K + 1))
    np.add.at(obs, (np.minimum(a, K), np.minimum(b, K)), 1)
    res = np.array([(a > b).sum(), (a == b).sum(), (a < b).sum()], float)
    ga, gb = float(a.sum()), float(b.sum())
    esp = exact.ravel() / exact.sum() * n
    o = obs.ravel()
    chico = esp < 5
    o2 = np.r_[o[~chico], o[chico].sum()] if chico.any() else o
    e2 = np.r_[esp[~chico], esp[chico].sum()] if chico.any() else esp
    if e2[-1] < 5 and len(e2) > 2:  # lo juntado también debe llegar a 5
        o2, e2 = np.r_[o2[:-2], o2[-2:].sum()], np.r_[e2[:-2], e2[-2:].sum()]
    chi2 = float(((o2 - e2) ** 2 / e2).sum())
    gl = len(e2) - 1
    pg, pe, pp = float(d.p_gana[0]), float(d.p_empata[0]), float(d.p_pierde[0])
    ee = lambda p: float(np.sqrt(p * (1 - p) / n))
    # error estándar de la media de goles: desviación de los goles exactos de cada lado
    marg_a, marg_b = P.sum(1), P.sum(0)
    g = np.arange(G1)
    var_a = float((marg_a * g**2).sum() - (marg_a * g).sum() ** 2)
    var_b = float((marg_b * g**2).sum() - (marg_b * g).sum() ** 2)
    z = [(res[k] / n - p) / ee(p) for k, p in enumerate((pg, pe, pp))]
    za = (ga / n - float(d.eg_i[0])) / np.sqrt(var_a / n)
    zb = (gb / n - float(d.eg_j[0])) / np.sqrt(var_b / n)
    return {
        "n": n,
        "frecuencias": (res / n).tolist(),
        "exactas": [pg, pe, pp],
        "z_resultados": [float(x) for x in z],
        "goles_medios": [ga / n, gb / n],
        "goles_exactos": [float(d.eg_i[0]), float(d.eg_j[0])],
        "z_goles": [float(za), float(zb)],
        "chi2": chi2,
        "gl": int(gl),
        "p": float(stats.chi2.sf(chi2, gl)),
        "pasa": bool(stats.chi2.sf(chi2, gl) > 0.01 and max(abs(np.r_[z, za, zb])) < 3),
    }


# ---------------------------------------------------------------- ficha completa
def _tipos_remate(sim) -> np.ndarray:
    """% de las jugadas de cada tipo que termina en remate (gol o remate), de la fuente."""
    return np.array([d["remate"] for d in sim.tipos_de_jugada()]) / 100


def metricas(sim, estilo: dict) -> dict:
    """Todas las métricas de un resultado, por partido (remates por tipo: jugadas del tipo × % que termina en remate de la fuente)."""
    rem = _tipos_remate(sim)
    cb = estilo.get("cambios", {})
    return {
        "pi": [100 * x for x in estilo["pi"]],
        "pi_rival": [100 * x for x in estilo["pi_rival"]],
        "remates": list(np.asarray(estilo["N_k"]) * rem),
        "remates_rival": list(np.asarray(estilo["N_k_rival"]) * rem),
        "goles_k_favor": list(estilo["goles_k_favor"]),
        "goles_k_contra": list(estilo["goles_k_contra"]),
        "bp_favor": float(sum(estilo["goles_bp_favor"])),
        "bp_contra": float(sum(estilo["goles_bp_contra"])),
        "min_cambio": cb.get("minuto_primer_cambio"),
        "tipo_cambio": cb.get("tipo_mas_comun"),
    }


# ---------------------------------------------------------------- cambio significativo (ficha completa, D-091)
def cambio(tu: float, actual: float, tipo: str, ee_tu: float = 0.0, ee_actual: float = 0.0) -> dict:
    """¿Cambia «de verdad» una cantidad de la ficha contra el América de hoy? Sale de los valores SIN redondear y de `ficha_cambio` del config, nunca de lo que se vea en pantalla.
    tipo: «pp» (mezclas, en puntos porcentuales), «conteo» (remates y goles por partido), «minutos», o «mc» (Monte Carlo: puntos, P(liguilla), P(top N)).
    Exactas: cambio relativo ≥ rel_min Y cambio absoluto ≥ el mínimo de su unidad. Monte Carlo: |Δ| ≥ k·hypot(EE, EE). Devuelve {estado: sube | baja | igual, delta, rel, de_cero}.
    `rel` es con signo (None si el valor de hoy es 0); `de_cero`: hoy es 0 y el técnico no."""
    c = config.cargar()["ficha_cambio"]
    d = float(tu) - float(actual)
    ref = abs(float(actual))
    rel = None if ref < 1e-12 else d / ref
    if tipo == "mc":
        grande = abs(d) >= c["k_ee"] * float(np.hypot(ee_tu, ee_actual)) and d != 0.0
    else:
        minimo = {
            "pp": c["abs_pp_min"],
            "conteo": c["abs_goles_min"],
            "minutos": c["abs_minutos_min"],
        }[tipo]
        grande = abs(d) >= minimo and (rel is None or abs(rel) >= c["rel_min"])
    estado = "igual" if not grande else ("sube" if d > 0 else "baja")
    return {"estado": estado, "delta": d, "rel": rel, "de_cero": bool(rel is None and grande)}


def decimales_distintos(a: float, b: float, base: int, tope: int = 4) -> int:
    """Decimales con que se escriben dos números para que, si son distintos, SE VEAN distintos (el redondeo no puede mostrar «baja» con dos cifras iguales)."""
    d = base
    while d < tope and a != b and round(a, d) == round(b, d):
        d += 1
    return d


# ---------------------------------------------------------------- qué torneo se simula (D-092)
def torneo_anterior(torneo: str) -> str | None:
    """El torneo que cierra justo antes del que se simula, por su nombre: «Apertura 2026» → «Clausura 2026»; «Clausura 2026» → «Apertura 2025» (Liga MX: Clausura y luego Apertura)."""
    m = re.fullmatch(r"\s*(Apertura|Clausura)\s+(\d{4})\s*", torneo or "")
    if not m:
        return None
    return (
        f"Clausura {m.group(2)}" if m.group(1) == "Apertura" else f"Apertura {int(m.group(2)) - 1}"
    )


def torneo_info(sim) -> dict:
    """Lo que dice el bloque «qué torneo simulamos», TODO de `meta.json`: torneo objetivo, partidos y jornadas del calendario, torneo anterior (por su nombre), y el corte por fecha
    (`corte`: fecha_corte, partidos_quitados, fechas_quitadas) si la calibración lo guardó. Lo que falta queda en None."""
    m = sim.p.meta
    corte = m.get("corte") or {}
    fechas = corte.get("fechas_quitadas") or []
    return {
        "torneo": m.get("torneo"),
        "partidos": len(m.get("calendario") or []),
        "jornadas": int(max(m["jornada"])) if m.get("jornada") else None,
        "anterior": torneo_anterior(m.get("torneo")),
        "fecha_corte": corte.get("fecha_corte"),
        "quitados": corte.get("partidos_quitados"),
        "desde": fechas[0] if len(fechas) == 2 else None,
        "hasta": fechas[1] if len(fechas) == 2 else None,
        "foco": m.get("foco"),
        "tecnico": m.get("tecnico_actual_foco"),
    }
