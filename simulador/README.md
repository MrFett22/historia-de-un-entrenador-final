# `simulador/` — Simulador de técnico · Club América

Responde: *si el América tuviera a este técnico, con su plantel actual y los demás equipos sin
cambios, ¿cómo jugaría y cuántos puntos haría en el Apertura 2026?* Sirve para técnicos reales
(con al menos 30 partidos en la Liga MX desde 2021) y para técnicos inventados.

Esta carpeta es parte del repositorio [Historia de un entrenador](../) y contiene todo el código
del simulador y de su aplicación web. Para instalar y correr el proyecto completo de una vez,
parte del [README principal](../README.md); esta página documenta el simulador por dentro.

## 1. Instalar

Requiere Python 3.10 o más nuevo (se construyó con 3.14). Si ya instalaste el proyecto desde la
raíz, el simulador ya quedó instalado. Para trabajar solo con esta carpeta:

```bash
cd simulador
python -m venv .venv
.venv/Scripts/python -m pip install -e .        # Windows
# .venv/bin/python -m pip install -e .          # macOS / Linux (Arch: python -m venv .venv && .venv/bin/python -m pip install -e .)
```

Con `make`: `make instalar`. Sin `make` (Windows): cada objetivo existe como
`python -m simdt.tareas <objetivo>`.

## 2. Abrir la app

```bash
.venv/Scripts/python -m streamlit run app.py
```

Los parámetros ya calibrados con los datos reales están en `artefactos/`, así que la app abre
sin datos de StatsBomb. "Simular torneo" en modo rápido tarda unos segundos.

## 3. Calibrar con datos reales

Los datos de StatsBomb no se suben al repositorio (ver [`../AVISO_DATOS.md`](../AVISO_DATOS.md)).
`--datos` recibe la carpeta raíz de los datos; dentro de ella se buscan los eventos en
`analisis_inicial/cache_events/events_<id>.json` y los partidos en
`analisis_inicial/matches_*.json` (claves `eventos_dir` y `partidos_glob` de
`config/simulador.yaml`). Desde `simulador/`, con los datos dentro de este repositorio:

```bash
.venv/Scripts/python -m simdt.calibrar --datos .. --salida _cache/artefactos_nuevo
```

**Cuidado:** `calibrar` sin `--salida` **sobrescribe `artefactos/`**, que es lo que usa la app publicada. Usa siempre `--salida`.

Opciones: `--vocab-dtcoach <carpeta>` toma el vocabulario K = 3 de la fuente (`mezcla_K3.npz`) en vez de reajustarlo (D-048). Por omisión se aplica un corte por fecha: solo se usan partidos anteriores al inicio del torneo objetivo (D-050). La atribución del técnico es continua (D-051).

Hace todo: corta las posesiones en secuencias, ajusta los tres tipos de jugada, estima la liga,
separa técnico y plantel (fase A, unos 10 minutos) y escribe `artefactos/`. Lo que es nivel
secuencia queda en `simulador/_cache/` (ignorado por git).

`--datos` también acepta una carpeta con las tablas ya agregadas en parquet (`partidos`, `juego`,
`exposicion`, `saques`, `cambios`, `panel`; columnas en `src/simdt/datos/esquema.py`). Para
probar ese camino sin datos reales:

```bash
.venv/Scripts/python -m simdt.calibrar --exportar-sintetico _cache/tablas_demo
.venv/Scripts/python -m simdt.calibrar --datos _cache/tablas_demo --salida _cache/artefactos_demo
```

## 4. Todo de una vez

```bash
.venv/Scripts/python -m simdt.correr_todo --modo sintetico   # datos de demostración
.venv/Scripts/python -m simdt.correr_todo --modo real        # datos reales
```

Para abrir la app con los artefactos de demostración:
`SIMDT_ARTEFACTOS=_cache/artefactos_sintetico streamlit run app.py` (la app muestra
"Datos de demostración").

## 5. Validar y probar

```bash
.venv/Scripts/python -m simdt.validacion.reporte    # escribe reportes/validacion/
.venv/Scripts/python -m pytest -q                   # todas las pruebas (las "lento" tardan ~5 min)
.venv/Scripts/python -m pytest -q -m "not lento"
```

## 6. Abrir la app con un solo comando

Desde la raíz del repositorio:

