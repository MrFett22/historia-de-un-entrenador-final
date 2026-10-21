"""Piezas con un poco de JavaScript (D-064): se dibujan en un iframe con `st.components.v1.html`. Sin dependencias, sin parpadeos ni destellos: todo entra con
fundidos y movimientos suaves, y con `prefers-reduced-motion` aparece directo el estado final. Los datos (qué torneo, qué goles) los decide Python con el motor;
aquí solo se reproducen. Los textos vienen de textos.py dentro del JSON.
"""

from __future__ import annotations

import json

import streamlit as st

from . import paleta as PA

BASE_CSS = (
    PA.css_variables(esquema=False)
    + """
*{box-sizing:border-box}html,body{margin:0;background:transparent;color:var(--texto);font-family:Inter,-apple-system,system-ui,sans-serif}
.caja{background:var(--superficie);border:1px solid var(--borde);border-radius:18px;padding:16px 18px}
.escudo{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;background:var(--azul-club);border:1px solid var(--borde);
font-size:15px;font-weight:700;letter-spacing:.02em;color:var(--texto);flex:none}
.escudo.foco{background:var(--amarillo);border-color:var(--amarillo);color:var(--fondo)}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
canvas.conf{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none}
"""
)

JS_COMUN = """
const REDUCIDO = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function confeti(canvas){
  if (REDUCIDO) return;
  const c = canvas, x = c.getContext('2d'); const w = c.width = c.clientWidth, h = c.height = c.clientHeight;
  const css = getComputedStyle(document.documentElement), col = ['--amarillo','--texto','--azul','--rojo'].map(v => css.getPropertyValue(v).trim());
  const ps = Array.from({length: 46}, () => ({x: w*(0.2+0.6*Math.random()), y: -10-Math.random()*h*0.3, vx: (Math.random()-.5)*1.6, vy: 1+Math.random()*1.6,
    r: 2+Math.random()*2.5, c: col[Math.floor(Math.random()*col.length)], a: 0.9}));
  let t0 = null;
  function f(t){ if(!t0) t0 = t; const dt = (t-t0)/1700; x.clearRect(0,0,w,h);
    ps.forEach(p => { p.x += p.vx; p.y += p.vy; x.globalAlpha = Math.max(0, p.a*(1-dt)); x.fillStyle = p.c; x.beginPath(); x.arc(p.x,p.y,p.r,0,6.283); x.fill(); });
    if (dt < 1) requestAnimationFrame(f); else x.clearRect(0,0,w,h); }
  requestAnimationFrame(f);
}
"""

