"""TODAS las cadenas que ve el usuario. Ninguna cadena visible vive en otro archivo (T-U2).

Tono de la v6: como un reel de Instagram. Gancho primero (título-pregunta corto con un emoji), una idea por tarjeta, frases de unas 12 palabras como máximo, cifras grandes.
Español de México casual y respetuoso. Que lo entienda cualquiera a la primera: cada número técnico va traducido («rango probable», «¿es casualidad?», «¿acorta o exagera
las diferencias?») y el nombre técnico va solo en letra chica entre paréntesis. Sin las palabras prohibidas (spec 06_INTERFAZ.md, T-U1), sin «xG», «percentil», «componente»,
«intensidad», «momentum», «posterior», «parámetro» ni la letra μ, y sin lenguaje de apuestas.
"""

TITULO = "Simulador de técnico · Club América"
SUBTITULO = "Elige un técnico. Mira cómo le iría al América."
ETIQUETA_DEMO = "Datos de demostración"
TITULO_PESTANA = "Simulador de técnico"

# ---------------------------------------------------------------- barra lateral (solo controles)
PANEL = "Tu técnico"
PRESET = "¿Con quién juegas?"
PRESET_CREA = "Crea tu propio técnico"
PRESET_AYUDA = (
    "Inventa uno o elige uno real: hay perfiles variados. Los reales no se pueden modificar."
)
PRESET_ACTUAL = "(dirige hoy al América)"
PRESET_ANTECESOR = "(dirigió antes al América)"
ETIQUETA_VIGENTE = "Dirige hoy al América."
ETIQUETA_ANTECESOR = "Dirigió antes al América."
CREA_NOTA = "Empiezas en el estilo más común de la liga. Muévele."
BLOQUEADO = "🔒 Así juega {nombre}. Para inventar uno, elige «Crea tu propio técnico»"
PRESET_NOTA = "Su estilo, con el plantel actual del América."
PERFIL_POCO_COMUN = "Perfil poco común: su estimación es la más incierta."
REPRESENTA = "Representa a {n} técnicos de perfil parecido."
ETIQUETA_TECNICO = "{a} y {b}."
ETIQUETA_UN_RASGO = "{a}."
ETIQUETA_SIN_RASGOS = "Sin rasgos que se destaquen."
PRESET_PARTIDOS = "partidos en la Liga MX"

FRANJA_TEXTO = "La franja amarilla: donde están 8 de cada 10 técnicos."
ATACA = "¿Cómo ataca?"
ATACA_AYUDA = "De directo a elaborado. En medio está lo más común de la liga."
ATACA_EXTREMOS = ("Como el más directo de la liga", "Como el más elaborado")
DEFIENDE = "¿Cómo defiende?"
DEFIENDE_PRESION = "¿Qué tanto presiona?"
DEFIENDE_AYUDA = "De dejar jugar al rival a obligarlo a jugar largo y apurado."
DEFIENDE_EXTREMOS = ("Deja jugar al rival", "Lo obliga a jugar largo y apurado")
PP_CONTRA = "Pelota parada en contra"
PP_CONTRA_AYUDA = "Qué tan bien defiende esquinas, tiros libres y saques largos del rival."
PP_FAVOR = "Pelota parada a favor"
PP_FAVOR_AYUDA = "Cuántas esquinas, tiros libres y saques largos consigue, y cuánto los aprovecha."
PP_EXTREMOS = ("De las peores", "De las mejores")
FINOS = "Ajustes finos"
FINOS_AYUDA = "Casi no mueven los puntos. Cambian cómo se ve el estilo."
REACCION = "¿Cambia el plan si se complica?"
REACCION_AYUDA = "Si va perdiendo o el rival es más fuerte, ¿cambia su forma de jugar?"
OPCIONES_REACCION = ("Nunca", "Poco", "Como la mayoría", "Bastante", "Mucho")
CAMBIOS_MOMENTO = "¿Cuándo hace sus cambios?"
CAMBIOS_EXTREMOS = ("Temprano", "Tarde")
CAMBIOS_TIPO = "¿Qué cambios prefiere?"
OPCIONES_CAMBIO = ("Cuidar el resultado", "Mismo puesto", "Buscar el gol")
NO_MUEVE_PUNTOS = "Con los datos que hay, esto no mueve los puntos. Solo cambia el estilo."

PRECISION = "Precisión"
OPCIONES_PRECISION = ("Rápida", "Profunda")
PRECISION_BASE = "Rápida: {n1} torneos, unos {t1}. Profunda: {n2} torneos, unos {t2}."
PRECISION_AFINA = " Los puntos esperados casi no cambian; los porcentajes de liguilla y de cada lugar se afinan (de ±{a} a ±{b} puntos porcentuales)."
PRECISION_SIN_EE = " Los puntos esperados casi no cambian; los porcentajes de liguilla y de cada lugar se afinan. Corre una simulación para ver cuánto."
PRECISION_NO_MAS = (
    " Los puntos esperados ya son exactos dentro de cada versión de los equipos; lo que los limita son las {v} versiones de los equipos "
    "({u} rivales distintos en el caché)."
)

BOTON_SIMULAR = "Simular torneo"
BOTON_REINICIAR = "Volver a empezar"

AYUDA_DESACTIVADA = NO_MUEVE_PUNTOS
AVISO_EXTREMO = (
    "Este técnico es más extremo que cualquiera de la liga. El resultado es menos confiable."
)
AVISO_FUERA_ZONA = "Nadie en la Liga MX ha jugado con esta mezcla. El resultado es menos confiable."

LIMITES_SWITCH = "Modo sin límites"
LIMITES_AYUDA = "Las perillas llegan a unas tres veces lo que se ha visto en la liga."
LIMITES_AVISO_TITULO = "Esto nunca se ha visto en la Liga MX"
LIMITES_AVISO = "Estás fuera de lo que han hecho los técnicos reales. Tómalo como un juego, no como una predicción."
INSIGNIA_FUERA = "Fuera de lo visto"
LIMITES_ETIQUETA = "Cada perilla va de −300 a 300. ±100 es el técnico real más extremo."

