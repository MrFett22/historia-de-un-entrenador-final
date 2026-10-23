"""Genera `REPORTE.html`: el reporte de la entrega en un solo archivo, sin conexión a internet.

    python docs/herramientas/generar_reporte.py            # desde la raíz del repositorio

Necesita `latex2mathml` (las fórmulas se escriben en MathML, que el navegador dibuja sin
bibliotecas externas) y `Pillow` (las figuras se incrustan en el HTML). No calcula nada: todas
las cifras están copiadas de `README.md`, `docs/` y `estudio/docs/RESULTADOS_ALMADA.md`.
"""

from __future__ import annotations

import base64
import html
import io
from pathlib import Path

from latex2mathml.converter import convert
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "estudio" / "docs" / "figuras"
APP = "https://historia-de-un-entrenador-final-evvt6gu6etyfa7veza8clq.streamlit.app/"
VIDEO = "https://www.youtube.com/watch?v=xKYpLE7MCm8"
REPO = "https://github.com/MrFett22/historia-de-un-entrenador-final"


def m(tex: str) -> str:
    """Fórmula en línea."""
    return convert(tex)


def M(tex: str) -> str:
    """Fórmula en bloque."""
    tex = tex.replace(r"\sum_", r"\sum\limits_").replace(r"\prod_", r"\prod\limits_")
    return f'<div class="eq">{convert(tex, display="block")}</div>'


def img_b64(ruta: Path, ancho: int | None = None, recorte=None, jpeg: bool = False) -> str:
    im = Image.open(ruta)
    if recorte:
        im = im.crop(recorte)
    if ancho and im.width > ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    if jpeg:
        im.convert("RGB").save(buf, "JPEG", quality=84, optimize=True)
        tipo = "jpeg"
    else:
        im.save(buf, "PNG", optimize=True)
        tipo = "png"
    return f"data:image/{tipo};base64,{base64.b64encode(buf.getvalue()).decode()}"


def fig(ruta: Path, pie: str, alt: str, **kw) -> str:
    return (
        f'<figure><img src="{img_b64(ruta, **kw)}" alt="{html.escape(alt)}" loading="lazy">'
        f"<figcaption>{pie}</figcaption></figure>"
    )


def barras_pesa_mas() -> str:
    """Suerte, jugadores y técnico en la misma escala (docs/VALIDACION_ENTREGA.md)."""
    filas = [
        ("El azar de los partidos", 5.27, 5.26, 5.28, "var(--gris)"),
        ("La fuerza del plantel", 5.75, 4.47, 6.33, "var(--azul)"),
        ("El técnico", 0.64, 0.5, 0.8, "var(--amarillo)"),
    ]
    x0, ancho, escala = 210, 470, 470 / 7.0
    out = [
        (
            '<svg viewBox="0 0 760 190" role="img" aria-label="Variación típica de los puntos de un '
            'equipo en un torneo: azar 5.3, plantel 5.75, técnico 0.6">'
        )
    ]
    for i, (nombre, v, lo, hi, color) in enumerate(filas):
        y = 22 + i * 56
        out.append(f'<text x="0" y="{y + 19}" class="lbl">{nombre}</text>')
        out.append(
            f'<rect x="{x0}" y="{y}" width="{ancho}" height="28" rx="6" class="pista"/>'
            f'<rect x="{x0}" y="{y}" width="{v * escala:.1f}" height="28" rx="6" fill="{color}"/>'
            f'<line x1="{x0 + lo * escala:.1f}" x2="{x0 + hi * escala:.1f}" y1="{y + 14}" '
            f'y2="{y + 14}" class="ic"/>'
            f'<text x="{x0 + ancho + 12}" y="{y + 20}" class="val">±{v:.2f}</text>'
        )
    out.append(
        f'<text x="{x0}" y="186" class="nota">puntos por torneo de 17 jornadas (desviación '
        "estándar); la línea es el intervalo</text></svg>"
    )
    return "".join(out)


