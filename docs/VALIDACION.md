# Validación del simulador

Sometimos el simulador a ocho pruebas, las mismas que muestra la pestaña de validación de la
aplicación. Usamos los parámetros publicados, estimados con 1,701 partidos anteriores al
Apertura 2026. Cada número se recalcula con `python docs/herramientas/numeros_control.py`; el
detalle técnico está en `simulador/reportes/validacion/VALIDACION.md`.

| # | prueba | H0 | H1 | estadístico | resultado |
|---|---|---|---|---|---|
| 1 | Goles por partido | Lo simulado y lo real tienen la misma distribución. | Son distintas. | χ² de bondad de ajuste, 5 gl, 3,402 equipo-partido. | No se rechaza H0: χ² = 1.49, p = 0.91. |
| 2 | Puntos por equipo y torneo | La pendiente entre puntos reales y simulados es 1. | La pendiente no es 1. | Regresión de los puntos reales sobre los simulados (180 equipo-torneo) y error total de xPts. | Se rechaza H0: pendiente 1.50 (R² = 0.53). El simulador acorta las diferencias entre equipos, aunque el total de la liga cuadra (xPts +0.43 %). |
| 3 | Calibración de probabilidades | Lo predicho coincide con lo observado. | No coincide. | Prueba tipo Hosmer-Lemeshow por bandas para ganar, empatar y perder. | Se rechaza H0 en alguna banda (p mínima 1.9·10⁻¹⁰). |
| 4 | Independencia entre partidos | ρ = 0: no hay rachas. | ρ ≠ 0. | Autocorrelación de lag 1 de los residuos (3,222 pares) y pendiente por día de descanso. | No se rechaza H0: ρ = −0.009 [−0.05, 0.03]; descanso −0.015 [−0.029, 0.000]. |
| 5 | Placebo | El efecto es 0 cuando barajamos a los técnicos. | El efecto no es 0. | Etiquetas de técnico barajadas entre celdas; intervalo del 95 % de la diferencia de puntos. | No se rechaza H0: 3 de 3 intervalos contienen el 0 (32 componentes). |
| 6 | Recuperación de estilos | Lo simulado cae en el rango observado. | No cae. | Pares técnico-club con al menos 50 partidos; bootstrap por partido; mínimo exigido, 85 %. | Se cumple: 14 de 15 pares (93 %). |
| 7 | Retroprueba con cambios de técnico | El simulador acierta igual que suponer que todo sigue igual. | El simulador acierta mejor. | Diebold-Mariano con la corrección de Harvey, Leybourne y Newbold; 35 llegadas de técnico, sin usar información futura. | No se rechaza H0: error medio 0.371 contra 0.381, DM = 0.87, p = 0.195. |
| 8 | Partidos sorteados jugada por jugada | El sorteo sigue la distribución exacta del modelo. | No la sigue. | χ² de marcadores en 5,000 partidos sorteados, 24 gl. | No se rechaza H0: χ² = 23.2, p = 0.51. |

## Limitaciones

El simulador describe estilos, pero no predice. Ante cambios de técnico reales no acierta
mejor que la inercia, y así lo dice la aplicación.

El simulador acorta las diferencias entre equipos: los puntos reales se separan 1.52 veces más
que los simulados (IC 95 % [1.23, 1.70]). Los equipos fuertes obtienen más puntos, y los
débiles menos, de los que el simulador les asigna. Corregirlo exige recalibrar la dispersión de
las fichas.

El RPS no mejora al modelo de referencia (Poisson con ataque y defensa del mismo torneo):
0.2119 contra 0.2038. Ese modelo usa el xG de los propios partidos que predice, una ventaja que
solo existe dentro de la muestra. Frente a las frecuencias base sí mejora (0.2119 contra
0.2256).

El técnico pesa poco frente al azar y al plantel (±0.6 puntos por torneo contra ±5.3 y ±5.75).
Por eso la mayoría de las comparaciones entre técnicos reales resultan prácticamente iguales.

El simulador no modela jugadores, lesiones, expulsiones, arbitraje, otros torneos ni el
vestidor. Simula el torneo completo desde la primera jornada, sin condicionar en los partidos
ya jugados.

Las pruebas 1 a 6 y la 8 son dentro de la muestra. La retroprueba usa ajustes que solo ven el
pasado. No hay todavía una prueba sobre un torneo que no se haya jugado.