# ---------------------------------------------------------------- pestañas
PESTANA_ANTES = "👀 Antes de jugar"
PESTANA_SIMULADOR = "🎮 Simulador"
PESTANA_CREER = "🔍 ¿Le podemos creer?"
INVITACION = "Mueve las perillas de la izquierda y pulsa «Simular torneo»."
SIM_TITULO = "Simulando {torneos} torneos · {partidos} partidos cada uno · {total}"
SIM_MILLONES = "{x} millones de partidos"
SIM_PARTIDOS = "{x} partidos"
SIM_AVANCE = "{p} % · {t}"
SIM_FALTAN = "faltan unos {t}"
SIM_CALCULANDO = "calculando el ritmo…"
SIM_CANCELAR = "Cancelar"
SIM_CANCELADA = "Simulación cancelada. Puedes volver a simular cuando quieras."
SIM_ERROR = "No se pudo simular. Intenta de nuevo."

# ---------------------------------------------------------------- pestaña «Simulador»: ¿qué pesa más?
PESA_TITULO = "¿Qué pesa más?"
PESA_SUERTE = "La suerte"
PESA_JUGADORES = "Los jugadores"
PESA_TECNICO = "El técnico"
PESA_VALOR = "±{x} pts"
PESA_RANGO = "rango probable: {a} a {b}"
PESA_FRASE_IGUALES = "La suerte y los jugadores pesan casi igual. El técnico, mucho menos."
PESA_FRASE_UNO = {
    "suerte": "La suerte pesa más que los jugadores. El técnico, mucho menos.",
    "jugadores": "Los jugadores pesan más que la suerte. El técnico, mucho menos.",
}
PESA_FRASE_TECNICO = "Aquí el técnico pesa más que la suerte y los jugadores."
PESA_FRASE_NEUTRA = "Lo que más mueve los puntos: {que}."
PESA_QUE = {"suerte": "la suerte", "jugadores": "los jugadores", "tecnico": "el técnico"}
PESA_SUERTE_LINEA = "{medida} de lo que varían los puntos es pura suerte ({pct} %)."
PESA_SUERTE_MAS = "Más de la mitad"
PESA_SUERTE_CASI = "Casi la mitad"
PESA_SUERTE_TERCIO = "Cerca de un tercio"
PESA_SUERTE_POCO = "Una parte menor"
PESA_NOTA = "Lo típico que varía en un torneo, en puntos. Los jugadores se miden de la tabla real, no con el simulador."
PESA_AYUDA = (
    "Las tres barras usan la misma medida: lo típico que varía en un torneo, en puntos. Suerte: lo que varía un equipo por puro azar de los partidos. "
    "Jugadores: qué tan distintos son los equipos en fuerza, medido directo de las tablas reales (el simulador acorta esas diferencias, por eso no se usa). "
    "Técnico: lo típico que se separan los técnicos reales de un estilo neutro, con el mismo plantel. El rango probable deja fuera el 5 % más raro."
)
PESA_SIN_DATO = "Falta medir cuánto pesan los jugadores."

# tarjetas de resultado
TARJETA_PUNTOS = "Puntos esperados"
TARJETA_RANGO = "Rango probable: {a} a {b}"
TARJETA_VS = "Contra el América de hoy (Almada)"
TARJETA_VS_IGUAL = "Igual"
TARJETA_VS_DETALLE = "Medido contra el América de hoy, con su plantel"
UNIDAD_PTS = "pts"
UNIDAD_LIGUILLA = "liguilla"
TARJETA_LIGUILLA = "Liguilla"
TARJETA_LIGUILLA_DETALLE = "Probabilidad de quedar entre los {n} primeros"
TARJETA_FUERA = "Fuera"
TARJETA_FUERA_DETALLE = "Probabilidad de quedar fuera (sin play-in)"
TARJETA_PLAYIN = "Probabilidad de play-in"
TARJETA_PLAYIN_DETALLE = "Lugares {a} a {b}"
TARJETA_TOP = "Top {n}"
TARJETA_TOP_DETALLE = "Probabilidad de terminar entre los {n} primeros"
EXIGENCIA = {
    "top": ("🏆", "A la altura del América", "Pelea arriba igual que con Almada."),
    "corto": (
        "😬",
        "Se queda corto",
        "Sale peor que con Almada, aunque dentro de lo que han hecho técnicos reales.",
    ),
    "alerta": (
        "🚨",
        "No da el ancho para el América",
        "Queda por debajo de cualquier técnico real con este plantel.",
    ),
}