VALIDACION = [
    (
        "Goles por partido",
        "χ² de bondad de ajuste, 5 gl, 3,402 equipo-partido",
        "χ² = 1.49, p = 0.91",
        "ok",
        "No se rechaza H0",
    ),
    (
        "Puntos por equipo y torneo",
        "Regresión de puntos reales sobre simulados (180 equipo-torneo); error total de xPts",
        "pendiente 1.50 (R² = 0.53); xPts +0.43 %",
        "ojo",
        "Se rechaza H0: acorta diferencias",
    ),
    (
        "Calibración de probabilidades",
        "Tipo Hosmer-Lemeshow por bandas (gana, empata, pierde)",
        "p mínima 1.9·10⁻¹⁰",
        "ojo",
        "Se rechaza H0 en alguna banda",
    ),
    (
        "Independencia entre partidos",
        "Autocorrelación lag 1 de residuos (3,222 pares) y días de descanso",
        "ρ = −0.009 [−0.05, 0.03]",
        "ok",
        "No se rechaza H0",
    ),
    (
        "Placebo",
        "Técnicos barajados entre celdas; IC 95 % de la diferencia",
        "3 de 3 intervalos contienen el 0",
        "ok",
        "No se rechaza H0",
    ),
    (
        "Recuperación de estilos",
        "Pares técnico-club con ≥ 50 partidos; bootstrap; mínimo 85 %",
        "14 de 15 (93 %)",
        "ok",
        "Se cumple",
    ),
    (
        "Retroprueba con cambios de técnico",
        "Diebold-Mariano (corrección HLN), 35 llegadas, sin información futura",
        "0.371 contra 0.381; p = 0.195",
        "ojo",
        "No le gana a la inercia",
    ),
    (
        "Partidos sorteados jugada por jugada",
        "χ² de marcadores en 5,000 partidos, 24 gl",
        "χ² = 23.2, p = 0.51",
        "ok",
        "No se rechaza H0",
    ),
]

HIPOTESIS = [
    (
        "H1",
        "Los partidos son independientes (sin rachas ni cansancio).",
        "Se sostiene: autocorrelación −0.009 [−0.05, 0.03].",
    ),
    (
        "H2",
        "El ritmo de jugadas a lo largo del partido es el mismo perfil para todos.",
        "No contrastada; los totales se reproducen (xPts +0.43 %).",
    ),
    (
        "H3",
        "El técnico cambia qué jugadas hace, no cómo se mueve el balón dentro de cada tipo.",
        "Razonable en directa y elaborado; no concluyente en toque.",
    ),
    (
        "H4",
        "Técnico y plantel se suman, con interacción aleatoria.",
        "Se sostiene: la interacción entra con su incertidumbre.",
    ),
    (
        "H5",
        "El efecto del técnico es inmediato.",
        "Se sostiene: el estilo cambia de golpe al cambiar de club.",
    ),
    ("H6", "El plantel no cambia durante el torneo.", "Supuesto declarado en la app."),
    ("H7", "La ventaja de local es igual para todos.", "Supuesto: un solo parámetro."),
    (
        "H8",
        "El Elo de los rivales queda fijo al inicio.",
        "Supuesto, coherente con el corte sin fuga.",
    ),
    (
        "H9",
        "En balón parado el técnico solo influye en la prevención.",
        "Se sostiene: prevención τ² = 3·10⁻⁴; remate y portero τ² ≈ 0.",
    ),
    (
        "H10",
        "Expulsiones y eventos raros quedan implícitos en las tasas.",
        "No contrastada; goles simulados ≈ reales (p = 0.91).",
    ),
    (
        "H11",
        "Las sustituciones solo son descriptivas.",
        "Se sostiene: diferencias en diferencias con 360, efecto nulo.",
    ),
]

DECISIONES = [
    (
        "D-048, D-049",
        "Tomamos el vocabulario de jugadas del estudio en lugar de reajustar una mezcla propia: la diferencia venía de un óptimo local del EM causado por la semilla y de la falta del primer paso P⁰.",
        "Los tres tipos vuelven a ser los del estudio, con 100 % de pareo entre secuencias.",
    ),
    (
        "D-050",
        "Cortamos los datos sin fuga: todo se estima con partidos anteriores al Apertura 2026.",
        "Los parámetros anteriores incluían 66 a 88 partidos del torneo objetivo; al quitarlos desapareció la ventaja aparente al predecir cambios de técnico.",
    ),
    (
        "D-051",
        "Atribución continua: el técnico mueve todas las componentes con su posterior encogida.",
        "Con la regla de todo o nada, inalcanzable bajo el prior, el técnico no movía ninguna de las 32 componentes.",
    ),
    (
        "D-054, D-059",
        "Publicamos la calibración E y no la F.",
        "F mejoraba el error de xPts, pero bajaba la recuperación de estilos de 93 % a 40 %.",
    ),
    (
        "D-074",
        "Suerte, jugadores y técnico en la misma escala (desviación estándar de los puntos por torneo).",
        "Suerte ±5.3, jugadores ±5.75 y técnico ±0.6.",
    ),
]

