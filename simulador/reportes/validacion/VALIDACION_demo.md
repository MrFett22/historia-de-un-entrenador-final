# Validación (MODO_SINTETICO)

## Calibración (dentro de muestra, fichas de la celda de cada partido)
- Partidos: 918
- RPS motor 0.2167 · frecuencias base 0.2348 · simulador vigente (Poisson + log5) 0.2173
- Diferencia motor − base (IC 95 % bootstrap): [-0.0252, -0.0109]
- Diferencia motor − vigente (IC 95 %): [-0.0043, 0.0032]
- Puntos reales 2534 · xPts del motor 2532.4 · error -0.06 % (tolerancia 0.5 %)
- Goles reales 2638 · esperados 2670.4; empates reales 0.240 · motor 0.241
- Cumple RPS: True · cumple xPts: True

## H1: independencia entre partidos
- Autocorrelación lag 1 de (puntos − xPts) dentro de equipo-torneo: -0.0077 (IC 95 % [-0.0609, 0.0415], n = 1728)
- Pendiente sobre la diferencia de días de descanso: 0.0000 puntos por día (IC 95 % [0.0000, 0.0000], n = 1818)

## Recuperación (técnicos con ≥ 50 partidos en un club)
- Pares: 15 · mezcla simulada dentro del rango observado (95 %): 100 %

| tecnico | club | partidos | simulada | observada | dentro |
|---|---|---|---|---|---|
| Técnico 01 | América | 68 | [0.4838, 0.2146, 0.3016] | [0.4944, 0.2115, 0.2941] | True |
| Técnico 02 | Club 02 | 102 | [0.4406, 0.2576, 0.3017] | [0.4418, 0.2617, 0.2965] | True |
| Técnico 03 | Club 03 | 68 | [0.3533, 0.2276, 0.4191] | [0.3434, 0.2361, 0.4205] | True |
| Técnico 04 | Club 04 | 76 | [0.28, 0.1888, 0.5312] | [0.2788, 0.1879, 0.5333] | True |
| Técnico 10 | Club 16 | 68 | [0.4908, 0.2238, 0.2854] | [0.4957, 0.2249, 0.2794] | True |
| Técnico 11 | Club 06 | 51 | [0.4328, 0.2528, 0.3144] | [0.4429, 0.2526, 0.3044] | True |
| Técnico 12 | Club 12 | 85 | [0.4117, 0.2242, 0.364] | [0.4043, 0.2271, 0.3686] | True |
| Técnico 13 | Club 13 | 59 | [0.4206, 0.246, 0.3334] | [0.4099, 0.2488, 0.3413] | True |
| Técnico 15 | Club 14 | 51 | [0.355, 0.2128, 0.4322] | [0.3532, 0.2071, 0.4396] | True |
| Técnico 15 | Club 15 | 51 | [0.417, 0.2158, 0.3672] | [0.4148, 0.218, 0.3673] | True |
| Técnico 16 | Club 10 | 51 | [0.4203, 0.2289, 0.3508] | [0.4279, 0.2362, 0.3358] | True |
| Técnico 17 | Club 17 | 102 | [0.3632, 0.2194, 0.4174] | [0.3534, 0.2197, 0.4269] | True |
| Técnico 18 | Club 18 | 68 | [0.4087, 0.2346, 0.3567] | [0.4017, 0.235, 0.3634] | True |
| Técnico 27 | Club 09 | 51 | [0.3679, 0.2205, 0.4116] | [0.3682, 0.2188, 0.413] | True |
| Técnico 29 | Club 11 | 68 | [0.4054, 0.2481, 0.3465] | [0.4005, 0.2474, 0.3521] | True |

## Sobol (Saltelli, N = 1024, 11264 evaluaciones; salida = puntos esperados del América)
- Puntos esperados en el muestreo: media 30.33, DE 1.35, rango [25.50, 33.67]
| perilla | S1 | S1_ic | ST | ST_ic |
|---|---|---|---|---|
| rival_elaborada | 0.6976 | 0.0601 | 0.7330 | 0.0569 |
| rival_directa | 0.1225 | 0.0328 | 0.1580 | 0.0192 |
| mezcla_directa | 0.1187 | 0.0277 | 0.1229 | 0.0137 |
| mezcla_elaborada | 0.0209 | 0.0146 | 0.0273 | 0.0037 |
| reaccion_marcador | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| reaccion_rival | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| balon_parado | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| cambios_momento | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| cambios_tipo | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
- Perillas marcadas "solo cambia el estilo, no los puntos" (S_T + IC < 0.05): ['balon_parado', 'cambios_momento', 'cambios_tipo', 'reaccion_marcador', 'reaccion_rival']

## Placebo (etiquetas de técnico barajadas entre celdas)
- Componentes reajustadas: ['int_at[Directa]', 'int_co[Ataque elaborado]', 'l_co', 'alpha', 'gamma']
| placebo | celdas | media | int95 | contiene_cero | veredicto |
|---|---|---|---|---|---|
| Técnico 01 | 6 | -0.0634 | [-0.46601238936384587, 0.23835492564981137] | True | igual |
| Técnico 02 | 6 | 0.0668 | [-0.24479747932295248, 0.7279110681650636] | True | igual |
| Técnico 06 | 6 | 0.1175 | [-0.3070836924542746, 0.5886595809483417] | True | igual |
- Todos los intervalos del 95 % contienen el 0: True

## Rendimiento
- Un partido (en lote): 2.493 ms · una réplica: 34.5 ms
- Torneo rápido: 3.72 s · preciso: 205.19 s · arranque del servicio: 0.12 s
- c_R = 33.99 ms, c_S = 46.4 µs; σ_b² = 0.0081, σ_w² = 0.1368 (P de liguilla) → S* = 111