# ---------------------------------------------------------------- carta del técnico y calificación (D-067)
CARTA_TITULO = "Carta del técnico"
CARTA_ATRIBUTOS = (
    "Ataque elaborado",
    "Presión",
    "Pelota parada a favor",
    "Pelota parada en contra",
    "Cambia el plan",
    "Cambios tarde",
)
CARTA_ATRIBUTOS_RADAR = (
    "Ataque<br>elaborado",
    "Presión",
    "Pelota parada<br>a favor",
    "Pelota parada<br>en contra",
    "Cambia<br>el plan",
    "Cambios<br>tarde",
)
CARTA_PARECE = "Se parece a: {n}"
CARTA_ES = "Es {n}"
CARTA_NINGUNO = "No se parece a ningún técnico real"
CAMBIOS_CHIP = "Tipo de cambios: {x}"
CAMBIOS_SOLO_ESTILO = "solo estilo"
CARTA_NOTA = "Atributos de 0 a 100 contra los técnicos reales."
CALIF_ETIQUETA = "Calificación"
CALIF_SIN = "—"
CALIF_RANGO_NUM = "{a} a {b}"
CALIF_RANGO = "rango probable: " + CALIF_RANGO_NUM
CALIF_RANGO_SIN = "se ve al simular"
CALIF_SEGURIDAD = "Seguridad: {s}"
CALIF_SEGURIDAD_NIVELES = {"baja": "baja", "media": "media", "alta": "alta"}
CALIF_DELTA = "{d} puntos por torneo contra un estilo neutro"
CALIF_DELTA_ESTIMADO = "{d} puntos por torneo contra un estilo neutro (estimado)"
CALIF_NO_SEPARA = "no se puede separar del promedio"
CALIF_ESTIMADA = "estimada; simula para ver su rango"
CALIF_AVISO = "Califica lo que el simulador cree que aporta su estilo. No cuenta títulos, liguillas ni vestidor."
CALIF_CAMBIOS_AYUDA = "Los cambios no mueven los puntos en el simulador: en toda la liga su efecto en goles salió nulo."
CALIF_AYUDA = (
    "5 es igual al estilo neutro. Más de 5, el simulador cree que suma puntos; menos, que resta. Se compara con los técnicos reales: el mejor vale 10 y el peor, 0. "
    "La seguridad sale de qué tan ancho es su rango probable: ancho (más de 6 puntos), baja; de 3 a 6, media; angosto, alta. "
    "Solo lleva color si la seguridad no es baja y el rango no toca el 5. Rango probable: {rango}. "
    + CALIF_CAMBIOS_AYUDA
)

# ---------------------------------------------------------------- mapa de estilos (D-068)
SECCION_MAPA = "Mapa de estilos"
MAPA_VIVO_NOTA = (
    "Cada punto es un técnico real. La zona es lo que se ha visto. El amarillo eres tú."
)
MAPA_FUERA = "¡Fuera de lo visto!"
MAPA_EJE_X = "¿Cómo ataca?   ← más directo · más elaborado →"
MAPA_EJE_Y = "{nombre}   ← deja jugar · más presión →"
MAPA_ZONA = "Zona donde han jugado los técnicos reales"
MAPA_DENSIDAD = "Dónde se juntan más técnicos"
MAPA_TECNICO = "Tu técnico"
MAPA_PUNTO = "{nombre}"
MAPA_PUNTO_CALIF = "{nombre} · calificación {c}"
MAPA_AYUDA = "La zona no se ajusta a tu punto: es lo que han hecho los técnicos reales."
MAPA_AYUDA_X = "Cómo ataca su equipo: más directo ← → más elaborado."
MAPA_AYUDA_Y_PRESION = "Qué tanto presiona, medido por cómo obliga a jugar al rival. Se parece a la presión real que medimos en los partidos."
MAPA_AYUDA_Y_DEFIENDE = (
    "Cómo defiende: de dejar jugar al rival a obligarlo a jugar largo y apurado."
)
MAPA_AYUDA_ZONA = "La zona sombreada es la figura más chica que encierra a todos los técnicos reales. Afuera, nadie ha jugado así."
MAPA_AYUDA_DENSIDAD = "El tono más claro marca dónde se juntan más técnicos. No hay grupos de estilo: los técnicos se reparten parejo."

# ---------------------------------------------------------------- estilo, cancha, tabla
SECCION_ESTILO_PROPIO = "Así jugaría tu equipo"
SECCION_ESTILO_RIVAL = "Así le jugarían los rivales"
SERIE_TECNICO = "Con este técnico"
SERIE_ACTUAL = "América de hoy (Almada)"
SERIE_LIGA = "Lo normal en la liga"
SERIE_RIVAL_TECNICO = "Contra este técnico"
SERIE_RIVAL_ACTUAL = "Contra el América de hoy (Almada)"
TIPOS_JUGADA = ("Ataque directo", "Toque sin profundidad", "Ataque elaborado")
AYUDA_TOQUE = "Toque sin profundidad: mover el balón sin llegar al área."
EFECTO_CHICO = "Los técnicos de la liga atacan casi igual. Pesan más los jugadores."
EFECTO_CHICO_RIVAL = "A los equipos de la liga les juegan casi igual. Pesan más los jugadores."
BARRAS_NOTA = (
    "Porcentaje de las jugadas de juego abierto. Un decimal, porque las diferencias son chicas."
)

SECCION_PUNTOS = "¿Cuántos puntos haría?"
EJE_PUNTOS = "Puntos al final del torneo"
EJE_VECES = "Qué tan seguido"
SECCION_LUGAR = "¿En qué lugar terminaría?"
EJE_LUGAR = "Lugar en la tabla"
EJE_PROB = "Probabilidad"

SECCION_GOLES = "¿Qué jugadas dan sus goles?"
NOTA_GOLES = "Goles esperados por partido: los que suelen salir de esas jugadas."
SERIE_FAVOR = "A favor"
SERIE_CONTRA = "En contra"
TIPOS_BALON_PARADO = (
    "Tiros de esquina",
    "Tiros libres al área",
    "Saques de banda largos",
    "Tiros libres directos",
    "Penales",
)

SECCION_TABLA = "Tabla final simulada"
TABLA_NOTA = "Puntos esperados de los 18 equipos. La línea marca la liguilla."
TABLA_COLUMNAS = ("Equipo", "Puntos", "Liguilla")
TABLA_LINEA = "Liguilla"

# ---------------------------------------------------------------- gira un torneo
CASINO_TITULO = "Gira un torneo"
CASINO_NOTA = "Un torneo al azar de los ya simulados. Así podría terminar de verdad."
CASINO_BOTON = "Gira un torneo"
CASINO_CONTADOR = "Giros: {n} · Mejor lugar: {mejor}.º · Peor lugar: {peor}.º"
CASINO_SIN = "Todavía no giras. Pulsa el botón."
CASINO_CUENTA = "Los giros cuentan por simulación."
CASINO_TERMINO = "Terminó {n}.º"
CASINO_LIGUILLA = "¡A la liguilla!"
CASINO_FUERA = "Se quedó fuera de la liguilla"
CASINO_RACHA = "Su torneo, jornada por jornada"
CASINO_EQUIPO = "Equipo"
CASINO_PUNTOS = "Pts"
CASINO_DIF = "Dif"