COMO_SE_HIZO = (
    "El diseño del modelo es nuestro: la pregunta, el vocabulario de jugadas, las hipótesis, la "
    "separación entre técnico y plantel, las pruebas estadísticas y los criterios de validación. "
    "También son nuestras la auditoría que encontró y corrigió errores (la fuga de datos del torneo "
    "objetivo, el óptimo local del algoritmo EM causado por la semilla y una regla de atribución "
    "que el prior volvía inalcanzable) y la interpretación de los resultados. Para implementar el "
    "código, la aplicación web y la automatización de pruebas usamos asistentes de inteligencia "
    "artificial (Claude Code y Antigravity), bajo nuestra dirección. Revisamos y validamos cada "
    "resultado matemático."
)

CSS = """
:root{--fondo:#f7f7f4;--papel:#ffffff;--tinta:#16203a;--suave:#56607a;--linea:#dfe2ea;
--azul:#1f4fd1;--marino:#0b1a44;--amarillo:#f2b705;--gris:#8a93a8;--rojo:#c8372d;--verde:#1f8a4c;
--chip-ok:#e3f3ea;--chip-ojo:#fdf0d8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--fondo:#0b1020;--papel:#121a30;
--tinta:#e9ecf5;--suave:#a3acc4;--linea:#26304b;--azul:#6f95ff;--marino:#dfe6ff;--amarillo:#ffd23f;
--gris:#7f89a3;--rojo:#ff7a6e;--verde:#5ccf8e;--chip-ok:#173326;--chip-ojo:#3a2f12}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--fondo);color:var(--tinta);font:17px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
main{max-width:920px;margin:0 auto;padding:0 16px 64px}
header.portada{background:var(--marino);color:#fff;padding:56px 16px 40px;margin-bottom:8px}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) header.portada{background:#18244a}}
header.portada .in{max-width:920px;margin:0 auto}
header.portada h1{font-size:clamp(28px,5vw,44px);line-height:1.15;margin:0 0 12px;letter-spacing:-.01em}
header.portada p{margin:0 0 6px;color:#d6dcf0;max-width:720px}
.chips{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}
.chips a{display:inline-block;padding:8px 14px;border-radius:999px;background:#ffd23f;color:#0b1a44;font-weight:600;text-decoration:none}
.chips a.sec{background:transparent;color:#fff;border:1px solid #5b6a9c}
nav.indice{background:var(--papel);border:1px solid var(--linea);border-radius:12px;padding:14px 18px;margin:24px 0}
nav.indice ol{margin:0;padding-left:20px;columns:2;column-gap:28px}@media (max-width:640px){nav.indice ol{columns:1}}
h2{font-size:28px;line-height:1.2;margin:48px 0 12px;padding-top:8px;border-top:3px solid var(--amarillo)}
h3{font-size:20px;margin:28px 0 8px}
a{color:var(--azul)}
.tarjetas{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0}
.tarjeta{background:var(--papel);border:1px solid var(--linea);border-radius:12px;padding:14px 16px}
.tarjeta b{display:block;font-size:30px;line-height:1.1;color:var(--azul)}
.tarjeta span{color:var(--suave);font-size:15px}
ol.hallazgos li{margin-bottom:10px}
figure{margin:22px 0;background:var(--papel);border:1px solid var(--linea);border-radius:12px;padding:12px}
figure img{display:block;width:100%;height:auto;border-radius:6px;background:#fcfcfa}
figcaption{color:var(--suave);font-size:15px;margin-top:8px}
.eq{overflow-x:auto;padding:6px 0;margin:10px 0}.eq math{math-style:normal}
math{font-size:1.08em}
.tabla{overflow-x:auto;margin:16px 0}
table{border-collapse:collapse;width:100%;font-size:15px;background:var(--papel)}
th,td{border:1px solid var(--linea);padding:8px 10px;text-align:left;vertical-align:top}
th{background:var(--fondo);font-weight:600}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:13px;font-weight:600;white-space:nowrap}
.chip.ok{background:var(--chip-ok);color:var(--verde)}.chip.ojo{background:var(--chip-ojo);color:#9a6400}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .chip.ojo{color:#ffcf6b}}
.nota{background:var(--papel);border-left:4px solid var(--amarillo);padding:10px 14px;border-radius:0 10px 10px 0;margin:16px 0}
svg{width:100%;height:auto}svg .lbl{font-size:15px;fill:var(--tinta)}svg .val{font-size:16px;font-weight:700;fill:var(--tinta)}
svg .nota{font-size:12px;fill:var(--suave)}svg .pista{fill:var(--linea)}svg .ic{stroke:var(--tinta);stroke-width:2.5;opacity:.55}
.grafica{background:var(--papel);border:1px solid var(--linea);border-radius:12px;padding:16px;margin:18px 0}
footer{color:var(--suave);font-size:14px;margin-top:48px;border-top:1px solid var(--linea);padding-top:16px}
"""


