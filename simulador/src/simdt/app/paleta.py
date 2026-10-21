"""La ÚNICA fuente de color de la app (D-097): los tokens están en `config/simulador.yaml` (`paleta`) y de aquí salen las variables CSS (`estilos.css` y las animaciones), la plantilla de
Plotly y el resto de los módulos. Solo del América se toman sus colores: amarillo, azul marino, rojo y blanco sobre oscuro. Sin degradados.

También trae las cuentas de accesibilidad que usan las pruebas y la lámina de la paleta: contraste WCAG, ΔE2000 y simulación de daltonismo (Machado et al. 2009)."""

from __future__ import annotations

import numpy as np

from .. import config
from . import textos as T

NOMBRES = (
    "fondo",
    "superficie",
    "borde",
    "elevada",
    "texto",
    "texto2",
    "texto3",
    "amarillo",
    "azul",
    "azul_club",
    "rojo",
    "rojo_texto",
    "gris",
    "gris_tipo",
    "sombra",
)
# lo que significa cada color en TODA la app (D-097): América = amarillo, rival = azul; tipos de jugada: directo = rojo, toque = gris, elaborado = azul
USO = {
    "america": "amarillo",
    "rival": "azul",
    "bueno": "amarillo",
    "malo": "rojo",
    "neutro": "gris",
    "directo": "rojo",
    "toque": "gris_tipo",
    "elaborado": "azul",
}


def tokens() -> dict:
    t = config.cargar()["paleta"]
    return {k: t[k] for k in NOMBRES}


def opacidad_rival() -> float:
    return float(config.cargar()["paleta"]["rival_opacidad"])


def hex_a_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_a_hex(rgb) -> str:
    return "#" + "".join(f"{int(round(max(0, min(255, c)))):02X}" for c in rgb)


def color(nombre: str) -> str:
    """El color (hex) de un token o de un uso («america», «rival», «bueno», «malo», «neutro», «directo», «toque», «elaborado»)."""
    return tokens()[USO.get(nombre, nombre)]


def rgba(nombre: str, alfa: float) -> str:
    """Un token con opacidad (la única forma de escribir rgba() en la app)."""
    r, g, b = hex_a_rgb(color(nombre))
    return f"rgba({r},{g},{b},{alfa:g})"


def mezcla(nombre: str, sobre: str = "superficie", alfa: float = 0.55) -> str:
    """El color opaco que da `nombre` al `alfa` sobre `sobre` (lo del rival: el mismo color al 55 %, sólido)."""
    a, b = np.array(hex_a_rgb(color(nombre)), float), np.array(hex_a_rgb(color(sobre)), float)
    return rgb_a_hex(alfa * a + (1 - alfa) * b)


def tipos() -> tuple[str, str, str]:
    """Directo, toque sin profundidad y elaborado."""
    return color("directo"), color("toque"), color("elaborado")


def tipos_rival() -> tuple[str, str, str]:
    return tuple(rgba(n, opacidad_rival()) for n in ("directo", "toque", "elaborado"))  # type: ignore[return-value]


def css_variables(esquema: bool = True) -> str:
    """El bloque `:root` con todos los tokens y sus usos; `estilos.css` solo usa estas variables (y mezclas de ellas con `color-mix`). `esquema=False` (los iframes de las animaciones): sin
    `color-scheme`, porque si el iframe declara uno distinto al de la página el navegador le pinta un fondo opaco y queda un rectángulo negro (D-094)."""
    t = tokens()
    v = {f"--{k.replace('_', '-')}": val for k, val in t.items() if k != "sombra"}
    v["--sombra-color"] = t["sombra"]
    v.update(
        {
            "--america": "var(--amarillo)",
            "--rival": "var(--azul)",
            "--bueno": "var(--amarillo)",
            "--malo": "var(--rojo)",
            "--neutro": "var(--gris)",
            "--directo": "var(--rojo)",
            "--toque": "var(--gris-tipo)",
            "--elaborado": "var(--azul)",
            "--rival-opacidad": f"{100 * opacidad_rival():g}%",
            "--acento": "var(--amarillo)",
            "--acento-texto": "var(--fondo)",
            "--vidrio": "var(--superficie)",
            "--vidrio-fuerte": "var(--elevada)",
            "--verde": "var(--amarillo)",
            "--borde-fuerte": "color-mix(in srgb, var(--texto) 18%, var(--borde))",
            "--linea-tenue": "color-mix(in srgb, var(--texto) 16%, transparent)",
            "--sombra": "0 1px 1px color-mix(in srgb, var(--sombra-color) 40%, transparent), 0 8px 18px color-mix(in srgb, var(--sombra-color) 45%, transparent)",
            "--brillo": "inset 0 1px 0 color-mix(in srgb, var(--texto) 8%, transparent)",
        }
    )
    return (
        ":root {"
        + " ".join(f"{k}: {x};" for k, x in v.items())
        + (" color-scheme: dark;" if esquema else "")
        + " }"
    )