# ---------------------------------------------------------------- ver un partido (D-069)
PARTIDO_TITULO = "Ver un partido"
PARTIDO_NOTA = "Un partido posible, jugada por jugada, con las mismas reglas del simulador."
PARTIDO_RIVAL = "¿Contra quién?"
PARTIDO_SEDE = "¿Dónde juega?"
PARTIDO_SEDES = ("En casa", "De visita")
PARTIDO_BOTON = "Jugar el partido"
PARTIDO_ANTES = "Antes de empezar: gana {g} % · empata {e} % · pierde {p} %"
PARTIDO_RESULTADO = ("Ganó el América", "Empató el América", "Perdió el América")
PARTIDO_GOL = "Gol de {eq}, minuto {m}"
PARTIDO_SIN_GOLES = "Sin goles"
PARTIDO_MINUTO = "Minuto"
PARTIDO_FINAL = "Esto es UN partido posible. En 100 partidos así, el América gana {x}."
PARTIDO_BARRAS = "¿Quién domina? Minuto a minuto"
PARTIDO_BARRAS_AYUDA = (
    "Cada barra es un minuto y sube si domina el América o baja si domina el rival: nunca hay dos barras en el mismo minuto. Domina quien tiene más jugadas peligrosas "
    "y remates mejores, con unos minutos de memoria. ⚽ marca los goles, del lado de quien anotó. La línea punteada es el tope de la escala; si una barra la pasa, "
    "no se recorta: pasa el cursor para ver su valor."
)
PARTIDO_HOVER = "Minuto {m}"
PARTIDO_HOVER_FILA = "Domina {eq}: ventaja de {x} goles por partido a este ritmo"
PARTIDO_REMATES = "Remates: América {a} · {rival} {b}"
PARTIDO_AMERICA = "América"
PARTIDO_STATS_TITULO = "Estadísticas del partido"
PARTIDO_STATS_GRUPOS = {
    "general": "Remates y pelota parada",
    "jugadas": "Jugadas por tipo",
    "fin": "Cómo terminaron las jugadas",
}
PARTIDO_STATS = {
    "remates": "Remates",
    "corner": "Córners",
    "tiro_libre_area": "Tiros libres al área",
    "tiro_libre_directo": "Tiros libres directos",
    "lateral_largo": "Saques de banda largos",
    "penal": "Penales",
    "gol_abierto": "Acabaron en gol",
    "remate_sin_gol": "Acabaron en remate (sin gol)",
    "perdidas": "Acabaron en pérdida",
    "fuera_interrupcion": "Acabaron fuera o en falta",
}
PARTIDO_HONESTO = "El torneo usa exactamente estas reglas, pero calculadas de forma exacta, sin sortear jugada por jugada, para que sea rápido."
PARTIDO_STATS_NOTA = "Las faltas y los fuera de lugar van juntos en «fuera o en falta»: el simulador no los separa. No hay tarjetas ni expulsiones."

# ---------------------------------------------------------------- ficha completa
SECCION_FICHA = "Ficha completa"
FICHA_TABLA_TITULO = "Comparado con el América de hoy (estilo de Almada y plantel actual)"
FICHA_NOTA = (
    "Por partido. ▲ sube y ▼ baja solo cuando el cambio cuenta: al menos {rel} % y {pp} punto porcentual (o {g} por partido, o {m} minuto); en puntos y probabilidades, "
    "al menos {k} errores estándar. Lo demás va en gris: «≈ igual»."
)
FICHA_AYUDA = (
    "▲ amarillo: sube. ▼ rojo: baja. No dicen si es mejor o peor, solo hacia dónde se mueve. Los remates por tipo son un estimado: jugadas de ese tipo por el "
    "porcentaje que termina en remate."
)
FICHA_COLUMNAS = ("Métrica", "Tu técnico", "América hoy", "Cambio")
FICHA_IGUAL = "≈ igual"
FICHA_DISTINTO = "distinto"
FICHA_DE_CERO = "antes 0"
FICHA_GRUPOS = {
    "resultado": "Resultado del torneo",
    "mezcla": "Cómo juega (% de las jugadas)",
    "mezcla_rival": "Cómo le juegan los rivales (% de las jugadas)",
    "remates": "Remates por partido (estimado)",
    "remates_rival": "Remates que concede por partido (estimado)",
    "goles": "Goles por partido, juego abierto",
    "goles_rival": "Goles en contra por partido, juego abierto",
    "pp": "Goles de pelota parada por partido",
    "cambios": "Sus cambios",
}
FICHA_RESULTADO = ("Puntos esperados", "Probabilidad de liguilla", "Probabilidad de top {n}")
FICHA_PP = ("A favor", "En contra")
FICHA_CAMBIO_MINUTO = "Minuto del primer cambio"
FICHA_CAMBIO_TIPO = "Tipo de cambio más común"
NOMBRES_CAMBIO = ("Cuidar el resultado", "Mismo puesto", "Buscar el gol")

# ---------------------------------------------------------------- comparar
COMPARAR_BASE_TU = "Tu técnico"
VEREDICTOS = {
    "mejor": "Le iría mejor",
    "peor": "Le iría peor",
    "igual": "Le iría prácticamente igual",
    "no_se_sabe": "No se puede saber con estos datos",
}
PIE_CORTO = "Sirve para explorar, no para predecir. Lee «Antes de jugar»."

