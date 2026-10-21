"""Lámina `capturas/v11/paleta.png` (D-097): los tokens de la paleta del América, para qué sirve cada uno, su contraste medido y cómo se ven los tres tipos de jugada con
deuteranopía y protanopía. Todo sale de `app/paleta.py` y del config; no escribe un solo color a mano.
Uso:  python herramientas/lamina_paleta.py [--salida capturas/v11/paleta.png] [--chromium /ruta/al/chrome]"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from simdt.app import paleta as PA  # noqa: E402


def lamina_html() -> str:
    t = PA.tokens()
    filas = "".join(
        f'<tr><td><i style="background:{f["hex"]}"></i></td><td><b>{html.escape(f["token"])}</b><br><code>{f["hex"]}</code></td><td>{html.escape(f["uso"])}</td>'
        f'<td class="n">{f["contraste"]:.2f}:1<br><small>contra {html.escape(f["contra"])} · mín. {f["minimo"]:g}</small></td></tr>'
        for f in PA.tabla_uso()
    )
    d, tq, e = PA.tipos()
    sims = ""
    for nombre in ("normal",) + PA.DALTONISMOS:
        cols = [c if nombre == "normal" else PA.simular_daltonismo(c, nombre) for c in (d, tq, e)]
        pares = [(0, 1), (0, 2), (1, 2)]
        de = " · ".join(
            f"{PA.diferencia(d, tq, None if nombre == 'normal' else nombre) if i == 0 else (PA.diferencia(d, e, None if nombre == 'normal' else nombre) if i == 1 else PA.diferencia(tq, e, None if nombre == 'normal' else nombre)):.0f}"
            for i in range(3)
        )
        sims += (
            f'<div class="sim"><span class="nom">{nombre}</span>'
            + "".join(f'<i style="background:{c}"></i>' for c in cols)
            + "".join(
                f'<i class="rv" style="background:{PA.mezcla(n, alfa=PA.opacidad_rival()) if nombre == "normal" else PA.simular_daltonismo(PA.mezcla(n, alfa=PA.opacidad_rival()), nombre)}"></i>'
                for n in ("directo", "toque", "elaborado")
            )
            + f'<span class="de">ΔE2000 {de}</span></div>'
        )
    usos = "".join(
        f'<div class="uso"><i style="background:{PA.color(u)}"></i><b>{n}</b></div>'
        for n, u in (
            ("América", "america"),
            ("Rival", "rival"),
            ("Bueno / pasa / ▲", "bueno"),
            ("Malo / alerta / ▼", "malo"),
            ("Neutro / ≈ igual", "neutro"),
            ("Ataque directo", "directo"),
            ("Toque sin profundidad", "toque"),
            ("Ataque elaborado", "elaborado"),
        )
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{PA.css_variables()}
*{{box-sizing:border-box}}body{{margin:0;background:var(--fondo);color:var(--texto);font-family:Inter,-apple-system,system-ui,sans-serif;padding:28px 32px;width:1180px}}
h1{{font-size:30px;margin:0 0 4px}}p{{color:var(--texto2);font-size:17px;margin:0 0 18px}}
table{{width:100%;border-collapse:collapse;background:var(--superficie);border:1px solid var(--borde);border-radius:14px;overflow:hidden}}
td{{padding:9px 12px;border-bottom:1px solid var(--borde);font-size:16px;vertical-align:middle}}td i{{display:block;width:54px;height:34px;border-radius:8px;border:1px solid var(--borde)}}
code{{color:var(--texto2);font-size:15px}}.n{{text-align:right;font-weight:700;white-space:nowrap}}small{{color:var(--texto3);font-weight:400;font-size:14px}}
h2{{font-size:22px;margin:22px 0 8px}}.usos{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.uso{{display:flex;align-items:center;gap:10px;background:var(--superficie);border:1px solid var(--borde);border-radius:12px;padding:10px 12px;font-size:16px}}
.uso i{{width:28px;height:28px;border-radius:7px;flex:none}}.sim{{display:flex;align-items:center;gap:8px;background:var(--superficie);border:1px solid var(--borde);border-radius:12px;padding:8px 12px;margin-bottom:8px}}
.sim .nom{{width:130px;font-size:16px;color:var(--texto2)}}.sim i{{width:70px;height:30px;border-radius:7px}}.sim i.rv{{margin-left:0}}.sim .de{{margin-left:auto;font-size:15px;color:var(--texto2)}}</style></head><body>
<h1>Paleta del América (D-097)</h1><p>Amarillo, azul marino, rojo y blanco sobre oscuro. Sin degradados, sin verdes, morados ni naranjas. Una sola fuente: <code>paleta</code> en el config.</p>
<table>{filas}</table><h2>Significado fijo en toda la app</h2><div class="usos">{usos}</div>
<h2>Los tres tipos de jugada (arriba el América, a la derecha el rival al 55 %) con la visión normal y con daltonismo</h2>{sims}</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="capturas/v11/paleta.png")
    ap.add_argument("--chromium", default="")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright

    out = Path(a.salida)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        kw = {"executable_path": a.chromium} if a.chromium else {}
        b = p.chromium.launch(args=["--no-sandbox"], **kw)
        pg = b.new_page(viewport={"width": 1244, "height": 900})
        pg.set_content(lamina_html())
        pg.wait_for_timeout(400)
        pg.locator("body").screenshot(path=str(out))
        b.close()
    print("lámina:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
