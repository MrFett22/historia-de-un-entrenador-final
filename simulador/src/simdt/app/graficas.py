"""Gráficas Plotly de la app: UNA plantilla (`paleta.plantilla()`, aplicada por `_base`) con fondo transparente (viven dentro de una tarjeta), solo líneas horizontales tenues, la tipografía de
la app, números con 0–1 decimales, leyenda arriba y sin barra de herramientas. NINGÚN color se escribe aquí: todo sale de `paleta` (D-097): América = amarillo, rival = azul; tipos de jugada:
directo = rojo, toque sin profundidad = gris, elaborado = azul; lo del rival, en el mismo color al 55 %, sólido y sin rayas; neutro = gris. Sin degradados.
"""

from __future__ import annotations

import textwrap

import numpy as np
import plotly.graph_objects as go

from . import paleta as PA
from . import textos as T

FUENTE = "Inter, -apple-system, system-ui, sans-serif"
TINTA = PA.color("texto")  # texto primario
GRIS = PA.color("texto2")  # texto secundario (ejes, leyendas)
REJILLA = PA.rgba("texto", 0.08)
LINEA = PA.rgba("texto", 0.25)
AMERICA = PA.color("america")  # amarillo: el América, lo bueno, lo que pasa
RIVAL = PA.color("rival")  # azul: el rival, la información
ACENTO = AMERICA
NEUTRO = PA.color("neutro")  # gris: lo que no clasifica, la referencia
FONDO = PA.color("fondo")
TIPOS = PA.tipos()  # directo (rojo), toque sin profundidad (gris), elaborado (azul)
TIPOS_RIVAL = PA.tipos_rival()  # los mismos al 55 %
CONFIG = {"displayModeBar": False}
PLANTILLA = PA.plantilla()


def _base(fig: go.Figure, alto: int = 300, leyenda: bool = False) -> go.Figure:
    fig.update_layout(
        template=PLANTILLA,
        height=alto,
        margin=dict(l=8, r=8, t=34 if leyenda else 8, b=8),
        font=dict(family=FUENTE, size=15),
        bargap=0.2,
        showlegend=leyenda,
        legend=dict(
            orientation="h", y=1.16, x=0, yanchor="bottom", font=dict(size=16), traceorder="normal"
        ),
        hoverlabel=dict(font=dict(family=FUENTE)),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=15), zeroline=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, tickfont=dict(size=15), zeroline=False)
    return fig


def _eje(titulo: str) -> dict:
    return dict(text=titulo, font=dict(color=GRIS, size=16))


# ---------------------------------------------------------------- pestaña «Simulador»
def histograma_puntos(hist: list, rango: tuple) -> go.Figure:
    """Amarillo dentro del rango probable (el 80 % central), gris fuera."""
    h = np.asarray(hist, dtype=float)
    p = h / h.sum()
    x = np.arange(len(p))
    sel = np.flatnonzero(p > 0.0005)
    a, b = (sel.min(), sel.max()) if len(sel) else (0, 51)
    xs = x[a : b + 1]
    colores = [ACENTO if rango[0] <= v <= rango[1] else NEUTRO for v in xs]
    fig = go.Figure(
        go.Bar(
            x=xs,
            y=100 * p[a : b + 1],
            marker=dict(color=colores, cornerradius=4),
            hovertemplate="%{x} puntos: %{y:.1f} %<extra></extra>",
        )
    )
    fig.update_xaxes(title=_eje(T.EJE_PUNTOS))
    fig.update_yaxes(title=_eje(T.EJE_VECES), ticksuffix=" %")
    return _base(fig)


def barras_lugar(p_lugar: list, n_liguilla: int) -> go.Figure:
    p = 100 * np.asarray(p_lugar)
    x = np.arange(1, len(p) + 1)
    colores = [ACENTO if i <= n_liguilla else NEUTRO for i in x]
    fig = go.Figure(
        go.Bar(
            x=x,
            y=p,
            marker=dict(color=colores, cornerradius=4),
            hovertemplate="Lugar %{x}: %{y:.1f} %<extra></extra>",
        )
    )
    fig.update_xaxes(title=_eje(T.EJE_LUGAR), dtick=1)
    fig.update_yaxes(title=_eje(T.EJE_PROB), ticksuffix=" %")
    return _base(fig)