def construir() -> str:
    filas_val = "".join(
        f"<tr><td>{i}</td><td>{p}</td><td>{e}</td><td>{r}</td>"
        f'<td><span class="chip {c}">{v}</span></td></tr>'
        for i, (p, e, r, c, v) in enumerate(VALIDACION, 1)
    )
    filas_hip = "".join(f"<tr><td>{h}</td><td>{t}</td><td>{r}</td></tr>" for h, t, r in HIPOTESIS)
    filas_dec = "".join(f"<tr><td>{d}</td><td>{t}</td><td>{e}</td></tr>" for d, t, e in DECISIONES)
    captura = RAIZ / "simulador" / "capturas" / "v11" / "escritorio_1_simulador.png"

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Historia de un entrenador</title>
<meta name="description" content="Reporte de la entrega del Hackathon ISAC 2026: metodología, visualizaciones y resultados del estudio de Guillermo Almada y del simulador de técnico del Club América.">
<style>{CSS}</style>
</head>
<body>
<header class="portada"><div class="in">
<p>Hackathon ISAC 2026 · Reto Club América</p>
<h1>Historia de un entrenador: estudio y simulador</h1>
<p>¿Qué hay de propio en el juego de un técnico de la Liga MX y qué se explica por su plantel?
Lo respondemos para Guillermo Almada con los eventos y el tracking 360 de StatsBomb de toda la
liga, y con ese modelo construimos un simulador para el América.</p>
<p>Diego Muñoz Gonzalez · Rodrigo Moreno Cruz · Uriel Antonio Chavez Sanchez · Diego Nieto Pizano</p>
<div class="chips"><a href="{APP}">Abrir la aplicación</a><a class="sec" href="{VIDEO}">Ver el video</a><a class="sec" href="{REPO}">Código en GitHub</a></div>
</div></header>
<main>

<nav class="indice" aria-label="Contenido"><ol>
<li><a href="#resumen">Resumen</a></li><li><a href="#datos">Datos y pregunta</a></li>
<li><a href="#metodologia">Metodología</a></li><li><a href="#almada">Resultados: cómo juega Almada</a></li>
<li><a href="#simulador">Resultados: el simulador</a></li><li><a href="#validacion">Validación</a></li>
<li><a href="#hipotesis">Hipótesis y decisiones</a></li><li><a href="#limites">Limitaciones</a></li>
<li><a href="#reproducir">Reproducir, datos y equipo</a></li></ol></nav>

<h2 id="resumen">1. Resumen</h2>
<div class="tarjetas">
<div class="tarjeta"><b>0.882</b><span>AUC: un clasificador reconoce los partidos de Almada (4.º de 45 técnicos-club)</span></div>
<div class="tarjeta"><b>36.8 m</b><span>ancho de su bloque contra 38.5 de la liga: el más estrecho (percentil 1)</span></div>
<div class="tarjeta"><b>±0.6</b><span>puntos por torneo que mueve el técnico, contra ±5.3 del azar y ±5.75 del plantel</span></div>
<div class="tarjeta"><b>p = 0.195</b><span>el simulador describe estilos, pero no le gana a la inercia (Diebold-Mariano)</span></div>
</div>
<p>Todas las cifras de Almada se miden contra la liga completa y sobreviven a un único control
de falsos positivos (Benjamini-Hochberg sobre 730 afirmaciones; quedan 243 demostradas).</p>
<ol class="hallazgos">
<li><b>Se le reconoce.</b> Un clasificador distingue sus partidos de los del resto de la liga
con AUC 0.882. Lo que más lo delata: la presión alta, las conducciones hacia adelante y los
saques de meta en corto (que usa menos).</li>
<li><b>Aprieta encima del rival.</b> PPDA de 8.50 contra 10.29 de la liga, y un jugador suyo a
menos de 2 m en el 20.7 % de los toques del rival (la liga, 17.2 %).</li>
<li><b>Defiende con el bloque más estrecho de la Liga MX:</b> 36.8 m de ancho contra 38.5, y se
sostiene controlando lo que alcanza a ver la cámara.</li>
<li><b>Ataca vertical.</b> Entra al área conduciendo el 47 % de las veces (la liga, 37 %) y
remata 16.2 veces por partido contra 13.3.</li>
<li><b>El técnico pesa poco frente al plantel y la suerte:</b> ±0.6 puntos por torneo contra
±5.3 del azar y ±5.75 del plantel (37 técnicos con al menos 30 partidos).</li>
<li><b>En el simulador, el América con Almada rinde casi igual:</b> ≈26.5 puntos en el Apertura
2026 y liguilla en 66.8 % de los torneos, +0.62 puntos frente a un estilo neutro (IC 90 %
[−0.42, +1.73]). Es un escenario para explorar, no un pronóstico.</li>
<li><b>El simulador describe estilos, pero no predice:</b> en 35 cambios de técnico reales no
acierta mejor que suponer que todo sigue igual (p = 0.195).</li>
</ol>

