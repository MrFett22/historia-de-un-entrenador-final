# INVENTARIO (fase 0)

Fecha: 2026-10-09 · a partir del análisis inicial (commit 0363e00, ver D-001)

## Modo de datos decidido: **MODO_REAL_PIPELINE**
`python -m simdt.datos.inventario` (función `detectar`) encontró:

| qué | dónde | hallazgo |
|---|---|---|
| eventos StatsBomb crudos | `cache_events/events_<id>.json` | 1,769 partidos (4.7 GB) |
| 360 (frames) | `cache_events/frames_<id>.json` | 1,769 (no se usan en la v1) |
| partidos | `matches_{108,235,281,317,318,351}.json` | temporadas 2021/22 a 2026/27; técnico por partido en `managers` |
| calendario objetivo | `matches_351.json` | Apertura 2026: 153 partidos, 17 jornadas, 79 jugados y 74 programados |
| tablas derivadas (secuencias con r_sk, eras, saques) | — | **no existen** en este entorno |
| paquete `dtcoach` | `dtcoach_revision/dtcoach_revision_20260925_0951/` (no versionado) | revisión del 2026-09-25, commit 77b720b |

No hay parquet derivados → se corre un pipeline propio de solo lectura (`simdt.datos.repo`) que
reutiliza las definiciones de `dtcoach` (copiadas con `# Procedencia`) y escribe todo lo que es
nivel secuencia en `simulador/_cache/` (en `.gitignore`). A `artefactos/` solo suben agregados.

## Documentos del repo
El spec cita `04_MODELO`, `RESULTADOS_ALMADA` y `modelo_simulador.tex`: **no existen en este
entorno** (D-002). Están `docs/{00_ROADMAP,01_ARQUITECTURA,02_ESTADO,03_FRAMEWORK,06_DECISIONES,
10_RESULTADOS,11_HIPOTESIS}.md` de la revisión de dtcoach. Las ecuaciones de M1–M4, la intensidad y
la recursión se escribieron a partir de 04_ESPECIFICACION.md y quedan documentadas en
`reportes/MODELO.md`.

## Módulos reutilizables (inventario real)
| tema | archivo en dtcoach | uso en simdt |
|---|---|---|
| malla 5×4, zonas | `grid.py` (`StateSpace.zone_of`) | copiado a `datos/repo.py` |
| posesión → acciones → transiciones; absorción terminal; corte en secuencias (ADR-v2-14) | `possessions.py` | reimplementado sin polars en `datos/repo.py` (mismas reglas) + INTERRUPCIÓN |
| mezcla EM-MAP con escalera (ADR-v2-17) | `mezcla.py` (`_loglik_tipos`, `_m_step`, `_em`, `_partir`, `pooled`) | copiado a `estimacion/mezcla.py` |
| cadena absorbente N, B, E[T], visitas | `absorbing.py` (`Cadena`) | copiado a `modelos/cadena.py` |
| encogimiento Dirichlet | `estimate.py` (`shrink`) | copiado |
| logit fraccional con sandwich por partido | `pesos.py` (`ajustar_pesos`) | reimplementado (cuasi-verosimilitud Papke-Wooldridge) en `estimacion/celdas.py` |
| tipo de cambio (nivel de puesto) | `decisiones.py` (`nivel_puesto`) | copiado a `datos/repo.py` |
| Elo | `elo.py` (`correr_elo`) | reimplementado sin polars en `estimacion/liga.py` (K = 20, h = 60) |
| xPts Poisson-binomial | `simulador.py` | sustituido por la recursión exacta del marcador |
| proyección Maher, balón parado, Kalman | no están en esta revisión | — |

## Partidos por torneo (temporada regular + liguilla)
2021/22 a 2025/26: 10 torneos completos (≈ 153 de fase regular + 13–19 de liguilla cada uno);
2026/27: Apertura 2026 en curso (79 jugados). Total con eventos: 1,769.

## Entorno
Python 3.14.3 (≥ 3.10, se usa el del sistema), `venv` en `simulador/.venv` (uv no disponible),
dependencias fijadas en `pyproject.toml`. PyMC 6.3.2 con muestreador NUTS de numpyro (no hay g++
para compilar PyTensor; D-006). `make` no existe en Windows: el `Makefile` se acompaña de
`python -m simdt.tareas <objetivo>` con los mismos objetivos (D-007).
