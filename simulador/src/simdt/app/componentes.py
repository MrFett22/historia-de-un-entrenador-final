"""Piezas de interfaz (HTML mínimo + Streamlit). Sin cadenas visibles propias: todo de textos."""

from __future__ import annotations

import html
import re

import streamlit as st

from . import graficas as G
from . import paleta as PA
from . import textos as T


def tarjeta(etiqueta: str, cifra: str, detalle: str = "", texto: bool = False) -> None:
    clase = "cifra" + (" cifra-texto" if texto else "")
    st.markdown(
        f'<div class="tarjeta"><div class="etiqueta">{html.escape(etiqueta)}</div>'
        f'<div class="{clase}">{html.escape(cifra)}</div><div class="detalle">{html.escape(detalle)}</div></div>',
        unsafe_allow_html=True,
    )


def encabezado(demo: bool) -> None:
    insignia = f'<div class="insignia">{html.escape(T.ETIQUETA_DEMO)}</div>' if demo else ""
    st.markdown(
        f'<div class="encabezado">{insignia}<h1>{html.escape(T.TITULO)}</h1>'
        f"<p>{html.escape(T.SUBTITULO)}</p></div>",
        unsafe_allow_html=True,
    )


def seccion(titulo: str, ayuda: str | None = None) -> None:
    st.markdown(f"### {titulo}", help=ayuda)


def nota(texto: str) -> None:
    st.markdown(f'<div class="nota">{html.escape(texto)}</div>', unsafe_allow_html=True)


def franja_pct(lo: float, hi: float, a: float, b: float) -> tuple[float, float]:
    """(izquierda, ancho) en % de la franja [a, b] dentro del rango [lo, hi] del MISMO deslizador (sin anchos mínimos inventados)."""
    ancho = max(hi - lo, 1e-9)
    i = 100 * max(min((a - lo) / ancho, 1.0), 0.0)
    f = 100 * max(min((b - lo) / ancho, 1.0), 0.0)
    return i, max(f - i, 0.0)


def franja_reales(lo: float, hi: float, a: float, b: float) -> None:
    """Franja bajo un deslizador: el tramo [a, b] que cubren los técnicos reales, en la misma escala [lo, hi] del deslizador."""
    i, w = franja_pct(lo, hi, a, b)
    st.markdown(
        f'<div class="franja"><div class="franja-real" style="left:{i:.2f}%;width:{w:.2f}%"></div></div>',
        unsafe_allow_html=True,
    )


