# Validación de esta entrega

Verificamos el repositorio en local el 21 de octubre de 2026, sin recalibrar el simulador.

Entorno: Windows 11 (10.0.26200), Intel Core i7-12700H, 16 GB de RAM, Python 3.14.3 en un solo
entorno virtual, con numpy 2.5.3, pandas 3.0.6, polars 1.44.2, scipy 1.18.1, streamlit 1.65.0,
pymc 6.3.2 y numba 0.67.0. La aplicación en producción corre con Python 3.12 en Streamlit
Community Cloud.

## Simulador

| prueba | valor esperado | valor obtenido | estado |
|---|---|---|---|
| Suite completa de `simulador/` | unas 265 pasan, 0 fallan, unas 17 se omiten, 2 xfail | 265 pasan, 0 fallan, 17 se omiten, 2 xfail | cumple |
| La aplicación arranca solo con `artefactos/` | sin excepciones | sin excepciones | cumple |
| Almada en el América, puntos esperados (modo preciso) | 26.54 | 26.54 | cumple |
| Almada, probabilidad de liguilla (modo preciso) | 66.8 % | 66.8 % | cumple |
| Diferencia de Almada frente al estilo neutro | +0.62 | +0.62 (IC 90 % [−0.42, +1.73]) | cumple |
| Error de xPts | +0.43 % | +0.43 % | cumple |
| χ² de goles | p = 0.91 | χ² = 1.49, 5 gl, p = 0.91 | cumple |
| Autocorrelación de residuos | −0.009 [−0.05, 0.03] | −0.009 [−0.050, 0.030] | cumple |
| Placebo | limpio | 3 de 3 intervalos contienen el 0 | cumple |
| Recuperación de estilos | 93 % | 14 de 15 (93 %) | cumple |
| Diebold-Mariano | p = 0.195 | p = 0.195 (35 llegadas) | cumple |
| Dispersión r | 1.52 [1.23, 1.70] | 1.52 [1.23, 1.70] | cumple |
| Variación por los jugadores | ±5.75 | ±5.75 [4.47, 6.33] | cumple |
| Variación por el azar | ±5.3 | ±5.27 [5.26, 5.28] | cumple |
| Partidos sorteados contra el cálculo exacto | sin diferencias | χ² = 23.2, 24 gl, p = 0.51 | cumple |

Los números de control se recalculan con `python docs/herramientas/numeros_control.py`; la
salida de esta verificación está en `docs/numeros_control.json`.

## Estudio

| prueba | valor esperado | valor obtenido | estado |
|---|---|---|---|
| Suite de `estudio/` | todas pasan | 176 pasan, 1 falla, 1 deseleccionada | con observación |
| PPDA (`analisis_inicial/scripts/ppda.py`) | Pachuca 2.24 contra liga 2.67; Mann-Whitney p < 0.00001 | 2.24 contra 2.67; p < 0.00001; diferencia −0.44 [−0.53, −0.34] | cumple |
| Balón parado defensivo (`balon_parado.py`) | 13.73 % (n = 2,549) contra 15.44 % (n = 56,967); IC [−3.08, −0.32] pp | idéntico | cumple |
| Roles de jugadores (`nmf_roles.py`) | k = 5; 61 jugadores con al menos 150 toques; roles que coinciden con posiciones | idéntico | cumple |
| Evolución del estilo (`kalman_estilo.py`) | 2 % de la varianza es deriva real | 0.020 (Q = 0.0060, R = 0.2927) | cumple |
| Transición defensiva, riesgos competidores | a 30 s: 53.3 % contra 48.4 %; a 45 s: 68.2 % contra 62.7 % | no re-ejecutado por tiempo; resultados tomados del informe original | no re-ejecutado |
| Organización defensiva con 360 | línea más alta y bloque más compacto en 5 de 5 métricas | no re-ejecutado por tiempo; resultados tomados del informe original | no re-ejecutado |

La prueba que falla es `estudio/tests/test_historia.py::test_cadena_de_jugadores`, que espera
que la probabilidad de remate desde cada jugador quede entre 0 y 1. Ya fallaba antes de unir el
proyecto: la reprodujimos en una copia intacta del estudio, con polars 2.0 y con polars 1.44.
No la causó la unión, y no la modificamos para no alterar la lógica.

## Orden y formato del código

Corrimos las suites antes y después de dar formato al código y de limpiar comentarios, y el
resultado de cada prueba fue idéntico: solo cambiaron espacios, saltos de línea y comentarios
(`ruff format --line-length 100`; el árbol sintáctico de cada archivo es el mismo).