def barras_tipos(filas: list[tuple[str, list]], rival: bool = False) -> go.Figure:
    """filas: [(nombre de la serie, [p_directo, p_toque, p_elaborado]), ...] — barras apiladas con 1 decimal. `rival`: el mismo color del tipo al 55 %, sólido y sin rayas."""
    nombres = [f[0] for f in filas][::-1]
    fig = go.Figure()
    for k in range(3):
        v = [100 * f[1][k] for f in filas][::-1]
        uso = ("directo", "toque", "elaborado")[k]
        color = TIPOS_RIVAL[k] if rival else TIPOS[k]
        base = PA.mezcla(uso, alfa=PA.opacidad_rival()) if rival else TIPOS[k]
        marca = dict(color=color, line=dict(color=FONDO, width=2))
        fig.add_trace(
            go.Bar(
                y=nombres,
                x=v,
                orientation="h",
                name=T.TIPOS_JUGADA[k],
                marker=marca,
                text=[f"{x:.1f} %" for x in v],
                textposition="inside",
                insidetextfont=dict(color=PA.texto_sobre(base), size=16),
                hovertemplate=T.TIPOS_JUGADA[k] + ": %{x:.1f} %<extra>%{y}</extra>",
            )
        )
    fig.update_layout(barmode="stack")
    _base(
        fig, 36 + 64 * len(filas)
    )  # la leyenda va en HTML, una sola para las dos gráficas (componentes.leyenda_tipos)
    fig.update_layout(margin=dict(l=8, r=18, t=8, b=8))
    fig.update_xaxes(range=[0, 100], ticksuffix=" %", showgrid=False, visible=False)
    fig.update_yaxes(showgrid=False)
    return fig


def barras_goles(etiquetas: list, favor: list, contra: list) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=etiquetas[::-1],
            x=list(favor)[::-1],
            orientation="h",
            name=T.SERIE_FAVOR,
            marker=dict(color=AMERICA, cornerradius=4),
            hovertemplate=T.SERIE_FAVOR + ": %{x:.2f}<extra>%{y}</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=etiquetas[::-1],
            x=list(contra)[::-1],
            orientation="h",
            name=T.SERIE_CONTRA,
            marker=dict(color=RIVAL, cornerradius=4),
            hovertemplate=T.SERIE_CONTRA + ": %{x:.2f}<extra>%{y}</extra>",
        )
    )
    fig.update_layout(barmode="group")
    _base(fig, 380, leyenda=True)
    fig.update_xaxes(showgrid=True, gridcolor=REJILLA)
    fig.update_yaxes(showgrid=False)
    return fig


def mapa_tecnicos(
    nombres: list,
    puntos: np.ndarray,
    casco: np.ndarray | None,
    actual: tuple | None = None,
    nombre_y: str = "",
    califs: dict | None = None,
    limite: int = 112,
    fuera: bool = False,
    densidad: tuple | None = None,
) -> go.Figure:
    """Dispersión de los técnicos reales (x = ¿cómo ataca?, y = defensa/presión), con la zona observada sombreada y, EN VIVO, el técnico de las perillas.
    Al pasar el cursor por un técnico real sale su nombre y su calificación. `fuera`: el punto amarillo se sale de la zona."""
    fig = go.Figure()
    if (
        densidad is not None
    ):  # sombreado suave de dónde se juntan más técnicos; sin fronteras ni grupos (D-068)
        xs, ys, Z = densidad
        fig.add_trace(
            go.Heatmap(
                x=xs,
                y=ys,
                z=Z,
                zsmooth="best",
                showscale=False,
                hoverinfo="skip",
                name=T.MAPA_DENSIDAD,
                colorscale=[[0.0, PA.rgba("azul", 0)], [1.0, PA.rgba("azul", 0.30)]],
            )
        )
    if casco is not None:
        c = np.vstack([casco, casco[:1]])
        fig.add_trace(
            go.Scatter(
                x=c[:, 0],
                y=c[:, 1],
                mode="lines",
                fill="toself",
                fillcolor=PA.rgba("azul", 0.15),
                line=dict(color=LINEA, width=1.2, dash="dot"),
                hoverinfo="skip",
                name=T.MAPA_ZONA,
            )
        )
    p = np.asarray(puntos)
    califs = califs or {}
    texto = [
        T.MAPA_PUNTO_CALIF.replace("{nombre}", n).replace("{c}", f"{califs[n]:.1f}")
        if n in califs
        else n
        for n in nombres
    ]
    fig.add_trace(
        go.Scatter(
            x=p[:, 0],
            y=p[:, 1],
            mode="markers",
            name="",
            customdata=np.array(texto, dtype=object),
            marker=dict(size=12, color=NEUTRO, opacity=0.95, line=dict(color=FONDO, width=1.5)),
            hovertemplate="%{customdata}<extra></extra>",
        )
    )
    if actual is not None:
        fig.add_trace(
            go.Scatter(
                x=[actual[0]],
                y=[actual[1]],
                mode="markers",
                name=T.MAPA_TECNICO,
                marker=dict(size=28, color=ACENTO, line=dict(color=FONDO, width=2.5)),
                hovertemplate=T.MAPA_TECNICO + "<extra></extra>",
            )
        )
        if fuera:
            fig.add_annotation(
                x=actual[0],
                y=actual[1],
                text=T.MAPA_FUERA,
                showarrow=True,
                arrowcolor=ACENTO,
                arrowwidth=1.5,
                ax=0,
                ay=-44,
                font=dict(color=ACENTO, size=16),
                bgcolor=PA.rgba("fondo", 0.85),
                bordercolor=ACENTO,
                borderwidth=1,
                borderpad=4,
            )
    _base(fig, 430)
    paso = 50 if limite <= 120 else 100
    fig.update_xaxes(
        range=[-limite, limite],
        title=_eje(T.MAPA_EJE_X),
        showgrid=True,
        gridcolor=REJILLA,
        zeroline=True,
        zerolinecolor=LINEA,
        dtick=paso,
    )
    fig.update_yaxes(
        range=[-limite, limite],
        title=_eje(T.MAPA_EJE_Y.format(nombre=nombre_y or T.DEFIENDE)),
        zeroline=True,
        zerolinecolor=LINEA,
        dtick=paso,
    )
    return fig