```bash
bash simulador/correr_app.sh              # macOS / Linux / Git Bash
```

```powershell
.\simulador\correr_app.ps1                # Windows PowerShell
```

Usan el Python de `SIMDT_PYTHON` si está definido o, si no, el entorno `simulador/.venv` o
`.venv` en la raíz (si no hay ninguno, dicen cómo crearlo). Abren la app con
`simulador/artefactos/` en http://localhost:8501 (otro puerto con `PUERTO`) y no publican nada. La versión pública está en
https://simulador-america.streamlit.app. Para desplegar una copia propia en Streamlit Community
Cloud, el archivo principal es `simulador/app.py` con Python 3.12; las dependencias salen de
`simulador/requirements.txt` y el tema, de `.streamlit/config.toml` en la raíz del repositorio.

## 7. Qué muestra la app

- **Tres pestañas:** «👀 Antes de jugar» (qué pesa más: suerte, jugadores y técnico en la misma
  escala; los tres tipos de jugada y una sección por perilla), «🎮 Simulador» y «🔍 ¿Le podemos
  creer?» (las ocho pruebas, cada una con su nombre clásico, H0, H1 y qué resultado queremos).
- **Técnicos:** arriba «🧑‍🍳 Crea tu propio técnico»; debajo, solo técnicos reales, con sus
  perillas fijas. La carta del técnico trae la calificación con su seguridad (baja, media o
  alta) y el cambio en puntos.
- **Precisión:** «Rápida» = 10,000 torneos (100 versiones de los equipos × 100) y «Profunda» =
  1,000,000 (1,000 × 1,000). Se simula por bloques en segundo plano, con avance real y
  «Cancelar»; el resultado es el mismo con cualquier tamaño de bloque.
- **Ficha completa:** «Tu técnico», «América hoy» y «Cambio»; ▲ amarillo / ▼ rojo solo en los
  cambios significativos (`ficha_cambio` del config) y «≈ igual» en lo demás.
- **Qué torneo se simula:** el Apertura 2026 completo con su calendario real; el plantel se
  estima con partidos hasta el torneo anterior. Todo sale de `artefactos/meta.json`.
- **«⚽ Ver un partido»:** se sortea jugada por jugada con las piezas del motor, y los goles
  siguen exactamente la misma ley que el cálculo exacto (prueba 8). Muestra la presión de cada
  equipo por minuto y las estadísticas del partido.
- **Paleta del América** con una sola fuente en el config (`paleta`) y una prueba de contraste y
  daltonismo; letra de 18 px (17 en el celular, nada menor de 15 px).

Herramientas de análisis en `herramientas/` (no son parte de la app):
`variacion_graficas.py` (D-090: qué gráficas cambian entre técnicos) y `diagnostico_presion.py`
(D-093: la presión por minuto) repiten sus mediciones con `artefactos/`; `prior_ftheta.py` y
`prior_vs_posterior.py` muestran por qué la regla de atribución original era inalcanzable bajo
el prior (D-051); `medir_servicio.py` mide los tiempos del servicio; `capturar_v11.py` y
`lamina_paleta.py` generan las capturas de `capturas/v11/`.

## Relación con el estudio

Este simulador sale del estudio de [`../estudio/`](../estudio/) y toma de él: el vocabulario de
jugadas de `dtcoach` (los tres tipos de jugada y la cadena de la fuente), las definiciones de
PPDA, de recuperación en 10 s y de línea y compacidad con los cuadros 360 (lo que alimenta la
tarjeta «Lo que dicen los datos de su equipo» y la decisión de si la perilla de defensa se llama
«presión»).

## Qué leer

- [`../docs/VALIDACION.md`](../docs/VALIDACION.md): las ocho pruebas y las limitaciones.
- `reportes/MODELO.md`: las ecuaciones que implementa el código.
- `reportes/DECISIONES.md`: cada decisión y por qué.
- `reportes/validacion/`: fase A, calibración, retroprueba, sensibilidad.

## Cómo leer el resultado

El simulador explora estilos; no predice el futuro. Con los datos de 2021–2026, casi todo lo que
distingue a un equipo es de su plantel; lo que mueve el técnico son pocas cosas (qué tanto deja
rematar al rival tras ataques directos y cuándo hace sus cambios). Por eso muchas comparaciones
salen "prácticamente igual": eso también es una respuesta.
