"""Revisa y normaliza caracteres invisibles o no estándar en los archivos de texto del repo.

    python docs/herramientas/normalizar_unicode.py --revisar        # lista archivo:línea:col y carácter
    python docs/herramientas/normalizar_unicode.py --aplicar        # corrige y reporta lo corregido

Qué busca (en .py .md .sh .toml .yaml .yml .json .css):
  - espacios de ancho cero U+200B–U+200D y U+2060; U+FEFF fuera del inicio del archivo;
  - marcas de dirección U+200E, U+200F, U+202A–U+202E;
  - caracteres de control (C0 salvo tabulador, salto de línea y retorno; DEL; C1);
  - espacios no separables U+00A0 y U+202F, SOLO en archivos de código (no en .md).
El español con acentos, comillas «», guiones largos, etc. es válido y no se toca.
Excepción: U+200D (unidor) entre dos emoji es parte del emoji (p. ej. 🧑‍🍳) y no se toca;
Corrección: los invisibles se quitan; los espacios no separables pasan a espacio ASCII.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

EXTENSIONES = {".py", ".md", ".sh", ".toml", ".yaml", ".yml", ".json", ".css"}
CODIGO = EXTENSIONES - {".md"}
EXCLUIR_DIRS = {".git", ".venv", "_cache", "__pycache__", "node_modules", ".pytest_cache"}
ANCHO_CERO = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF}
DIRECCION = {0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E}
NO_SEPARABLES = {0x00A0, 0x202F}


def clasificar(cp: int, es_codigo: bool, inicio: bool) -> str | None:
    if cp == 0xFEFF and inicio:
        return None
    if cp in ANCHO_CERO:
        return "ancho cero"
    if cp in DIRECCION:
        return "marca de dirección"
    if cp in NO_SEPARABLES:
        return "espacio no separable" if es_codigo else None
    if (cp < 0x20 and cp not in (0x09, 0x0A, 0x0D)) or cp == 0x7F or 0x80 <= cp <= 0x9F:
        return "control"
    return None


def archivos(raiz: Path):
    for p in sorted(raiz.rglob("*")):
        if (
            p.is_file()
            and p.suffix.lower() in EXTENSIONES
            and not (set(p.relative_to(raiz).parts) & EXCLUIR_DIRS)
        ):
            yield p


def _emoji(ch: str) -> bool:
    return ord(ch) >= 0x1F000 or unicodedata.category(ch) == "So"


def revisar_archivo(p: Path):
    texto = p.read_text(encoding="utf-8", errors="surrogateescape")
    es_codigo = p.suffix.lower() in CODIGO
    hallazgos, salida = [], []
    linea, col = 1, 0
    for i, ch in enumerate(texto):
        col += 1
        tipo = clasificar(ord(ch), es_codigo, i == 0)
        if (
            tipo
            and ord(ch) == 0x200D
            and 0 < i < len(texto) - 1
            and _emoji(texto[i - 1])
            and _emoji(texto[i + 1])
        ):
            tipo = None  # unidor dentro de un emoji compuesto
        if tipo:
            hallazgos.append((linea, col, f"U+{ord(ch):04X}", unicodedata.name(ch, "?"), tipo))
            if tipo == "espacio no separable":
                salida.append(" ")
        else:
            salida.append(ch)
        if ch == "\n":
            linea, col = linea + 1, 0
    return hallazgos, "".join(salida)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--revisar", action="store_true")
    g.add_argument("--aplicar", action="store_true")
    ap.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args(argv)
    total, por_tipo, tocados = 0, {}, 0
    for p in archivos(a.raiz):
        hallazgos, nuevo = revisar_archivo(p)
        if not hallazgos:
            continue
        rel = p.relative_to(a.raiz).as_posix()
        for ln, c, cod, nombre, tipo in hallazgos:
            print(f"{rel}:{ln}:{c}\t{cod}\t{nombre}\t({tipo})")
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        total += len(hallazgos)
        if a.aplicar:
            p.write_text(nuevo, encoding="utf-8", errors="surrogateescape", newline="")
            tocados += 1
    if a.aplicar:
        print(f"\nTotal: {total} caracteres corregidos en {tocados} archivos")
    else:
        print(f"\nTotal: {total} caracteres")
    for t, n in sorted(por_tipo.items()):
        print(f"  {t}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
