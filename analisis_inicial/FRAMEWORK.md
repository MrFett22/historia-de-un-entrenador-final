# Framework analítico (reto 5.6)

**Caso de estudio:** Guillermo Almada en Pachuca, Liga MX, 139 partidos de fase
regular (2021/22 a 2024/25 — el resto de la ventana de datos, 2025/26 y
2026/27, no aplica porque Almada dejó Pachuca antes de esas temporadas).

Este documento define los objetos, supuestos y alcance del análisis **antes**
de calcular ninguna métrica, siguiendo la familia de modelos anidados
Markov (M0) ⊂ +contexto (M1) ⊂ +memoria (M2) ⊂ capa oculta (M3, solo si
hace falta). Cada escalón de esa familia solo se acepta si predice mejor en
partidos que no vio — ningún paso se agrega "porque sí".

## 1. Objetos

| Objeto | Definición |
|---|---|
| **Evento** | Acción anotada por StatsBomb. Coordenadas en $[0,120]\times[0,80]$ **desde el equipo que la ejecuta** ($y$ crece hacia abajo). Esto ya incorpora el hallazgo de espejeo de coordenadas de la exploración inicial: un evento del equipo rival viene en su propio marco de ataque, no en el nuestro — nunca se combinan posiciones de ambos equipos sin pasar antes por ese marco. |
| **Posesión** | Eventos con el mismo `possession` dentro del mismo partido; dueño = `possession_team`. Solo se usan períodos 1 y 2 (tiempo regular) — tiempo extra y tandas de penales quedan fuera del alcance (ver sección 4). |
| **Secuencia** *(corregido 2026-09-24, ver bitácora C1)* | Tramo de una posesión desde su inicio (o desde la absorción anterior) hasta su **primera** absorción. StatsBomb no cierra la posesión cuando el mismo equipo conserva el balón tras un tiro que rebota, un córner a favor o un pase fallido que recupera al toque — verificado en los propios datos: ~10% de las posesiones de Pachuca-Almada tienen más de una absorción real. **Es la unidad de la cadena** ($M_0$), no la posesión completa de StatsBomb. Una posesión con $k$ absorciones da $k$ secuencias. |
| **Estado** | Zona $z \in \{1,\dots,20\}$ de una malla $5\times4$ (franjas en $x$: 0-24-48-72-96-120; 4 carriles en $y$). Grid más fino que el 4×3 que se usó en la exploración inicial — se sostiene porque el encogimiento hacia la liga (sección 3) compensa la dispersión por celda; se revalida empíricamente antes de usarse en M1 (ver bitácora). |
| **Absorbentes** | $G$ gol, $R$ remate sin gol, $P$ pérdida, $D$ detención (fuera, falta, offside). Se determinan por **secuencia**, no por posesión completa: un tiro (`Shot`) siempre cierra la secuencia en curso, clasificado por SU PROPIO resultado ($G$ si gol, si no $R$); un pase con resultado `Incomplete`/`Out`/`Pass Offside`/`Unknown`/`Injury Clearance` cierra la secuencia en $P$; si la posesión se acaba sin ninguna de esas dos cosas, el último evento decide: fuera de juego o un tipo de detención (`Foul Committed`, `Offside`, `Injury Stoppage`, `Half End`, `Referee Ball-Drop`) u `out=true` da $D$, cualquier otro caso da $P$. Clasificación validada contra 15 partidos reales de Pachuca-Almada antes de adoptarla. |
| **Fases ofensivas** | Construcción ($x<48$), progresión (cruza de $x<48$ a $x\geq72$), ocasión (absorción en $G$ o $R$). |
| **Transición ofensiva** | Posesión que nace de una recuperación en juego abierto; *contraataque* si llega a $x\geq96$ en $\leq10$ s. |
| **Transición defensiva** | Los 10 s posteriores a una pérdida propia. |
| **Fase de presión** | $\geq2$ eventos `Pressure` del mismo equipo en $\leq5$ s; *alta* si ocurre en el 40% propio del rival. |

## 2. Supuestos explícitos

- Markov es una aproximación que se contrasta, no se asume — M2 (memoria)
  solo se agrega si la cadena de orden 1 falla una prueba de bondad de
  ajuste sobre la duración de las posesiones (ver M2 en el roadmap).
- En un pase incompleto, `end_location` es el destino **intentado**, no
  donde terminó realmente el balón.
- La organización defensiva se mide únicamente con 360, y únicamente sobre
  el `visible_area` reportado — lo que la cámara no ve no se imputa (para
  organización defensiva; sí se imputa freeze frames faltantes para las
  features de presión ya validadas en la exploración inicial, con su
  incertidumbre documentada, error mediano ~4.1 m).
- Todo lo que se calcula para el técnico se compara contra **la liga del
  mismo torneo, sin Pachuca** — evita que el equipo se compare contra sí
  mismo diluido en su propio promedio de referencia.
- Nada de lo que se mide es causal: se describe el estilo y su
  incertidumbre, no se aíslan causalmente las decisiones del técnico (el
  plantel y el club van incluidos en cualquier número que se reporte).

## 3. Coherencia interna

Todas las matrices, métricas y figuras se derivan de la **misma** cadena
absorbente ($M_0$) y sus extensiones ($M_1$, $M_2$) — no se calculan
números sueltos con definiciones distintas de posesión, zona o absorbente
en distintas partes del informe.

## 4. Alcance y límites

- Cubre: estilo ofensivo/defensivo de Pachuca bajo Almada, consistencia
  vs. contexto (marcador/periodo), evolución en el tiempo, jugadores,
  balón parado, simulación — todo dentro del framework de esta única
  familia de modelos.
- No cubre: tiempo extra ni tandas de penales (excluidos por diseño, no
  encajan en el marco de partido regular); afirmaciones causales sobre
  decisiones del técnico; comparación estadísticamente generalizable de
  "todos los DTs de la liga" (ya se investigó en la exploración inicial —
  4 métodos independientes no encontraron esa señal a nivel liga; por eso
  el foco es este caso de estudio delimitado, no una afirmación general).
- Datos: StatsBomb eventos + 360, uso exclusivo para esta competencia.

---

## Bitácora

- **2026-09-24** — Framework inicial escrito, siguiendo el roadmap
  matemático acordado con el equipo. Grid definido en 5×4=20 zonas (más
  fino que el 4×3 usado en la exploración inicial) — pendiente de
  revalidar la densidad de datos por celda con el encogimiento hacia la
  liga puesto, antes de usarlo en M1.