# ---------------------------------------------------------------- lo que dicen los datos de su equipo (descriptivo; no entra a la simulación)
PERFIL_TITULO = "Lo que dicen los datos de su equipo"
PERFIL_NOTA = "Esto describe a su equipo. El simulador usa sus consecuencias."
PERFIL_BASE = "Frente a {n} técnicos con al menos {m} partidos. Datos de los {p} partidos de {nombre}, con todos sus clubes."
PERFIL_SIN_DATOS = "Todavía no hay datos de su equipo para este técnico."
PERFIL_TODOS_LOS_CLUBES = (
    "Esta tarjeta usa todos los partidos del técnico en la liga, no solo los del América."
)
PERFIL_FRASES = {
    "presion": (
        "Presiona más que el {p} % de los técnicos de la liga",
        "Presiona menos que el {p} % de los técnicos de la liga",
        "Presiona como el técnico típico de la liga",
    ),
    "recuperacion": (
        "Recupera el balón tras perderlo más rápido que el {p} % de los técnicos",
        "Recupera el balón tras perderlo más lento que el {p} % de los técnicos",
        "Recupera el balón tras perderlo como el técnico típico",
    ),
    "linea": (
        "Defiende con la línea más adelantada que el {p} % de los técnicos",
        "Defiende con la línea más retrasada que el {p} % de los técnicos",
        "Defiende con la línea a una altura como la del técnico típico",
    ),
    "compacidad": (
        "Defiende más junto que el {p} % de los técnicos",
        "Defiende más abierto que el {p} % de los técnicos",
        "Defiende con un bloque como el del técnico típico",
    ),
    "pp_favor": (
        "Remata a pelota parada más que el {p} % de los técnicos",
        "Remata a pelota parada menos que el {p} % de los técnicos",
        "Remata a pelota parada como el técnico típico",
    ),
    "pp_contra": (
        "Concede menos remates de pelota parada que el {p} % de los técnicos",
        "Concede más remates de pelota parada que el {p} % de los técnicos",
        "Concede remates de pelota parada como el técnico típico",
    ),
}
PERFIL_ORDEN = ("presion", "recuperacion", "linea", "compacidad", "pp_favor", "pp_contra")


def frase_perfil(clave: str, p: float) -> str:
    """p = de cada 100 técnicos de la liga, a cuántos supera en esa dirección (0-100). De 40 a 60 se dice que es como el típico."""
    alta, baja, media = PERFIL_FRASES[clave]
    if p >= 60:
        return alta.format(p=int(round(p)))
    if p <= 40:
        return baja.format(p=int(round(100 - p)))
    return media


# ---------------------------------------------------------------- qué torneo se simula y qué es «América hoy» (D-092): las fechas y los nombres salen de meta.json
MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
TORNEO_TITULO = "Qué torneo simulamos"
TORNEO_SIMULAMOS = "Simulamos el {torneo} completo, desde la jornada 1, con su calendario real (local y visita): {partidos} partidos."
TORNEO_PLANTEL = (
    "El plantel del América y de los rivales se estima con partidos hasta el {anterior}{antes}."
)
TORNEO_ANTERIOR_GENERICO = "último torneo anterior"
TORNEO_ANTES = ", jugados antes del {fecha}"
TORNEO_NO_USAMOS = (
    "Los partidos ya jugados de este torneo NO se usan{cuantos}: así no hacemos trampa."
)
TORNEO_CUANTOS = " (son {n}, del {a} al {b})"
TORNEO_HOY = "«América hoy» = este plantel con el estilo de Almada, su técnico actual."


def fecha_es(iso: str) -> str:
    """«2026-07-17» → «17 de julio de 2026»."""
    a, m, d = (int(x) for x in iso[:10].split("-"))
    return f"{d} de {MESES[m - 1]} de {a}"


