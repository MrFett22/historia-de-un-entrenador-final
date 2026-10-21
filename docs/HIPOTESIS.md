# Hipótesis del simulador

Escribimos once hipótesis antes de construir el simulador. Algunas las pudimos contrastar con
los datos; las demás quedan como supuestos declarados.

| | hipótesis | cómo la revisamos | resultado |
|---|---|---|---|
| H1 | Los partidos son independientes entre sí (sin rachas ni cansancio). | Autocorrelación de lag 1 de los residuos (puntos − xPts) dentro de cada equipo y torneo, y regresión del residuo sobre la diferencia de días de descanso, con intervalos por bootstrap por equipo. | Se sostiene: autocorrelación −0.009 [−0.05, 0.03]; descanso −0.015 puntos por día [−0.029, 0.000]. |
| H2 | El ritmo de jugadas a lo largo del partido sigue el mismo perfil en todos los equipos. | Supuesto: el perfil por tramo de 15 minutos es el de la liga y cada equipo solo lo escala. | No contrastada. Los totales por partido se reproducen (error de xPts de +0.43 %). |
| H3 | El técnico cambia qué tipo de jugadas hace su equipo, no cómo se mueve el balón dentro de cada tipo. | Comparación, en el estudio, de las cadenas de cada tipo entre técnicos. | Razonable en ataque directo y en ataque elaborado; no concluyente en toque sin profundidad. |
| H4 | Técnico y plantel se suman, con una interacción aleatoria. | Modelo de efectos cruzados con $\sigma_{int}$ estimada para cada componente. | Se sostiene: la interacción se estima con su incertidumbre y entra en la ficha del América. |
| H5 | El efecto del técnico es inmediato, sin curva de adaptación. | Filtro de Kalman sobre el estilo alrededor de cada cambio de club, en el estudio. | Se sostiene: el estilo cambia de golpe al cambiar de club. |
| H6 | El plantel y el entorno no cambian durante el torneo (sin fichajes ni lesiones). | Supuesto declarado en la aplicación. | No contrastada. |
| H7 | La ventaja de local es la misma para todos los equipos. | Supuesto: un solo parámetro de localía en el ritmo, en la mezcla y en el balón parado. | No contrastada. |
| H8 | El Elo de los rivales queda fijo al inicio del torneo. | Supuesto: Elo (K = 20, h = 60) calculado con partidos anteriores al torneo. | No contrastada; es coherente con el corte sin fuga del torneo objetivo. |
| H9 | En balón parado, el técnico solo influye en la prevención (que el rival remate); la calidad del remate y el portero son los de la liga. | Contracción normal–normal de la variación entre equipos en cada capa, en el estudio. | Se sostiene: la prevención varía entre equipos (τ² = 3·10⁻⁴); la calidad del remate y el portero no (τ² ≈ 0). |
| H10 | Las expulsiones y otros eventos raros quedan implícitos en las tasas. | Supuesto: no los modelamos por separado. | No contrastada; los goles simulados se parecen a los de la liga (χ², p = 0.91). |
| H11 | Las sustituciones solo son descriptivas y no mueven el resultado. | Diferencias en diferencias del xG antes y después de cada sustitución, con datos 360, en el estudio. | Se sostiene: el efecto es nulo. En la aplicación, los cambios solo modifican el estilo. |

Las hipótesis del estudio sobre Almada siguen otra numeración (H1–H26) y están en
`estudio/docs/11_HIPOTESIS.md`, con su fecha de registro y sus enmiendas.