- **2026-09-24** — Clasificación de absorbentes (G/R/P/D) validada contra
  15 partidos reales antes de adoptarla — ver tabla de la sección 1.
- **2026-09-24** — $M_0$ (cadena absorbente) resuelto sobre los 139 partidos
  de Pachuca-Almada: 111,844 transiciones, $\rho(Q)=0.838<1$ (converge). $t$
  (acciones esperadas hasta absorción) va de 3.09 a 7.95 por zona; $B_{G}$
  (prob. de gol) de 0.006 a 0.059; $V$ (valor de zona, goles esperados) de
  0.009 a 0.081 — las zonas cerca del área rival valen ~9× más que las
  propias, orden de magnitud consistente con modelos de *expected threat*
  publicados. $\bar{x}_{G,R}$ (xG promedio de tiros sin gol, para el vector
  de recompensa $r$) = 0.069. Incertidumbre con bootstrap por partido
  ($B=2000$): las zonas con menos datos (z17, z18, cerca del área rival)
  tienen los intervalos más anchos, ej. $B_{G}$ en z17 = 0.0585
  [0.0432, 0.0751] — justo donde más ayuda el encogimiento. Ver
  `scripts/m0_cadena_absorbente.py`, `scripts/m0_bootstrap.py`,
  `m0_pachuca_almada.png`, `m0_bootstrap.png`.
- **2026-09-24** — Encogimiento (shrinkage) validado por validación cruzada
  de 5 folds por partido: el óptimo está en **λ≈1,500-2,000** (mejora la
  log-verosimilitud fuera de muestra hasta ahí, luego empeora porque diluye
  demasiado la información del club frente al promedio de liga). Con los
  tamaños de muestra reales por zona (n entre 1,477 y 9,665), λ≈1,500
  representa un peso no trivial hacia la liga en las zonas con menos datos
  (~50% en z3/z17/z18) y casi nulo en las zonas con más datos. *Cómo se
  aplica:* las magnitudes de $M_0$ se siguen reportando con $\lambda=0$
  (crudo) por transparencia, tal como especifica el roadmap; este
  encogimiento se activa en $M_1$, donde el grid más fino (20 zonas ×
  contexto) sí puede generar celdas con poca muestra. Ver
  `scripts/m0_encogimiento.py`.
- **2026-09-24** — Elo de fuerza de rival ajustado sobre los 1,780 partidos
  con resultado de las 6 temporadas: **K=15, h=50** elegidos por máxima
  verosimilitud (grid search). Ranking final con sentido futbolístico (Cruz
  Azul, Toluca, América arriba; Pachuca a media tabla, 1,542) — sirve como
  chequeo de sanidad del ajuste. El Elo previo a cada partido queda guardado
  por partido para usarse como covariable en $M_1$. Ver `scripts/elo.py`,
  `elo_resultados.json`.
- **2026-09-24** — Descarga de 360: no fue necesario volver a descargar nada
  — los 139 partidos de Pachuca-Almada (y el resto de la liga, para la
  referencia de $q$) ya estaban en caché local de la exploración inicial,
  con 100% de cobertura de 360 confirmada previamente. Semana 1 del roadmap
  completa: framework, cadena, encogimiento, bootstrap, Elo, 360.
- **2026-09-24** — $M_1$ (logit multinomial contextual) ajustado sobre los
  2,837,937 filas-transición de las 6 temporadas (164,166 de Pachuca),
  usando el truco de una sola regresión softmax: `onehot(origen)` (20) +
  `x` (4: marcador, fracción de periodo, local/visita, diferencia de Elo/400)
  + `x·is_pachuca` (4), de donde $\alpha_{ij}$, $\beta_j$ (efecto de liga) y
  $\delta_j$ (desviación específica de Pachuca) salen del mismo ajuste.
  Lectura del efecto de `marcador` (ir ganando, +1): a nivel liga, ir
  ganando aumenta la probabilidad de que la posesión termine en gol
  ($\beta_G=+0.358$) y, algo menos esperado, también la de perder el balón
  ($\beta_P=+0.125$, consistente con jugar más arriesgado o con más presión
  del rival). Pachuca **amplifica** el primer efecto ($\delta_G=+0.106$) y
  **atenúa** el segundo ($\delta_P=-0.017$): bajo Almada, ir ganando se
  traduce en más gol y menos pérdidas que lo que el patrón de liga
  predeciría en la misma situación. En la última franja, $\delta$ es
  heterogéneo por carril: z18 duplica el efecto de liga ($\beta=+0.048$,
  $\delta=+0.042$) mientras z16 va en contra del patrón de liga
  ($\beta\approx0$, $\delta=-0.062$) — sugiere una preferencia de carril
  cuando el equipo va arriba en el marcador, no solo "más ataque en
  general". **Pendiente antes de reportar esto como hallazgo:** el test de
  razón de verosimilitudes $G^2$ corriendo abajo. Ver `scripts/m1_dataset.py`,
  `scripts/m1_modelo.py`.
- **2026-09-24** — Test de significancia de $M_1$ ($G^2=2(\ell_1-\ell_0)$,
  modelo completo contra restringido sin $\delta$): $G^2$ observado =
  **1308.6** sobre los datos reales. Nula por bootstrap (remuestreo de
  partidos completos con reemplazo, simulando el destino de cada fila desde
  las probabilidades del modelo restringido — así se preserva la
  correlación dentro de partido y se elimina por construcción cualquier
  efecto específico de equipo): la primera repetición ya da $G^2_{boot}
  \approx 200$, muy por debajo del observado. Corriendo 30 repeticiones en
  segundo plano para la nula completa (~2h) — resultado final pendiente de
  confirmar antes de declarar significancia. Ver `scripts/m1_g2_test.py`.