<h2 id="datos">2. Datos y pregunta</h2>
<p>Usamos eventos y tracking 360 de StatsBomb de la Liga MX, temporadas 2021/22 a 2026/27
(1,789 partidos). Almada dirigió 168 de ellos: 139 con Pachuca, 20 con Santos Laguna y 9 con
el América. Con el América, 9 partidos no alcanzan para demostrar nada por sí solos.</p>
<p>La pregunta tiene dos partes. Primero, describir qué hace distinto a Almada frente a la liga,
sin confundirlo con su plantel. Segundo, simular el Apertura 2026 del América con el estilo de
cualquier técnico real (con al menos 30 partidos) o inventado, y ver cuántos puntos haría.</p>
<div class="nota">Nada de esto es causa y efecto: describimos lo que hizo su equipo. El
simulador separa técnico y plantel con un modelo, y lo validamos antes de usarlo (sección 6).</div>

<h2 id="metodologia">3. Metodología</h2>
<h3>3.1 Vocabulario de jugadas: cadena absorbente y mezcla de tres tipos</h3>
<p>Cortamos cada posesión en secuencias, desde su inicio hasta su primera absorción. Una
secuencia recorre una malla de 5×4 zonas (20 estados transitorios) y termina en uno de cinco
estados absorbentes: gol, remate, pérdida, balón fuera o interrupción a favor. Con la matriz de
transición en bloques {m(r"P=\begin{pmatrix} Q & R\\ 0 & I\end{pmatrix}")}:</p>
{M(r"N=(I-Q)^{-1},\qquad t=N\mathbf{1},\qquad B=NR")}
<p>donde {m("t")} da las acciones esperadas hasta la absorción y {m("B")} la probabilidad de
cada final. Las secuencias de la liga no salen de una sola cadena: las modelamos como una mezcla
de {m("K=3")} cadenas, cada una con su matriz para el primer paso {m(r"P^{0,k}")}, estimada con
EM-MAP (prior de Dirichlet hacia la cadena de la liga):</p>
{M(r"\Pr(s)=\sum_{k=1}^{3}\pi_k\,\mu^k_{z_1}\,P^{0,k}_{z_1z_2}\prod_{t\ge2}P^{k}_{z_tz_{t+1}}")}
<p>Los tres tipos son el <b>ataque directo</b> (unas 3.5 acciones; 14 % termina en remate), el
<b>toque sin profundidad</b> o circulación estéril (unas 6.7 acciones; 2 a 3 %) y el <b>ataque
elaborado</b> (unas 9.2 acciones; 12 %).</p>
{fig(FIG / "vocabulario" / "visitas.png", "Los tres tipos de jugada de la Liga MX: por dónde pasa el balón en cada uno (más oscuro, más visitas). Ataque hacia la derecha.", "Tres canchas con las zonas más visitadas por cada tipo de jugada", ancho=1400)}

<h3>3.2 Separar al técnico de su plantel</h3>
<p>Cada equipo tiene una ficha de 32 componentes (ritmo, mezcla de tipos según el contexto,
eficiencia de cada tipo y balón parado), medidas como desviaciones de la liga. Estimamos en dos
etapas: primero cada componente por celda técnico × club × torneo (al menos 8 partidos); luego
un modelo bayesiano de efectos cruzados separa al técnico del plantel:</p>
{M(r"y_c\sim\mathcal{N}\left(b_0+\varphi_{\mathrm{club},\mathrm{torneo}}+\theta_{\mathrm{técnico}}+\varepsilon_{\mathrm{técnico},\mathrm{club}},\ v_c\right)")}
{M(r"\varphi_{\mathrm{club},t}\sim\mathcal{N}(\varphi_{\mathrm{club},t-1},\sigma_\Delta),\quad\theta\sim\mathcal{N}(0,\sigma_\theta),\quad\varepsilon\sim\mathcal{N}(0,\sigma_{int})")}
<p>Lo ajustamos con NUTS (PyMC y numpyro). Usamos atribución continua: con el técnico
{m("T^*")}, la ficha del América es {m(r"\zeta=b_0+\varphi_{Am}+\theta_{T^*}+\varepsilon_{T^*,Am}")}
en todas las componentes, con la posterior completa de {m(r"\theta")} encogida por
{m(r"\sigma_\theta")}. Así el técnico pesa lo que los datos permiten distinguir.</p>

