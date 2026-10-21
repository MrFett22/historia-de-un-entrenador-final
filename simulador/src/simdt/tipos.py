"""Tipos del simulador.

Una FICHA de equipo ζ es un vector de componentes (desviaciones respecto a la liga, m = 0).
El registro COMPONENTES fija su orden; cada entrada escalar tiene su propio modelo univariado
en la fase A (etapa 1: celdas; etapa 2: efectos cruzados).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

FAMILIAS = ("Directa", "Circulación estéril", "Ataque elaborado")
K = 3
REF = 1  # Circulación estéril (referencia del logit)
NO_REF = (0, 2)
TIPOS_BP = ("corner", "tiro_libre_area", "lateral_largo", "tiro_libre_directo", "penal")
U = len(TIPOS_BP)
BP_CON_RHO = (0, 1, 2, 3)  # el técnico/plantel mueve la frecuencia de estos
BP_CAPA1 = (0, 1, 2)  # q̄ < 1: tienen capa 1 (prevención)
N_TRAMOS = 6
COLUMNAS_X = ("intercepto", "pierde", "gana", "tramo_final", "local", "elo_100")
TIPOS_CAMBIO = ("defensivo", "mismo puesto", "ofensivo")

# (nombre, etiquetas de las entradas)
_BLOQUES = (
    ("int_at", [FAMILIAS[k] for k in NO_REF]),
    ("int_co", [FAMILIAS[k] for k in NO_REF]),
    ("s_marcador", [""]),
    ("s_rival", [""]),
    ("l_at", [""]),
    ("l_co", [""]),
    ("u_at", list(FAMILIAS)),
    ("u_co", list(FAMILIAS)),
    ("w_at", list(FAMILIAS)),
    ("w_co", list(FAMILIAS)),
    ("rho", [TIPOS_BP[u] for u in BP_CON_RHO]),
    ("nu_at", [TIPOS_BP[u] for u in BP_CAPA1]),
    ("nu_co", [TIPOS_BP[u] for u in BP_CAPA1]),
    ("alpha", [""]),
    ("gamma", [""]),
)


def _registro():
    nombres, bloques, idx = [], {}, 0
    for b, etiquetas in _BLOQUES:
        sl = []
        for e in etiquetas:
            nombres.append(f"{b}[{e}]" if e else b)
            sl.append(idx)
            idx += 1
        bloques[b] = np.array(sl)
    return tuple(nombres), bloques


COMPONENTES, BLOQUES = _registro()
Q = len(COMPONENTES)


def bloque_de(nombre: str) -> str:
    return nombre.split("[")[0]


@dataclass
class Liga:
    """Parámetros de la liga m (todo lo que no es del equipo)."""

    lam_bar: np.ndarray  # (6,) secuencias de juego abierto por minuto por equipo
    h_ritmo: float  # log-ventaja de local en el ritmo (λ ∝ exp(h·(2·local−1)))
    b_liga: np.ndarray  # (K, 6) logit de π; fila REF = 0
    p_bar: np.ndarray  # (K,) P(remate | k)
    g_bar: np.ndarray  # (K,) xG por remate en k
    r_bar: np.ndarray  # (U, 6) saques por minuto por tipo y tramo
    h_bp: float  # log-ventaja de local en la frecuencia de saques
    q_bar: np.ndarray  # (U,) P(remate) de la capa 1 (1 en directo y penal)
    kappa: np.ndarray  # (U,) xG medio por saque con remate
    hazard_base: np.ndarray = field(default_factory=lambda: np.zeros(45))  # logit por minuto 46..90
    hazard_m: np.ndarray = field(default_factory=lambda: np.zeros(3))  # efecto del marcador
    tipo_base: np.ndarray = field(default_factory=lambda: np.zeros((3, 3)))  # (m, tipo) log-pesos
    P_cadenas: np.ndarray | None = None  # (K, 20, 25) cadenas de la liga (M5, H3)
    mu_cadenas: np.ndarray | None = None  # (K, 20) inicio por familia
    P0_cadenas: np.ndarray | None = (
        None  # (K, 20, 25) primer paso de cada familia (D-047); None = artefactos sin P0
    )
    minutos: int = 90
    factor_gol: float = 1.0  # goles reales / xG de la liga (autogoles y definición, D-030)

    def a_dict(self) -> dict:
        return {
            k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in self.__dict__.items()
        }

    @classmethod
    def de_dict(cls, d: dict) -> "Liga":
        kw = {}
        for k, v in d.items():
            kw[k] = np.asarray(v, dtype=float) if isinstance(v, list) else v
        return cls(**kw)


@dataclass
class FichaEquipo:
    nombre: str
    zeta: np.ndarray  # (Q,) o (n_muestras, Q)


@dataclass
class Tecnico:
    nombre: str
    theta: np.ndarray  # (Q,) o (n_muestras, Q): desviación del técnico
    observado: bool = False
    epsilon_america: np.ndarray | None = None  # interacción con el América si se observó
    perillas: dict | None = None
    ilimitado: bool = False  # las perillas están en la escala del modo sin límites (±300); el resultado es «fuera de lo visto»


@dataclass
class Plantel:
    club: str
    phi: np.ndarray  # (n_muestras, Q)


@dataclass
class Entorno:
    """Lo que el América enfrenta: fichas de los rivales, calendario y Elo (H6, H8)."""

    equipos: list[str]
    fichas: np.ndarray  # (n_muestras, 18, Q)
    calendario: np.ndarray  # (153, 2) índices (local, visitante)
    elo: np.ndarray  # (18,)
    liga: Liga
    foco: int  # índice del América


@dataclass
class DistPartido:
    P: np.ndarray  # (B, G+1, G+1) marcador final (goles i, goles j)
    p_gana: np.ndarray
    p_empata: np.ndarray
    p_pierde: np.ndarray
    xpts_i: np.ndarray
    xpts_j: np.ndarray
    eg_i: np.ndarray
    eg_j: np.ndarray
    ocupacion: np.ndarray  # (B, T, 3) P(estado m al inicio del minuto t) desde i
    masa_truncada: np.ndarray  # (B,)
    extra: dict = field(default_factory=dict)


@dataclass
class ResultadoTemporada:
    puntos_exactos: np.ndarray  # (R,) puntos esperados del foco por réplica (suma de xPts)
    puntos: np.ndarray  # (R, S) puntos realizados del foco
    posicion: np.ndarray  # (R, S) 1..18
    gf: np.ndarray  # (R, S)
    gc: np.ndarray  # (R, S)
    resumen: dict = field(default_factory=dict)
    estilo: dict = field(default_factory=dict)
    interno: dict = field(default_factory=dict)  # arreglos para pruebas (no JSON)


@dataclass
class Comparacion:
    delta: np.ndarray  # (R,) diferencia de puntos esperados por réplica
    veredicto: str
    resumen: dict = field(default_factory=dict)
