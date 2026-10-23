# Historia de un entrenador: estudio y simulador

Nos preguntamos qué hay de propio en el juego de un técnico de la Liga MX y qué se explica por
su plantel. Lo respondemos para **Guillermo Almada** con los eventos y el tracking 360 de
StatsBomb de toda la liga (temporadas 2021/22 a 2026/27). Con ese modelo construimos un
simulador: si el América tuviera a un técnico dado, ¿cómo jugaría y cuántos puntos haría en el
Apertura 2026?

Este repositorio reúne **todo el entregable en un solo lugar**: el análisis inicial, el estudio
completo de la liga, el simulador con su aplicación web y la documentación. Es un solo proyecto
organizado en carpetas, no varios repositorios juntos. 

## Enlaces

- **Video de presentación:** https://www.youtube.com/watch?v=xKYpLE7MCm8
- **Reporte (HTML):** [`REPORTE.html`](REPORTE.html): metodología, visualizaciones y resultados en un solo archivo, que se abre sin conexión.
- **Aplicación en producción:** https://historia-de-un-entrenador-final-evvt6gu6etyfa7veza8clq.streamlit.app/
- **Nuestro hallazgo principal, explicado con cifras:** [`estudio/docs/RESULTADOS_ALMADA.md`](estudio/docs/RESULTADOS_ALMADA.md)

## Hallazgos principales

Todas las cifras son de Almada medido contra la liga completa y sobreviven a un único control de
falsos positivos (Benjamini-Hochberg). El detalle, con intervalos y pruebas, está en
[`estudio/docs/RESULTADOS_ALMADA.md`](estudio/docs/RESULTADOS_ALMADA.md).

1. **Se le reconoce.** Un clasificador distingue sus partidos de los del resto de la liga con un
   AUC de 0.882, y queda entre los técnicos más reconocibles de la Liga MX (4.º de 45
   técnicos-club). Lo que más lo delata: la presión alta, las conducciones hacia adelante y los
   saques de meta en corto (que usa menos).
2. **Aprieta encima del rival.** Su PPDA es de 8.50 contra 10.29 de la liga (menos pases del
   rival antes de robar) y tiene a un jugador a menos de dos metros en el 20.7 % de los toques
   del rival, contra el 17.2 % de la liga.
3. **Defiende con el bloque más estrecho de la Liga MX.** 36.8 m de ancho contra 38.5 de la liga
   (percentil 1), y se sostiene aun controlando lo que alcanza a ver la cámara.
4. **Ataca vertical.** Avanza conduciendo, entra al área conduciendo el 47 % de las veces (la
   liga, 37 %) y remata 16.2 veces por partido contra 13.3.
5. **El técnico pesa poco frente al plantel y la suerte.** En un torneo de 17 jornadas, los
   puntos de un equipo varían típicamente ±5.3 por el azar de los partidos y ±5.75 por la fuerza
   del plantel; el técnico explica apenas ±0.6 (entre 37 técnicos con al menos 30 partidos).
6. **En el simulador, el América con Almada rinde casi igual.** Si le diera el puesto, el
   simulador proyecta ≈26.5 puntos en el Apertura 2026 y liguilla directa en 2 de cada 3 torneos
   (66.8 %), apenas por encima del América de hoy. Es un escenario para explorar, no un pronóstico.
7. **El simulador describe estilos, pero no predice.** En 35 cambios de técnico reales no acierta
   mejor que suponer que todo sigue igual (prueba de Diebold-Mariano, p = 0.195).

## El repositorio, de un vistazo

Cada carpeta es una pieza del mismo trabajo, y todas comparten la documentación de `docs/`.

| carpeta | contenido |
|---|---|
| [`analisis_inicial/`](analisis_inicial/) | El primer análisis de Almada en Pachuca: PPDA, transición defensiva, organización defensiva con 360, balón parado, roles de jugadores (NMF) y evolución del estilo (filtro de Kalman). El informe está en [`analisis_inicial/REPORTE_FINAL.md`](analisis_inicial/REPORTE_FINAL.md). |
| [`estudio/`](estudio/) | El estudio completo de la liga, y el núcleo del proyecto: el vocabulario de jugadas, el técnico como mezcla de ese vocabulario, las hipótesis registradas antes del análisis y los resultados ([`estudio/docs/RESULTADOS_ALMADA.md`](estudio/docs/RESULTADOS_ALMADA.md)). |
| [`simulador/`](simulador/) | El simulador y la aplicación web, con sus parámetros calibrados y sus pruebas. |
| [`docs/`](docs/) | La documentación central: [modelo](docs/MODELO.md), [hipótesis](docs/HIPOTESIS.md), [validación](docs/VALIDACION.md), [decisiones](docs/DECISIONES.md) y [validación de esta entrega](docs/VALIDACION_ENTREGA.md). |

## Cómo correrlo

```bash
git clone https://github.com/MrFett22/historia-de-un-entrenador-final.git
cd historia-de-un-entrenador-final
python -m venv .venv
.venv/Scripts/python -m pip install -e ./simulador -e "./estudio[dev]"
bash simulador/correr_app.sh          # o, en PowerShell: .\simulador\correr_app.ps1
.venv/Scripts/python -m pytest -q simulador/tests estudio/tests
```

En macOS o Linux se usa `.venv/bin/python`. La aplicación funciona sin los datos de StatsBomb:
le bastan los parámetros calibrados de `simulador/artefactos/`. Validamos el repositorio con
Python 3.14 en Windows 11; la aplicación en producción corre con Python 3.12 en Streamlit
Community Cloud.

## Datos y licencia

Los datos son eventos y tracking 360 de StatsBomb de la Liga MX, provistos para el Hackathon
ISAC 2026 para uso exclusivo de la competencia. No están en este repositorio: solo incluimos
parámetros agregados por liga, equipo y técnico (ver [AVISO_DATOS.md](AVISO_DATOS.md)). El
código y la documentación se distribuyen bajo la licencia MIT ([LICENSE](LICENSE)), que no
cubre los datos.

## Cómo se hizo este proyecto

El diseño del modelo es nuestro: la pregunta, el vocabulario de jugadas, las hipótesis, la
separación entre técnico y plantel, las pruebas estadísticas y los criterios de validación.
También son nuestras la auditoría que encontró y corrigió errores (la fuga de datos del torneo
objetivo, el óptimo local del algoritmo EM causado por la semilla y una regla de atribución
que el prior volvía inalcanzable) y la interpretación de los resultados. Para implementar el
código, la aplicación web y la automatización de pruebas usamos asistentes de inteligencia
artificial (Claude Code y Antigravity), bajo nuestra dirección. Revisamos y validamos cada
resultado matemático.

## Equipo

- Diego Muñoz Gonzalez
- Rodrigo Moreno Cruz
- Uriel Antonio Chavez Sanchez
- Diego Nieto Pizano