# ---------------------------------------------------------------- pestaña «👀 Antes de jugar»: una cuadrícula de tarjetas, una idea por tarjeta (D-070)
ANTES_QUE_ES_TITULO = "¿Qué es esto?"
ANTES_QUE_ES = (
    "Simula el torneo del América con el estilo de un técnico.",
    "Tú eliges cómo juega. El simulador hace el resto.",
)
ANTES_QUE_NO_TITULO = "¿Qué NO es?"
ANTES_QUE_NO = (
    "No predice el futuro.",
    "Describe estilos: qué jugadas haría el equipo y cuántos puntos suelen dar.",
)
ETIQUETA_GLOBAL = {
    "descriptivo": "Este simulador describe estilos. No predice mejor que suponer que todo sigue igual.",
    "predictivo": "En pruebas con cambios de técnico reales, este simulador acertó mejor que suponer que todo sigue igual.",
}
ANTES_PESA_TITULO = "¿Qué pesa más?"
ANTES_TIPOS_TITULO = "Los 3 tipos de jugada"
ANTES_TIPOS_INTRO = "Cada vez que un equipo recupera el balón, empieza una jugada. Hay tres tipos."
TIPOS_CHIPS = (
    "de las jugadas",
    "toques en promedio",
    "terminan en remate",
    "goles por cada 100 jugadas",
)
TIPOS_NOTA = (
    "Promedios de la liga en juego abierto (sin pelota parada). Salen de la fuente del simulador."
)
TIPOS_DESCRIPCION = (
    "Llega rápido al área con pocos pases: pase largo, filtrado o contragolpe.",
    "Mueve el balón de lado y hacia atrás sin llegar al área. Controla el partido.",
    "Construye con paciencia, casi siempre por las bandas, hasta centrar o rematar.",
)
TIPOS_DATOS = (
    "Son el {p} % de las jugadas",
    "Duran {t} toques en promedio",
    "Terminan en remate el {r} % de las veces",
    "Dan {g} goles por cada 100 jugadas",
)
ANTES_PERILLAS_TITULO = "Qué hace cada perilla"
FICHA_CANCHA = "En la cancha"
FICHA_SIMULADOR = "En el simulador"
FICHA_PUNTOS = "Cuánto mueve los puntos"
FICHAS = {
    "ataca": (
        ATACA,
        "Si busca llegar rápido al área o construye con paciencia.",
        "Cambia cuántas jugadas son directas, elaboradas o de toque.",
    ),
    "defiende": (
        DEFIENDE,
        "Qué hace para que el rival ataque de una forma u otra: dejarlo jugar o apurarlo.",
        "Cambia qué jugadas hace el rival y cuántos remates logra.",
    ),
    "pp_contra": (
        PP_CONTRA,
        "Qué tan bien defiende las esquinas, tiros libres y saques largos del rival.",
        "Cambia cuántos de esos tiros del rival terminan en remate.",
    ),
    "pp_favor": (
        PP_FAVOR,
        "Cuántas esquinas, tiros libres y saques largos consigue, y cuánto los aprovecha.",
        "Cambia cuántas pelotas paradas tiene y cuántas terminan en remate.",
    ),
    "ajustes": (
        FINOS,
        "Si cambia el plan cuando se complica, cuándo hace cambios y de qué tipo.",
        "Cambia el estilo que se ve en «Así jugaría tu equipo».",
    ),
}
EFECTO_NUMERO = "De un extremo al otro: unos {x} puntos en el torneo. Por pura suerte, el mismo equipo varía ±{a}."
EFECTO_MENOS = "menos de 0.1"
EFECTO_NO_CAMBIA = "Con los datos que hay, nada: solo cambia el estilo. Por pura suerte, el mismo equipo varía ±{a}."
EFECTO_SIN_DATO = "Todavía no está medido."
ANTES_FIJOS_TITULO = "Técnicos reales = fijos"
ANTES_FIJOS = (
    "Los técnicos reales no se pueden modificar.",
    "Así jugaron de verdad: sus perillas se ven, pero están bloqueadas.",
    "Para inventar uno, elige «Crea tu propio técnico».",
)
ANTES_NO_SIMULA_TITULO = "Qué no simula"
ANTES_NO_SIMULA = (
    "Lesiones, expulsiones ni arbitraje.",
    "Fichajes: el plantel no cambia en todo el torneo.",
    "El vestidor ni la química del grupo.",
    "Concachampions ni otros torneos.",
    "Liguilla: solo la fase regular y quién entra.",
    "Jugadores ni alineaciones. Tampoco partidos que ya se jugaron.",
    "Cada partido es independiente: sin rachas ni cansancio.",
)
ANTES_CIERRE = "Si dice «prácticamente igual», eso también es una respuesta."
ANTES_NIVELES_TITULO = "Cómo leer los resultados"
NIVELES = {
    "top": ("🏆", "A la altura del América", "igual o mejor que Almada, el técnico de hoy."),
    "corto": (
        "😬",
        "Se queda corto",
        "peor que Almada, pero dentro de lo que han hecho técnicos reales.",
    ),
    "alerta": (
        "🚨",
        "No da el ancho para el América",
        "peor que cualquier técnico real con este plantel.",
    ),
}
NIVELES_NOTA = "Como el simulador acorta las diferencias, todos los porcentajes se juntan al centro: compáralos contra Almada, no contra 50 %."

