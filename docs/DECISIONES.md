# Decisiones que cambiaron los resultados

Aquí reunimos solo las decisiones que movieron algún número. La bitácora completa, con 99
decisiones, sus alternativas y sus fuentes, está en
[`simulador/reportes/DECISIONES.md`](../simulador/reportes/DECISIONES.md).

| | decisión | efecto en los resultados |
|---|---|---|
| D-048, D-049 | Tomamos el vocabulario de jugadas del estudio en lugar de reajustar una mezcla propia en el simulador. La diferencia que veíamos venía de un óptimo local del EM causado por la semilla y de la falta del primer paso $P^0$. | Los tres tipos de jugada vuelven a ser los del estudio, con 100 % de pareo entre secuencias. |
| D-050 | Cortamos los datos sin fuga: la estimación de técnico y plantel, los parámetros de la liga y la mezcla solo usan partidos anteriores al inicio del Apertura 2026. | Los parámetros anteriores incluían entre 66 y 88 partidos del torneo objetivo. Al quitarlos desapareció la ventaja aparente al predecir cambios de técnico. |
| D-051 | Adoptamos atribución continua: el técnico mueve todas las componentes con su posterior encogida, en lugar de una regla de todo o nada por componente. | Con la regla original, inalcanzable bajo el prior, el técnico no movía ninguna de las 32 componentes. Con la continua, Almada frente a cinco técnicos reales da diferencias de −1.8 a +1.8 puntos. |
| D-054, D-059 | Publicamos la calibración E y no la F. F mejoraba el error de xPts, pero bajaba la recuperación de estilos de 93 % a 40 % y empeoraba el RPS y la retroprueba. | La aplicación usa E y se presenta como descriptiva (Diebold-Mariano, p = 0.195). |
| D-074 | Medimos suerte, jugadores y técnico en la misma escala: cuánto varían típicamente los puntos de un equipo en un torneo (desviación estándar). | Antes se mezclaban escalas (la suerte como la mitad del rango del 80 %, ±7). Ahora: suerte ±5.3, jugadores ±5.75 y técnico ±0.6. |