# ---------------------------------------------------------------- plantilla de Plotly: la única fuente de color de las figuras
def plantilla():
    """`go.layout.Template` con la tipografía y los colores de la app. Cada figura la usa (`graficas._base`); los colores de los datos salen de `color()`/`tipos()`."""
    import plotly.graph_objects as go

    t = tokens()
    eje = dict(
        linecolor=t["borde"],
        tickfont=dict(color=t["texto2"]),
        gridcolor=rgba("texto", 0.08),
        zerolinecolor=t["borde"],
    )
    return go.layout.Template(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=t["texto"]),
            colorway=[t["amarillo"], t["azul"], t["gris"], t["rojo"]],
            xaxis=eje,
            yaxis=eje,
            legend=dict(font=dict(color=t["texto"]), bgcolor="rgba(0,0,0,0)"),
            hoverlabel=dict(
                font=dict(color=t["texto"]), bgcolor=t["elevada"], bordercolor=t["borde"]
            ),
        )
    )


# ---------------------------------------------------------------- accesibilidad
def _lin(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luminancia(h: str) -> float:
    r, g, b = _lin(np.array(hex_a_rgb(h), float) / 255.0)
    return float(0.2126 * r + 0.7152 * g + 0.0722 * b)


def contraste(a: str, b: str) -> float:
    """Razón de contraste WCAG entre dos colores hex (1 a 21)."""
    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _lab(rgb01: np.ndarray) -> np.ndarray:
    M = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    X, Y, Z = (M @ _lin(rgb01)) / np.array([0.95047, 1.0, 1.08883])
    f = lambda t: np.where(t > 216 / 24389, np.cbrt(t), (24389 / 27 * t + 16) / 116)  # noqa: E731
    fx, fy, fz = f(X), f(Y), f(Z)
    return np.array([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)])


