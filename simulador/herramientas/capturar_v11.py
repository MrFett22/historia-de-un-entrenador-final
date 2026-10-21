"""Capturas de la app v11 en `capturas/v11/` (escritorio 1440 px y móvil 390 px) y un GIF corto de «Ver un partido».

Uso (con la app ya corriendo, p. ej. con simulador/correr_app.sh):
    python simulador/herramientas/capturar_v11.py --url http://localhost:8501 --salida simulador/capturas/v11
Necesita Playwright y un Chromium (`pip install playwright`; el GIF necesita ffmpeg; PLAYWRIGHT_BROWSERS_PATH o --chromium=/ruta/al/chrome). No es parte de la app.
Escenario: en «Crea tu propio técnico» se mueve «¿Cómo ataca?» a su extremo directo, se simula, se gira un torneo y se juega un partido; aparte, se mira a Almada (bloqueado).
"""

from __future__ import annotations

import argparse
from pathlib import Path


def listo(pg) -> None:
    """Espera a que termine la simulación en segundo plano: el veredicto de exigencia solo existe con un resultado (al lanzarla se quita el resultado anterior)."""
    pg.wait_for_timeout(1800)
    pg.wait_for_selector(".exigencia", timeout=240000)
    pg.wait_for_timeout(1200)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    ap.add_argument("--salida", default="simulador/capturas/v11")
    ap.add_argument("--chromium", default="")
    ap.add_argument(
        "--espera",
        type=int,
        default=10000,
        help="milisegundos que se espera a que termine la simulación",
    )
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright

    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        kw = {"executable_path": a.chromium} if a.chromium else {}
        b = p.chromium.launch(args=["--no-sandbox"], **kw)
        for nombre, (w, h, esc) in {
            "escritorio": (1440, 7800, 1),
            "movil": (390, 11000, 1),
        }.items():
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=esc)
            pg.goto(a.url, wait_until="networkidle")
            pg.wait_for_selector("[data-testid=stSlider]", timeout=90000)
            pg.wait_for_timeout(2500)
            pg.locator("[role=tab]").nth(1).evaluate("e => e.click()")  # pestaña «🎮 Simulador»
            pg.wait_for_timeout(1000)
            if (
                nombre == "escritorio"
            ):  # «Crea tu propio técnico» con «¿Cómo ataca?» en su extremo directo
                pg.locator("section[data-testid=stSidebar] input[type=range]").first.focus()
                pg.keyboard.press("Home")
                pg.wait_for_timeout(800)
            if nombre == "movil":
                pg.screenshot(path=str(out / f"{nombre}_0_panel.png"))
                for sel in (
                    "[data-testid=stSidebarCollapseButton] button",
                    "[data-testid=stSidebarCollapseButton]",
                ):
                    try:
                        pg.locator(sel).first.click(timeout=2000)
                        break
                    except Exception:
                        pass
                pg.wait_for_timeout(1000)
                try:
                    pg.locator(
                        "[data-testid=stExpandSidebarButton], [data-testid=stSidebarCollapsedControl] button"
                    ).first.click(timeout=2000)
                    pg.wait_for_timeout(800)
                    pg.get_by_role("button", name="Simular torneo").first.click(timeout=3000)
                    listo(pg)
                    pg.locator("[data-testid=stSidebarCollapseButton] button").first.click(
                        timeout=2000
                    )
                    pg.wait_for_timeout(1000)
                except Exception as e:  # noqa: BLE001
                    print("móvil sin simular:", e)
            else:
                pg.get_by_role("button", name="Simular torneo").first.click(timeout=5000)
                listo(pg)
                progreso(pg, out)
                pg.get_by_role("button", name="Gira un torneo").first.click(timeout=5000)
                pg.wait_for_timeout(4500)
                pg.get_by_role("button", name="Jugar el partido").first.click(timeout=5000)
                pg.wait_for_timeout(4500)
                pg.locator(".bloque-torneo:visible").first.screenshot(
                    path=str(out / "bloque_torneo.png")
                )
                pg.locator(".tarjeta-tabla:has(table.ficha)").first.scroll_into_view_if_needed()
                pg.locator(".tarjeta-tabla:has(table.ficha)").first.screenshot(
                    path=str(out / "ficha_completa.png")
                )
                pg.locator("[class*=st-key-casino_torneo]").first.screenshot(
                    path=str(out / "casino_torneo.png")
                )
                pg.locator("[class*=st-key-casino_partido]").first.screenshot(
                    path=str(out / "casino_partido.png")
                )
                pg.locator("[role=tab]").nth(0).evaluate("e => e.click()")
                pg.wait_for_timeout(1500)
                pg.screenshot(path=str(out / "escritorio_0_antes.png"))
                pg.locator("[role=tab]").nth(1).evaluate("e => e.click()")
                pg.wait_for_timeout(1500)
            pg.screenshot(path=str(out / f"{nombre}_1_simulador.png"))
            for i, t in ((0, "antes"), (2, "creer")):
                pg.locator("[role=tab]").nth(i).evaluate("e => e.click()")
                pg.wait_for_timeout(3500)
                pg.screenshot(path=str(out / f"{nombre}_{'0' if i == 0 else '2'}_{t}.png"))
            if nombre == "escritorio":
                pg.locator("[role=tab]").nth(1).evaluate("e => e.click()")
                pg.wait_for_timeout(1000)
                tecnico_real(pg, out / "escritorio_tecnico_real.png", a.espera)
                modo_sin_limites(pg, out / "escritorio_sin_limites.png", a.espera)
            pg.close()
        gif(b, a.url, out / "ver_un_partido.gif", a.espera)
        b.close()
    print("capturas en", out)
    return 0