CASINO = (
    """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>"""
    + BASE_CSS
    + """
.f{display:grid;grid-template-columns:34px 1fr 44px 44px;align-items:center;gap:8px;padding:4px 8px;border-radius:10px;font-size:18px;opacity:0;transform:translateY(8px);
transition:opacity .35s ease,transform .35s ease}
.f.on{opacity:1;transform:none}.f.cab{opacity:1;transform:none;color:var(--texto2);font-size:15px;letter-spacing:.06em;text-transform:uppercase}
.f .n{color:var(--texto2);text-align:right;font-variant-numeric:tabular-nums}.f .e{display:flex;align-items:center;gap:9px;min-width:0}.f .e span:last-child{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.f .p{text-align:right;font-weight:650;font-variant-numeric:tabular-nums}.f .d{text-align:right;color:var(--texto2);font-variant-numeric:tabular-nums}
.f.liga{box-shadow:inset 3px 0 0 color-mix(in srgb,var(--amarillo) 55%,transparent)}
.f.foco{background:color-mix(in srgb,var(--amarillo) 16%,transparent);box-shadow:inset 3px 0 0 var(--acento);font-weight:700;font-size:18px;padding:8px 8px}
.f.foco .n{color:var(--acento);font-size:20px}
.linea{height:1px;margin:3px 8px;border-top:1px dashed color-mix(in srgb,var(--amarillo) 70%,transparent);background:none;opacity:0;transition:opacity .4s}.linea.on{opacity:1}
.res{margin:14px 0 4px;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;opacity:0;transform:scale(.96);transition:opacity .5s ease,transform .5s ease}
.res.on{opacity:1;transform:none}.res b{font-size:clamp(34px,7vw,52px);line-height:1}.res span{font-size:18px;font-weight:650}
.ok{color:var(--amarillo)}.no{color:var(--rojo-texto)}
.racha{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.pill{width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;
font-size:15px;font-weight:700;color:var(--fondo);opacity:0;transform:scale(.8);transition:opacity .3s,transform .3s}.pill.on{opacity:1;transform:none}
.pill.G{background:var(--amarillo)}.pill.E{background:var(--texto2)}.pill.P{background:var(--rojo-texto)}.sub{color:var(--texto2);font-size:15px;margin-top:12px}
</style></head><body><div class="caja" style="position:relative"><canvas class="conf" id="cv"></canvas><div id="t"></div>
<div class="res" id="res"><b id="lug"></b><span id="msg"></span></div><div class="sub">__RACHA__</div><div class="racha" id="racha"></div></div>
<script>"""
    + JS_COMUN
    + """
const D = __DATA__;
const t = document.getElementById('t');
const cab = document.createElement('div'); cab.className = 'f cab'; cab.innerHTML = '<span></span><span>'+D.textos.equipo+'</span><span style="text-align:right">'+D.textos.pts+'</span><span style="text-align:right">'+D.textos.dif+'</span>'; t.appendChild(cab);
const els = [];
D.tabla.forEach((r, i) => {
  const d = document.createElement('div'); d.className = 'f' + (r.foco ? ' foco' : '') + (r.lugar <= D.liguilla ? ' liga' : '');
  d.innerHTML = '<span class="n">'+r.lugar+'</span><span class="e"><span class="escudo'+(r.foco?' foco':'')+'">'+r.iniciales+'</span><span>'+r.equipo+'</span></span><span class="p">'+r.puntos+'</span><span class="d">'+(r.gf-r.gc>0?'+':'')+(r.gf-r.gc)+'</span>';
  t.appendChild(d); els.push(d);
  if (r.lugar === D.liguilla) { const l = document.createElement('div'); l.className = 'linea'; t.appendChild(l); els.push(l); }
});
const rachaEl = document.getElementById('racha');
D.racha.forEach(x => { const p = document.createElement('span'); p.className = 'pill ' + x; p.textContent = x; rachaEl.appendChild(p); });
function fin(){
  const r = document.getElementById('res'), l = document.getElementById('lug');
  l.textContent = D.textos.termino; l.className = D.clasifica ? 'ok' : '';
  document.getElementById('msg').textContent = D.clasifica ? D.textos.liguilla : D.textos.fuera; document.getElementById('msg').className = D.clasifica ? 'ok' : 'no';
  r.classList.add('on');
  const ps = rachaEl.children; for (let k = 0; k < ps.length; k++) setTimeout(() => ps[k].classList.add('on'), REDUCIDO ? 0 : 60*k);
  if (D.clasifica) confeti(document.getElementById('cv'));
}
if (REDUCIDO) { els.forEach(e => e.classList.add('on')); fin(); }
else { let i = els.length - 1; (function paso(){ els[i].classList.add('on'); i--; if (i >= 0) setTimeout(paso, 95); else setTimeout(fin, 250); })(); }
</script></body></html>"""
)