def delta_e2000(l1, l2) -> float:
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb**7 / (Cb**7 + 25**7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h = lambda b, a: (np.degrees(np.arctan2(b, a)) % 360) if (a != 0 or b != 0) else 0.0  # noqa: E731
    h1p, h2p = h(b1, a1p), h(b2, a2p)
    dL, dC = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dh = 0.0
    else:
        dh = h2p - h1p
        dh = dh - 360 if dh > 180 else (dh + 360 if dh < -180 else dh)
    dH = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hb = h1p + h2p
    else:
        hb = (h1p + h2p) / 2
        if abs(h1p - h2p) > 180:
            hb += 180 if h1p + h2p < 360 else -180
    T = (
        1
        - 0.17 * np.cos(np.radians(hb - 30))
        + 0.24 * np.cos(np.radians(2 * hb))
        + 0.32 * np.cos(np.radians(3 * hb + 6))
        - 0.20 * np.cos(np.radians(4 * hb - 63))
    )
    dth = 30 * np.exp(-(((hb - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp**7 / (Cbp**7 + 25**7))
    Sl = 1 + 0.015 * (Lb - 50) ** 2 / np.sqrt(20 + (Lb - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return float(
        np.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh))
    )


# Machado, Oliveira y Fernandes (2009), severidad 1.0, sobre RGB lineal
_CVD = {
    "deuteranopia": np.array(
        [
            [0.367322, 0.860646, -0.227968],
            [0.280085, 0.672501, 0.047413],
            [-0.011820, 0.042940, 0.968881],
        ]
    ),
    "protanopia": np.array(
        [
            [0.152286, 1.052583, -0.204868],
            [0.114503, 0.786281, 0.099216],
            [-0.003882, -0.048116, 1.051998],
        ]
    ),
    "tritanopia": np.array(
        [
            [1.255528, -0.076749, -0.178779],
            [-0.078411, 0.930809, 0.147602],
            [0.004733, 0.691367, 0.303900],
        ]
    ),
}
DALTONISMOS = tuple(_CVD)


def simular_daltonismo(h: str, tipo: str) -> str:
    rgb = np.clip(_CVD[tipo] @ _lin(np.array(hex_a_rgb(h), float) / 255.0), 0, 1)
    srgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)
    return rgb_a_hex(srgb * 255)


def diferencia(h1: str, h2: str, daltonismo: str | None = None) -> float:
    """ΔE2000 entre dos colores hex, tal como los ve una persona normal o con el daltonismo indicado."""
    if daltonismo:
        h1, h2 = simular_daltonismo(h1, daltonismo), simular_daltonismo(h2, daltonismo)
    return delta_e2000(
        _lab(np.array(hex_a_rgb(h1), float) / 255.0), _lab(np.array(hex_a_rgb(h2), float) / 255.0)
    )


def texto_sobre(fondo_hex: str) -> str:
    """El color de texto (blanco o el fondo de la página) con más contraste sobre un relleno: así los números dentro de las barras se leen siempre."""
    return (
        color("texto")
        if contraste(color("texto"), fondo_hex) >= contraste(color("fondo"), fondo_hex)
        else color("fondo")
    )


def texto_sobre(fondo_hex: str) -> str:
    """El color de texto (blanco o el fondo de la página) con más contraste sobre un relleno: así los números dentro de las barras se leen siempre."""
    return (
        color("texto")
        if contraste(color("texto"), fondo_hex) >= contraste(color("fondo"), fondo_hex)
        else color("fondo")
    )


# (token, para qué se usa, color contra el que se mide, mínimo de contraste exigido): lo que dibuja la lámina `capturas/v11/paleta.png` y revisan las pruebas (D-097)
FILAS_USO = (
    ("fondo", T.PALETA_USO["fondo"], "amarillo", 4.5),
    ("superficie", T.PALETA_USO["superficie"], "texto", 4.5),
    ("borde", T.PALETA_USO["borde"], "superficie", 1.0),
    ("elevada", T.PALETA_USO["elevada"], "texto", 4.5),
    ("texto", T.PALETA_USO["texto"], "superficie", 4.5),
    ("texto2", T.PALETA_USO["texto2"], "superficie", 4.5),
    ("texto3", T.PALETA_USO["texto3"], "superficie", 4.5),
    ("amarillo", T.PALETA_USO["amarillo"], "superficie", 3.0),
    ("azul", T.PALETA_USO["azul"], "superficie", 3.0),
    ("azul_club", T.PALETA_USO["azul_club"], "texto", 4.5),
    ("rojo", T.PALETA_USO["rojo"], "superficie", 3.0),
    ("rojo_texto", T.PALETA_USO["rojo_texto"], "superficie", 4.5),
    ("gris", T.PALETA_USO["gris"], "superficie", 3.0),
    ("gris_tipo", T.PALETA_USO["gris_tipo"], "superficie", 3.0),
    ("sombra", T.PALETA_USO["sombra"], "fondo", 1.0),
)


def tabla_uso() -> list[dict]:
    """Una fila por token: hex, uso y el contraste medido contra el color con el que se usa."""
    t = tokens()
    out = []
    for nombre, uso, contra, minimo in FILAS_USO:
        a, b = t[nombre], t[contra]
        if nombre == "fondo":  # el fondo se mide como TEXTO sobre el amarillo del botón
            c = contraste(a, b)
        elif nombre in (
            "superficie",
            "elevada",
        ):  # las superficies se miden con el texto principal encima
            c = contraste(b, a)
        else:
            c = contraste(a, b)
        out.append(
            {
                "token": nombre,
                "hex": a,
                "uso": uso,
                "contra": contra,
                "contraste": round(c, 2),
                "minimo": minimo,
            }
        )
    return out