def gif(b, url: str, destino: Path, espera: int) -> None:
    """GIF de «Ver un partido» (marcador y presión de cada equipo minuto a minuto): cuadros de la pantalla con el protocolo de Chromium (CDP) y ffmpeg para armarlos (si no hay ffmpeg, se omite)."""
    import base64
    import shutil
    import subprocess
    import tempfile

    ff = shutil.which("ffmpeg")
    if ff is None:
        print("sin ffmpeg: no se hace el GIF")
        return
    pg = b.new_page(viewport={"width": 1440, "height": 2300})
    pg.goto(url, wait_until="networkidle")
    pg.wait_for_selector("[data-testid=stSlider]", timeout=90000)
    pg.locator("[role=tab]").nth(1).evaluate("e => e.click()")
    pg.get_by_role("button", name="Simular torneo").first.click(timeout=5000)
    listo(pg)
    caja = pg.locator("[class*=st-key-casino_partido]").first
    caja.scroll_into_view_if_needed()
    pg.get_by_role(
        "button", name="Jugar el partido"
    ).first.click()  # un primer partido, sin grabar, para que la caja tenga su altura completa
    pg.wait_for_timeout(5000)
    box = caja.bounding_box()
    cdp = pg.context.new_cdp_session(pg)
    cuadros: list[tuple[float, bytes]] = []

    def al_cuadro(ev):
        cuadros.append((ev["metadata"]["timestamp"], base64.b64decode(ev["data"])))
        cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

    cdp.on("Page.screencastFrame", al_cuadro)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 85, "everyNthFrame": 1})
    pg.get_by_role("button", name="Jugar el partido").first.click()
    pg.wait_for_timeout(5600)
    cdp.send("Page.stopScreencast")
    pg.close()
    if len(cuadros) < 5:
        print("pocos cuadros; no se hace el GIF")
        return
    with tempfile.TemporaryDirectory() as tmp:
        lista = []
        for i, (t, jpg) in enumerate(cuadros):
            (Path(tmp) / f"f_{i:04d}.jpg").write_bytes(jpg)
            dur = (cuadros[i + 1][0] - t) if i + 1 < len(cuadros) else 1.5
            lista.append(f"file 'f_{i:04d}.jpg'\nduration {max(dur, 0.02):.3f}")
        lista.append(f"file 'f_{len(cuadros) - 1:04d}.jpg'")
        (Path(tmp) / "lista.txt").write_text("\n".join(lista), encoding="utf-8")
        x, y, w, h = (
            int(v) for v in (box["x"], box["y"], box["width"], min(box["height"], 2300 - box["y"]))
        )
        filtro = f"crop={w}:{h}:{x}:{y},fps=12,scale=640:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse"
        subprocess.run(
            [
                ff,
                "-y",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(Path(tmp) / "lista.txt"),
                "-vf",
                filtro,
                "-loop",
                "0",
                str(destino),
            ],
            check=True,
        )
    print("GIF:", destino, f"{destino.stat().st_size / 1e6:.1f} MB ({len(cuadros)} cuadros)")


