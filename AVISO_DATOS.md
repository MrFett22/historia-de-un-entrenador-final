# Aviso sobre los datos

Este proyecto usa eventos y tracking 360 de StatsBomb de la Liga MX (2021–2026). Esos datos
fueron provistos para el Hackathon ISAC 2026 y son de uso exclusivo para la competencia.

- No se incluyen en este repositorio: ni eventos (`events_*.json`), ni tracking
  (`frames_*.json`), ni partidos (`matches_*.json`), ni derivados por evento o por secuencia.
- No quedan cubiertos por la licencia MIT del repositorio (`LICENSE`), que aplica solo al
  código y a la documentación.
- El repositorio sí incluye parámetros agregados por liga, equipo y técnico
  (`simulador/artefactos/`), estimados a partir de esos datos. Con ellos la aplicación funciona
  sin acceso a los datos originales.

Quien quiera reproducir el análisis necesita su propio acceso a los datos de StatsBomb.
