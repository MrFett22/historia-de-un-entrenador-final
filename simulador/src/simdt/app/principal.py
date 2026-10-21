"""Pantalla principal del simulador (v6). Tres pestañas, en este orden:
  «Antes de jugar»      — una cuadrícula de tarjetas (qué es, qué no es, qué pesa más, tipos de jugada, perillas, técnicos fijos, qué no simula)
  «Simulador»           — todo lo visual: qué pesa más, resultados contra el América actual, carta y mapa del técnico, estilo, goles en la cancha,
                             tabla final, «Gira un torneo», «Ver un partido» (con el peligro de gol minuto a minuto), comparación y ficha completa
  «¿Le podemos creer?»  — la validación: una cuadrícula de ocho tarjetas con el mismo formato
Los técnicos reales son FIJOS (sus perillas se ven, bloqueadas); solo «Crea tu propio técnico» las mueve (D-065). Animaciones suaves y apagadas con `prefers-reduced-motion` (D-064)."""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import streamlit as st

from .. import analisis as A
from .. import config
from ..datos.inventario import MODO_SINTETICO
from ..perillas import ejes as mejes
from ..perillas.mapeo import perillas_activas, rangos_perillas
from ..trabajo import Tarea, Trabajo, fijar_hilos
from ..servicio import CREA, NEUTRO, Simulador
from ..validacion import tarjetas as VT
from . import animacion as AN
from . import componentes as C
from . import graficas as G
from . import paleta as PA
from . import textos as T


@st.cache_resource(show_spinner=False)
def _simulador() -> Simulador:
    fijar_hilos()  # la nube es una máquina chica (D-084)
    return Simulador()


def _tecnico_vigente(sim: Simulador):
    n = sim.p.meta.get("tecnico_actual_foco")
    return sim.tecnico_preset(n) if n in sim.p.piezas.theta_tec else sim.tecnico_promedio()


def _referencia(clave: str, modo: str):
    """Resultados de referencia que comparten las sesiones (Almada y el estilo neutro con el plantel del América): se calculan una vez por modo. Si el trabajo en segundo plano ya
    los dejó en `sim.memo`, no se vuelve a simular nada."""
    sim = _simulador()
    k = (clave, modo)
    if k not in sim.memo:
        sim.memo[k] = sim.simular(
            _tecnico_vigente(sim) if clave == "actual" else sim.tecnico_promedio(), modo
        )
    return sim.memo[k]


def _america_actual(modo: str):
    return _referencia("actual", modo)


def _referencia_liga(modo: str):
    """«Lo normal en la liga»: el estilo neutro (θ = 0) con el plantel del América. Es una referencia, no un técnico que se pueda elegir."""
    return _referencia("neutro", modo)