- **2026-09-24** — Bootstrap de $M_1$ **completo** (30 repeticiones, ~1h54m):
  $G^2_{boot}$ tiene media $30.45$, percentil 95 $=594.73$, máximo
  $=1250.89$ — **ninguna** de las 30 repeticiones alcanza el $G^2$
  observado de 1308.62. $p = (1+0)/(30+1) \approx 0.032$ (convención
  estándar de bootstrap con $B$ finito, en vez de reportar 0 exacto).
  Nota de honestidad metodológica: algunas repeticiones dieron $G^2_{boot}$
  negativo (ej. $-790.6$), lo cual en teoría no debería pasar si ambos
  modelos fueran MLE puro sobre los mismos datos simulados — es ruido
  numérico por la regularización L2 finita ($C=10$) y la convergencia de
  `lbfgs` en 300 iteraciones, no un error de diseño del test; no cambia la
  conclusión porque el $G^2$ observado sigue superando por mucho al máximo
  de la nula (1308.6 vs. 1250.9). **Conclusión: el efecto específico de
  Pachuca ($\delta$) en $M_1$ es estadísticamente real**, no explicable
  por el tipo de variación que se observa al etiquetar "Pachuca" a un
  equipo cualquiera de tamaño de muestra comparable. Los números
  descriptivos de $\delta$ reportados arriba (amplificación de gol al ir
  ganando, menos pérdidas, heterogeneidad z16/z18) quedan validados, no
  son artefacto de ruido.
- **2026-09-24** — Bondad de ajuste de $M_0$ sobre la duración de posesión
  (regla explícita del roadmap para decidir si hace falta $M_2$): se
  simularon 50,000 posesiones desde la $Q,R$ de Pachuca-Almada y se
  compararon contra las 16,972 posesiones reales con Kolmogorov-Smirnov.
  $D=0.050$, $p<0.0001$ — **se rechaza** que la cadena de orden 1 explique
  bien la duración real (mediana real=4 pasos vs. simulada=5; la realidad
  tiene más posesiones cortas de lo que predice un proceso sin memoria).
  Por la regla "se añade historia hasta que pase, y no más", esto habilita
  construir $M_2$. Ver `scripts/m0_bondad_ajuste.py`.
- **2026-09-24** — $M_2$ (memoria) construido agregando al exponente de
  $M_1$ cuatro features de historia dentro de la posesión, sin ampliar el
  espacio de estados: acciones acumuladas, si la acción anterior fue Carry
  (vs. Pase o inicio de posesión), si la acción actual fue bajo presión, y
  si la posesión nació de una recuperación en juego abierto (misma
  definición operacional que "Transición ofensiva" en la sección 1: no
  arranca de un reinicio a balón parado y el evento inmediatamente anterior
  en el partido es del rival). A diferencia de $M_0$/$M_1$, $M_2$ se valida
  con un **split 80/20 por partido completo** (no por fila) y se compara la
  log-verosimilitud fuera de muestra contra $M_1$ — el roadmap exige que
  cada escalón prediga mejor en partidos que no vio, no solo que ajuste
  mejor in-sample. Ver `scripts/m2_dataset.py`, `scripts/m2_modelo.py`.
- **2026-09-24** — $M_2$ **adoptado**: sobre 353 partidos de prueba (566,905
  filas) nunca vistos en entrenamiento, la log-verosimilitud promedio por
  fila mejora de $-1.9648$ ($M_1$) a $-1.9431$ ($M_2$), $+0.0217$/fila
  ($+12{,}295$ nats en total) — mejora clara y consistente, no ruido de
  ajuste in-sample. Lectura de los coeficientes de historia (kappa=liga,
  mu=específico Pachuca; sin test de significancia individual todavía, solo
  descriptivo): las posesiones que se resuelven en la primera acción
  (tiro directo, remate de córner) terminan en gol/remate/detención mucho
  más que las posesiones largas ($\kappa_{G,inicio}=+1.69$); encarar
  (carry) antes de la acción final predice más gol a nivel liga
  ($\kappa_{G,carry}=+0.60$); estar bajo presión predice fuertemente
  perder el balón ($\kappa_{P,presion}=+0.94$, el efecto más grande de la
  tabla). Lo específico de Pachuca: convierte a gol bajo presión más que
  el promedio de liga ($\mu_{G,presion}=+0.19$, a tratar con cautela) y
  **amplifica notablemente** la conversión a gol cuando la posesión nace
  de una recuperación en juego abierto ($\mu_{G,recuperacion}=+0.20$ sobre
  $\kappa=+0.12$ de liga) — coherente con el objeto "Transición ofensiva"
  ya definido en la sección 1. Ver `m2_modelo.npz`.
- **2026-09-24** — Vulnerabilidad defensiva (reto 5.1, lado defensivo): se
  construyó la misma cadena $M_0$ pero para el **rival**, sobre sus
  104,948 transiciones contra Pachuca (139 partidos), encogida
  ($\lambda=1750$) hacia una referencia de liga limpia (1,564 partidos que
  no involucran a Pachuca, 2.51M transiciones — se excluyó explícitamente
  cualquier partido de Pachuca de esta referencia para no contaminarla).
  Se comparó $B_{gol}$ del rival por zona contra esa referencia. Con
  bootstrap por partido ($B=2000$, remuestreando los 139 partidos): **5 de
  20 zonas** tienen una diferencia estadísticamente distinguible de cero
  (IC 95% no cruza 0) — las 5 son negativas (z0, z1, z3, z4, z7, todas en
  la franja más alejada del propio arco de Pachuca, $x$ banda 0-1 en el
  marco del rival). Es decir: cuando el rival construye desde su propio
  campo, termina en gol contra Pachuca con menor probabilidad que contra
  una defensa promedio de liga en esa misma zona — una fortaleza
  defensiva real y localizada, no ruido. Ninguna zona mostró vulnerabilidad
  significativamente mayor a la liga (las zonas cercanas al área rival,
  z16-z19, tienen point estimates dispersos en ambos sentidos pero con
  intervalos muy anchos por poca muestra — no concluyentes). Ver
  `scripts/defensa_vulnerabilidad.py`, `scripts/defensa_vulnerabilidad_bootstrap.py`.
- **2026-09-24** — PPDA, definición reconciliada con la exploración inicial
  (acciones defensivas = Pressure+Duel+Interception+Foul Committed con
  $x\geq40$ en marco propio; pases del rival con $x\leq80$ en su propio
  marco — misma franja física, sin espejeo, porque $120-40=80$). PPDA de
  Pachuca-Almada (139 partidos): **media 2.24** (mediana 2.11) vs. liga sin
  Pachuca (3,128 equipo-partido): **media 2.67** (mediana 2.54).
  Mann-Whitney $p<0.00001$; diferencia de medias con IC bootstrap 95% =
  $[-0.53,-0.34]$, no cruza cero. Pachuca permite casi medio pase menos
  por acción defensiva que el promedio de liga — presiona sensiblemente
  más intenso. **Esto explica el hallazgo anterior**: la razón por la que
  el rival convierte menos que el promedio de liga al construir desde
  zonas alejadas del arco de Pachuca es, consistentemente, que ahí mismo
  Pachuca ya está presionando más de lo normal — no son dos hallazgos
  sueltos, es la misma historia de estilo defensivo vista desde dos
  ángulos distintos (coherencia interna, sección 3). Ver `scripts/ppda.py`.
