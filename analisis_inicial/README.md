# Historia de un Entrenador — Reto Oficial 2026, Club América

Análisis del estilo de juego de **Guillermo Almada en Pachuca** (2021/22–2024/25)
usando eventos + 360 de StatsBomb, para el Hackathon ISAC 2026.

El repo sigue el **roadmap matemático** acordado con el equipo: framework
(reto 5.6), cadena de Markov absorbente (M0), contexto (M1), memoria (M2), y
las extensiones de defensa, jugadores y balón parado descritas ahí. El
documento vivo del proyecto (framework, decisiones de diseño, bitácora) se
sube conforme se va escribiendo — empieza con la Semana 1 del roadmap.

## Setup

1. Clona el repo e instala dependencias:

   ```bash
   pip install -r requirements.txt
   ```

2. Copia `.env.example` a `.env` y pon las credenciales de StatsBomb que nos
   compartieron para la competencia (pídanlas en el grupo si no las tienen):

   ```bash
   cp .env.example .env
   ```

3. Los datos de StatsBomb **no están en este repo** — su uso es exclusivo
   para la competencia. Cada quien los descarga y regenera localmente
   corriendo los scripts de `scripts/`. Cachean lo descargado en
   `cache_events/` (ignorado por git) para no volver a pedirlo a la API.

## Reglas del repo

- Nunca subir `.env` ni nada dentro de `cache_events/` — son credenciales y
  datos de uso exclusivo para la competencia.
- Solo se sube el trabajo que sigue el roadmap acordado, en el orden de sus
  4 semanas — no exploración suelta ni experimentos descartados.
- Cada decisión de diseño (supuestos, umbrales, qué se descarta y por qué)
  se documenta en el framework/bitácora del repo, no solo en el código.
