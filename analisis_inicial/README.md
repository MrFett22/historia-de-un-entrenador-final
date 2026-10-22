# `analisis_inicial/` — Primer análisis de Guillermo Almada

Esta carpeta es parte del repositorio [Historia de un entrenador](../) y guarda el **primer
análisis** del estilo de juego de **Guillermo Almada en Pachuca** (2021/22–2024/25) con eventos y
tracking 360 de StatsBomb. De aquí partió el estudio completo de la liga que vive en
[`../estudio/`](../estudio/).

- **El informe:** [`REPORTE_FINAL.md`](REPORTE_FINAL.md) reúne los resultados de esta primera etapa.
- **El marco de trabajo:** [`FRAMEWORK.md`](FRAMEWORK.md) describe el roadmap matemático que
  seguimos: framework, cadena de Markov absorbente (M0), contexto (M1), memoria (M2), y las
  extensiones de defensa, jugadores y balón parado.
- **Las figuras** (PPDA, transición defensiva, organización defensiva con 360, roles con NMF,
  evolución del estilo con Kalman) están en los `.png` de esta carpeta.

## Cómo correrlo

```bash
pip install -r requirements.txt
cp .env.example .env     # pon las credenciales de StatsBomb de la competencia
```

Los datos de StatsBomb **no están en el repositorio**: su uso es exclusivo para la competencia
(ver [`../AVISO_DATOS.md`](../AVISO_DATOS.md)). Los scripts de [`scripts/`](scripts/) los descargan
y los regeneran localmente, y cachean lo descargado en `cache_events/` (ignorado por git). Nunca
se suben `.env` ni `cache_events/`: son credenciales y datos de uso exclusivo para la competencia.