def tecnico_real(pg, destino: Path, espera: int) -> None:
    """Con un técnico real (el que dirige hoy al América) las perillas se ven bloqueadas."""
    pg.locator("[data-testid=stSelectbox]").first.click()
    pg.wait_for_timeout(500)
    pg.locator("[role=option]").nth(1).click()
    pg.wait_for_timeout(2500)
    pg.get_by_role("button", name="Simular torneo").first.click()
    listo(pg)
    pg.screenshot(path=str(destino))
    pg.locator(".exigencia").first.screenshot(
        path=str(destino.with_name("exigencia_a_la_altura.png"))
    )
    pg.locator(
        "[data-testid=stSelectbox]"
    ).first.click()  # 😬 un técnico real que se queda corto (el de peor P(top 4), si hay)
    pg.wait_for_timeout(500)
    opciones = pg.locator("[role=option]")
    idx = next((i for i in range(opciones.count()) if "Ambriz" in opciones.nth(i).inner_text()), 2)
    opciones.nth(idx).click()
    pg.wait_for_timeout(2500)
    pg.get_by_role("button", name="Simular torneo").first.click()
    listo(pg)
    pg.locator(".exigencia").first.screenshot(
        path=str(destino.with_name("exigencia_se_queda_corto.png"))
    )
    pg.locator("[data-testid=stSelectbox]").first.click()
    pg.wait_for_timeout(500)
    pg.locator("[role=option]").nth(0).click()
    pg.wait_for_timeout(2500)


def modo_sin_limites(pg, destino: Path, espera: int) -> None:
    pg.get_by_text("Modo sin límites").first.click()
    pg.wait_for_timeout(2500)
    for i in range(4):  # las cuatro perillas de eje al extremo −300: un estilo que nadie ha usado
        pg.locator("section[data-testid=stSidebar] input[type=range]").nth(i).focus()
        pg.keyboard.press("Home")
        pg.wait_for_timeout(300)
    pg.get_by_role("button", name="Simular torneo").first.click()
    listo(pg)
    pg.screenshot(path=str(destino))
    pg.locator(".exigencia").first.screenshot(
        path=str(destino.with_name("exigencia_no_da_el_ancho.png"))
    )


def progreso(pg, out: Path) -> None:
    """La barra de progreso a mitad de una simulación Alta (1,000,000 de torneos): se lanza, se espera unos segundos y se captura la barra lateral; luego se espera a que termine."""
    pg.get_by_text("Profunda", exact=True).first.click()
    pg.wait_for_timeout(1000)
    pg.get_by_role("button", name="Simular torneo").first.click()
    pg.wait_for_selector("[class*=sim-progreso]", timeout=60000)
    pg.wait_for_timeout(5000)
    pg.locator("section[data-testid=stSidebar]").screenshot(
        path=str(out / "progreso_simulacion.png")
    )
    listo(pg)
    pg.get_by_text("Rápida", exact=True).first.click()
    pg.wait_for_timeout(800)


if __name__ == "__main__":
    raise SystemExit(main())
