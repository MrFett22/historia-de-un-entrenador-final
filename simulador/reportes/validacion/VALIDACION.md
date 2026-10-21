# Validación (MODO_REAL_PIPELINE)

## Calibración (dentro de muestra, fichas de la celda de cada partido)
- Partidos: 1701
- RPS motor 0.2119 · frecuencias base 0.2256 · simulador vigente (Poisson + log5) 0.2038
- Diferencia motor − base (IC 95 % bootstrap): [-0.0185, -0.0091]
- Diferencia motor − vigente (IC 95 %): [0.0049, 0.0115]
- Puntos reales 4651 · xPts del motor 4670.9 · error 0.43 % (tolerancia 0.5 %)
- Goles reales 4659 · esperados 4618.7; empates reales 0.266 · motor 0.254
- Cumple RPS: False · cumple xPts: True

## H1: independencia entre partidos
- Autocorrelación lag 1 de (puntos − xPts) dentro de equipo-torneo: -0.0090 (IC 95 % [-0.0500, 0.0303], n = 3222)
- Pendiente sobre la diferencia de días de descanso: -0.0146 puntos por día (IC 95 % [-0.0291, 0.0004], n = 3384)

## Recuperación (técnicos con ≥ 50 partidos en un club)
- Pares: 15 · mezcla simulada dentro del rango observado (95 %): 93 %

| tecnico | club | partidos | simulada | observada | dentro |
|---|---|---|---|---|---|
| Andre Jardine | América | 129 | [0.3284, 0.2636, 0.4079] | [0.3195, 0.2638, 0.4166] | True |
| Andre Jardine | Atlético San Luis | 54 | [0.3676, 0.2787, 0.3537] | [0.3765, 0.2738, 0.3497] | True |
| Andres Luciano Lillini | Pumas UNAM | 57 | [0.3562, 0.2829, 0.3609] | [0.3481, 0.2781, 0.3739] | True |
| Antonio Ricardo Mohamed Matijevich | Toluca | 65 | [0.3267, 0.2694, 0.4039] | [0.3286, 0.2716, 0.3998] | True |
| Diego Martin Cocca Pera | Atlas | 95 | [0.3511, 0.2961, 0.3529] | [0.3443, 0.2938, 0.3619] | True |
| Efrain Valdez | Pumas UNAM | 50 | [0.3437, 0.27, 0.3863] | [0.3443, 0.2658, 0.3899] | True |
| Fernando Ortiz | América | 55 | [0.3369, 0.2589, 0.4041] | [0.3343, 0.2493, 0.4165] | True |
| Guido Hernan Pizarro Demestri | Tigres UANL | 52 | [0.32, 0.265, 0.415] | [0.3216, 0.2674, 0.411] | True |
| Jorge Guillermo Almada Alves | Pachuca | 139 | [0.3473, 0.2728, 0.38] | [0.3471, 0.2713, 0.3816] | True |
| Marcos Ignacio Ambriz Espinoza | Toluca | 73 | [0.3248, 0.2923, 0.3829] | [0.3138, 0.2918, 0.3943] | True |
| Mauro Nestor Gerk Larrea | Querétaro | 86 | [0.3734, 0.2928, 0.3338] | [0.3664, 0.2921, 0.3416] | True |
| Miguel Ernesto Herrera Aguirre | Tigres UANL | 62 | [0.3323, 0.2781, 0.3895] | [0.3211, 0.2724, 0.4065] | False |
| Nicolas Ricardo Larcamon | Puebla | 60 | [0.3674, 0.2946, 0.338] | [0.3635, 0.2894, 0.3471] | True |
| Robert Dante Siboldi Badiola | Tigres UANL | 51 | [0.3308, 0.2728, 0.3964] | [0.3305, 0.2766, 0.3929] | True |
| Victor Manuel Vucetich Rojas | Monterrey | 54 | [0.3463, 0.2753, 0.3784] | [0.3509, 0.2774, 0.3718] | True |

## Sobol (Saltelli, N = 1024, 11264 evaluaciones; salida = puntos esperados del América)
- Puntos esperados en el muestreo: media 25.85, DE 0.17, rango [25.36, 26.35]
| perilla | S1 | S1_ic | ST | ST_ic |
|---|---|---|---|---|
| balon_parado | 0.6040 | 0.0594 | 0.6094 | 0.0481 |
| rival_elaborada | 0.1623 | 0.0350 | 0.1849 | 0.0170 |
| mezcla_elaborada | 0.0672 | 0.0227 | 0.0875 | 0.0087 |
| rival_directa | 0.0564 | 0.0220 | 0.0780 | 0.0084 |
| mezcla_directa | 0.0375 | 0.0207 | 0.0523 | 0.0058 |
| reaccion_rival | 0.0228 | 0.0137 | 0.0283 | 0.0026 |
| reaccion_marcador | 0.0021 | 0.0037 | 0.0018 | 0.0002 |
| cambios_momento | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| cambios_tipo | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
- Perillas marcadas "solo cambia el estilo, no los puntos" (S_T + IC < 0.05): ['cambios_momento', 'cambios_tipo', 'reaccion_marcador', 'reaccion_rival']

## Placebo (etiquetas de técnico barajadas entre celdas)
- Componentes reajustadas: ['int_at[Directa]', 'int_at[Ataque elaborado]', 'int_co[Directa]', 'int_co[Ataque elaborado]', 's_marcador', 's_rival', 'l_at', 'l_co', 'u_at[Directa]', 'u_at[Circulación estéril]', 'u_at[Ataque elaborado]', 'u_co[Directa]', 'u_co[Circulación estéril]', 'u_co[Ataque elaborado]', 'w_at[Directa]', 'w_at[Circulación estéril]', 'w_at[Ataque elaborado]', 'w_co[Directa]', 'w_co[Circulación estéril]', 'w_co[Ataque elaborado]', 'rho[corner]', 'rho[tiro_libre_area]', 'rho[lateral_largo]', 'rho[tiro_libre_directo]', 'nu_at[corner]', 'nu_at[tiro_libre_area]', 'nu_at[lateral_largo]', 'nu_co[corner]', 'nu_co[tiro_libre_area]', 'nu_co[lateral_largo]', 'alpha', 'gamma']
| placebo | celdas | media | int95 | contiene_cero | veredicto |
|---|---|---|---|---|---|
| Andre Jardine | 9 | 0.1141 | [-0.740728505821572, 0.9514895230883621] | True | igual |
| Nicolas Ricardo Larcamon | 8 | 0.1089 | [-0.5924875754939917, 0.7942119497394032] | True | igual |
| Jorge Guillermo Almada Alves | 8 | 0.1836 | [-0.5541028336068685, 0.9448056326697675] | True | igual |
- Todos los intervalos del 95 % contienen el 0: True

## Retroprueba (llegadas de técnico, sin mirar el futuro)
- Llegadas evaluadas: 35 (detalle en retroprueba_llegadas.csv)
- MAE simulador 0.371 · inercia 0.381 puntos por partido
- RMSE simulador 0.458 · inercia 0.516
- Diebold-Mariano (HLN): 0.870, p = 0.195 → etiqueta **descriptivo**
- Cobertura conforme del 80 %: 80 %

## Rendimiento
- Un partido (en lote): 0.301 ms · una réplica: 5.5 ms
- Torneo rápido: 1.08 s · preciso: 10.38 s · arranque del servicio: 0.14 s
- c_R = 4.99 ms, c_S = 52.4 µs; σ_b² = 0.0180, σ_w² = 0.2220 (P de liguilla) → S* = 34