# ---------------------------------------------------------------- pestaña «¿Le podemos creer?»: siete pruebas y una autoverificación (D-071)
CREER_TITULO = "¿Le podemos creer?"
CREER_INTRO = "Ocho pruebas. Cada una dice qué suponemos, qué medimos y si pasó."
CREER_NO_RECHAZAR = (
    "No rechazar H0 no demuestra que sea cierta: dice que los datos no encontraron diferencia."
)
CREER_CLASICA = "Prueba clásica:"
CREER_H0 = "H0"
CREER_H1 = "H1"
CREER_QUEREMOS = "Aquí queremos…"
CREER_CERO_BUENO = "Aquí el 0 dentro es buena noticia: significa que no hay efecto."
CREER_MEDIMOS = "Lo que medimos"
CREER_SIGNIFICA = "Qué significa para ti"
CREER_FACIL = "Prueba fácil (con los mismos partidos)"
CREER_DIFICIL = "Prueba difícil (sin mirar el futuro)"
PASA = "✅ Pasa"
OJO = "⚠️ Ojo"
VALIDACION_PENDIENTE = "Validación pendiente"
VALIDACION_PENDIENTE_DETALLE = (
    "Todavía no se corre la validación de estos datos. Cuando termine, aquí salen las pruebas."
)
VALIDACION_FECHA = "Generada el {fecha} con {n} partidos."
VER_DETALLE = "Detalle técnico del simulador"
ESTUDIO_ORIGINAL = "Ver la documentación del modelo"
P_VALOR = "p = {p}"
P_MENOR = "p < 0.001"
RANGO_VALOR = "{a} a {b}"
CASUALIDAD = "¿Es casualidad?"
CARTAS = {
    "goles": dict(
        clasica="χ² de bondad de ajuste de Pearson",
        hipotesis0="Lo simulado y lo real tienen la misma distribución.",
        hipotesis1="Son distintas.",
        queremos="p > 0.05 (no rechazar H0).",
        cero_bueno=False,
        titulo="¿Mete los goles que se meten de verdad?",
        mide="¿La diferencia es casualidad? Más de 0.05 = sí.",
        tec="prueba χ² (chi cuadrada): χ² = {chi2}, {gl} grados de libertad",
        pasa="Los goles del simulador se parecen a los de la liga.",
        ojo="Con miles de partidos, hasta una diferencia chica se nota. Mira qué barra se despega.",
        tipo="facil",
    ),
    "puntos": dict(
        clasica="Regresión lineal simple de lo real contra lo predicho, más la descomposición de la varianza (r)",
        hipotesis0="La pendiente es 1 y r = 1.",
        hipotesis1="La pendiente no es 1.",
        queremos="Que el rango incluya el 1.",
        cero_bueno=False,
        titulo="¿Acierta los puntos de cada equipo?",
        mide="¿Acorta o exagera las diferencias entre equipos?",
        tec="pendiente {b}; error de puntos totales {err}",
        pasa="Acierta los puntos de cada equipo, buenos y malos.",
        ojo="El simulador acorta las diferencias: los buenos sacan más y los malos menos de lo que dice. Es un límite conocido.",
        r_linea="Las diferencias reales entre equipos son {r}× las del simulador ({a} a {b}).",
        tipo="facil",
    ),
    "calibracion": dict(
        clasica="Hosmer-Lemeshow (χ² por bandas)",
        hipotesis0="Lo predicho cuadra con lo observado.",
        hipotesis1="No cuadra.",
        queremos="p > 0.05 (no rechazar H0).",
        cero_bueno=False,
        titulo="Cuando dice 30 %, ¿pasa 30 %?",
        mide="¿Sus porcentajes cuadran con lo que pasó, por bandas?",
        tec="prueba tipo Hosmer-Lemeshow para ganar, empatar y perder",
        pasa="Cuando dice 30 %, pasa cerca de 30 %.",
        ojo="Algún porcentaje no cuadra con lo que pasó. Mira en qué banda.",
        tipo="facil",
    ),
    "independencia": dict(
        clasica="Autocorrelación de los residuos con retraso de un partido (la idea de Durbin-Watson y Ljung-Box)",
        hipotesis0="ρ = 0: no hay rachas.",
        hipotesis1="ρ ≠ 0: sí hay rachas.",
        queremos="Que el rango contenga el 0.",
        cero_bueno=True,
        titulo="¿Hay rachas entre un partido y otro?",
        mide="¿El resultado de hoy se parece al de ayer? ¿Y el descanso importa?",
        tec="autocorrelación de los residuos: ρ = {rho}; efecto del descanso: {pend} puntos por día",
        pasa="No se ven rachas ni cansancio. Tratar cada partido por separado está bien.",
        ojo="Aparece una relación entre partidos seguidos o con el descanso.",
        tipo="facil",
    ),
    "placebo": dict(
        clasica="Prueba de permutación",
        hipotesis0="El efecto es 0 con los técnicos revueltos.",
        hipotesis1="El efecto no es 0.",
        queremos="Que el rango contenga el 0.",
        cero_bueno=True,
        titulo="Si revuelvo los técnicos, ¿sale un efecto fantasma?",
        mide="¿Algún efecto «inventado» sale como si fuera real?",
        tec="placebo: {k} de {n} rangos probables (IC 95 %) contienen el 0",
        pasa="El simulador no inventa efectos donde no los hay.",
        ojo="Algún efecto fantasma salió: el simulador ve efectos donde no los hay.",
        tipo="facil",
    ),
    "recuperacion": dict(
        clasica="Cobertura de intervalos bootstrap",
        hipotesis0="Lo simulado cae en el rango observado.",
        hipotesis1="No cae.",
        queremos="85 % o más.",
        cero_bueno=False,
        titulo="¿Reconoce el estilo de cada técnico?",
        mide="¿Cuántos estilos simulados caen dentro de lo que se vio?",
        tec="recuperación de estilos: {k} de {n} pares técnico-club; mínimo 85 %",
        pasa="Casi todos los estilos se reconocen.",
        ojo="Menos de 85 % de los estilos se reconocen: el simulador los aplana.",
        tipo="facil",
    ),
    "retro": dict(
        clasica="Diebold-Mariano (con la corrección de Harvey, Leybourne y Newbold)",
        hipotesis0="Aciertan igual que «todo sigue igual».",
        hipotesis1="El simulador acierta mejor.",
        queremos="Rechazar H0: que el simulador acierte mejor.",
        cero_bueno=False,
        titulo="La prueba difícil: cambios de técnico reales",
        mide="¿Le gana a «todo sigue igual» cuando llega un técnico nuevo?",
        tec="prueba de Diebold-Mariano: DM = {dm}, {n} llegadas; error medio {mae} contra {mae_in}",
        pasa="Le gana a suponer que todo sigue igual.",
        ojo="No le gana claro. Por eso decimos que describe estilos y no que predice.",
        tipo="dificil",
    ),
    "partido": dict(
        clasica="χ² de bondad de ajuste",
        hipotesis0="El sorteo jugada a jugada sigue al motor.",
        hipotesis1="No lo sigue.",
        queremos="p > 0.05 (no rechazar H0).",
        cero_bueno=False,
        titulo="¿El partido simulado se parece al cálculo exacto?",
        mide="¿Gana, empata y pierde con la frecuencia correcta? ¿Y los marcadores?",
        tec="{n} partidos sorteados; marcadores: χ² = {chi2}, {gl} grados de libertad",
        pasa="«Ver un partido» muestra partidos posibles de verdad: sin trampas.",
        ojo="Los partidos sorteados se salen del cálculo exacto. Avísanos.",
        tipo="facil",
    ),
}
RESUMEN_CREER = "{ok} de {n} ✅ · {ojo} ⚠️ {expl}"
RESUMEN_EXPLICADA = ("explicada", "explicadas")
RESUMEN_EXPLICADO = "Cada «Ojo» trae su explicación en la tarjeta."
EJE_PREDICHOS = "Puntos predichos"
EJE_REALES = "Puntos reales"
SERIE_SIMULADO = "Simulado"
SERIE_REAL = "Real"
EJE_GOLES = "Goles de un equipo en un partido"
EJE_DIJO = "Lo que dijo el simulador"
EJE_PASO = "Lo que pasó"
NOMBRES_RESULTADO = ("Ganar", "Empatar", "Perder")
NOMBRES_RESULTADO_PROB = {"ganar": "ganar", "empatar": "empate", "perder": "perder"}
SERIE_SIMULADOR = "El simulador"
SERIE_INERCIA = "Suponer que todo sigue igual"
EJE_ERROR_MEDIO = "Error medio"
EJE_ERROR_CUADRATICO = "Error cuadrático"
EJE_DENTRO = "Dentro del rango"
UMBRAL = "mínimo 85 %"
LINEA_PERFECTA = "Acierto perfecto"
CERO = "Cero"
EJE_MARCADOR = "Marcador"
SERIE_EXACTO = "Cálculo exacto"
SERIE_SORTEADO = "Partidos sorteados"