# ---------------------------------------------------------------- minigráficas de las tarjetas de «¿Le podemos creer?»
ALTO_MINI = 260  # todas las minigráficas de «¿Le podemos creer?» miden lo mismo: las tarjetas quedan parejas (D-087)


def mini_goles(c: dict) -> go.Figure:
    """Barras de la distribución de goles: simulado contra real (c viene de `validacion.tarjetas.goles`)."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=c["bins"],
            y=[100 * a for a in c["real"]],
            name=T.SERIE_REAL,
            marker=dict(color=NEUTRO, cornerradius=4),
            hovertemplate=T.SERIE_REAL + ": %{y:.1f} %<extra>%{x}</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=c["bins"],
            y=[100 * a for a in c["simulado"]],
            name=T.SERIE_SIMULADO,
            marker=dict(color=AMERICA, cornerradius=4),
            hovertemplate=T.SERIE_SIMULADO + ": %{y:.1f} %<extra>%{x}</extra>",
        )
    )
    fig.update_layout(barmode="group")
    _base(fig, ALTO_MINI, leyenda=True)
    fig.update_xaxes(title=_eje(T.EJE_GOLES), type="category")
    fig.update_yaxes(ticksuffix=" %", rangemode="tozero")
    return fig


def mini_puntos(pts: list, c: dict) -> go.Figure:
    x = np.array([p["predichos"] for p in pts])
    y = np.array([p["reales"] for p in pts])
    lo, hi = float(min(x.min(), y.min())), float(max(x.max(), y.max()))
    pad = 0.04 * (hi - lo)
    xs = np.array([lo - pad, hi + pad])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=xs,
            mode="lines",
            line=dict(color=GRIS, width=1, dash="dot"),
            hoverinfo="skip",
            name=T.LINEA_PERFECTA,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(color=NEUTRO, size=9, opacity=0.9),
            name="",
            text=[f"{p['equipo']} · {p['torneo']}" for p in pts],
            hovertemplate="%{text}<br>"
            + T.EJE_PREDICHOS
            + ": %{x:.1f}<br>"
            + T.EJE_REALES
            + ": %{y:.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=c["intercepto"] + c["pendiente"] * xs,
            mode="lines",
            line=dict(color=AMERICA, width=2),
            hoverinfo="skip",
            name="",
        )
    )
    _base(fig, ALTO_MINI)
    fig.update_xaxes(
        title=_eje(T.EJE_PREDICHOS), range=[lo - pad, hi + pad], showgrid=True, gridcolor=REJILLA
    )
    fig.update_yaxes(title=_eje(T.EJE_REALES), range=[lo - pad, hi + pad])
    return fig


def mini_calibracion(calib: dict) -> go.Figure:
    from plotly.subplots import make_subplots

    claves = ("ganar", "empatar", "perder")
    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=T.NOMBRES_RESULTADO,
        shared_yaxes=True,
        horizontal_spacing=0.05,
    )
    for j, k in enumerate(claves, 1):
        b = calib[k]
        px, py = [100 * x["predicha"] for x in b], [100 * x["observada"] for x in b]
        fig.add_trace(
            go.Scatter(
                x=[0, 100],
                y=[0, 100],
                mode="lines",
                line=dict(color=GRIS, width=1, dash="dot"),
                hoverinfo="skip",
                showlegend=False,
            ),
            row=1,
            col=j,
        )
        fig.add_trace(
            go.Scatter(
                x=px,
                y=py,
                mode="markers",
                marker=dict(color=AMERICA, size=11, line=dict(color=FONDO, width=1)),
                showlegend=False,
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=[100 * (x["ic95"][1] - x["observada"]) for x in b],
                    arrayminus=[100 * (x["observada"] - x["ic95"][0]) for x in b],
                    color=GRIS,
                    thickness=1.2,
                    width=3,
                ),
                customdata=[x["n"] for x in b],
                hovertemplate="%{x:.0f} % → %{y:.0f} %<br>%{customdata} partidos<extra></extra>",
            ),
            row=1,
            col=j,
        )
        fig.update_xaxes(
            range=[0, 100], tickvals=[0, 50, 100], ticksuffix=" %", showgrid=False, row=1, col=j
        )
    fig.update_yaxes(
        range=[0, 100], ticksuffix=" %", showgrid=True, gridcolor=REJILLA, row=1, col=1
    )
    _base(fig, ALTO_MINI)
    fig.update_layout(margin=dict(l=8, r=8, t=30, b=8))
    fig.update_annotations(font=dict(color=TINTA, size=16))
    return fig


def mini_rango(
    titulo_cero: str, centro: float, ic: list, extra_pt: tuple | None = None
) -> go.Figure:
    """Un valor con su rango probable alrededor del cero (autocorrelación)."""
    lim = max(abs(ic[0]), abs(ic[1]), abs(centro)) * 1.6 + 1e-9
    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color=LINEA, width=1.5))
    fig.add_trace(
        go.Scatter(
            x=ic,
            y=[0, 0],
            mode="lines",
            line=dict(color=NEUTRO, width=12),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[centro],
            y=[0],
            mode="markers",
            marker=dict(size=18, color=AMERICA, line=dict(color=FONDO, width=2)),
            showlegend=False,
            hovertemplate="%{x:.3f}<extra></extra>",
        )
    )
    fig.add_annotation(
        x=0, y=0.6, text=titulo_cero, showarrow=False, font=dict(color=GRIS, size=15)
    )
    _base(fig, ALTO_MINI)
    fig.update_xaxes(range=[-lim, lim], showgrid=False, zeroline=False)
    fig.update_yaxes(visible=False, range=[-1, 1], showgrid=False)
    return fig


def mini_placebo(placebos: list) -> go.Figure:
    nombres = [p["placebo"] for p in placebos][::-1]
    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color=LINEA, width=1.5))
    for p in placebos[::-1]:
        fig.add_trace(
            go.Scatter(
                x=p["int95"],
                y=[p["placebo"]] * 2,
                mode="lines",
                line=dict(color=NEUTRO, width=10),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[p["media"]],
                y=[p["placebo"]],
                mode="markers",
                marker=dict(size=13, color=AMERICA, line=dict(color=FONDO, width=1.5)),
                showlegend=False,
                hovertemplate=p["placebo"] + ": %{x:+.2f}<extra></extra>",
            )
        )
    _base(fig, ALTO_MINI)
    fig.update_xaxes(showgrid=False, zeroline=False, title=_eje(T.CERO))
    fig.update_yaxes(showgrid=False, categoryorder="array", categoryarray=nombres)
    return fig


def mini_recuperacion(c: dict) -> go.Figure:
    v = 100 * c["fraccion"]
    fig = go.Figure(
        go.Bar(
            x=[v],
            y=[T.EJE_DENTRO],
            orientation="h",
            marker=dict(color=AMERICA, cornerradius=4),
            text=[f"{v:.0f} %"],
            textposition="inside",
            insidetextfont=dict(color=PA.texto_sobre(AMERICA), size=16),
            hovertemplate="%{x:.0f} %<extra></extra>",
        )
    )
    fig.add_vline(x=100 * c["umbral"], line=dict(color=TINTA, width=2, dash="dot"))
    fig.add_annotation(
        x=100 * c["umbral"],
        y=1.0,
        yref="paper",
        text=T.UMBRAL,
        showarrow=False,
        yanchor="bottom",
        font=dict(color=GRIS, size=15),
    )
    _base(fig, ALTO_MINI)
    fig.update_layout(margin=dict(l=8, r=8, t=30, b=28))
    fig.update_xaxes(range=[0, 100], tickvals=[0, 50, 85, 100], ticksuffix=" %", showgrid=False)
    fig.update_yaxes(showgrid=False, visible=False)
    return fig


def mini_retro(c: dict) -> go.Figure:
    medidas = (
        (T.EJE_ERROR_MEDIO, "mae", "mae_inercia"),
        (T.EJE_ERROR_CUADRATICO, "rmse", "rmse_inercia"),
    )
    medidas = [m for m in medidas if c.get(m[1]) is not None and c.get(m[2]) is not None]
    fig = go.Figure()
    for nombre, idx, marca in (
        (T.SERIE_SIMULADOR, 1, dict(color=AMERICA, cornerradius=4)),
        (T.SERIE_INERCIA, 2, dict(color=NEUTRO, cornerradius=4)),
    ):
        v = [c[m[idx]] for m in medidas]
        fig.add_trace(
            go.Bar(
                x=[m[0] for m in medidas],
                y=v,
                name=nombre,
                marker=marca,
                text=[f"{x:.2f}" for x in v],
                textposition="outside",
                cliponaxis=False,
                hovertemplate=nombre + ": %{y:.3f}<extra>%{x}</extra>",
            )
        )
    fig.update_layout(barmode="group")
    _base(fig, ALTO_MINI, leyenda=True)
    fig.update_yaxes(rangemode="tozero")
    return fig


# ================================================================
def radar(atributos: list[float], nombres: tuple, color: str) -> go.Figure:
    """Radar de los seis atributos (0 a 100): UN solo polígono, el del técnico que se está viendo. El fondo es un hexágono neutro con anillos en 25, 50 y 75; no hay
    ningún otro técnico de referencia (D-076)."""
    th = list(nombres) + [nombres[0]]
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=list(atributos) + [atributos[0]],
            theta=th,
            mode="lines+markers",
            name="",
            fill="toself",
            fillcolor=PA.rgba("amarillo", 0.22),
            line=dict(color=AMERICA, width=2.6),
            marker=dict(size=9, color=AMERICA),
            hovertemplate="%{theta}: %{r:.0f}<extra></extra>",
        )
    )
    _base(fig, 360)
    fig.update_layout(
        margin=dict(l=70, r=70, t=26, b=40),
        showlegend=False,
        polar=dict(
            bgcolor=PA.rgba("fondo", 0),
            radialaxis=dict(
                range=[0, 100],
                showticklabels=False,
                gridcolor=REJILLA,
                linecolor=REJILLA,
                tickvals=[25, 50, 75],
            ),
            angularaxis=dict(
                gridcolor=REJILLA, linecolor=LINEA, tickfont=dict(color=TINTA, size=15)
            ),
            gridshape="linear",
        ),
    )
    return fig


def barras_pelota_parada(etiquetas: list, favor: list, contra: list) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=etiquetas[::-1],
            x=list(favor)[::-1],
            orientation="h",
            name=T.SERIE_FAVOR,
            marker=dict(color=AMERICA, cornerradius=4),
            hovertemplate=T.SERIE_FAVOR + ": %{x:.2f}<extra>%{y}</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=etiquetas[::-1],
            x=list(contra)[::-1],
            orientation="h",
            name=T.SERIE_CONTRA,
            marker=dict(color=RIVAL, cornerradius=4),
            hovertemplate=T.SERIE_CONTRA + ": %{x:.2f}<extra>%{y}</extra>",
        )
    )
    fig.update_layout(barmode="group")
    _base(fig, 340, leyenda=True)
    fig.update_xaxes(showgrid=True, gridcolor=REJILLA)
    fig.update_yaxes(showgrid=False)
    return fig


def mini_partido(c: dict) -> go.Figure:
    """Tarjeta «¿El partido simulado se parece al cálculo exacto?»: ganar / empatar / perder, cálculo exacto contra partidos sorteados."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=list(T.NOMBRES_RESULTADO),
            y=[100 * v for v in c["exactas"]],
            name=T.SERIE_EXACTO,
            marker=dict(color=NEUTRO, cornerradius=4),
            hovertemplate=T.SERIE_EXACTO + ": %{y:.1f} %<extra>%{x}</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=list(T.NOMBRES_RESULTADO),
            y=[100 * v for v in c["frecuencias"]],
            name=T.SERIE_SORTEADO,
            marker=dict(color=AMERICA, cornerradius=4),
            hovertemplate=T.SERIE_SORTEADO + ": %{y:.1f} %<extra>%{x}</extra>",
        )
    )
    fig.update_layout(barmode="group")
    _base(fig, ALTO_MINI, leyenda=True)
    fig.update_yaxes(ticksuffix=" %", rangemode="tozero")
    return fig