- **2026-09-24** — Transición defensiva (tiempo desde que Pachuca pierde el
  balón hasta que lo recupera; evento=recuperación observada, censura=tiro
  del rival o fin de periodo antes de recuperar). Kaplan-Meier + log-rank
  contra la liga (sin Pachuca): mediana de recuperación **26.0s** en
  Pachuca-Almada (11,314 pérdidas) vs. **30.0s** en liga (232,333
  pérdidas, 1,564 partidos). La curva de Pachuca está consistentemente por
  debajo de la de liga en todo el rango (ej. a los 20s: 59.4% de las
  pérdidas de Pachuca siguen sin recuperar vs. 62.5% en liga). Log-rank
  p<0.000001. **Tercera confirmación independiente de la misma historia**
  (junto con PPDA y la vulnerabilidad por zona): Almada monta un equipo que
  no solo presiona más intenso, sino que efectivamente recupera el balón
  más rápido tras perderlo — un patrón de contrapresión consistente medido
  desde tres ángulos distintos con la misma conclusión. Ver
  `scripts/transicion_defensiva.py`, `scripts/transicion_defensiva_km.py`,
  `transicion_defensiva_km.png`.
- **2026-09-24** — Organización defensiva por 360 (última pieza del lado
  defensivo de la Semana 2). Solo se usan los jugadores que el
  `freeze_frame` realmente reporta — nada se imputa (supuesto explícito de
  la sección 2). Sobre 194,860 frames defensivos de Pachuca-Almada (139
  partidos) contra 4,461,048 de referencia de liga (1,564 partidos, sin
  Pachuca): altura de línea +1.57 (Pachuca más alta), ancho de bloque
  -1.71 (más angosto), profundidad -0.67 (más compacto), área del casco
  convexo -48.7 (forma más compacta en conjunto), jugadores por delante
  del balón +0.10 (leve). Con un $n$ tan grande, las 5 diferencias son
  estadísticamente significativas ($p\approx0$) casi por construcción —
  lo relevante es el tamaño del efecto (Cohen's $d$): todas son
  **pequeñas** ($|d|$ entre 0.05 y 0.16, el más grande en ancho de bloque
  y área del casco). No hay que sobrevenderlas como un cambio dramático de
  forma. Lo que sí importa es que **las 5 apuntan en la misma dirección**
  que PPDA y transición defensiva: línea más alta, bloque más compacto
  (angosto y profundo), más jugadores adelantados — la firma geométrica de
  un equipo que presiona más arriba y más junto, consistente con las otras
  tres métricas independientes ya reportadas. **Cuarta confirmación
  independiente** del mismo patrón de estilo defensivo, con la honestidad
  de que cada pieza individual es un efecto modesto — la fuerza del
  hallazgo está en la consistencia entre las cuatro, no en la magnitud de
  ninguna por separado. Ver `scripts/organizacion_defensiva_360.py`.
- **2026-09-23** — **Arranca Semana 3.** Primera pieza: NMF de roles de
  jugador (reto 5.3, Uso de Jugadores — sección del rubro sin cobertura
  hasta ahora, a diferencia de estilo/defensa ya cubiertos en Semanas 1-2).
  Matriz $V$ (61 jugadores con ≥150 toques × 20 zonas) = conteo de
  toques (Pass+Carry+Shot) en los 139 partidos de Almada, factorizada con
  NMF ($k=5$) en $V\approx WH$. **Validación importante: el NMF no usa la
  posición registrada por StatsBomb para nada** — se cruza después, como
  chequeo independiente de que los roles recuperados son reales y no
  ruido. Los 5 roles se alinean limpiamente con posiciones reconocibles:
  rol 1 = **porteros** (Carlos Moreno, Óscar Ustari, mezcla 99% en ese
  rol, sin excepción); rol 4 = **zaga central + mediocampo defensivo**
  (Erick Sánchez Ocegueda, Gustavo Cabral, Luis Chávez Magallón, Sergio
  Barreto, Miguel Tapias — todos centrales o "6"); rol 2 = **costado
  izquierdo** (Bryan González, Oussama Idrissi, Mauricio Isaís); rol 3 =
  **ataque central** (José Rondón, Nelson Deossa). El hallazgo más
  interesante es el **rol 0** (banda ancha ofensiva, cerca del área
  rival): domina en varios **laterales nominales** (Kevin Álvarez, Luis
  Rodríguez Alanís, Miguel Rodríguez Macías, José Castillo, Carlos Sánchez
  Nava, Jorge Berlanga — todos "Right Back"/"Left Back" registrados) junto
  con extremos y mediapuntas — evidencia de que **los laterales de Almada
  se proyectan sistemáticamente hasta el tercio ofensivo**, no se quedan
  jugando un rol defensivo clásico. Esto es un hallazgo de "Uso de
  Jugadores" genuino, no solo una curiosidad del clustering: conecta con
  el resto del framework (una defensa que presiona alto necesita
  laterales que suban para sostener el bloque). Ver `scripts/nmf_roles.py`,
  `scripts/plot_nmf_roles.py`, `nmf_roles.png`.
- **2026-09-23** — Balón parado (reto 5.4, segunda pieza de la Semana 3 —
  el otro hueco del rubro sin cobertura). Se reutiliza la clasificación de
  absorbentes G/R/P/D ya validada, restringida a posesiones que arrancan
  con `play_pattern` = "From Corner" o "From Free Kick". **Ofensivo**:
  Pachuca (2,737 balones parados propios) no difiere de la liga (56,967,
  1,564 partidos) — ni en tasa de gol (1.86% vs. 1.84%, $p=0.93$) ni en
  tasa de tiro (22.1% vs. 21.4%, $p=0.37$). Sin sobrevender: el balón
  parado ofensivo de Almada es, sencillamente, de nivel de liga, ni mejor
  ni peor. **Defensivo**: los balones parados del rival **contra**
  Pachuca (2,549) sí difieren — terminan en tiro 18.75% de las veces vs.
  21.39% en liga, diferencia de $-2.64$pp, $z=-3.18$, $p=0.0015$,
  significativa. La tasa de gol específicamente no difiere (1.84% vs.
  1.84%, muestra insuficiente de goles para detectar diferencias ahí), 
  pero Pachuca sí concede menos remates desde balón parado rival de lo
  esperado. **Quinta confirmación independiente** de organización
  defensiva (junto con vulnerabilidad por zona, PPDA, transición
  defensiva, organización 360) — esta vez por un mecanismo distinto
  (marcaje/organización en área durante corners y tiros libres, no
  presión en juego abierto), lo cual la hace evidencia complementaria, no
  redundante. Ver `scripts/balon_parado.py`.
- **2026-09-23** — Modelo propio de xG (pieza de profundidad de la Semana
  3). Logit interpretable con 6 features geométricas/contextuales
  (distancia, ángulo, cabeza vs. pie, tiro libre directo, bajo presión,
  número de defensores en la trayectoria tiro-arco calculado del propio
  `freeze_frame` del tiro — penales excluidos por no tener geometría
  informativa), entrenado con 46,756 tiros de las 6 temporadas (split
  80/20 por partido). **AUC modelo propio = 0.7594** vs. **AUC
  `statsbomb_xg` = 0.7949** en el mismo conjunto de prueba — brecha de
  ~3.5pp, razonable dado que StatsBomb usa features mucho más ricas
  (posicionamiento exacto del portero, calidad de ejecución, etc., visto
  en los campos `gk_save_difficulty_xg`/`shot_execution_xg` del dataset).
  **Esto valida usar `statsbomb_xg` en el resto del proyecto** (ej. el
  $\bar{x}_{G,R}$ de $M_0$): un modelo simple y transparente ya captura la
  mayoría de la señal discriminativa, así que no es una caja negra
  arbitraria. Calibración global razonable en los tres (xg propio=0.091,
  xg StatsBomb=0.088, tasa de gol real=0.086). Signos con sentido
  futbolístico: ángulo (+), distancia (−), cabeza (−), presión (−),
  defensores en la trayectoria (−, valida el feature diseñado). Una
  anomalía honesta: `es_falta_libre` sale positivo controlando por
  distancia/ángulo — contraintuitivo (la barrera debería reducir la
  conversión); probablemente refleja que el feature de "defensores en
  trayectoria" no captura bien la barrera a corta distancia del balón, o
  una correlación residual con especialistas de tiro libre — se deja
  documentado como limitación del modelo, no se sobreinterpreta. Ver
  `scripts/xg_propio.py`.
- **2026-09-23** — Evolución temporal del estilo (Kalman, pieza de
  profundidad). Modelo de nivel local ($x_t=x_{t-1}+w_t$,
  $y_t=x_t+v_t$) sobre PPDA por partido, ordenado cronológicamente a lo
  largo de las 4 temporadas de Almada (139 partidos). $Q,R$ ajustados por
  máxima verosimilitud (grid search, mismo método que $K,h$ del Elo):
  óptimo asigna solo **2% de la varianza observada a deriva real**, el
  98% restante es ruido partido a partido. Cambio neto suavizado de
  inicio a fin del período: $-0.07$ (sobre una desviación estándar de
  0.55) — prácticamente nulo. Promedios suavizados por temporada
  (2.19 → 2.21 → 2.27 → 2.26) tampoco muestran tendencia consistente.
  **Lectura**: no es un resultado nulo a esconder, es el hallazgo — el
  estilo de presión de Almada es **temporalmente estable**, no una fase
  transitoria ni una evolución gradual. Complementa la consistencia ya
  encontrada en $M_1$ (estable ante contexto dentro del partido) con
  consistencia en el eje temporal (estable entre temporadas) — dos
  ángulos distintos de la misma idea de "Consistencia y Variabilidad"
  (reto 5.2). Ver `scripts/kalman_estilo.py`, `scripts/plot_kalman_estilo.py`,
  `kalman_estilo.png`.
- **2026-09-23** — Simulador validado (Semana 3, pieza de profundidad).
  Se usa $M_1$ ya ajustado para simular posesiones completas de Pachuca
  manteniendo fijos la zona inicial y el contexto real (marcador,
  periodo, local/visita, Elo) de cada posesión de los 139 partidos, pero
  dejando que el destino de cada paso se muestree del modelo. **Nota
  metodológica honesta**: la primera versión comparó goles reales contra
  el *promedio* de 20 simulaciones por partido — comparación injusta,
  porque promediar reduce artificialmente la varianza (KS daba
  $p\approx0$ solo por eso, no por mal ajuste). Corregido comparando
  contra **una sola** realización simulada por partido (misma
  estructura de varianza que un partido real): **agregado**: 218 goles
  reales vs. 216.2 esperados (<1% de diferencia) en los 139 partidos.
  **Distribución** (comparación justa, una corrida): KS $D=0.079$,
  $p=0.78$ — no se puede distinguir de la distribución real de goles por
  partido. **Calibración**: percentil del valor real dentro de la propia
  distribución simulada del partido, media=0.495 (ideal 0.5), con
  colas cercanas a lo esperado (8% por debajo de p10, 13% por encima de
  p90, ideal ~10% en ambas). El simulador no solo ajusta bien in-sample
  (ya sabíamos eso por la verosimilitud) sino que genera partidos
  "jugables" con macro-estadística realista. Ver
  `scripts/simulador_validado.py`, `scripts/plot_simulador.py`,
  `simulador_validado.png`.
- **2026-09-23** — DiD de sustituciones (última pieza de profundidad de la
  Semana 3). Métrica de valor por posesión consistente con el vector de
  recompensa de $M_0$ ($1$ si gol, $\bar{x}_{G,R}=0.069$ si remate sin
  gol, $0$ si no), agregada por minuto. Para las 449 sustituciones de
  Pachuca con ventana completa (minuto 15-75): tratado (post15−pre15
  alrededor de la sustitución) media $=+0.0036$; control (788 ventanas
  sin sustitución cercana, incluye margen de $\pm15$min para no
  contaminar el control) media $=-0.0015$. **DiD $=+0.0051$**, IC
  bootstrap 95% $=[-0.0003, +0.0103]$ — roza el cero por muy poco (no
  cruza técnicamente el umbral de significancia al 95%, $p$ de una cola
  $=0.034$, $t$-test de dos colas $p=0.063$). **Lectura honesta**:
  evidencia **sugestiva pero no concluyente** de que las sustituciones de
  Almada se asocian a un pequeño repunte de valor generado — no se puede
  afirmar con la confianza de los otros hallazgos de este documento; se
  deja documentado como una pista, no como una conclusión. Ver
  `scripts/did_sustituciones.py`.
- **2026-09-23** — **Semana 3 completa** (NMF de roles, balón parado,
  xG propio, Kalman de estilo, simulador validado, DiD de sustituciones).
  El HMM de "modos de juego" sigue deprioritizado por la misma razón
  discutida al inicio del proyecto: repetiría a nivel liga el patrón de
  búsqueda que ya falló cuatro veces en la exploración inicial, sin
  aportar algo que el resto del framework no cubra ya para este caso de
  estudio puntual.

---

## Corrección C1 y C2 (2026-09-24)

Una auditoría cruzada de otro equipo trabajando el mismo reto (con datos de
toda la liga) señaló dos errores. **Ninguno se aceptó sin verificar contra
nuestros propios datos primero** — eso es lo que sigue.

- **C1 — unidad de análisis, confirmado y corregido.** El código trataba
  cada posesión completa de StatsBomb como una sola trayectoria de la
  cadena, clasificada por su "mejor" resultado. Pero StatsBomb no cierra
  la posesión cuando el mismo equipo conserva el balón tras un tiro que
  rebota, un córner a favor o un pase fallido que recupera al toque —
  verificado en una muestra de 30 partidos propios: **10.3% de las
  posesiones tienen más de una absorción real**. Una cadena absorbente
  debe terminar en la **primera** absorción, no en la mejor de toda la
  posesión. Se reescribió `possession_to_secuencias` en
  `m0_cadena_absorbente.py` para cortar correctamente, y se agregó una
  **prueba de cierre** obligatoria: $\alpha^\top N \mathbf{1}$ (duración
  media predicha desde la distribución real de zonas iniciales) contra la
  duración media empírica. Resultado: **0.00% de diferencia** — la cadena
  corregida cierra exacto. Se repropagó el fix a todo el pipeline que
  depende de posesiones: $M_0$, su bootstrap, el encogimiento, la bondad
  de ajuste, $M_1$, $M_2$, la vulnerabilidad defensiva, balón parado, el
  simulador y el DiD de sustituciones — todos recalculados con secuencias
  correctas, no con el código viejo.
- **C2 — el test de significancia de $M_1$, confirmado y corregido.** El
  test $G^2$ con nula por bootstrap (Semana 2) producía repeticiones con
  $G^2$ **negativo** (hasta $-790.6$), algo que no puede pasar si ambos
  modelos son un MLE limpio sobre los mismos datos — señal de que la
  regularización L2 o la convergencia de `lbfgs` rompían la comparación,
  no ruido cosmético como se documentó entonces. Se reemplazó por el
  **mismo criterio ya usado para aceptar $M_2$**: log-verosimilitud fuera
  de muestra, split 80/20 por partido. Ver `scripts/m1_significancia.py`.
- **Nombre del técnico**: corregido "Jorge Almada" → **Guillermo
  Almada** (su nombre de uso; el legal es Jorge Guillermo Almada Álves,
  confirmado contra el campo `managers` del propio dataset) en todo el
  repositorio.

### Resultados recalculados

- **$M_0$**: 19,768 secuencias (antes: 16,972 "posesiones", que en realidad
  mezclaban trayectorias distintas), 111,894 transiciones. $\rho(Q)=0.817$
  (antes 0.838, sigue convergiendo). $t$ ahora va de 2.34 a 7.13 (antes
  3.09–7.95) — secuencias más cortas en promedio, como se esperaba al
  cortar correctamente. $B_G$ de 0.004 a 0.058, $V$ de 0.007 a 0.082 —
  mismo orden de magnitud y mismo patrón espacial que antes (las zonas
  cerca del área rival siguen valiendo ~9-10× más). **Prueba de bondad de
  ajuste (KS) repetida con secuencias correctas: sigue rechazando $M_0$**
  ($D=0.049$, prácticamente igual al $0.050$ de antes) — es decir, el fix
  de C1 **no elimina** la necesidad de $M_2$; la memoria dentro de la
  posesión es un efecto real, no un artefacto del bug de unidad. Esto es
  tranquilizador: $M_2$ no se estaba construyendo sobre una base rota.
- **Encogimiento**: $\lambda$ óptimo por CV sigue en **~1,500**
  (log-verosimilitud pico en $\lambda=1500$: $-1.89494$), prácticamente
  idéntico al hallazgo original. Sin cambios en cómo se usa.
- **$M_1$**: reajustado sobre 2,839,513 filas (164,247 de Pachuca). Los
  coeficientes centrales se mantienen: $\delta_G=+0.106$ (gol al ir
  ganando, casi idéntico a antes) y z16/z18 mantienen la heterogeneidad
  de carril reportada. Pero $\delta_P$ pasó de $-0.017$ a $+0.003$ —
  **prácticamente cero**, confirmando la crítica de que ese número nunca
  fue un hallazgo real, solo ruido que un $n$ enorme hacía parecer
  distinto de cero. **Test de significancia corregido** (out-of-sample,
  no el $G^2$ inválido): la mejora del modelo con $\delta$ sobre el
  modelo sin $\delta$ en partidos de prueba es $+25.9$ nats totales,
  $+0.00005$ por fila — **positiva pero diminuta**, unas 400 veces más
  chica que la mejora que sí sostuvo la adopción de $M_2$ ($+0.0217$ por
  fila). Lectura honesta: hay algo real ahí (la dirección es consistente
  y positiva en datos que el modelo no vio), pero es un efecto **mucho
  más débil** de lo que el test $G^2$ roto sugería — no se puede llamar
  "hallazgo fuerte" como se hizo antes. Ver `scripts/m1_significancia.py`.
- **Vulnerabilidad defensiva**: con secuencias correctas y bootstrap
  repetido, **4 de 20 zonas** siguen significativas (antes 5), todas
  negativas, en la misma franja alejada del arco de Pachuca (z0, z1, z3,
  z4) — el hallazgo central no cambia.
- **Balón parado**: al usar solo la **primera secuencia** de cada
  posesión de balón parado (la entrega inmediata, no lo que pase después
  de un rebote), el resultado **cambia y mejora**: el balón parado
  **ofensivo** de Pachuca ahora SÍ es significativamente mejor que la
  liga en tasa de tiro (18.1% vs. 15.4%, $z=3.74$, $p=0.0002$) — antes
  parecía "sin diferencia" porque la clasificación por posesión completa
  diluía la señal de la entrega real. El lado **defensivo** se mantiene
  significativo (13.7% vs. 15.4%, $p=0.02$, antes $p=0.0015$ — sigue
  siendo evidencia real, algo menos fuerte que antes). Ver
  `scripts/balon_parado.py`.
- **Simulador**: recalculado con secuencias. Diferencia agregada de goles
  1.63% (antes <1%, sigue siendo muy buena calibración), KS $D=0.079$,
  $p=0.78$ (idéntico a antes), y la correlación partido-a-partido entre
  goles reales y esperados **mejoró** de 0.250 a 0.484. El simulador
  sigue validando bien, y mejor que antes.
- **DiD de sustituciones**: sin cambios sustantivos ($DiD=+0.0049$, IC
  $[-0.0006, +0.0102]$, sigue sin ser significativo) — se mantiene como
  pista sugestiva, no concluyente.

**Conclusión de la corrección**: el fix de C1/C2 no invalidó la historia
central del proyecto (presión, bloque compacto, recuperación rápida,
laterales ofensivos), pero sí **debilitó honestamente** uno de los
hallazgos ofensivos de $M_1$ (el efecto $\delta$ era mucho más chico de
lo que el test roto sugería) y **fortaleció** uno del balón parado
ofensivo que antes parecía nulo. Es exactamente el tipo de cambio que una
corrección metodológica honesta debe producir: algunas cosas se debilitan,
otras se fortalecen, ninguna se fuerza a la conclusión que uno esperaba
de antemano.

---

## Correcciones de inferencia (2026-09-26)

Una segunda auditoría cruzada (informe `INFORME_METODO_Y_COMPARACION.md`
del equipo de `dtcoach`) señaló tres debilidades de inferencia. Las tres
se implementaron (no solo se declararon como limitación):

- **Corrección por comparaciones múltiples (Benjamini-Hochberg)** en las
  20 zonas de vulnerabilidad defensiva y en las 5 métricas de organización
  360. **Resultado: las 4 zonas de vulnerabilidad y las 5 métricas 360 que
  ya se reportaban como significativas sobreviven la corrección** — no
  eran falsos positivos por probar muchas zonas/métricas a la vez. Ver
  `scripts/defensa_vulnerabilidad_bootstrap.py`,
  `scripts/organizacion_defensiva_360_significancia.py`.
- **Agrupación por partido en balón parado** (antes: cada córner/tiro
  libre se trataba como una observación independiente, ignorando que
  varios balones parados del mismo partido están correlacionados). Se
  reemplazó el test de dos proporciones por un **bootstrap por partido**
  (2000 repeticiones), remuestreando partidos completos, no balones
  parados sueltos. **Ambos hallazgos se mantienen** incluso con esta
  corrección más conservadora: ofensivo IC 95% $[+0.96, +4.36]$pp
  ($p_{boot}<0.0001$), defensivo IC 95% $[-3.08, -0.32]$pp
  ($p_{boot}=0.019$). Ver `scripts/balon_parado.py`.
- **Incidencia acumulada (Aalen-Johansen) en vez de Kaplan-Meier ingenuo**
  para la transición defensiva. El remate del rival no es censura simple
  — es un **riesgo competidor**: si el rival remata, la "recuperación" no
  ocurrió por una razón informativa (ya organizó un ataque), no por falta
  de información, y tratarlo como censura sesga hacia arriba la
  probabilidad de recuperación estimada. Se recodificaron los desenlaces
  (0=censura real, 1=recuperación, 2=riesgo competidor) y se comparó
  Pachuca contra la liga con incidencia acumulada + bootstrap por partido
  en 7 tiempos de corte (5-60s), con Benjamini-Hochberg entre los 7. Ver
  `scripts/transicion_defensiva.py`,
  `scripts/transicion_defensiva_riesgos_competidores.py`.
  **Resultado: Pachuca recupera más balón que la referencia de liga en 5
  de los 7 tiempos de corte tras BH** (15s, 20s, 30s, 45s, 60s; en 5s y
  10s la diferencia no alcanza significancia). La brecha crece hasta los
  45s y luego se achica: a los 30s, incidencia acumulada de recuperación
  53.3% (Pachuca) vs. 48.4% (liga), diff +4.9pp, IC 95% por partido
  $[+3.7, +6.2]$pp ($p_{boot}<0.0001$); a los 45s, 68.2% vs. 62.7%, diff
  +5.5pp, IC 95% $[+4.3, +6.5]$pp ($p_{boot}<0.0001$). La conclusión
  cualitativa de la versión KM anterior (Pachuca recupera más rápido) se
  mantiene, pero ahora corregida por el sesgo hacia arriba que introducía
  tratar el tiro rival como censura simple.

---

## Patrones de juego por contexto (2026-09-30)

Pedido del equipo: ver cómo cambian los patrones de Pachuca-Almada según
marcador (perdiendo/empatado/ganando), minuto (0-30'/30-60'/60-90') y
fuerza del rival (Elo pre-partido) — y si ese cambio es distinto al de la
liga, no solo si Pachuca cambia (cualquier equipo cambia algo con el
marcador). Ver `scripts/contexto_patrones.py`,
`scripts/contexto_patrones_plot.py`.

**Diseño:** unidad = secuencia (M0, fix C1). Dos métricas: termina en tiro
(G+R) y pierde el balón (P) — gol (G) solo no se prueba aparte por muy
pocas secuencias por celda (33-171). Para cada eje, cada categoría se
compara Pachuca vs. liga con bootstrap por partido + Benjamini-Hochberg
dentro del eje (familias de prueba separadas por eje, igual que zonas y
métricas 360). Además, un contraste de extremos por eje
(diferencia-en-diferencias, bootstrap por partido) prueba si el CAMBIO de
Pachuca a través del eje es distinto al cambio de la liga — mismo espíritu
que `did_sustituciones.py`.

**Resultado:**
- **Pierde el balón menos que la liga en casi todos los contextos**: 6/8
  celdas sobreviven BH (todas menos "perdiendo" y "rival más
  débil/similar"), entre -0.9pp y -2.0pp. Es la pieza más estable: no
  depende del marcador, el minuto ni el rival.
- **Remata más que la liga, pero solo en situaciones favorables**:
  significativo empatado (+1.0pp) y ganando (+1.5pp), en los primeros dos
  tercios del partido (+1.2pp ambos) y contra rivales más fuertes
  (+1.5pp) — no significativo perdiendo, en los últimos 30' ni contra
  rivales más débiles.
- **Ningún contraste de extremos (diferencia-en-diferencias) fue
  significativo** (6 de 6, 3 ejes × 2 métricas): no hay evidencia de que
  Pachuca reaccione MÁS o MENOS que la liga al contexto — su ventaja es
  de línea base, relativamente pareja, no una amplificación que se
  dispara con la adversidad o la ventaja. Matiza (sin contradecir) el
  $\delta_G=+0.106$ de M1: real pero pequeño, y esta prueba más directa
  (categorías separadas, no una variable lineal simétrica) no encuentra
  una asimetría fuerte entre ir perdiendo y ganando.

Gráfica: `contexto_patrones.png` (6 paneles: 2 métricas × 3 ejes).

---

## Desglose del DiD de sustituciones (2026-09-30)

Pedido del equipo: apartado dedicado al impacto de sustituciones. El DiD
original (`did_sustituciones.py`, 2026-09-23) agrupa las 449 sustituciones
de Pachuca en un solo promedio y da un resultado débil (DiD=+0.0051, IC
$[-0.0003,+0.0103]$, roza el cero). Se prueba si ese promedio esconde
señal real en subgrupos. Ver `scripts/did_sustituciones_desglose.py`,
`scripts/did_sustituciones_desglose_plot.py`.

**Diseño:** misma métrica y ventana que el original (valor por posesión
agregado por minuto, tratado=post15-pre15 alrededor del cambio). Dos
ejes:
1. **Por marcador al momento del cambio** (perdiendo/empatado/ganando),
   con **control emparejado por el mismo marcador** (no el pool
   completo) — para no confundir el efecto de la sustitución con que el
   ritmo del partido ya cambia solo por el marcador en ese momento.
2. **Por tipo de sustitución**: se compara el id de posición de StatsBomb
   (corre aprox. de portero=1 a delantero=24) de quien sale contra quien
   entra. Entrante > saliente = "ofensiva"; entrante < saliente =
   "defensiva"; igual = "lateral" (mismo puesto, piernas frescas —
   confirmado a mano sobre 30 sustituciones reales, es la mayoría:
   354/449).

A diferencia del original (bootstrapea sustituciones sueltas), aquí se
bootstrapea por PARTIDO (3000 reps) — varias sustituciones del mismo
partido no son observaciones independientes.

**Resultado:**
- **Por marcador: ningún contraste sobrevive BH** (perdiendo q=0.942,
  empatado q=0.392, ganando q=0.707). El marcador en el momento del
  cambio no explica nada por sí solo.
- **Por tipo: las sustituciones OFENSIVAS sí tienen efecto real.**
  Ofensiva (n=47): DiD=+0.0174, IC 95% $[+0.0043,+0.0293]$,
  $p_{boot}=0.008$, **sobrevive BH** ($q=0.024$). Defensiva (n=48):
  DiD=-0.0024, IC $[-0.0167,+0.0117]$, no significativa. Lateral
  (n=354): DiD=+0.0042, IC $[-0.0032,+0.0121]$, no significativa.
- **Conclusión:** el promedio general débil estaba diluido por
  composición — 9 de cada 10 sustituciones de Almada son de mantenimiento
  (mismo puesto o repliegue) y no mueven la aguja; cuando mete a alguien
  más ofensivo que quien sale, sí hay un repunte de valor medible y
  robusto a BH. **Caveat de causalidad inversa no descartado**: podría
  ser que Almada mete gente ofensiva cuando YA percibe una ventana
  abierta, no que la sustitución la cause — se reporta como hallazgo
  real pero acotado (n=47), no como prueba causal.

Gráfica: `did_sustituciones_desglose.png` (forest plot, 2 paneles).

---

## Desglose de balón parado por tipo (2026-09-30)

Pedido del equipo: apartado completo de balón parado, desglosado en tres
tipos (antes `balon_parado.py` juntaba córner y tiro libre en una sola
cifra), cada uno ofensivo y defensivo. Ver
`scripts/balon_parado_desglose.py`, `scripts/balon_parado_desglose_plot.py`.

**Tipos:**
1. **Corner**: `play_pattern == "From Corner"`.
2. **Tiro libre cerca del área**: `play_pattern == "From Free Kick"` Y el
   saque arranca en el tercio de ataque ($x\geq80$ en el marco del que
   cobra) — un tiro libre en campo propio no es amenaza directa de gol,
   uno cerca del área sí. Umbral elegido por simplicidad (tercio de
   ataque), no calibrado.
3. **Saque de banda muy ofensivo**: `play_pattern == "From Throw In"` Y
   arranca en el tercio de ataque ($x\geq80$) — un saque largo directo a
   zona de remate, no un reinicio en campo propio.

**Diseño:** misma maquinaria que `balon_parado.py` (M0, primera secuencia
de la posesión, bootstrap por partido, 2000 reps). A diferencia del
original, aquí se corrige por **Benjamini-Hochberg dentro de cada
métrica** (tiro, gol) a través de las 6 celdas (3 tipos × ofensivo/
defensivo) — el original solo probaba 1 celda por lado, aquí se prueban
6 a la vez y hace falta corregir.

**Resultado:** de 6 celdas en "termina en tiro", **solo una sobrevive
BH**: tiro libre cerca del área, ofensivo — Pachuca 44.8% (n=359) vs.
liga 37.9% (n=7,559), diff +6.9pp, IC 95% $[+1.9,+11.9]$pp,
$p_{boot}=0.007$, $q_{BH}=0.042$. Corner (ofensivo y defensivo) y saque
de banda muy ofensivo (ofensivo y defensivo) no muestran diferencia con
la liga tras la corrección. Ninguna celda de "gol" sobrevive BH (goles
son eventos raros, n insuficiente para ese nivel de detalle).
**Conclusión:** de los tres tipos, el tiro libre cercano al área ofensivo
es el único con señal propia robusta — córner y saque de banda no
añaden nada más allá del número combinado ya reportado en la sección 6
del informe.

Gráfica: `balon_parado_desglose.png` (2×3 paneles).