@st.cache_resource(show_spinner=False)
def _autoverificacion() -> dict:
    sim = _simulador()
    rivales = [e for e in range(len(sim.elo)) if e != sim.foco]
    rival = rivales[
        int(np.argsort(sim.elo[rivales])[len(rivales) // 2])
    ]  # el rival de fuerza mediana
    return A.autoverificacion_partido(sim, _tecnico_vigente(sim), rival, True, 5000)


LLAVES = {
    "ataca": "k_ataca",
    "defiende": "k_defiende",
    "pp_contra": "k_ppc",
    "pp_favor": "k_ppf",
    "reaccion": "k_reac",
    "cambios_momento": "k_cm",
    "cambios_tipo": "k_ct",
}
TODAS_LLAVES = list(LLAVES.values()) + [LLAVES[k] + "_u" for k in mejes.CLAVES_EJES]


def _llave(clave: str, ilim: bool) -> str:
    """Las cuatro perillas de eje tienen un deslizador por modo (normal y sin límites): así cada uno conserva su escala."""
    return LLAVES[clave] + ("_u" if ilim and clave in mejes.CLAVES_EJES else "")


def _es_crea() -> bool:
    return st.session_state.get("k_preset", CREA) == CREA


def _ilim() -> bool:
    """El modo sin límites solo existe en «Crea tu propio técnico»."""
    return bool(st.session_state.get("k_ilim", False)) and _es_crea()


def _cargar_perillas(sim: Simulador, t) -> None:
    th = t.theta.mean(0) if t.theta.ndim == 2 else t.theta
    per = t.perillas or sim.ejes.posiciones(th)
    for k, llave in LLAVES.items():
        st.session_state[llave] = per[k]
    for k, v in sim.ejes.posiciones(th, ilim=True).items():
        if k in mejes.CLAVES_EJES:
            st.session_state[LLAVES[k] + "_u"] = v


def _leer_perillas(ilim: bool | None = None) -> dict:
    ilim = _ilim() if ilim is None else ilim
    return {k: st.session_state[_llave(k, ilim)] for k in LLAVES}


def _al_cambiar_limites() -> None:
    """Al prender o apagar el modo sin límites, cada perilla de eje conserva el mismo técnico: se convierte entre las dos escalas."""
    sim = _simulador()
    nuevo = bool(st.session_state.get("k_ilim", False))
    for k in mejes.CLAVES_EJES:
        viejo = st.session_state.get(_llave(k, not nuevo))
        if viejo is None:
            continue
        e = sim.ejes[k]
        lo, hi = e.limites_de(nuevo)
        st.session_state[_llave(k, nuevo)] = int(
            np.clip(e._pos_de_z(e.z_de_posicion(viejo, not nuevo), nuevo), lo, hi)
        )


def _nombre_con_rol(sim: Simulador, n: str, actual: str | None) -> str:
    if n == CREA:
        return T.PRESET_CREA
    if n == actual:
        return f"{n} {T.PRESET_ACTUAL}"
    return f"{n} {T.PRESET_ANTECESOR}" if sim.info_preset(n).get("rol") == "antecesor" else n


def _tecnico_elegido(sim: Simulador, preset: str, ilim: bool):
    """Un técnico real se simula tal cual (su posterior completa de θ). «Crea tu propio técnico» parte del estilo neutro y mueve solo lo que cambiaron las perillas."""
    if preset != CREA:
        return sim.tecnico_preset(preset)
    base = sim.tecnico_promedio(T.COMPARAR_BASE_TU)
    per = _leer_perillas(ilim)
    return (
        base
        if not sim.perillas_cambiadas(base, per, ilim)
        else sim.tecnico_perillas(per, base, T.COMPARAR_BASE_TU, ilim)
    )


def _nombre_defensa(sim: Simulador) -> str:
    return sim.nombre_perilla_defensa() or T.DEFIENDE


def _eje_con_franja(
    sim: Simulador, clave: str, titulo: str, ayuda: str, extremos: tuple, desactivado: bool = False
) -> None:
    """Un deslizador de la escala de técnicos reales, sus etiquetas de extremo y la franja de la mayoría de los técnicos, en la MISMA escala."""
    ilim = _ilim()
    lo, hi = sim.ejes[clave].limites_de(ilim)
    st.markdown(f"**{titulo}**", help=ayuda)
    st.slider(
        titulo, lo, hi, key=_llave(clave, ilim), disabled=desactivado, label_visibility="collapsed"
    )
    a, b = sim.rango_reales(ilim)[clave]
    C.franja_reales(lo, hi, a, b)
    C.extremos(*extremos)


def _duracion_modo(sim: Simulador, modo: str) -> float:
    """Lo que tarda una simulación de ese modo en la nube: lo medido en el contenedor de pruebas (`simulacion.duracion_medida`) por el factor supuesto `rendimiento.factor_nube`."""
    return float(sim.cfg["simulacion"]["duracion_medida"][modo]) * float(
        sim.cfg["rendimiento"]["factor_nube"]
    )


def _ee_lugar_pp(sb2: float, sw2: float, R: int, S: int) -> float:
    """Margen de error (95 %) de una probabilidad, en puntos porcentuales, con la fórmula de dos etapas: Var = σ_b²/R + σ_w²/(R·S)."""
    return 196.0 * float(np.sqrt(sb2 / R + sw2 / (R * S)))


def _ayuda_precision(sim: Simulador) -> str:
    """Cuántos torneos hace cada precisión y cuánto tarda (todo del config) y, si ya hay una simulación, cuánto se afinan los porcentajes de liguilla y de cada lugar."""
    s = sim.cfg["simulacion"]
    r1, s1, r2, s2 = (
        int(s["rapido"]["R"]),
        int(s["rapido"]["S"]),
        int(s["profundo"]["R"]),
        int(s["profundo"]["S"]),
    )
    txt = T.PRECISION_BASE.format(
        n1=f"{r1 * s1:,}",
        t1=_tiempo_aprox(_duracion_modo(sim, "rapido")),
        n2=_cifra_torneos(r2 * s2),
        t2=_tiempo_aprox(_duracion_modo(sim, "profundo")),
    )
    v, u = sim.n_versiones("profundo")
    nomas = T.PRECISION_NO_MAS.format(v=f"{v:,}", u=f"{u:,}")
    r = st.session_state.get("resultado")
    pl = r.temporada.resumen.get("p_liguilla") if r is not None else None
    if not pl or "sigma_b2" not in pl:
        return txt + T.PRECISION_SIN_EE + nomas
    a, b = (
        _ee_lugar_pp(pl["sigma_b2"], pl["sigma_w2"], r1, s1),
        _ee_lugar_pp(pl["sigma_b2"], pl["sigma_w2"], r2, s2),
    )
    return txt + T.PRECISION_AFINA.format(a=f"{a:.1f}", b=f"{b:.1f}") + nomas


# ---------------------------------------------------------------- barra lateral: solo controles
def barra_lateral(sim: Simulador) -> tuple[str, str]:
    activas = perillas_activas(sim.p.escalas)
    estilo = set(sim.p.meta.get("perillas_solo_estilo", []))
    actual = sim.p.meta.get("tecnico_actual_foco")
    reales = list(sim.nombres_lista_corta())
    if actual in reales:
        reales.remove(actual)
        reales.insert(0, actual)
    opciones = [CREA] + reales  # arriba «Crea tu propio técnico»; debajo, SOLO técnicos reales
    with st.sidebar:
        st.markdown(f"## {T.PANEL}")
        preset = st.selectbox(
            T.PRESET,
            opciones,
            help=T.PRESET_AYUDA,
            key="k_preset",
            format_func=lambda n: _nombre_con_rol(sim, n, actual),
        )
        crea = preset == CREA
        previo = st.session_state.get("_preset_cargado")
        if previo != preset:
            if previo == CREA:  # lo que inventaste se guarda para cuando vuelvas
                st.session_state["_crea_guardado"] = {
                    k: st.session_state[k] for k in TODAS_LLAVES if k in st.session_state
                }
            if crea and "_crea_guardado" in st.session_state:
                st.session_state.update(st.session_state["_crea_guardado"])
            else:
                _cargar_perillas(
                    sim, sim.tecnico_promedio() if crea else sim.tecnico_preset(preset)
                )
            st.session_state["_preset_cargado"] = preset
            st.session_state.pop("resultado", None)
        if crea:
            C.nota(T.CREA_NOTA)
        else:
            C.nota(T.BLOQUEADO.format(nombre=preset))
            info = sim.info_preset(preset)
            if preset == actual:
                C.nota(T.ETIQUETA_VIGENTE)
            elif info.get("rol") == "antecesor":
                C.nota(T.ETIQUETA_ANTECESOR)
            elif info.get("rasgos"):
                C.nota(T.etiqueta_tecnico(info["rasgos"]))
            if info.get("rol") == "medoide":
                C.nota(
                    T.PERFIL_POCO_COMUN
                    if info.get("representa", 0) <= 1
                    else T.REPRESENTA.format(n=info["representa"])
                )
            C.nota(T.PRESET_NOTA)
        if crea:
            st.markdown('<div class="grupo"></div>', unsafe_allow_html=True)
            st.toggle(
                T.LIMITES_SWITCH, key="k_ilim", help=T.LIMITES_AYUDA, on_change=_al_cambiar_limites
            )
            if _ilim():
                C.nota(T.LIMITES_ETIQUETA)
        C.nota(T.FRANJA_TEXTO)
        st.markdown('<div class="grupo"></div>', unsafe_allow_html=True)
        _eje_con_franja(
            sim,
            "ataca",
            T.ATACA,
            T.ATACA_AYUDA,
            T.ATACA_EXTREMOS,
            (not activas["mezcla"]) or not crea,
        )
        st.markdown('<div class="grupo"></div>', unsafe_allow_html=True)
        _eje_con_franja(
            sim,
            "defiende",
            _nombre_defensa(sim),
            T.DEFIENDE_AYUDA,
            T.DEFIENDE_EXTREMOS,
            (not activas["rival"]) or not crea,
        )
        st.markdown('<div class="grupo"></div>', unsafe_allow_html=True)
        _eje_con_franja(
            sim,
            "pp_contra",
            T.PP_CONTRA,
            T.PP_CONTRA_AYUDA,
            T.PP_EXTREMOS,
            (not activas["balon_parado"]) or not crea,
        )
        st.markdown('<div class="grupo"></div>', unsafe_allow_html=True)
        _eje_con_franja(sim, "pp_favor", T.PP_FAVOR, T.PP_FAVOR_AYUDA, T.PP_EXTREMOS, not crea)
        with st.expander(T.FINOS):
            if {"reaccion_marcador", "reaccion_rival", "cambios_momento", "cambios_tipo"} <= estilo:
                C.nota(T.FINOS_AYUDA)
            st.markdown(f"**{T.REACCION}**")
            st.select_slider(
                T.REACCION,
                T.OPCIONES_REACCION,
                key=LLAVES["reaccion"],
                label_visibility="collapsed",
                disabled=not crea,
                help=T.AYUDA_DESACTIVADA
                if {"reaccion_marcador", "reaccion_rival"} <= estilo
                else T.REACCION_AYUDA,
            )
            st.markdown(f"**{T.CAMBIOS_MOMENTO}**")
            lo, hi = rangos_perillas(sim.p.escalas, sim.p.liga)["cambios_momento"]
            st.slider(
                T.CAMBIOS_MOMENTO,
                int(lo),
                int(max(hi, lo + 1)),
                key=LLAVES["cambios_momento"],
                label_visibility="collapsed",
                disabled=not crea,
                help=T.AYUDA_DESACTIVADA if "cambios_momento" in estilo else None,
            )
            C.extremos(*T.CAMBIOS_EXTREMOS)
            st.markdown(f"**{T.CAMBIOS_TIPO}**")
            st.select_slider(
                T.CAMBIOS_TIPO,
                T.OPCIONES_CAMBIO,
                key=LLAVES["cambios_tipo"],
                label_visibility="collapsed",
                disabled=not crea,
                help=T.AYUDA_DESACTIVADA if "cambios_tipo" in estilo else None,
            )
        st.markdown('<div class="grupo"></div>', unsafe_allow_html=True)
        st.session_state.setdefault("k_precision", T.OPCIONES_PRECISION[0])
        lugar_precision = (
            st.empty()
        )  # su ayuda se escribe DESPUÉS de simular, con el margen de error de esa simulación
        precision = (
            st.segmented_control(
                T.PRECISION, T.OPCIONES_PRECISION, key="k_precision", label_visibility="collapsed"
            )
            or T.OPCIONES_PRECISION[0]
        )
        st.markdown('<div class="grupo"></div>', unsafe_allow_html=True)
        corriendo = _corriendo()
        simular = st.button(T.BOTON_SIMULAR, type="primary", width="stretch", disabled=corriendo)
        panel_progreso = st.container()  # el avance REAL de la simulación en segundo plano (D-084)
        reiniciar = st.button(T.BOTON_REINICIAR, width="stretch")
    modo = "profundo" if precision == T.OPCIONES_PRECISION[1] else "rapido"
    if reiniciar:
        j = st.session_state.get("trabajo")
        if j is not None:
            j.cancelar()
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    if simular and not corriendo:
        _iniciar_trabajo(sim, preset, crea, modo)
        _cosechar(
            sim
        )  # si ya terminó (las pruebas lo esperan al lanzarlo), el resultado entra en esta misma ejecución
    with panel_progreso:
        _panel_progreso()
    lugar_precision.markdown(f"**{T.PRECISION}**", help=_ayuda_precision(sim))
    return preset, modo


def _corriendo() -> bool:
    j = st.session_state.get("trabajo")
    return j is not None and j.estado == "corriendo"


def _iniciar_trabajo(sim: Simulador, preset: str, crea: bool, modo: str) -> None:
    """Lanza la simulación en un hilo. Al terminar, `_cosechar` deja el resultado en la sesión. Mientras corre no hay resultado a medias en pantalla."""
    ilim = _ilim()
    t = _tecnico_elegido(sim, preset, ilim)
    es_vigente = (
        (not crea)
        and preset == sim.p.meta.get("tecnico_actual_foco")
        and preset in sim.p.piezas.theta_tec
        and ("actual", modo) not in sim.memo
    )  # elegir al técnico de hoy ES la referencia: se simula una sola vez
    tareas = [Tarea("objetivo", t, modo, True, ("actual", modo) if es_vigente else None)]
    for clave in (
        ("actual", "neutro") if crea else (() if es_vigente else ("actual",))
    ):  # las referencias: Almada (tarjetas y ficha) y, solo para calificar a un técnico inventado, el estilo neutro (una vez por modo)
        if (clave, modo) not in sim.memo:
            tareas.append(
                Tarea(
                    clave,
                    _tecnico_vigente(sim) if clave == "actual" else sim.tecnico_promedio(),
                    modo,
                    True,
                    (clave, modo),
                )
            )
    meta = {
        "modo": modo,
        "preset": preset,
        "crea": crea,
        "ilim": ilim,
        "extremo": sim.es_extremo(t),
        "fuera_zona": sim.fuera_de_la_zona(t.perillas, ilim) if crea else False,
        "huella": _huella(_leer_perillas(ilim), ilim),
    }
    st.session_state.pop("resultado", None)
    st.session_state["trabajo"] = Trabajo(sim, tareas, meta).iniciar()


def _cosechar(sim: Simulador) -> bool:
    """Si el trabajo en segundo plano terminó, deja su resultado en la sesión (una sola vez). Se llama al principio de cada ejecución del script."""
    j = st.session_state.get("trabajo")
    if j is None or j.aplicado or j.estado != "listo":
        return False
    j.aplicado = True
    m, r = j.meta, j.resultados["objetivo"]
    st.session_state["resultado"] = r
    st.session_state["resultado_id"] = st.session_state.get("resultado_id", 0) + 1
    st.session_state["modo_simulado"] = m["modo"]
    st.session_state["extremo"] = m["extremo"]
    st.session_state["fuera_zona"] = m["fuera_zona"]
    st.session_state["limites_simulado"] = m["ilim"]
    st.session_state["preset_simulado"] = m["preset"]
    if m["crea"]:  # su calificación sale del Δ de ESTA simulación contra el estilo neutro
        from ..motor.comparar import comparar as _cmp

        c = _cmp(r.temporada, _referencia_liga(m["modo"]).temporada)
        st.session_state["calif_creada"] = {
            "huella": m["huella"],
            "delta": float(c.resumen["media"]),
            "ic90": [float(x) for x in c.resumen["int90"]],
        }
    st.session_state["casino"] = {"giros": 0, "mejor": None, "peor": None, "ultimo": None}
    st.session_state.pop("partido", None)
    return True


def _cifra_partidos(n: int) -> str:
    """«7.6 millones de partidos» (un decimal, truncado) o «153 millones de partidos» si la cifra es redonda; menos de un millón, con comas."""
    if n < 1_000_000:
        return T.SIM_PARTIDOS.format(x=f"{n:,}")
    x = math.floor(n / 1e5) / 10
    return T.SIM_MILLONES.format(x=f"{x:.0f}" if x == int(x) else f"{x:.1f}")


def _cifra_torneos(n: int) -> str:
    """«10,000» o «1,000,000 de» (con «de» a partir del millón: «1,000,000 de torneos»)."""
    return f"{n:,} de" if n >= 1_000_000 else f"{n:,}"


def _tiempo_aprox(s: float) -> str:
    """«unos 2 s» / «unos 3 min» (redondeado: es un estimado)."""
    return f"{max(1, round(s))} s" if s < 90 else f"{round(s / 60)} min"


def _tiempo(s: float) -> str:
    s = int(math.ceil(s))
    return f"{s} s" if s < 60 else f"{s // 60} min {s % 60} s"


def _progreso_vivo() -> None:
    """El avance de la simulación (se refresca solo cada segundo mientras corre): lo que se simula, el % real y el tiempo restante según el ritmo medido."""
    j = st.session_state.get("trabajo")
    if j is None:
        return
    if j.estado != "corriendo":
        st.rerun()  # terminó (o se canceló): la app se redibuja con el resultado
    c = _simulador().cifras_modo(j.meta["modo"])
    titulo = T.SIM_TITULO.format(
        torneos=_cifra_torneos(c["torneos"]),
        partidos=c["partidos_por_torneo"],
        total=_cifra_partidos(c["partidos"]),
    )
    st.markdown(f'<div class="sim-progreso">{titulo}</div>', unsafe_allow_html=True)
    resto = j.restante()
    st.progress(
        j.progreso,
        text=T.SIM_AVANCE.format(
            p=int(100 * j.progreso),
            t=T.SIM_CALCULANDO if resto is None else T.SIM_FALTAN.format(t=_tiempo(resto)),
        ),
    )
    if st.button(T.SIM_CANCELAR, key="b_cancelar", width="stretch"):
        j.cancelar()


def _panel_progreso() -> None:
    j = st.session_state.get("trabajo")
    if j is None:
        return
    if j.estado == "corriendo":
        st.fragment(run_every=1.0)(_progreso_vivo)()
    elif j.estado == "cancelado":
        C.nota(T.SIM_CANCELADA)
    elif j.estado == "error":
        st.error(T.SIM_ERROR)


def _huella(per: dict, ilim: bool) -> tuple:
    return (bool(ilim),) + tuple(sorted((k, str(v)) for k, v in per.items()))


# ---------------------------------------------------------------- pestaña «Simulador»
def pesa_mas_datos(sim: Simulador) -> dict:
    return A.escala_efectos(sim)


def _rango(ic) -> tuple:
    return (
        ((ic[0], ic[1]), T.PESA_RANGO.format(a=f"{ic[0]:.1f}", b=f"{ic[1]:.1f}"))
        if ic
        else (None, "")
    )


def _pesa_mas(sim: Simulador, compacto: bool = False, heroe: bool = False) -> None:
    """Tres barras que crecen: suerte, jugadores y técnico, en la MISMA escala (lo típico que varía en un torneo, en puntos), cada una con su rango probable (D-074)."""
    e = pesa_mas_datos(sim)
    frase = A.frase_pesa_mas(e) or ""
    (s_ic, s_txt), (j_ic, j_txt), (t_ic, t_txt) = (
        _rango(e.get("suerte_ic")),
        _rango(e.get("jugadores_ic")),
        _rango(e.get("tecnico_ic")),
    )
    C.pesa_mas(
        [
            (
                T.PESA_SUERTE,
                e["suerte"],
                PA.color("neutro"),
                s_ic,
                s_txt,
            ),  # suerte en gris, jugadores en azul, técnico en amarillo (D-097)
            (T.PESA_JUGADORES, e["jugadores"], PA.color("azul"), j_ic, j_txt),
            (T.PESA_TECNICO, e["tecnico"], PA.color("amarillo"), t_ic, t_txt),
        ],
        frase,
        T.PESA_NOTA,
        T.PESA_TITULO,
        T.PESA_SIN_DATO,
        T.PESA_AYUDA,
        compacto,
        A.frase_suerte(e.get("azar_sobre_real")) or "",
        heroe,
    )


def _insignias() -> None:
    if st.session_state.get("limites_simulado") and (
        st.session_state.get("fuera_zona") or st.session_state.get("extremo")
    ):
        st.markdown(
            f'<div class="fila-insignias">{C.insignia(T.INSIGNIA_FUERA, "fuera")}</div>',
            unsafe_allow_html=True,
        )


def exigencia_de(sim: Simulador, r, base) -> dict:
    """El veredicto de exigencia del resultado: P(top N) de este técnico contra la de Almada (la misma simulación y modo) y contra el peor técnico real (`perfiles_tecnicos.json`)."""
    R, Rb = r.temporada.resumen, base.temporada.resumen
    peor = A.peor_tecnico_real((sim.perfiles() or {}).get("exigencia"))
    nivel = A.nivel_exigencia(
        R["p_top"]["media"], R["p_top"]["ee"], Rb["p_top"]["media"], Rb["p_top"]["ee"], peor
    )
    return {
        "nivel": nivel,
        "top": R["p_top"]["media"],
        "top_actual": Rb["p_top"]["media"],
        "peor": peor,
    }


def _veredicto(nivel: str) -> None:
    emoji, titulo, frase = T.EXIGENCIA[nivel]
    st.markdown(
        f'<div class="exigencia exigencia-{nivel}"><span class="ex-emoji">{emoji}</span><div><div class="ex-titulo">{titulo}</div><div class="ex-frase">{frase}</div></div></div>',
        unsafe_allow_html=True,
    )


def _tarjetas(sim: Simulador, r, base) -> None:
    """Cinco tarjetas con cifras grandes (lo que cambia se mide contra el América actual) y el veredicto de exigencia. La celebración (banner y confeti) solo sale en ."""
    R, Rb = r.temporada.resumen, base.temporada.resumen
    cfg = config.cargar()["torneo"]
    top_n = config.cargar()["exigencia"]["top"]
    pts, pl, pt = R["puntos_esperados"], 100 * R["p_liguilla"]["media"], 100 * R["p_top"]["media"]
    dp, dl = pts - Rb["puntos_esperados"], pl - 100 * Rb["p_liguilla"]["media"]
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        a, b = R["puntos_rango80"]
        C.tarjeta_grande(
            T.TARJETA_PUNTOS, C.numero(pts, 1), T.TARJETA_RANGO.format(a=int(a), b=int(b)), 0.0
        )
    with c2:
        if C.signo_delta(dp, 0.05) == 0 and C.signo_delta(dl, 0.5) == 0:
            cuerpo = (
                f'<span class="delta" style="color:{C.NEUTRO_HTML}">= {T.TARJETA_VS_IGUAL}</span>'
            )
        else:
            cuerpo = C.delta_html(dp, 1, T.UNIDAD_PTS, 0.05) + C.delta_html(
                dl, 0, "% " + T.UNIDAD_LIGUILLA, 0.5
            )
        C.tarjeta_grande(T.TARJETA_VS, cuerpo, T.TARJETA_VS_DETALLE, 0.08)
    with c3:
        C.tarjeta_grande(
            T.TARJETA_LIGUILLA,
            C.numero(pl, 0, "", " %"),
            T.TARJETA_LIGUILLA_DETALLE.format(n=cfg["liguilla_directa"]),
            0.16,
            C.barra_prob(pl),
        )
    with c4:
        C.tarjeta_grande(
            T.TARJETA_TOP.format(n=top_n),
            C.numero(pt, 0, "", " %"),
            T.TARJETA_TOP_DETALLE.format(n=top_n),
            0.2,
            C.barra_prob(pt),
        )
    with c5:
        if cfg["play_in"] > 0:
            C.tarjeta_grande(
                T.TARJETA_PLAYIN,
                C.numero(100 * R["p_play_in"]["media"], 0, "", " %"),
                T.TARJETA_PLAYIN_DETALLE.format(
                    a=cfg["liguilla_directa"] + 1, b=cfg["liguilla_directa"] + cfg["play_in"]
                ),
                0.24,
            )
        else:
            C.tarjeta_grande(
                T.TARJETA_FUERA,
                C.numero(100 * R["p_fuera"], 0, "", " %"),
                T.TARJETA_FUERA_DETALLE,
                0.24,
            )
    e = exigencia_de(sim, r, base)
    _veredicto(e["nivel"])
    C.nota(T.NIVELES_NOTA)


def _calificacion_actual(sim: Simulador, preset: str, per: dict, ilim: bool) -> dict | None:
    """La calificación de lo que hay en pantalla: de un técnico real, su Δ guardado contra el estilo neutro; de uno inventado, el Δ de la simulación de ESTAS perillas si ya
    se corrió (con su rango) o, si no, un Δ estimado de las perillas (sin rango, así que sin color)."""
    if preset != CREA:
        return A.calificaciones_reales(sim).get(preset)
    cc = st.session_state.get("calif_creada")
    if cc and cc["huella"] == _huella(per, ilim):
        return A.calificacion_de_delta(sim, cc["delta"], cc["ic90"])
    d = A.delta_estimado(sim, per, ilim)
    return None if d is None else A.calificacion_de_delta(sim, d)


def _ayuda_mapa(sim: Simulador) -> str:
    y = (
        T.MAPA_AYUDA_Y_PRESION
        if sim.nombre_perilla_defensa() == T.DEFIENDE_PRESION
        else T.MAPA_AYUDA_Y_DEFIENDE
    )
    return " ".join((T.MAPA_AYUDA_X, y, T.MAPA_AYUDA_ZONA, T.MAPA_AYUDA_DENSIDAD))


def _carta_y_mapa(sim: Simulador) -> None:
    """La carta del técnico (calificación, seis atributos y «Se parece a») y su radar, junto al mapa de estilos. Todo se mueve con las perillas, sin simular."""
    ilim = _ilim()
    per = _leer_perillas(ilim)
    preset = st.session_state.get("k_preset", CREA)
    c = A.carta(sim, per, ilim)
    nombre = T.COMPARAR_BASE_TU if preset == CREA else preset
    fuera = preset == CREA and sim.fuera_de_la_zona(per, ilim)
    cal = _calificacion_actual(sim, preset, per, ilim)
    calif = cal["calif"] if cal else None
    color = PA.color(
        A.color_calificacion(calif, cal["cruza"], cal.get("seguridad")) if cal else A.COLOR_NEUTRO
    )
    seg = (
        T.CALIF_SEGURIDAD.format(s=T.CALIF_SEGURIDAD_NIVELES[cal["seguridad"]])
        if cal and cal.get("seguridad")
        else ""
    )
    ayuda_rango = (
        T.CALIF_RANGO.format(a=f"{cal['rango'][0]:.1f}", b=f"{cal['rango'][1]:.1f}")
        if cal and cal.get("rango")
        else ""
    )
    delta = ""
    if cal:
        d = f"{cal['delta']:+.1f}" if abs(cal["delta"]) >= 0.05 else "0.0"
        delta = (T.CALIF_DELTA_ESTIMADO if cal.get("estimada") else T.CALIF_DELTA).format(d=d)
    aviso = ""
    if cal and cal.get("estimada"):
        aviso = T.CALIF_ESTIMADA
    elif cal and (cal["cruza"] or cal.get("seguridad") == "baja"):
        aviso = T.CALIF_NO_SEPARA
    parece = (
        T.CARTA_NINGUNO
        if c["parecido"] is None
        else (T.CARTA_ES if c["es_el_mismo"] else T.CARTA_PARECE).format(n=c["parecido"])
    )
    solo_estilo = "cambios_tipo" in set(sim.p.meta.get("perillas_solo_estilo", []))
    num = (
        T.CALIF_RANGO_NUM.format(a=f"{cal['rango'][0]:.1f}", b=f"{cal['rango'][1]:.1f}")
        if cal and cal.get("rango")
        else T.CALIF_RANGO_SIN
    )
    C.seccion(T.CARTA_TITULO, T.CALIF_AYUDA.format(rango=num))
    col1, col2 = st.columns([5, 6])
    with col1:
        st.markdown(
            C.carta_tecnico_html(
                nombre,
                calif,
                color,
                list(zip(T.CARTA_ATRIBUTOS, c["atributos"])),
                parece,
                T.CALIF_ETIQUETA,
                fuera and ilim,
                T.INSIGNIA_FUERA,
                seg,
                aviso,
                delta,
                ayuda_rango,
                T.CAMBIOS_CHIP.format(x=per["cambios_tipo"]),
                T.CAMBIOS_SOLO_ESTILO if solo_estilo else "",
                T.CALIF_CAMBIOS_AYUDA,
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.plotly_chart(
            G.radar(c["atributos"], T.CARTA_ATRIBUTOS_RADAR, color),
            config=G.CONFIG,
            width="stretch",
            key="radar_carta",
        )
    C.nota(T.CARTA_NOTA + " " + T.CALIF_AVISO)
    C.seccion(T.SECCION_MAPA, _ayuda_mapa(sim))
    C.nota(T.MAPA_VIVO_NOTA)
    if fuera:
        st.markdown(C.insignia(T.MAPA_FUERA, "fuera"), unsafe_allow_html=True)
    lim = 312 if ilim else 112
    califs = {n: v["calif"] for n, v in A.calificaciones_reales(sim).items()}
    st.plotly_chart(
        G.mapa_tecnicos(
            sim.ejes.nombres,
            sim.ejes.puntos,
            sim.ejes.casco(),
            (per["ataca"], per["defiende"]),
            _nombre_defensa(sim),
            califs,
            lim,
            fuera,
            A.densidad_tecnicos(sim.ejes.puntos, lim),
        ),
        config=G.CONFIG,
        width="stretch",
        key="mapa_en_vivo",
    )
    C.nota(T.MAPA_AYUDA)


def _estilos(sim: Simulador, r, modo: str) -> None:
    e = r.estilo
    act = _america_actual(modo).estilo
    liga = sim.p.meta["mezcla_liga"]
    c1, c2 = st.columns(2)
    for col, titulo, clave, series, nota_chico, rival in (
        (
            c1,
            T.SECCION_ESTILO_PROPIO,
            "pi",
            (T.SERIE_TECNICO, T.SERIE_ACTUAL),
            T.EFECTO_CHICO,
            False,
        ),
        (
            c2,
            T.SECCION_ESTILO_RIVAL,
            "pi_rival",
            (T.SERIE_RIVAL_TECNICO, T.SERIE_RIVAL_ACTUAL),
            T.EFECTO_CHICO_RIVAL,
            True,
        ),
    ):
        with col:
            C.seccion(titulo)
            filas = [(series[0], e[clave]), (series[1], act[clave]), (T.SERIE_LIGA, liga)]
            st.plotly_chart(
                G.barras_tipos(filas, rival=rival),
                config=G.CONFIG,
                width="stretch",
                key=f"barras_{clave}",
            )
            if max(abs(100 * (np.asarray(e[clave]) - np.asarray(act[clave])))) < 1.0:
                C.nota(nota_chico)
    st.markdown(f'<div class="leyenda">{C.leyenda_tipos()}</div>', unsafe_allow_html=True)
    C.nota(T.BARRAS_NOTA + " " + T.AYUDA_TOQUE)


def _tabla_final(sim: Simulador, r) -> None:
    cfg = config.cargar()["torneo"]
    C.seccion(T.SECCION_TABLA)
    C.nota(T.TABLA_NOTA)
    st.markdown(
        f'<div class="tarjeta-tabla">{C.tabla_final_html(A.tabla_final(sim, r), cfg["liguilla_directa"], T.TABLA_COLUMNAS, T.TABLA_LINEA)}</div>',
        unsafe_allow_html=True,
    )


def _contadores_ocultos(sim: Simulador) -> set:
    """Contadores de pelota parada que la medición de la exigencia encontró a más de 5 % de la media REAL de la liga (se ocultan; D-085). Sin esa medición no se oculta ninguno."""
    cont = ((sim.perfiles() or {}).get("exigencia") or {}).get("contadores") or {}
    return {k for k, v in cont.items() if not v.get("ok", True)}


def estadisticas_para_panel(sim: Simulador, p: dict) -> list:
    """Los grupos de filas (etiqueta, América, rival) del panel de estadísticas del partido, sin los contadores ocultos."""
    a, b = p["estadisticas"]["america"], p["estadisticas"]["rival"]
    ocultos = _contadores_ocultos(sim)
    fila = lambda clave, etiqueta: (
        (etiqueta, a[clave], b[clave]) if clave in a and clave not in ocultos else None
    )
    general = [
        fila(k, T.PARTIDO_STATS[k])
        for k in (
            "remates",
            "corner",
            "tiro_libre_area",
            "tiro_libre_directo",
            "lateral_largo",
            "penal",
        )
    ]
    jugadas = [
        (T.TIPOS_JUGADA[i], a[k], b[k]) for i, k in enumerate(("directa", "toque", "elaborada"))
    ]
    fin = [
        fila(k, T.PARTIDO_STATS[k])
        for k in ("gol_abierto", "remate_sin_gol", "perdidas", "fuera_interrupcion")
    ]
    grupos = [
        (T.PARTIDO_STATS_GRUPOS["general"], [x for x in general if x]),
        (T.PARTIDO_STATS_GRUPOS["jugadas"], jugadas),
        (T.PARTIDO_STATS_GRUPOS["fin"], [x for x in fin if x]),
    ]
    return [(n, f) for n, f in grupos if f]


def _casino(sim: Simulador, r) -> None:
    """«Gira un torneo»: UN torneo de los ya simulados (no se vuelve a simular) y «Ver un partido»: UN partido sorteado minuto a minuto con las reglas del motor."""
    estado = st.session_state.setdefault(
        "casino", {"giros": 0, "mejor": None, "peor": None, "ultimo": None}
    )
    with st.container(key="casino_torneo"):
        C.seccion(T.CASINO_TITULO)
        C.nota(T.CASINO_NOTA)
        if st.button(T.CASINO_BOTON, type="primary", key="b_girar", help=T.CASINO_CUENTA):
            i = int(np.random.default_rng().integers(A.n_torneos_muestra(r)))
            g = A.girar_torneo(sim, r, i)
            estado["giros"] += 1
            estado["mejor"] = (
                g["lugar"] if estado["mejor"] is None else min(estado["mejor"], g["lugar"])
            )
            estado["peor"] = (
                g["lugar"] if estado["peor"] is None else max(estado["peor"], g["lugar"])
            )
            estado["ultimo"] = g
        if estado["giros"] == 0:
            C.nota(T.CASINO_SIN)
        else:
            st.markdown(
                f'<div class="casino-contador">{T.CASINO_CONTADOR.format(n=estado["giros"], mejor=estado["mejor"], peor=estado["peor"])}</div>',
                unsafe_allow_html=True,
            )
            g = estado["ultimo"]
            textos = {
                "equipo": T.CASINO_EQUIPO,
                "pts": T.CASINO_PUNTOS,
                "dif": T.CASINO_DIF,
                "termino": T.CASINO_TERMINO.format(n=g["lugar"]),
                "liguilla": T.CASINO_LIGUILLA,
                "fuera": T.CASINO_FUERA,
                "racha": T.CASINO_RACHA,
            }
            AN.casino(
                {
                    "tabla": g["tabla"],
                    "racha": g["racha"],
                    "clasifica": g["clasifica"],
                    "liguilla": g["liguilla"],
                },
                textos,
            )
    with st.container(key="casino_partido"):
        C.seccion(T.PARTIDO_TITULO, T.PARTIDO_BARRAS_AYUDA)
        C.nota(T.PARTIDO_NOTA)
        equipos = sim.p.meta["equipos"]
        rivales = [e for e in range(len(equipos)) if e != sim.foco]
        c1, c2 = st.columns([3, 2])
        with c1:
            rival = st.selectbox(
                T.PARTIDO_RIVAL, rivales, format_func=lambda e: equipos[e], key="k_rival"
            )
        with c2:
            sede = st.radio(T.PARTIDO_SEDE, T.PARTIDO_SEDES, horizontal=True, key="k_sede")
        if st.button(T.PARTIDO_BOTON, type="primary", key="b_partido"):
            st.session_state["partido"] = A.partido_unico(
                sim,
                r.tecnico,
                rival,
                sede == T.PARTIDO_SEDES[0],
                int(np.random.default_rng().integers(2**31)),
            )
        p = st.session_state.get("partido")
        if p is not None:
            textos = {
                "america": equipos[sim.foco],
                "gol": T.PARTIDO_GOL,
                "resultado": list(T.PARTIDO_RESULTADO),
                "sin_goles": T.PARTIDO_SIN_GOLES,
                "minuto": T.PARTIDO_MINUTO,
                "antes": T.PARTIDO_ANTES.format(
                    g=round(100 * p["p_gana"]),
                    e=round(100 * p["p_empata"]),
                    p=round(100 * p["p_pierde"]),
                ),
                "barras": T.PARTIDO_BARRAS,
                "cien": T.PARTIDO_FINAL.format(x=round(100 * p["p_gana"])),
                "remates": T.PARTIDO_REMATES.format(
                    a=p["remates_america"], rival=p["nombre_rival"], b=p["remates_rival"]
                ),
                "hover": T.PARTIDO_HOVER,
                "hover_fila": T.PARTIDO_HOVER_FILA,
            }
            AN.partido(AN.datos_partido(p), textos)
            st.markdown(
                C.estadisticas_partido_html(
                    estadisticas_para_panel(sim, p),
                    T.PARTIDO_STATS_TITULO,
                    equipos[sim.foco],
                    p["nombre_rival"],
                    p["local"],
                    T.PARTIDO_HONESTO,
                    T.PARTIDO_STATS_NOTA,
                ),
                unsafe_allow_html=True,
            )


def _texto_cambio(c: dict) -> str:
    """«+12 %» o «−3.4 %» del valor SIN redondear (con los decimales justos para que no salga «+0 %»); «antes 0» si hoy el valor es 0."""
    if c["de_cero"]:
        return T.FICHA_DE_CERO
    for d in (0, 1, 2):
        t = f"{100 * c['rel']:+.{d}f} %".replace("-", "−")
        if round(100 * c["rel"], d) != 0 or d == 2:
            return t
    return t


def _fila_ficha(
    nombre: str,
    tu: float,
    actual: float,
    tipo: str,
    decimales: int,
    sufijo: str = "",
    ee: tuple = (0.0, 0.0),
) -> dict:
    """Una fila de la ficha: el estado sale de `A.cambio` con los números sin redondear; si hay cambio, los decimales suben hasta que los dos números se vean distintos."""
    c = A.cambio(tu, actual, tipo, *ee)
    d = A.decimales_distintos(tu, actual, decimales) if c["estado"] != "igual" else decimales
    cfg = config.cargar()["ficha_cambio"]
    ancho = (
        0.0
        if c["estado"] == "igual"
        else (100.0 if c["de_cero"] else min(abs(c["rel"]) / cfg["barra_max_rel"], 1.0) * 100)
    )
    return {
        "nombre": nombre,
        "tu": f"{tu:.{d}f}{sufijo}",
        "actual": f"{actual:.{d}f}{sufijo}",
        "estado": c["estado"],
        "ancho": ancho,
        "cambio": T.FICHA_IGUAL if c["estado"] == "igual" else _texto_cambio(c),
    }


def ficha_filas(sim: Simulador, r, base) -> list:
    """Los grupos de la ficha completa: el técnico contra el América de hoy. Cada fila trae su estado (sube / baja / igual) de `A.cambio` (D-091)."""
    mt, ma = (A.metricas(sim, x.estilo) for x in (r, base))
    Rt, Ra = r.temporada.resumen, base.temporada.resumen
    top_n = config.cargar()["exigencia"]["top"]
    tipos, g = T.TIPOS_JUGADA, T.FICHA_GRUPOS
    k3 = range(3)
    res = [
        _fila_ficha(
            T.FICHA_RESULTADO[0],
            Rt["puntos_esperados"],
            Ra["puntos_esperados"],
            "mc",
            1,
            "",
            (Rt["puntos_esperados_ee"], Ra["puntos_esperados_ee"]),
        ),
        _fila_ficha(
            T.FICHA_RESULTADO[1],
            100 * Rt["p_liguilla"]["media"],
            100 * Ra["p_liguilla"]["media"],
            "mc",
            0,
            " %",
            (100 * Rt["p_liguilla"]["ee"], 100 * Ra["p_liguilla"]["ee"]),
        ),
        _fila_ficha(
            T.FICHA_RESULTADO[2].format(n=top_n),
            100 * Rt["p_top"]["media"],
            100 * Ra["p_top"]["media"],
            "mc",
            0,
            " %",
            (100 * Rt["p_top"]["ee"], 100 * Ra["p_top"]["ee"]),
        ),
    ]
    minuto = (
        _fila_ficha(T.FICHA_CAMBIO_MINUTO, mt["min_cambio"], ma["min_cambio"], "minutos", 0, "'")
        if mt["min_cambio"] is not None and ma["min_cambio"] is not None
        else {
            "nombre": T.FICHA_CAMBIO_MINUTO,
            "tu": "—",
            "actual": "—",
            "ancho": 0.0,
            "estado": "igual",
            "cambio": T.FICHA_IGUAL,
        }
    )
    cambios = [
        minuto,
        {
            "nombre": T.FICHA_CAMBIO_TIPO,
            "tu": T.NOMBRES_CAMBIO[mt["tipo_cambio"]],
            "actual": T.NOMBRES_CAMBIO[ma["tipo_cambio"]],
            "ancho": 0.0,
            "estado": "igual" if mt["tipo_cambio"] == ma["tipo_cambio"] else "distinto",
            "cambio": T.FICHA_IGUAL if mt["tipo_cambio"] == ma["tipo_cambio"] else T.FICHA_DISTINTO,
        },
    ]
    return [
        (g["resultado"], res),
        (g["mezcla"], [_fila_ficha(tipos[k], mt["pi"][k], ma["pi"][k], "pp", 1, " %") for k in k3]),
        (
            g["mezcla_rival"],
            [
                _fila_ficha(tipos[k], mt["pi_rival"][k], ma["pi_rival"][k], "pp", 1, " %")
                for k in k3
            ],
        ),
        (
            g["remates"],
            [_fila_ficha(tipos[k], mt["remates"][k], ma["remates"][k], "conteo", 2) for k in k3],
        ),
        (
            g["remates_rival"],
            [
                _fila_ficha(tipos[k], mt["remates_rival"][k], ma["remates_rival"][k], "conteo", 2)
                for k in k3
            ],
        ),
        (
            g["goles"],
            [
                _fila_ficha(tipos[k], mt["goles_k_favor"][k], ma["goles_k_favor"][k], "conteo", 2)
                for k in k3
            ],
        ),
        (
            g["goles_rival"],
            [
                _fila_ficha(tipos[k], mt["goles_k_contra"][k], ma["goles_k_contra"][k], "conteo", 2)
                for k in k3
            ],
        ),
        (
            g["pp"],
            [
                _fila_ficha(T.FICHA_PP[0], mt["bp_favor"], ma["bp_favor"], "conteo", 2),
                _fila_ficha(T.FICHA_PP[1], mt["bp_contra"], ma["bp_contra"], "conteo", 2),
            ],
        ),
        (g["cambios"], cambios),
    ]


def _ficha_completa(sim: Simulador, r, modo: str) -> None:
    """Todas las métricas del técnico contra el América de hoy (D-091): amarillo ▲ / rojo ▼ solo si el cambio es significativo; si no, «≈ igual» en gris."""
    c = config.cargar()["ficha_cambio"]
    C.seccion(T.SECCION_FICHA, T.FICHA_AYUDA)
    C.nota(
        T.FICHA_NOTA.format(
            rel=f"{100 * c['rel_min']:g}",
            pp=f"{c['abs_pp_min']:g}",
            g=f"{c['abs_goles_min']:g}",
            m=f"{c['abs_minutos_min']:g}",
            k=f"{c['k_ee']:g}",
        )
    )
    st.markdown(
        f'<div class="tarjeta-tabla">{C.ficha_html(ficha_filas(sim, r, _america_actual(modo)), T.FICHA_COLUMNAS, T.FICHA_TABLA_TITULO)}</div>',
        unsafe_allow_html=True,
    )


def perfil_tecnico(sim: Simulador, nombre: str | None) -> None:
    """Tarjeta descriptiva (no entra a la simulación): dónde está el equipo del técnico frente a los técnicos de la liga."""
    pf = sim.perfiles()
    if not pf or not nombre:
        return
    d = pf.get("tecnicos", {}).get(nombre)
    if not d:
        return
    C.seccion(T.PERFIL_TITULO)
    C.nota(
        T.PERFIL_BASE.format(
            n=pf.get("n_referencia", ""),
            m=pf.get("min_partidos", ""),
            p=d.get("partidos", ""),
            nombre=nombre,
        )
    )
    filas = [
        T.frase_perfil(k, d["metricas"][k]["pct"])
        for k in T.PERFIL_ORDEN
        if d.get("metricas", {}).get(k, {}).get("pct") is not None
    ]
    if not filas:
        C.nota(T.PERFIL_SIN_DATOS)
        return
    C.tarjeta_lista(filas)
    C.nota(T.PERFIL_NOTA)


def barras_goles_visibles(sim: Simulador) -> bool:
    """«¿Qué jugadas dan sus goles?» solo se muestra si de verdad cambia entre técnicos (D-090): la regla (alguna barra cambia ≥ 5 % entre los técnicos reales) la mide
    `herramientas/variacion_graficas.py` y la publicación la guarda en `perfiles_tecnicos.json["variacion_graficas"]`. Sin esa medición, se muestra."""
    v = (sim.perfiles() or {}).get("variacion_graficas") or {}
    return bool(v.get("barras_se_quedan", True))


def pestana_simulador(sim: Simulador, modo: str) -> None:
    r = st.session_state.get("resultado")
    _bloque_torneo(sim)  # 0. qué torneo se simula y qué es «América hoy» (D-092)
    _pesa_mas(sim)  # 1. ¿qué pesa más?
    if _ilim():
        C.aviso_limites(T.LIMITES_AVISO_TITULO, T.LIMITES_AVISO)
    if r is None:
        C.nota(T.INVITACION)
        _carta_y_mapa(sim)
        C.nota(T.PIE_CORTO)
        return
    if st.session_state.get("extremo"):
        st.warning(T.AVISO_EXTREMO)
    if st.session_state.get("fuera_zona") and not st.session_state.get("limites_simulado"):
        st.warning(T.AVISO_FUERA_ZONA)
    cfg = config.cargar()["torneo"]
    R = r.temporada.resumen
    _insignias()
    _tarjetas(sim, r, _america_actual(modo))  # 2. las cuatro tarjetas, contra el América actual
    _carta_y_mapa(sim)  # 3. carta del técnico y mapa de estilos
    _estilos(sim, r, modo)  # 4. así jugaría tu equipo / así le jugarían los rivales
    col1, col2 = st.columns(2)  # 6. puntos y lugar
    with col1:
        C.seccion(T.SECCION_PUNTOS)
        st.plotly_chart(
            G.histograma_puntos(R["puntos_hist"], R["puntos_rango80"]),
            config=G.CONFIG,
            width="stretch",
            key="hist_puntos",
        )
    with col2:
        C.seccion(T.SECCION_LUGAR)
        st.plotly_chart(
            G.barras_lugar(R["p_lugar"], cfg["liguilla_directa"]),
            config=G.CONFIG,
            width="stretch",
            key="barras_lugar",
        )
    _tabla_final(sim, r)  # 7. tabla final simulada
    _casino(sim, r)  # 8. gira un torneo / ver un partido (con el peligro de gol)
    if barras_goles_visibles(sim):  # 10. qué jugadas dan sus goles (barras)
        e = r.estilo
        C.seccion(T.SECCION_GOLES)
        C.nota(T.NOTA_GOLES)
        etiquetas = list(T.TIPOS_JUGADA) + list(T.TIPOS_BALON_PARADO)
        favor = list(e["goles_k_favor"]) + list(e["goles_bp_favor"])
        contra = list(e["goles_k_contra"]) + list(e["goles_bp_contra"])
        st.plotly_chart(
            G.barras_goles(etiquetas, favor, contra),
            config=G.CONFIG,
            width="stretch",
            key="barras_goles",
        )
    _ficha_completa(sim, r, modo)  # 11. ficha completa (a la vista; incluye sus cambios)
    perfil_tecnico(sim, st.session_state.get("preset_simulado"))  # 12. perfil del equipo
    C.nota(T.PIE_CORTO)


# ---------------------------------------------------------------- pestaña «Antes de jugar»: una cuadrícula de tarjetas
def _formato_efecto(x: float) -> str:
    return T.EFECTO_MENOS if x < 0.1 else (f"{x:.1f}" if x < 10 else f"{x:.0f}")


def _azar(sim: Simulador, efectos: dict) -> str:
    """Lo típico que varía la suerte en un torneo (la misma barra de «¿Qué pesa más?»); sin la medición de la dispersión, la media amplitud del rango del 80 %."""
    suerte = A.escala_efectos(sim).get("suerte")
    if suerte is None:
        a, b = _america_actual("rapido").temporada.resumen["puntos_rango80"]
        suerte = (b - a) / 2
    return f"{round(suerte):.0f}"


def _texto_efecto(clave: str, efectos: dict, estilo: set, azar: str) -> str:
    if clave == "ajustes":
        return (
            T.EFECTO_NO_CAMBIA.format(a=azar)
            if {"reaccion_marcador", "reaccion_rival", "cambios_momento", "cambios_tipo"} <= estilo
            else T.EFECTO_SIN_DATO
        )
    e = efectos.get(clave)
    if not e:
        return T.EFECTO_SIN_DATO
    return T.EFECTO_NUMERO.format(x=_formato_efecto(abs(e["delta"])), a=azar)


def _enlaces() -> None:
    """El enlace principal (la documentación del modelo, del config) y, más chico, el detalle técnico del simulador."""
    e = config.cargar()["enlaces"]
    st.link_button(T.ESTUDIO_ORIGINAL, e["estudio_original"], type="primary")
    st.link_button(T.VER_DETALLE, e["validacion"], type="tertiary")


def _etiqueta_global(sim: Simulador) -> str:
    g, _, _ = sim.validacion_total()
    etiqueta = ((g or {}).get("retroprueba") or {}).get("etiqueta") or sim.p.meta.get(
        "etiqueta_global", "descriptivo"
    )
    return T.ETIQUETA_GLOBAL.get(etiqueta, T.ETIQUETA_GLOBAL["descriptivo"])


def _tarjeta_reel(titulo: str, lineas, etiqueta: str = "", enlaces: bool = False) -> None:
    st.markdown(
        f'<div class="c-titulo">{titulo}</div>'
        + "".join(f'<div class="reel-linea">{l}</div>' for l in lineas),
        unsafe_allow_html=True,
    )
    if etiqueta:
        C.nota(etiqueta)
    if enlaces:
        _enlaces()


def _tipos_ancho(sim: Simulador) -> None:
    """Los tres tipos de jugada a todo lo ancho: una columna por tipo con su cancha, una frase y cuatro números en chips grandes."""
    cols = []
    for k, d in enumerate(sim.tipos_de_jugada()):
        valores = (
            f"{round(d['pct'])} %",
            f"{d['toques']:.1f}",
            f"{round(d['remate'])} %",
            f"{d['goles100']:.1f}",
        )
        chips = "".join(
            f'<div class="chip-dato"><b>{v}</b><span>{e}</span></div>'
            for v, e in zip(valores, T.TIPOS_CHIPS)
        )
        cols.append(
            f'<div class="tipo-col"><div class="tipo-nombre">{T.TIPOS_JUGADA[k]}</div><div class="tipo-cancha">{C.cancha_svg(k)}</div>'
            f'<div class="tipo-frase">{T.TIPOS_DESCRIPCION[k]}</div><div class="chips-datos">{chips}</div></div>'
        )
    st.markdown(
        f'<div class="c-titulo">{T.ANTES_TIPOS_TITULO}</div><div class="reel-linea">{T.ANTES_TIPOS_INTRO}</div><div class="tipos-ancho">{"".join(cols)}</div>'
        f'<div class="nota">{T.TIPOS_NOTA}</div>',
        unsafe_allow_html=True,
    )


def _perillas_desplegables(sim: Simulador, efectos: dict, estilo: set, azar: str) -> None:
    """Una sección desplegable por perilla (la primera abierta): en la cancha, en el simulador y cuánto mueve los puntos."""
    nombres = {"defiende": _nombre_defensa(sim)}
    partes = []
    for n, (clave, (nom, cancha, simulador)) in enumerate(T.FICHAS.items()):
        partes.append(
            f'<details class="perilla"{" open" if n == 0 else ""}><summary>{nombres.get(clave, nom)}</summary>'
            f'<div class="c-bloque"><b class="c-in">{T.FICHA_CANCHA}</b> {cancha}</div>'
            f'<div class="c-bloque"><b class="c-in">{T.FICHA_SIMULADOR}</b> {simulador}</div>'
            f'<div class="c-bloque"><b class="c-in">{T.FICHA_PUNTOS}</b> {_texto_efecto(clave, efectos, estilo, azar)}</div></details>'
        )
    st.markdown(
        f'<div class="c-titulo">{T.ANTES_PERILLAS_TITULO}</div>{"".join(partes)}',
        unsafe_allow_html=True,
    )


def lineas_torneo(sim: Simulador) -> list[str]:
    """Las tres ideas del bloque «qué torneo simulamos»: el torneo y su calendario, con qué partidos se estima el plantel y qué es «América hoy». Todo sale de `meta.json`."""
    i = A.torneo_info(sim)
    antes = T.TORNEO_ANTES.format(fecha=T.fecha_es(i["fecha_corte"])) if i["fecha_corte"] else ""
    cuantos = (
        T.TORNEO_CUANTOS.format(n=i["quitados"], a=T.fecha_es(i["desde"]), b=T.fecha_es(i["hasta"]))
        if i["quitados"] and i["desde"]
        else ""
    )
    return [
        T.TORNEO_SIMULAMOS.format(torneo=i["torneo"], partidos=i["partidos"]),
        T.TORNEO_PLANTEL.format(anterior=i["anterior"] or T.TORNEO_ANTERIOR_GENERICO, antes=antes),
        T.TORNEO_NO_USAMOS.format(cuantos=cuantos),
        T.TORNEO_HOY,
    ]


def _bloque_torneo(sim: Simulador) -> None:
    st.markdown(C.bloque_torneo(T.TORNEO_TITULO, lineas_torneo(sim)), unsafe_allow_html=True)


def pestana_antes(sim: Simulador) -> None:
    """«Antes de jugar» (v8): el héroe «¿Qué pesa más?» a todo lo ancho; cuatro tarjetas cortas de altura libre; los tres tipos de jugada a todo lo ancho; una sección por
    perilla; lo que no simula en dos columnas y el botón grande al final. Sin cuadrícula de alturas iguales: no sobra espacio vacío."""
    pf = sim.perfiles() or {}
    efectos = dict(pf.get("efecto_perillas", {}))
    azar = _azar(sim, efectos)
    estilo = set(sim.p.meta.get("perillas_solo_estilo", []))
    with st.container(key="antes_heroe"):
        _pesa_mas(sim, heroe=True)
    with st.container(
        key="fila_antes"
    ):  # 2 columnas en escritorio, 1 en móvil; cada tarjeta mide lo que su contenido
        with st.container(key="antes_torneo"):
            _bloque_torneo(sim)
        with st.container(key="antes_es"):
            _tarjeta_reel(T.ANTES_QUE_ES_TITULO, T.ANTES_QUE_ES, enlaces=True)
        with st.container(key="antes_no"):
            _tarjeta_reel(T.ANTES_QUE_NO_TITULO, T.ANTES_QUE_NO, _etiqueta_global(sim))
        with st.container(key="antes_fijos"):
            _tarjeta_reel(T.ANTES_FIJOS_TITULO, T.ANTES_FIJOS)
        with st.container(key="antes_niveles"):
            _tarjeta_reel(
                T.ANTES_NIVELES_TITULO,
                [f"{e} <b>{t}</b>: {d}" for e, t, d in T.NIVELES.values()],
                T.NIVELES_NOTA,
            )
    with st.container(key="antes_tipos"):
        _tipos_ancho(sim)
    with st.container(key="antes_perillas"):
        _perillas_desplegables(sim, efectos, estilo, azar)
    with st.container(key="antes_nosim"):
        st.markdown(
            f'<div class="c-titulo">{T.ANTES_NO_SIMULA_TITULO}</div><ul class="lista-dos">'
            + "".join(f"<li>{l}</li>" for l in T.ANTES_NO_SIMULA)
            + "</ul>"
            f'<div class="nota">{T.ANTES_CIERRE}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------- pestaña «¿Le podemos creer?»
def _p(p: float) -> str:
    return T.P_MENOR if p < 0.001 else T.P_VALOR.format(p=f"{p:.3f}" if p < 0.1 else f"{p:.2f}")


def _carta(c: dict, g: dict, disp: dict | None) -> None:
    """Una tarjeta con formato fijo: la pregunta, lo que suponemos, lo que medimos (nombre técnico en letra chica), el número grande, el veredicto, qué significa para ti,
    la minigráfica y si es prueba fácil o difícil."""
    t = T.CARTAS[c["id"]]
    pasa = c["pasa"]
    significa = t["pasa"] if pasa else t["ojo"]
    with st.container(key=f"carta_{c['id']}"):
        if c["id"] == "goles":
            C.carta_encabezado(t, t["mide"], t["tec"].format(chi2=f"{c['chi2']:.1f}", gl=c["gl"]))
            C.carta_resultado(_p(c["p"]), pasa, significa)
            st.plotly_chart(G.mini_goles(c), config=G.CONFIG, width="stretch", key="mini_goles")
        elif c["id"] == "puntos":
            err = c["error_xpts"]
            C.carta_encabezado(
                t,
                t["mide"],
                t["tec"].format(
                    b=f"{c['pendiente']:.2f} (rango {c['ic95'][0]:.2f} a {c['ic95'][1]:.2f})",
                    err=f"{100 * err:+.2f} %" if err is not None else "n/d",
                ),
            )
            extra = ""
            if disp and disp.get("r"):
                extra = t["r_linea"].format(
                    r=f"{disp['r']['valor']:.2f}",
                    a=f"{disp['r']['ic95'][0]:.2f}",
                    b=f"{disp['r']['ic95'][1]:.2f}",
                )
            C.carta_resultado(f"{c['pendiente']:.2f}", pasa, significa, extra)
            st.plotly_chart(
                G.mini_puntos(g["puntos"], c), config=G.CONFIG, width="stretch", key="mini_puntos"
            )
        elif c["id"] == "calibracion":
            C.carta_encabezado(t, t["mide"], t["tec"])
            C.carta_resultado(_p(c["p_min"]), pasa, significa)
            st.plotly_chart(
                G.mini_calibracion(g["calibracion"]),
                config=G.CONFIG,
                width="stretch",
                key="mini_calibracion",
            )
        elif c["id"] == "independencia":
            C.carta_encabezado(
                t,
                t["mide"],
                t["tec"].format(
                    rho=f"{c['rho']:+.3f}",
                    pend=f"{c['pendiente']:+.3f}" if c["pendiente"] is not None else "n/d",
                ),
            )
            C.carta_resultado(
                T.RANGO_VALOR.format(a=f"{c['ic95'][0]:+.2f}", b=f"{c['ic95'][1]:+.2f}"),
                pasa,
                significa,
            )
            st.plotly_chart(
                G.mini_rango(T.CERO, c["rho"], c["ic95"]),
                config=G.CONFIG,
                width="stretch",
                key="mini_rho",
            )
        elif c["id"] == "placebo":
            C.carta_encabezado(t, t["mide"], t["tec"].format(k=c["k"], n=c["n"]))
            C.carta_resultado(f"{c['k']} de {c['n']}", pasa, significa)
            if c["placebos"]:
                st.plotly_chart(
                    G.mini_placebo(c["placebos"]),
                    config=G.CONFIG,
                    width="stretch",
                    key="mini_placebo",
                )
        elif c["id"] == "recuperacion":
            C.carta_encabezado(t, t["mide"], t["tec"].format(k=c["k"], n=c["n"]))
            C.carta_resultado(f"{100 * c['fraccion']:.0f} %", pasa, significa)
            st.plotly_chart(
                G.mini_recuperacion(c), config=G.CONFIG, width="stretch", key="mini_recuperacion"
            )
        elif c["id"] == "retro":
            C.carta_encabezado(
                t,
                t["mide"],
                t["tec"].format(
                    dm=f"{c['dm']:.2f}" if c["dm"] is not None else "n/d",
                    n=c["n"],
                    mae=f"{c['mae']:.3f}",
                    mae_in=f"{c['mae_inercia']:.3f}",
                ),
            )
            C.carta_resultado(_p(c["p"]) if c["p"] is not None else "n/d", pasa, significa)
            st.plotly_chart(G.mini_retro(c), config=G.CONFIG, width="stretch", key="mini_retro")
        else:  # «partido»: la autoverificación de «Ver un partido»
            C.carta_encabezado(
                t, t["mide"], t["tec"].format(n=f"{c['n']:,}", chi2=f"{c['chi2']:.1f}", gl=c["gl"])
            )
            C.carta_resultado(_p(c["p"]), pasa, significa)
            st.plotly_chart(G.mini_partido(c), config=G.CONFIG, width="stretch", key="mini_partido")
        C.carta_pie(t["tipo"])


def pestana_creer(sim: Simulador) -> None:
    g, val, _ = sim.validacion_total()
    if g is None:
        C.veredicto(T.VALIDACION_PENDIENTE, T.VALIDACION_PENDIENTE_DETALLE, "")
        return
    C.seccion(T.CREER_TITULO)
    C.nota(T.CREER_INTRO)
    C.nota(T.CREER_NO_RECHAZAR)
    C.nota(T.VALIDACION_FECHA.format(fecha=g["generado"], n=g["n_partidos"]))
    cartas = VT.todas(g, val)
    av = _autoverificacion()
    cartas.append({"id": "partido", **VT.partido(av)})
    ok = sum(1 for c in cartas if c["pasa"])
    with st.container(key="carta_resumen"):  # la tarjeta de resumen va primero
        expl = T.RESUMEN_EXPLICADA[0 if len(cartas) - ok == 1 else 1]
        st.markdown(
            f'<div class="resumen-creer">{T.RESUMEN_CREER.format(ok=ok, n=len(cartas), ojo=len(cartas) - ok, expl=expl)}</div>'
            f'<div class="c-bloque">{T.RESUMEN_EXPLICADO}</div>',
            unsafe_allow_html=True,
        )
        retro = g.get("retroprueba") or {}
        C.nota(T.ETIQUETA_GLOBAL.get(retro.get("etiqueta"), T.ETIQUETA_GLOBAL["descriptivo"]))
        _enlaces()
    disp = (sim.perfiles() or {}).get("dispersion")
    with st.container(
        key="rejilla_creer"
    ):  # cuadrícula: las ocho pruebas, todas de la misma altura
        for c in cartas:
            _carta(c, g, disp)


def main() -> None:
    st.set_page_config(page_title=T.TITULO_PESTANA, layout="wide", initial_sidebar_state="auto")
    css = re.sub(
        r"\n\s*\n",
        "\n",
        PA.css_variables()
        + "\n"
        + (Path(__file__).parent / "estilos.css").read_text(encoding="utf-8"),
    )  # sin líneas en blanco: cortarían el bloque HTML
    st.markdown(
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" '
        f'rel="stylesheet"><style>{css}</style>',
        unsafe_allow_html=True,
    )
    sim = _simulador()
    _cosechar(
        sim
    )  # si la simulación en segundo plano ya terminó, su resultado entra antes de dibujar nada
    C.encabezado(sim.p.meta.get("modo") == MODO_SINTETICO)
    preset, modo = barra_lateral(sim)
    pestana_ant, pestana_sim, pestana_cre = st.tabs(
        [T.PESTANA_ANTES, T.PESTANA_SIMULADOR, T.PESTANA_CREER], key="k_pestana"
    )
    with pestana_ant:
        pestana_antes(sim)
    with pestana_sim:
        pestana_simulador(sim, modo)
    with pestana_cre:
        pestana_creer(sim)