<h3>3.3 Del estilo a los goles: intensidad y recursión exacta del marcador</h3>
<p>Con {m("f")} igual al cociente goles/xG de la liga, la intensidad de gol del equipo
{m("i")} contra {m("j")} en el minuto {m("t")} con el marcador en el estado {m("m")} junta el
juego abierto (jugadas por minuto {m(r"\lambda")}, tipo de jugada {m(r"\pi")}, probabilidad de
remate {m("p")} y xG por remate {m("g")}) y el balón parado:</p>
{M(r"\mu_{ij}(t,m)=f\left[\lambda_i(t)\sum_k\pi_{ik}(t,m)\,p_{ik}\,g_{ik}+\sum_u \bar r_u e^{\rho_{i,u}}\,q_{iju}\,\kappa_u\right]")}
<p>En cada minuto cada equipo anota un número de goles Poisson con esa intensidad, y la
distribución del marcador se propaga de forma exacta:</p>
{M(r"P_{t+1}(a+x,b+y)=\sum_{a,b}P_t(a,b)\,\mathrm{Pois}\left(x;\mu_{ij}(t,m_{ab})\right)\mathrm{Pois}\left(y;\mu_{ji}(t,2-m_{ab})\right)")}
<p>Como {m(r"\mu")} solo depende del signo de {m("a-b")}, cada paso se escribe con matrices de
Toeplitz y obtenemos el marcador final exacto (masa perdida menor a {m("10^{-6}")}).</p>

<h3>3.4 El torneo: Monte Carlo en dos niveles</h3>
<p>Jugamos los 153 partidos del calendario real del Apertura 2026: {m("R")} muestras de la
posterior de las fichas y, en cada una, {m("S")} torneos. Para comparar dos técnicos usamos los
mismos números aleatorios. El error de Monte Carlo es</p>
{M(r"\operatorname{Var}(\bar X)=\frac{\sigma_b^2}{R}+\frac{\sigma_w^2}{RS}")}
<p>Una comparación es «prácticamente igual» si el intervalo del 90 % de la diferencia cabe en
±3 puntos, y «mejor» o «peor» si el del 95 % excluye el 0.</p>

<h3>3.5 Control de falsos positivos</h3>
<p>Las 26 hipótesis del estudio se registraron antes del análisis. Cada afirmación sobre Almada
(hipótesis, métricas contra la liga, efectos con su intervalo) entra a un solo control de
Benjamini-Hochberg con α = 0.05: de 730 afirmaciones quedan 243 demostradas. Lo que no
sobrevive se reporta como «no demostrado» y no se interpreta. Las incertidumbres se calculan
con bootstrap por partido completo.</p>

<h2 id="almada">4. Resultados: cómo juega Almada</h2>
<h3>4.1 Identidad</h3>
<p>Además de reconocerse (AUC 0.882 contra la liga y 0.848 contra Pachuca con otros técnicos;
permutación p = 0.005), Almada <b>reacciona menos que la liga</b> al contexto: cuando va ganando
baja menos su ataque elaborado (+2.2 pp) y, contra un rival 100 Elo más fuerte, cambia menos su
receta (directa −1.1 pp, elaborado +2.0 pp). Su estilo viaja: H1 y H3 se sostienen en Pachuca
y en Santos Laguna.</p>
{fig(FIG / "identidad" / "contexto.png", "Cuánto cambia Almada su manera de atacar con el marcador, el minuto, la localía y el rival, por encima de lo que cambia la liga. En azul, los intervalos del 95 % que excluyen el 0.", "Gráfica de intervalos de la reacción de Almada al contexto contra la liga", ancho=1400)}

<h3>4.2 Ataque</h3>
<ul>
<li>Sale largo: saques de meta en corto 31.5 % contra 47.2 %.</li>
<li>Avanza vertical y conduciendo: 2.78 m/s contra 2.47; conduce hacia adelante 22.6 veces por
partido contra 16.4.</li>
<li>Llega al área conduciendo, no por centros: 47 % conduciendo (la liga, 37 %) y 15 % con
centro (la liga, 20 %).</li>
<li>Remata más (16.2 contra 13.3 por partido), de más lejos y menos de cabeza; xG por partido
1.46 contra 1.30.</li>
</ul>
{fig(FIG / "ofensiva" / "familias_cancha.png", "Las tres maneras de atacar de Almada contra la liga. Azul: zonas por donde pasa el balón más que la liga; rojo, menos. Flechas: el camino más probable hasta el remate.", "Tres canchas con las diferencias de Almada contra la liga por tipo de jugada", ancho=1400)}