PALABRAS_PROHIBIDAS = (
    "π",
    "θ",
    "φ",
    "μ",
    "logit",
    "softmax",
    "Poisson",
    "Markov",
    "Monte Carlo",
    "posterior",
    "bayesiano",
    "cadena",
    "absorbente",
    "secuencia",
    "familia",
    "parámetro",
    "iteración",
    "réplica",
    "Sobol",
    "Mahalanobis",
    "intervalo de confianza",
    "xG",
    "percentil",
    "componente",
    "intensidad",
    "momentum",
    "cuotas",
    "apostar",
    "desviación estándar",
)


# Rasgos de cada técnico en lenguaje común: bloque → (frase si θ > 0, frase si θ < 0); si el bloque tiene varias entradas llevan {tipo} (jugada o balón parado).
_TIPO_JUGADA = ("ataque directo", "toque sin profundidad", "ataque elaborado")
_TIPO_BP = (
    "tiros de esquina",
    "tiros libres al área",
    "saques de banda largos",
    "tiros libres directos",
)
_RASGOS = {
    "int_at": ("ataca más {tipo}", "ataca menos {tipo}"),
    "int_co": ("obliga al rival a atacar más {tipo}", "obliga al rival a atacar menos {tipo}"),
    "s_marcador": (
        "cambia más su forma de jugar según el marcador",
        "cambia menos su forma de jugar según el marcador",
    ),
    "s_rival": ("se adapta más al rival", "se adapta menos al rival"),
    "l_at": ("genera más jugadas de ataque", "genera menos jugadas de ataque"),
    "l_co": ("deja al rival crear más jugadas", "deja al rival crear menos jugadas"),
    "u_at": ("remata más con {tipo}", "remata menos con {tipo}"),
    "u_co": ("deja rematar más al rival con {tipo}", "deja rematar menos al rival con {tipo}"),
    "w_at": ("remata con más peligro con {tipo}", "remata con menos peligro con {tipo}"),
    "w_co": (
        "concede remates más peligrosos de {tipo}",
        "concede remates menos peligrosos de {tipo}",
    ),
    "rho": ("provoca más {tipo}", "provoca menos {tipo}"),
    "nu_at": ("aprovecha mejor sus {tipo}", "aprovecha peor sus {tipo}"),
    "nu_co": ("defiende peor los {tipo}", "defiende mejor los {tipo}"),
    "alpha": ("hace sus cambios antes", "hace sus cambios más tarde"),
    "gamma": ("prefiere cambios para buscar el gol", "prefiere cambios para cuidar el resultado"),
}
_ENTRADAS = {
    "int_at": ("ataque directo", "ataque elaborado"),
    "int_co": ("ataque directo", "ataque elaborado"),
}


def frase_rasgo(componente: str, signo: int) -> str:
    """«ataca más ataque directo» no se dice: cada entrada lleva su nombre en lenguaje común. componente = `bloque[entrada]`; signo = ±1."""
    bloque, _, resto = componente.partition("[")
    entrada = resto.rstrip("]")
    pos, neg = _RASGOS[bloque]
    plantilla = pos if signo > 0 else neg
    if "{tipo}" not in plantilla:
        return plantilla
    fam = ("directa", "circulación estéril", "ataque elaborado")
    bp = ("corner", "tiro_libre_area", "lateral_largo", "tiro_libre_directo", "penal")
    if bloque in ("int_at", "int_co"):
        nombre = {"Directa": "directo", "Ataque elaborado": "elaborado"}.get(
            entrada, entrada.lower()
        )
    elif entrada in bp:
        nombre = _TIPO_BP[bp.index(entrada)] if bp.index(entrada) < len(_TIPO_BP) else "penales"
    else:
        nombre = _TIPO_JUGADA[
            [f.lower() for f in ("Directa", "Circulación estéril", "Ataque elaborado")].index(
                entrada.lower()
            )
        ]
    return plantilla.format(tipo=nombre)


def etiqueta_tecnico(rasgos: list) -> str:
    frases = [frase_rasgo(r["componente"], r["signo"]) for r in rasgos]
    if not frases:
        return ETIQUETA_SIN_RASGOS
    out = (
        ETIQUETA_TECNICO.format(a=frases[0], b=frases[1])
        if len(frases) > 1
        else ETIQUETA_UN_RASGO.format(a=frases[0])
    )
    return out[0].upper() + out[1:]


# ---------------------------------------------------------------- lámina de la paleta (D-097): para qué sirve cada color
PALETA_USO = {
    "fondo": "Fondo de la página · texto del botón principal (sobre el amarillo)",
    "superficie": "Tarjetas",
    "borde": "Bordes de tarjetas y botones secundarios",
    "elevada": "Barra lateral y tarjetas héroe",
    "texto": "Texto principal",
    "texto2": "Texto secundario",
    "texto3": "Texto terciario · «≈ igual»",
    "amarillo": "América · bueno · pasa · ▲ · botón principal",
    "azul": "Rival · información · ataque elaborado · jugadores",
    "azul_club": "Escudos de iniciales (texto blanco encima)",
    "rojo": "Malo · alerta · ▼ · ataque directo",
    "rojo_texto": "Texto rojo (▼, «Ojo», alertas)",
    "gris": "Neutro · no clasifica · suerte",
    "gris_tipo": "Toque sin profundidad (gris más claro, para el daltonismo)",
    "sombra": "Sombras",
}