PARTIDO = (
    """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>"""
    + BASE_CSS
    + """
.tablero{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px}.eq{display:flex;flex-direction:column;align-items:center;gap:6px;font-size:15px;color:var(--texto2);text-align:center}
.eq .escudo{width:46px;height:46px;font-size:18px}.marcador{font-size:clamp(46px,10vw,72px);font-weight:750;line-height:1;font-variant-numeric:tabular-nums;display:flex;gap:14px;align-items:center}
.marcador span{display:inline-block;min-width:.6em;text-align:center;transition:transform .35s ease}.marcador span.sube{transform:scale(1.14)}
.min{text-align:center;color:var(--texto2);font-size:15px;margin:8px 0 2px;letter-spacing:.04em}.min b{color:var(--texto);font-size:20px}
.mom{margin-top:8px}.mom-t{font-size:15px;color:var(--texto2);margin:0 0 6px}
.graf{position:relative;height:190px;border-radius:12px;background:color-mix(in srgb,var(--texto) 4%,transparent);overflow:hidden}
.graf svg{position:absolute;inset:0;width:100%;height:100%}
.graf .et{position:absolute;left:8px;font-size:16px;font-weight:650;letter-spacing:.02em}.graf .et.arriba{top:6px;color:var(--america)}.graf .et.abajo{bottom:6px;color:var(--rival)}
.graf .gol{pointer-events:none;position:absolute;transform:translate(-50%,-50%);font-size:18px;opacity:0;transition:opacity .4s}.graf .gol.on{opacity:1}
.graf rect.col{fill:transparent}.graf rect.corte{fill:var(--texto)}
.ejex{position:relative;height:16px;font-size:15px;color:var(--texto2)}.ejex span{position:absolute;transform:translateX(-50%)}
.ev{display:flex;flex-direction:column;gap:4px;min-height:34px;font-size:18px;margin-top:8px}.ev div{opacity:0;transform:translateY(6px);transition:opacity .4s ease,transform .4s ease}.ev div.on{opacity:1;transform:none}
.res{margin-top:10px;font-size:20px;font-weight:700;opacity:0;transition:opacity .5s}.res.on{opacity:1}.ok{color:var(--amarillo)}.no{color:var(--rojo-texto)}.ig{color:var(--texto2)}
.cien{color:var(--texto2);font-size:15px;margin-top:4px;opacity:0;transition:opacity .5s}.cien.on{opacity:1}
.rem{color:var(--texto2);font-size:15px;margin-top:4px;opacity:0;transition:opacity .5s}.rem.on{opacity:1}
.antes{color:var(--texto2);font-size:15px;margin-top:10px}
</style></head><body><div class="caja" style="position:relative"><canvas class="conf" id="cv"></canvas>
<div class="tablero"><div class="eq" id="L"></div><div class="marcador"><span id="a">0</span><span style="font-size:.5em;color:var(--texto2)">:</span><span id="b">0</span></div><div class="eq" id="R"></div></div>
<div class="min">__MINUTO__ <b id="m">0</b>'</div>
<div class="mom"><div class="mom-t">__BARRAS__</div>
<div class="graf" id="graf"><svg viewBox="0 0 900 190" preserveAspectRatio="none" aria-hidden="true">
<line x1="0" x2="900" y1="95" y2="95" stroke="var(--linea-tenue)" stroke-width="1" vector-effect="non-scaling-stroke"/>
<line id="desc" y1="0" y2="190" stroke="var(--linea-tenue)" stroke-width="1" stroke-dasharray="4 4" vector-effect="non-scaling-stroke"/>
<g id="barras"></g></svg>
<span class="et arriba" id="eta"></span><span class="et abajo" id="etr"></span></div>
<div class="ejex" id="ejex"></div></div>
<div class="ev" id="ev"></div><div class="res" id="res"></div><div class="rem" id="rem"></div><div class="cien" id="cien"></div><div class="antes">__ANTES__</div></div>
<script>"""
    + JS_COMUN
    + """
const D = __DATA__;
const am = '<span class="escudo foco" style="width:46px;height:46px;font-size:18px">AME</span><span>'+D.textos.america+'</span>';
const rv = '<span class="escudo" style="width:46px;height:46px;font-size:18px">'+D.iniciales+'</span><span>'+D.rival+'</span>';
document.getElementById('L').innerHTML = D.local ? am : rv; document.getElementById('R').innerHTML = D.local ? rv : am;
document.getElementById('eta').textContent = D.textos.america; document.getElementById('etr').textContent = D.rival;
const A = document.getElementById('a'), B = document.getElementById('b'), M = document.getElementById('m'), EV = document.getElementById('ev'), GR = document.getElementById('graf');
const T = D.minutos, W = 900, Y0 = 95;
document.getElementById('desc').setAttribute('x1', W * 45 / T); document.getElementById('desc').setAttribute('x2', W * 45 / T);
const EJ = document.getElementById('ejex');
[0, 45, 90].forEach(v => { const s = document.createElement('span'); s.textContent = v + "'"; s.style.left = Math.min(Math.max(100 * v / T, 2), 98) + '%'; EJ.appendChild(s); });
const NS = 'http://www.w3.org/2000/svg', BARRAS = [], CORTES = [];
const MM = D.dominio, TOPE = D.tope, TECHO = D.techo, K = (Y0 - 10) / TECHO;                  // UNA serie con signo: M > 0 sube (América), M < 0 baja (rival)
const grupo = document.getElementById('barras');
function linea(y, clase){ const l = document.createElementNS(NS, 'line'); l.setAttribute('x1', 0); l.setAttribute('x2', W); l.setAttribute('y1', y); l.setAttribute('y2', y);
  l.setAttribute('class', clase); l.setAttribute('stroke', 'var(--linea-tenue)'); l.setAttribute('stroke-dasharray', '2 5'); l.setAttribute('vector-effect', 'non-scaling-stroke'); grupo.appendChild(l); }
linea(Y0 - K * TOPE, 'tope'); linea(Y0 + K * TOPE, 'tope');
const por = x => Math.abs(x * T).toFixed(2);
for (let t = 0; t < T; t++) {
  const w = W / T, arriba = MM[t] > 0;
  const r = document.createElementNS(NS, 'rect'); r.setAttribute('class', 'bar ' + (arriba ? 'ba' : 'br')); r.setAttribute('data-min', t + 1); r.setAttribute('x', (w * t + w * 0.06).toFixed(2));
  r.setAttribute('width', (w * 0.88).toFixed(2)); r.setAttribute('rx', 1.2); r.setAttribute('y', Y0); r.setAttribute('height', 0); r.setAttribute('fill', arriba ? 'var(--america)' : 'var(--rival)');
  grupo.appendChild(r); BARRAS.push(r);
  const c = document.createElementNS(NS, 'rect'); c.setAttribute('class', 'col'); c.setAttribute('x', (w * t).toFixed(2)); c.setAttribute('width', w.toFixed(2)); c.setAttribute('y', 0); c.setAttribute('height', 190);
  const ti = document.createElementNS(NS, 'title');
  ti.textContent = D.textos.hover.replace('{m}', t + 1) + '\\n' + D.textos.hover_fila.replace('{eq}', arriba ? D.textos.america : D.rival).replace('{x}', por(MM[t]));
  c.appendChild(ti); grupo.appendChild(c);
}
function tapa(t, arriba){ if (CORTES[t]) return; const b = BARRAS[t], c = document.createElementNS(NS, 'rect'); c.setAttribute('class', 'corte'); c.setAttribute('width', b.getAttribute('width')); c.setAttribute('x', b.getAttribute('x'));
  c.setAttribute('height', 3); c.setAttribute('rx', 1); c.setAttribute('y', arriba ? 10 : 2 * Y0 - 13); grupo.appendChild(c); CORTES[t] = c; }
function barra(t){ const b = BARRAS[t], h = Math.min(K * Math.abs(MM[t]), Y0 - 10), arriba = MM[t] > 0;
  if (K * Math.abs(MM[t]) > Y0 - 10 + 0.01) tapa(t, arriba);
  b.setAttribute('y', (arriba ? Y0 - h : Y0).toFixed(1)); b.setAttribute('height', h.toFixed(1)); }
function dibuja(upto){ for (let t = 0; t < upto; t++) barra(t); }
function marca(x, y){ A.textContent = D.local ? x : y; B.textContent = D.local ? y : x; }
const pins = [];
D.goles.forEach(g => { const s = document.createElement('span'); s.className = 'gol'; s.textContent = '⚽'; s.title = g[0] + "'"; s.style.left = (100 * (g[0] - 0.5) / T) + '%';
  s.style.top = (g[1] === 'i' ? 22 : 168) + 'px'; GR.appendChild(s); pins.push(s); });
function gol(g, k){
  marca(g[2], g[3]); const el = (g[1] === 'i' ? (D.local ? A : B) : (D.local ? B : A)); el.classList.add('sube');
  setTimeout(() => { A.classList.remove('sube'); B.classList.remove('sube'); }, 450);
  pins[k].classList.add('on');
  const d = document.createElement('div'); d.textContent = '⚽ ' + D.textos.gol.replace('{eq}', g[1] === 'i' ? D.textos.america : D.rival).replace('{m}', g[0]) + '  (' + (D.local ? g[2] : g[3]) + ' - ' + (D.local ? g[3] : g[2]) + ')';
  EV.appendChild(d); requestAnimationFrame(() => d.classList.add('on'));
}
function final(){
  M.textContent = T; dibuja(T);
  const r = document.getElementById('res'); const k = D.america > D.rival_goles ? 0 : (D.america === D.rival_goles ? 1 : 2);
  r.textContent = D.textos.resultado[k]; r.className = 'res on ' + (k === 0 ? 'ok' : (k === 1 ? 'ig' : 'no'));
  const rm = document.getElementById('rem'); rm.textContent = D.textos.remates; rm.classList.add('on');
  const c = document.getElementById('cien'); c.textContent = D.textos.cien; c.classList.add('on');
  if (!D.goles.length) { const d = document.createElement('div'); d.textContent = D.textos.sin_goles; d.className = 'on'; EV.appendChild(d); }
  if (k === 0) confeti(document.getElementById('cv'));
}
if (REDUCIDO) { D.goles.forEach((g, k) => gol(g, k)); EV.querySelectorAll('div').forEach(d => d.classList.add('on')); final(); }
else {
  let min = 0, gi = 0; const paso = 2600 / T;
  const id = setInterval(() => { min++; M.textContent = min; dibuja(min);
    while (gi < D.goles.length && D.goles[gi][0] <= min) { gol(D.goles[gi], gi); gi++; }
    if (min >= T) { clearInterval(id); setTimeout(final, 300); } }, paso);
}
</script></body></html>"""
)