<h3>4.3 Defensa</h3>
<p>Aprieta encima: PPDA de 8.50 contra 10.29 y un jugador a menos de 2 m en el 20.7 % de los
toques del rival (17.2 % en la liga). Recupera 13.7 balones en el último tercio contra 12.0.
Defiende con el bloque más estrecho de la liga (36.8 m contra 38.5; con la cámara abierta,
38.2 contra 40.1, diferencia −1.96 m [−2.24, −1.68]). Sus rivales le rematan 11.9 veces por
partido contra 13.3. El costo: cuando el rival logra salir, avanza más rápido (2.76 m/s contra
2.47).</p>
{fig(FIG / "defensa" / "pictograma_presion.png", "De cada 100 toques del rival, cuántos tienen a un jugador de Almada a 2 m o menos.", "Pictograma: 21 de cada 100 toques con Almada contra 17 de cada 100 en la liga", ancho=1100)}
{fig(FIG / "defensa" / "bloque_tipico.png", "El bloque típico sin balón de Almada (relleno) contra el de la liga (línea), solo con la cámara abierta.", "Rectángulos del bloque defensivo de Almada y de la liga sobre una cancha", ancho=920)}

<h3>4.4 Banca</h3>
<p>Hace cambios del mismo puesto (empatando, 90 % contra 78 % de la liga) y reacomoda menos la
formación (1.42 reacomodos por partido contra 1.81). No se demostró que sus cambios muevan el
xG ni la manera de atacar.</p>

<h3>4.5 Balón parado y el xDefense</h3>
<p>El xDefense es una métrica nuestra: un gol de córner exige que te rematen y que ese remate
entre. Con {m("C")} el saque, {m("S")} el remate y {m("G")} el gol, como {m(r"G\subseteq S")},
{m(r"P(G\mid C)=P(S\mid C)\,P(G\mid S,C)")}, y la diferencia entre lo esperado y lo ocurrido se
parte en cuatro pedazos exactos:</p>
{M(r"\hat p\kappa-g=(\hat p-s)\kappa+s(\kappa-B)+s(B-F)+s(F-g)")}
<p>prevención + alejamiento + supresión + portero. En córners en contra Almada pone menos gente
en el área (6.65 contra 8.67) y marca más al hombre (52.5 % contra 38.6 %); le rematan 15 %
menos por córner (razón 0.85 [0.75, 0.96]), pero los remates que concede llegan más limpios
(supresión −0.0048 de xG por remate [−0.0077, −0.0019]). A favor, manda menos córners al punto
penal, que es donde más rinden en la Liga MX.</p>
{fig(FIG / "balon_parado" / "rutinas_corner.png", "Qué córners producen más en la Liga MX (xG por córner con su IC 95 %) y cuánto usa cada rutina Almada.", "Gráfica de puntos con el xG por córner de cada rutina", ancho=1400)}

<h2 id="simulador">5. Resultados: el simulador</h2>
<p>La aplicación responde: <i>si el América tuviera a este técnico, con su plantel actual y los
demás equipos sin cambios, ¿cómo jugaría y cuántos puntos haría en el Apertura 2026?</i></p>
<h3>5.1 ¿Qué pesa más?</h3>
<div class="grafica">{barras_pesa_mas()}</div>
<p>En un torneo de 17 jornadas, lo típico que varían los puntos de un equipo es ±5.3 por el
azar de los partidos y ±5.75 por la fuerza de su plantel (medida directo de las tablas reales).
El técnico mueve ±0.6. Por eso la mayoría de las comparaciones entre técnicos reales salen
«prácticamente iguales», y eso también es una respuesta.</p>

<h3>5.2 Almada en el América</h3>
<div class="tarjetas">
<div class="tarjeta"><b>26.54</b><span>puntos esperados en el Apertura 2026 (modo preciso)</span></div>
<div class="tarjeta"><b>66.8 %</b><span>probabilidad de liguilla</span></div>
<div class="tarjeta"><b>+0.62</b><span>puntos frente a un estilo neutro, IC 90 % [−0.42, +1.73]</span></div>
<div class="tarjeta"><b>ρ = 0.60</b><span>la «presión» del simulador contra el PPDA medido (IC 95 % [0.34, 0.77], 37 técnicos)</span></div>
</div>
{fig(captura, "La aplicación: cada técnico se describe con cuatro perillas (cómo ataca, cómo defiende, balón parado en contra y a favor), y el simulador devuelve puntos, liguilla y su comparación contra el América de hoy. En la captura, un técnico inventado con el ataque más directo de la liga.", "Captura de la aplicación con el bloque qué pesa más y las tarjetas de resultados", recorte=(0, 0, 1440, 1500), ancho=1200, jpeg=True)}
<p>El modelo de partido del estudio, distinto del simulador, llega a una conclusión parecida:
con Almada el América haría 29.5 puntos (intervalo conforme del 80 %: 21 a 38) y solo con el
plantel 29.2. La diferencia, 0.3 puntos, cabe en cualquier intervalo.</p>
{fig(FIG / "simulacion" / "proyeccion.png", "Modelo de partido del estudio: puntos y posición del América con Almada contra solo el plantel (10 mil torneos), y la proyección contra lo real en 70 llegadas de técnicos (correlación 0.62).", "Tres paneles con la distribución de puntos, la posición final y la proyección contra lo real", ancho=1400)}

