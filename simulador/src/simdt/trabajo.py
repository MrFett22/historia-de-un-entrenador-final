"""Simulación en segundo plano (D-084): la app no se congela mientras corre y el avance es REAL.

Un `Trabajo` corre una lista de tareas (técnico, modo, con o sin estilo) en un hilo, por bloques de réplicas (`simulacion.torneos_por_bloque` del config). Cada bloque que termina
suma al avance; `cancelar()` para entre bloques. No hay esperas ni simulaciones de relleno: el avance es (bloques hechos) / (bloques totales) y el tiempo restante sale del ritmo
medido hasta ese momento. Cada sesión de la app tiene su propio `Trabajo`; no comparten estado. El hilo no toca Streamlit (solo escribe en el objeto y en `sim.memo`).
"""

from __future__ import annotations

import math
import os
import threading
import time
import traceback
from dataclasses import dataclass, field

from .motor.temporada import Cancelado


def fijar_hilos(n: int | None = None) -> int:
    """Limita los hilos de numba (la nube es una máquina chica): `rendimiento.hilos_numba` del config o la variable SIMDT_HILOS; nunca más que los procesadores. En numba el
    ajuste es POR HILO: se llama también al arrancar el hilo de la simulación. Devuelve los hilos usados (0 si no hay numba)."""
    from . import config
    from .motor import _nucleo

    if not _nucleo.DISPONIBLE:
        return 0
    import numba

    pedido = int(
        os.environ.get("SIMDT_HILOS") or n or config.cargar()["rendimiento"]["hilos_numba"]
    )
    hilos = max(1, min(pedido, numba.config.NUMBA_NUM_THREADS, os.cpu_count() or 1))
    numba.set_num_threads(hilos)
    return hilos


@dataclass
class Tarea:
    clave: str  # «objetivo», «actual», «neutro»… (donde se guarda el resultado)
    tecnico: object
    modo: str
    con_estilo: bool = True
    memo: tuple | None = None  # si trae (clave, modo), el resultado también se guarda en `sim.memo`


@dataclass
class Trabajo:
    sim: object
    tareas: list
    meta: dict = field(default_factory=dict)
    estado: str = "nuevo"  # nuevo | corriendo | listo | cancelado | error
    hechos: int = 0  # bloques terminados (solo crece)
    total: int = 0
    resultados: dict = field(default_factory=dict)
    error: str = ""
    aplicado: bool = False
    t0: float = 0.0
    t1: float = 0.0
    hilos: int = 0

    def __post_init__(self):
        self._parar = threading.Event()
        self._hilo = None
        self.total = sum(
            max(1, math.ceil(self.sim._modo(t.modo)[0] / self.sim.tam_bloque(t.modo)))
            for t in self.tareas
        )

    def iniciar(self) -> "Trabajo":
        self.estado = "corriendo"
        self.t0 = time.perf_counter()
        self._hilo = threading.Thread(target=self._correr, daemon=True, name="simdt-simulacion")
        self._hilo.start()
        return self

    def cancelar(self) -> None:
        self._parar.set()

    def esperar(self, tiempo: float | None = None) -> None:
        if self._hilo is not None:
            self._hilo.join(tiempo)

    def _correr(self) -> None:
        try:
            self.hilos = fijar_hilos()
            for tarea in self.tareas:
                base = self.hechos

                def progreso(k, n, base=base):
                    self.hechos = max(self.hechos, base + k)  # monótono

                r = self.sim.simular(
                    tarea.tecnico,
                    tarea.modo,
                    tarea.con_estilo,
                    tam_bloque=self.sim.tam_bloque(tarea.modo),
                    progreso=progreso,
                    cancelar=self._parar.is_set,
                )
                self.resultados[tarea.clave] = r
                if tarea.memo is not None:
                    self.sim.memo[tarea.memo] = r
            self.hechos = self.total
            self.estado = "listo"
        except Cancelado:
            self.resultados.clear()
            self.estado = "cancelado"
        except Exception:  # noqa: BLE001  (se muestra un mensaje; el detalle queda en el registro)
            self.error = traceback.format_exc()
            self.estado = "error"
        finally:
            self.t1 = time.perf_counter()

    @property
    def progreso(self) -> float:
        return (
            1.0
            if self.estado == "listo"
            else min(self.hechos / self.total, 1.0)
            if self.total
            else 0.0
        )

    @property
    def transcurrido(self) -> float:
        return (self.t1 or time.perf_counter()) - self.t0 if self.t0 else 0.0

    def restante(self) -> float | None:
        """Segundos que faltan según el ritmo medido (None mientras no hay un bloque terminado)."""
        p = self.progreso
        if self.estado != "corriendo" or p <= 0:
            return None
        return self.transcurrido * (1 - p) / p