def extremos(izq: str, der: str) -> None:
    """Etiquetas de los dos extremos de un deslizador."""
    st.markdown(
        f'<div class="extremos"><span>{html.escape(izq)}</span><span>{html.escape(der)}</span></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- canchas en SVG (ilustración, no gráfica): fondo oscuro, líneas blancas al 25 %, flechas con el color del tipo
_RUTAS = (
    [(14, 40), (78, 52), (104, 38), (118, 40)],  # directo: pase largo, pase filtrado y remate
    [
        (34, 30),
        (44, 54),
        (36, 66),
        (52, 46),
        (44, 24),
    ],  # toque sin profundidad: de lado y hacia atrás
    [
        (28, 10),
        (52, 8),
        (76, 7),
        (98, 10),
        (108, 36),
        (118, 40),
    ],  # elaborado: por la banda, centro y remate
)


def cancha_svg(tipo: int) -> str:
    """Cancha de 120 × 80 (el equipo ataca hacia la derecha) con un recorrido de ejemplo del tipo de jugada `tipo` (0 directo, 1 toque sin profundidad, 2 elaborado)."""
    color = G.TIPOS[tipo]
    k = 2.0
    r = _RUTAS[tipo]
    marca = f"fl{tipo}"
    seg, glow, puntos = [], [], []
    for i, ((x0, y0), (x1, y1)) in enumerate(zip(r[:-1], r[1:])):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        n = max((dx * dx + dy * dy) ** 0.5, 1e-9)
        cx, cy = mx - dy / n * 5, my + dx / n * 5  # curvita suave
        d = f"M{k * x0:.1f},{k * y0:.1f} Q{k * cx:.1f},{k * cy:.1f} {k * x1:.1f},{k * y1:.1f}"
        glow.append(
            f'<path d="{d}" stroke="{color}" stroke-width="9" opacity="0.18" fill="none" stroke-linecap="round"/>'
        )
        seg.append(
            f'<path d="{d}" stroke="{color}" stroke-width="2.6" fill="none" stroke-linecap="round" marker-end="url(#{marca})"/>'
        )
    for x, y in r[:-1]:
        puntos.append(
            f'<circle cx="{k * x:.1f}" cy="{k * y:.1f}" r="4.2" fill="{color}" stroke="{PA.color("fondo")}" stroke-width="1.5"/>'
        )
    ln = f'stroke="{PA.rgba("texto", 0.25)}" stroke-width="1.2" fill="none"'
    return (
        f'<div class="cancha"><svg viewBox="0 0 240 160" xmlns="http://www.w3.org/2000/svg" role="img">'
        f'<defs><marker id="{marca}" markerWidth="7" markerHeight="7" refX="5.2" refY="3.5" orient="auto"><path d="M1,1 L6,3.5 L1,6 z" fill="{color}" stroke="{color}" stroke-width="1.4" stroke-linejoin="round"/></marker></defs>'
        f'<rect x="1" y="1" width="238" height="158" rx="14" fill="{PA.color("fondo")}" stroke="{PA.rgba("texto", 0.12)}"/>'
        f'<rect x="8" y="8" width="224" height="144" rx="4" {ln}/><line x1="120" y1="8" x2="120" y2="152" {ln}/><circle cx="120" cy="80" r="20" {ln}/>'
        f'<rect x="8" y="36" width="36" height="88" {ln}/><rect x="196" y="36" width="36" height="88" {ln}/>'
        f'<rect x="8" y="60" width="12" height="40" {ln}/><rect x="220" y="60" width="12" height="40" {ln}/>'
        f"{''.join(glow)}{''.join(seg)}{''.join(puntos)}</svg></div>"
    )


def leyenda_tipos() -> str:
    return "".join(
        f'<span class="ley"><i style="background:{c}"></i>{html.escape(n)}</span>'
        for c, n in zip(G.TIPOS, T.TIPOS_JUGADA)
    )


def carta_encabezado(t: dict, mide: str, tec: str) -> None:
    """La tarjeta de una prueba (D-087): la pregunta (gancho), «Prueba clásica: …», H0 y H1 en lenguaje simple, «Aquí queremos…» (qué resultado es bueno) y lo que medimos con el
    nombre técnico entre paréntesis. En las pruebas donde se quiere el 0 dentro, la frase de que eso es buena noticia."""
    cero = (
        f'<div class="c-cero">{html.escape(T.CREER_CERO_BUENO)}</div>'
        if t.get("cero_bueno")
        else ""
    )
    st.markdown(
        f'<div class="c-titulo">{html.escape(t["titulo"])}</div>'
        f'<div class="c-clasica"><b>{html.escape(T.CREER_CLASICA)}</b> {html.escape(t["clasica"])}</div>'
        f'<div class="c-hipotesis"><div><b>{T.CREER_H0}</b> {html.escape(t["hipotesis0"])}</div><div><b>{T.CREER_H1}</b> {html.escape(t["hipotesis1"])}</div></div>'
        f'<div class="c-queremos"><b>{html.escape(T.CREER_QUEREMOS)}</b> {html.escape(t["queremos"])}</div>{cero}'
        f'<div class="c-bloque"><span class="c-et">{html.escape(T.CREER_MEDIMOS)}</span>{html.escape(mide)} <span class="chica">({html.escape(tec)})</span></div>',
        unsafe_allow_html=True,
    )


def animar_texto(texto: str) -> str:
    """El primer número del texto sube desde 0 si es entero o tiene un solo decimal («93 %», «5 de 7»); lo demás («p = 0.60», «0.93 a 1.08») queda fijo."""
    m = re.search(r"\d+(?:\.\d+)?", texto)
    if m is None or ("." in m.group() and len(m.group().split(".")[1]) > 1):
        return html.escape(texto)
    ini, fin = texto[: m.start()], texto[m.end() :]
    prefijo = ini.rstrip("−-+")
    signo = ini[len(prefijo) :]
    return html.escape(signo) + numero(
        float(m.group()), len(m.group().split(".")[1]) if "." in m.group() else 0, prefijo, fin
    )


def carta_resultado(numero: str, pasa: bool, significa: str, extra: str = "") -> None:
    """Número grande y veredicto grande (el amarillo es de los veredictos), y «Qué significa para ti» en una frase."""
    ex = f'<div class="c-explica">{html.escape(extra)}</div>' if extra else ""
    st.markdown(
        f'<div class="c-resultado"><div class="c-numero">{animar_texto(numero)}</div>'
        f'<div class="c-veredicto {"pasa" if pasa else "ojo"}">{html.escape(T.PASA if pasa else T.OJO)}</div></div>{ex}'
        f'<div class="c-bloque"><span class="c-et">{html.escape(T.CREER_SIGNIFICA)}</span>{html.escape(significa)}</div>',
        unsafe_allow_html=True,
    )


def carta_pie(tipo: str) -> None:
    st.markdown(
        f'<div class="c-pie">{html.escape(T.CREER_FACIL if tipo == "facil" else T.CREER_DIFICIL)}</div>',
        unsafe_allow_html=True,
    )


def tarjeta_lista(filas: list[str]) -> None:
    """Tarjeta con una frase por línea."""
    items = "".join(f"<li>{html.escape(f)}</li>" for f in filas)
    st.markdown(
        f'<div class="tarjeta tarjeta-lista"><ul>{items}</ul></div>', unsafe_allow_html=True
    )


def lista_datos(filas: list[str]) -> None:
    items = "".join(f"<li>{html.escape(f)}</li>" for f in filas)
    st.markdown(f'<ul class="datos">{items}</ul>', unsafe_allow_html=True)


def veredicto(frase: str, detalle: str, rango: str) -> None:
    st.markdown(
        f'<div class="veredicto"><div class="frase">{html.escape(frase)}</div>'
        f'<div class="detalle">{html.escape(detalle)}</div><div class="detalle">{html.escape(rango)}</div></div>',
        unsafe_allow_html=True,
    )


def pie(etiqueta: str) -> None:
    st.markdown('<div class="pie">', unsafe_allow_html=True)
    st.markdown(T.pie_completo(etiqueta))
    st.markdown("</div>", unsafe_allow_html=True)


# ================================================================ tarjetas con números grandes, animaciones suaves y colores de mejor/peor
VERDE, ROJO, NEUTRO_HTML = (
    PA.color("amarillo"),
    PA.color("rojo_texto"),
    PA.color("texto3"),
)  # «mejor» amarillo, «peor» rojo, «igual» gris (D-097)


def numero(valor: float, decimales: int = 0, prefijo: str = "", sufijo: str = "") -> str:
    """Número que sube desde 0 con CSS puro (sin parpadeos; con `prefers-reduced-motion` o sin soporte queda el número final, que SIEMPRE está en el HTML).
    Con decimales se anima la parte entera y el primer decimal; más de uno se deja fijo."""
    a = abs(float(valor))
    est = f"{a:.{decimales}f}"
    if decimales > 1:
        return f'<span class="num">{html.escape(prefijo)}{est}{html.escape(sufijo)}</span>'
    ent = int(
        est.split(".")[0]
    )  # del texto ya redondeado: el contador termina EXACTAMENTE en el mismo número
    dec = 0 if decimales == 0 else int(est.split(".")[1])
    cls = "d1" if decimales == 1 else "d0"
    return (
        f'<span class="num {cls}">{html.escape(prefijo)}<span class="est">{est}</span>'
        f'<span class="vivo" style="--fin-ent:{ent};--fin-dec:{dec}" aria-hidden="true"></span>{html.escape(sufijo)}</span>'
    )


def signo_delta(d: float, umbral: float) -> int:
    return 0 if abs(d) < umbral else (1 if d > 0 else -1)


def delta_html(d: float, decimales: int, unidad: str, umbral: float) -> str:
    """«▲ +0.4 pts» en amarillo si es mejor, «▼ −0.4 pts» en rojo si es peor, «=» en gris si es prácticamente igual."""
    s = signo_delta(d, umbral)
    flecha, color = ("▲", VERDE) if s > 0 else (("▼", ROJO) if s < 0 else ("=", NEUTRO_HTML))
    signo = "+" if s > 0 else ("−" if s < 0 else "")
    return f'<span class="delta" style="color:{color}">{flecha} {signo}{numero(d, decimales)} {html.escape(unidad)}</span>'


def tarjeta_grande(
    etiqueta: str, cifra_html: str, detalle: str = "", retraso: float = 0.0, extra: str = ""
) -> None:
    st.markdown(
        f'<div class="tarjeta tarjeta-v5" style="--d:{retraso}s"><div class="etiqueta">{html.escape(etiqueta)}</div>'
        f'<div class="cifra cifra-grande">{cifra_html}</div><div class="detalle">{html.escape(detalle)}</div>{extra}</div>',
        unsafe_allow_html=True,
    )


def barra_prob(p: float, color: str = "var(--acento)") -> str:
    """Barra que crece hasta el p % (p entre 0 y 100)."""
    return f'<div class="barra-fondo"><i class="barra-crece" style="--w:{max(0.0, min(100.0, p)):.1f}%;background:{color}"></i></div>'


def insignia(texto: str, clase: str = "") -> str:
    return f'<span class="insignia-v5 {clase}">{html.escape(texto)}</span>'


def pesa_mas(
    items: list[tuple],
    frase: str,
    nota: str,
    titulo: str,
    sin_dato: str,
    ayuda: str = "",
    compacto: bool = False,
    suerte: str = "",
    heroe: bool = False,
) -> None:
    """Tres barras horizontales que crecen: (nombre, valor en puntos o None, color, rango (lo, hi) o None, texto del rango). La más larga ocupa todo el ancho; el rango
    probable se dibuja como una franja clara sobre la barra."""
    mx = max([max(v, (ic[1] if ic else v)) for _, v, _, ic, _ in items if v is not None] + [1e-9])
    filas = []
    for i, (nombre, v, color, ic, txt_ic) in enumerate(items):
        if v is None:
            filas.append(
                f'<div class="pesa-fila"><div class="pesa-nombre">{html.escape(nombre)}</div><div class="pesa-sin">{html.escape(sin_dato)}</div></div>'
            )
            continue
        franja = (
            f'<i class="pesa-ic" style="left:{100 * ic[0] / mx:.1f}%;width:{max(100 * (ic[1] - ic[0]) / mx, 0.8):.1f}%"></i>'
            if ic
            else ""
        )
        rango = (
            f'<div class="pesa-rango">{html.escape(txt_ic)}</div>'
            if (ic and txt_ic and not compacto)
            else ""
        )
        filas.append(
            f'<div class="pesa-fila" style="--d:{0.12 * i:.2f}s"><div class="pesa-nombre">{html.escape(nombre)}</div>'
            f'<div class="pesa-pista"><i class="barra-crece" style="--w:{100 * v / mx:.1f}%;background:{color}"></i>{franja}</div>'
            f'<div class="pesa-valor">{numero(v, 1 if v < 10 else 0, "±")}</div>{rango}</div>'
        )
    nota_html = "" if compacto else f'<div class="nota">{html.escape(nota)}</div>'
    suerte_html = f'<div class="pesa-suerte">{html.escape(suerte)}</div>' if suerte else ""
    st.markdown(
        f'<div class="tarjeta pesa{" pesa-chica" if compacto else ""}{" pesa-heroe" if heroe else ""}" title="{html.escape(ayuda, quote=True)}"><div class="c-titulo">{html.escape(titulo)}</div>{"".join(filas)}'
        f'<div class="pesa-frase">{html.escape(frase)}</div>'
        f"{suerte_html}{nota_html}</div>",
        unsafe_allow_html=True,
    )


def calificacion_html(x: float | None, color: str, grande: bool = True) -> str:
    cls = "calif" + (" calif-grande" if grande else "")
    txt = "—" if x is None else f"{x:.1f}"
    return f'<span class="{cls}" style="--c:{color}">{txt}</span>'


def carta_tecnico_html(
    nombre: str,
    calif: float | None,
    color: str,
    atributos: list[tuple[str, float]],
    parece: str,
    etiqueta_calif: str,
    fuera: bool = False,
    texto_fuera: str = "",
    rango: str = "",
    aviso: str = "",
    delta: str = "",
    ayuda_rango: str = "",
    chip: str = "",
    chip_estilo: str = "",
    chip_ayuda: str = "",
) -> str:
    """Carta estilo videojuego: calificación grande a la izquierda, nombre, seis atributos con barra y «Se parece a». `rango`: la seguridad de la calificación (el rango
    probable completo va en `ayuda_rango`, como ayuda); `aviso`: por qué no lleva color; `delta`: lo que suma o resta contra un estilo neutro, en grande."""
    filas = "".join(
        f'<div class="atr"><span class="atr-n">{html.escape(n)}</span><span class="atr-v">{v:.0f}</span>'
        f'<div class="atr-pista"><i class="barra-crece" style="--w:{v:.0f}%;background:{color}"></i></div></div>'
        for n, v in atributos
    )
    ins = f'<div class="carta-fuera">{html.escape(texto_fuera)}</div>' if fuera else ""
    chip_html = (
        (
            f'<div class="chip-cambios" title="{html.escape(chip_ayuda, quote=True)}"><span>{html.escape(chip)}</span>'
            + (f"<em>{html.escape(chip_estilo)}</em>" if chip_estilo else "")
            + "</div>"
        )
        if chip
        else ""
    )
    sub = f'<div class="calif-delta">{html.escape(delta)}</div>' if delta else ""
    sub += (
        f'<div class="calif-rango" title="{html.escape(ayuda_rango, quote=True)}">{html.escape(rango)}</div>'
        if rango
        else ""
    ) + (f'<div class="calif-aviso">{html.escape(aviso)}</div>' if aviso else "")
    return (
        f'<div class="carta-fifa" style="--c:{color}"><div class="carta-top"><div>{calificacion_html(calif, color)}'
        f'<div class="calif-et">{html.escape(etiqueta_calif)}</div></div>'
        f'<div class="carta-nombre">{html.escape(nombre)}</div></div>{sub}{ins}<div class="carta-parece">{html.escape(parece)}</div>{chip_html}{filas}</div>'
    )


def escudo(iniciales: str, foco: bool = False) -> str:
    """Escudo genérico: círculo con las iniciales (no usamos escudos reales)."""
    return f'<span class="escudo{" escudo-foco" if foco else ""}">{html.escape(iniciales)}</span>'


def tabla_final_html(filas: list[dict], n_liguilla: int, cols: tuple, linea: str) -> str:
    out = [
        f'<table class="tabla-final"><thead><tr><th></th><th>{html.escape(cols[0])}</th><th class="der">{html.escape(cols[1])}</th><th>{html.escape(cols[2])}</th></tr></thead><tbody>'
    ]
    for f in filas:
        pl = 100 * f["p_liguilla"]
        out.append(
            f'<tr class="{"foco" if f["foco"] else ""}" style="--d:{0.035 * f["lugar"]:.2f}s"><td class="lugar">{f["lugar"]}</td>'
            f'<td class="eq"><div class="eqw">{escudo(f["iniciales"], f["foco"])}<span>{html.escape(f["equipo"])}</span></div></td>'
            f'<td class="der pts">{f["puntos"]:.1f}</td><td class="liga"><div class="ligaw">{barra_prob(pl)}<span class="pl">{pl:.0f} %</span></div></td></tr>'
        )
        if f["lugar"] == n_liguilla:
            out.append(
                f'<tr class="linea-liguilla"><td colspan="4"><span>{html.escape(linea)}</span></td></tr>'
            )
    out.append("</tbody></table>")
    return "".join(out)


def ficha_html(grupos: list[tuple[str, list[dict]]], cols: tuple, titulo: str = "") -> str:
    """grupos: [(título, [fila])]; fila = {nombre, tu, actual, cambio, estado, ancho}: los valores ya como texto; estado = sube | baja | igual | distinto; ancho = % que llena la mini-barra.
    «sube» va en amarillo con ▲, «baja» en rojo con ▼ y la mini-barra; lo demás, en gris sin flecha ni color (el estado sale de `analisis.cambio`, nunca del redondeo)."""
    cab = f'<div class="ficha-titulo">{html.escape(titulo)}</div>' if titulo else ""
    out = [
        f'{cab}<table class="ficha"><thead><tr><th>{html.escape(cols[0])}</th><th class="der">{html.escape(cols[1])}</th><th class="der">{html.escape(cols[2])}</th>'
        f'<th class="der">{html.escape(cols[3])}</th></tr></thead><tbody>'
    ]
    for nombre_grupo, filas in grupos:
        out.append(f'<tr class="grupo-ficha"><td colspan="4">{html.escape(nombre_grupo)}</td></tr>')
        for f in filas:
            e = f["estado"]
            flecha = {"sube": "▲ ", "baja": "▼ "}.get(e, "")
            barra = (
                f'<span class="cb-barra"><i style="width:{f["ancho"]:.0f}%"></i></span>'
                if e in ("sube", "baja")
                else ""
            )
            out.append(
                f'<tr><td>{html.escape(f["nombre"])}</td><td class="der">{html.escape(f["tu"])}</td><td class="der">{html.escape(f["actual"])}</td>'
                f'<td class="der cambio {e}">{flecha}{html.escape(f["cambio"])}{barra}</td></tr>'
            )
    out.append("</tbody></table>")
    return "".join(out)


def bloque_torneo(titulo: str, lineas: list[str]) -> str:
    """El bloque fijo «qué torneo simulamos»: título y una línea por idea (sin números escritos a mano: todo viene de meta.json)."""
    return (
        f'<div class="bloque-torneo"><div class="c-titulo">{html.escape(titulo)}</div>'
        + "".join(f'<div class="reel-linea">{html.escape(l)}</div>' for l in lineas)
        + "</div>"
    )


def aviso_limites(titulo: str, detalle: str) -> None:
    st.markdown(
        f'<div class="aviso-limites"><div class="al-titulo">{html.escape(titulo)}</div><div class="al-detalle">{html.escape(detalle)}</div></div>',
        unsafe_allow_html=True,
    )


def estadisticas_partido_html(
    grupos: list[tuple[str, list[tuple[str, int, int]]]],
    titulo: str,
    nombre_a: str,
    nombre_b: str,
    local: bool,
    honesto: str,
    nota: str,
) -> str:
    """«Estadísticas del partido» al estilo Sofascore: por cada dato, el número del América, su nombre, el número del rival y dos barras enfrentadas (cada una del tamaño de su valor
    contra el mayor de los dos). Aparece con un fundido cuando termina la animación del partido (sin movimiento si el usuario pide menos)."""
    izq, der = (nombre_a, nombre_b) if local else (nombre_b, nombre_a)
    cuerpo = []
    for nombre, filas in grupos:
        rows = []
        for etiqueta, a, b in filas:
            mx = max(a, b, 1)
            va, vb = (a, b) if local else (b, a)
            ca, cb = ("est-a", "est-b") if local else ("est-b", "est-a")
            rows.append(
                f'<div class="est-fila"><span class="est-v">{va}</span><span class="est-et">{html.escape(etiqueta)}</span><span class="est-v">{vb}</span>'
                f'<div class="est-barras"><div class="est-barra"><i class="{ca}" style="width:{100 * va / mx:.0f}%"></i></div>'
                f'<div class="est-barra der"><i class="{cb}" style="width:{100 * vb / mx:.0f}%"></i></div></div></div>'
            )
        cuerpo.append(
            f'<div class="est-grupo"><div class="est-gt">{html.escape(nombre)}</div>{"".join(rows)}</div>'
        )
    return (
        f'<div class="est-panel"><div class="c-titulo">{html.escape(titulo)}</div><div class="est-cab"><b>{html.escape(izq)}</b><b>{html.escape(der)}</b></div>'
        f'<div class="est-grupos">{"".join(cuerpo)}</div><div class="nota">{html.escape(honesto)}</div><div class="nota">{html.escape(nota)}</div></div>'
    )