<h2 id="validacion">6. Validación del simulador</h2>
<p>Ocho pruebas, las mismas que muestra la pestaña «¿Le podemos creer?» de la aplicación, con los
parámetros publicados (estimados con 1,701 partidos anteriores al Apertura 2026).</p>
<div class="tabla"><table>
<thead><tr><th>#</th><th>prueba</th><th>estadístico</th><th>resultado</th><th>veredicto</th></tr></thead>
<tbody>{filas_val}</tbody></table></div>
<p>Otras dos cifras: la dispersión de los puntos reales es 1.52 veces la del simulador (IC 95 %
[1.23, 1.70]), y el RPS (0.2119) mejora a las frecuencias base (0.2256) pero no al Poisson con
ataque y defensa del mismo torneo (0.2038), que usa información de la propia muestra.</p>

<h2 id="hipotesis">7. Hipótesis y decisiones</h2>
<h3>7.1 Hipótesis del simulador</h3>
<div class="tabla"><table><thead><tr><th></th><th>hipótesis</th><th>resultado</th></tr></thead>
<tbody>{filas_hip}</tbody></table></div>
<p>Las hipótesis del estudio sobre Almada (H1 a H26) están en
<code>estudio/docs/11_HIPOTESIS.md</code>, con su fecha de registro.</p>
<h3>7.2 Decisiones que cambiaron los resultados</h3>
<div class="tabla"><table><thead><tr><th></th><th>decisión</th><th>efecto</th></tr></thead>
<tbody>{filas_dec}</tbody></table></div>

<h2 id="limites">8. Limitaciones</h2>
<ul>
<li>El simulador describe estilos, pero no predice: ante cambios de técnico reales no acierta
mejor que la inercia, y así lo dice la aplicación.</li>
<li>Acorta las diferencias entre equipos (factor 1.52): los fuertes sacan más puntos, y los
débiles menos, de los que les asigna. Corregirlo exige recalibrar la dispersión de las fichas.</li>
<li>No modela jugadores, lesiones, expulsiones, arbitraje, otros torneos ni el vestidor, y
simula el torneo completo sin condicionar en los partidos ya jugados.</li>
<li>Las pruebas 1 a 6 y la 8 son dentro de la muestra; aún no hay una prueba sobre un torneo
que no se haya jugado.</li>
<li>En el estudio, el técnico mueve cuánto usa cada tipo de jugada, no cómo la juega; el
supuesto es razonable en directa y elaborado, y no concluyente en circulación estéril.</li>
<li>Las cámaras 360 no ven a todos los jugadores; por eso controlamos por lo que alcanza a ver
la cámara.</li>
</ul>

<h2 id="reproducir">9. Reproducir, datos y equipo</h2>
<p>Todo el código, las pruebas y la documentación están en <a href="{REPO}">{REPO}</a>. La
aplicación funciona sin los datos de StatsBomb: le bastan los parámetros calibrados de
<code>simulador/artefactos/</code>. La suite del simulador pasa completa (262 pruebas, 0 fallas).</p>
<p>Los datos de StatsBomb se usaron solo para esta competencia y no se publican; el repositorio
incluye únicamente parámetros agregados por liga, equipo y técnico. El código y la documentación
se distribuyen bajo la licencia MIT, que no cubre los datos.</p>
<h3>Cómo se hizo este proyecto</h3>
<p>{COMO_SE_HIZO}</p>
<h3>Equipo</h3>
<p>Diego Muñoz Gonzalez · Rodrigo Moreno Cruz · Uriel Antonio Chavez Sanchez · Diego Nieto Pizano</p>
<footer>Hackathon ISAC 2026 · Datos: StatsBomb (eventos y 360), Liga MX, uso exclusivo de la
competencia. Este reporte se genera con <code>docs/herramientas/generar_reporte.py</code>.</footer>
</main>
</body>
</html>
"""


if __name__ == "__main__":
    salida = RAIZ / "REPORTE.html"
    salida.write_text(construir(), encoding="utf-8")
    print(f"{salida} ({salida.stat().st_size / 1e6:.1f} MB)")