def _j(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False).replace("</", "<\\/")


def html_casino(datos: dict, textos: dict) -> str:
    return CASINO.replace("__DATA__", _j({**datos, "textos": textos})).replace(
        "__RACHA__", textos["racha"]
    )


def datos_partido(p: dict) -> dict:
    """Lo que la animación de «Ver un partido» necesita del partido sorteado (`analisis.partido_unico`): goles, marcador y el dominio M(t) de cada minuto (una sola serie con signo:
    positivo, domina el América; negativo, el rival), con el tope del eje y el marco (D-096)."""
    return {
        "minutos": p["minutos"],
        "goles": p["goles"],
        "local": p["local"],
        "rival": p["nombre_rival"],
        "iniciales": p["iniciales_rival"],
        "america": p["america"],
        "rival_goles": p["rival"],
        "dominio": p["dominio"],
        "tope": p["tope"],
        "techo": p["techo"],
    }


def html_partido(datos: dict, textos: dict) -> str:
    return (
        PARTIDO.replace("__DATA__", _j({**datos, "textos": textos}))
        .replace("__MINUTO__", textos["minuto"])
        .replace("__ANTES__", textos["antes"])
        .replace("__BARRAS__", textos["barras"])
    )


def _iframe(contenido: str, alto: int) -> None:
    """`st.iframe` (Streamlit ≥ 1.5x); `st.components.v1.html` quedó en desuso."""
    if hasattr(st, "iframe"):
        st.iframe(contenido, height=alto)
    else:  # pragma: no cover
        import streamlit.components.v1 as components

        components.html(contenido, height=alto, scrolling=False)


def casino(datos: dict, textos: dict) -> None:
    _iframe(html_casino(datos, textos), 860)


def partido(datos: dict, textos: dict) -> None:
    _iframe(html_partido(datos, textos), 600)
