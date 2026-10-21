"""Servicio de simulación: lo que la app llama (sin Streamlit).

sim = Simulador()                      # carga artefactos/
t = sim.tecnico_preset("Jorge Guillermo Almada Alves")   # o sim.tecnico_perillas({...})
res = sim.simular(t, "rapido")
cmp = sim.comparar(t, sim.tecnico_promedio(), "rapido")
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import artefactos, config
from .estimacion.fichas import ficha_foco
from .modelos import cambios as mcambios
from .motor.comparar import comparar
from .motor.temporada import muestras_replicas, precalcular, simular_temporada
from .perillas import ejes as mejes
from .perillas import mapeo
from .perillas.coherencia import Coherencia
from .tipos import BLOQUES, COMPONENTES, Q, Tecnico

_CANDADO_PRE = threading.Lock()

CREA = "__crea_tu_propio_tecnico__"  # primera opción del selector: se muestra como «Crea tu propio técnico» (app/textos.py)
NEUTRO = "Estilo neutro"  # θ = 0, el punto de partida de «Crea tu propio técnico» y la referencia de la calificación (nunca se muestra con ese nombre)


@dataclass
class Resultado:
    temporada: object
    estilo: dict
    tecnico: Tecnico
    segundos: float


class Simulador:
    def __init__(self, directorio=None):
        self.dir = Path(directorio or config.ARTEFACTOS)
        self.p = artefactos.cargar(self.dir)
        self.cfg = config.cargar()
        self.semilla = self.cfg["semilla"]
        self.calendario = np.asarray(self.p.meta["calendario"])
        self.elo = np.asarray(self.p.meta["elo"], dtype=float)
        self.foco = self.p.piezas.foco
        self._pre = {}
        self.memo = {}  # resultados de referencia (Almada, estilo neutro) que comparten las sesiones (D-084)
        pares = self.p.pares[list(COMPONENTES)].to_numpy()
        self.coherencia = Coherencia(pares) if len(pares) > len(BLOQUES) else None
        # perillas (D-057): ejes en la escala de los técnicos reales
        self.ejes = mejes.construir(
            self.p.piezas.theta_tec,
            {x["nombre"]: x.get("partidos", 0) for x in self.p.presets},
            self.p.escalas,
            self.p.liga,
        )

    # ---------------------------------------------------------------- técnicos
    def nombres_preset(self) -> list[str]:
        return [x["nombre"] for x in self.p.presets]

    # ---------------------------------------------------------------- lista corta (D-053)
    def nombres_lista_corta(self) -> list[str]:
        """Técnicos que ofrece la app: el vigente, su antecesor y los medoides (por cuántos representan). Sin lista corta en los artefactos: todos los presets."""
        if not self.p.meta.get("lista_corta"):
            return self.nombres_preset()
        orden = {"vigente": 0, "antecesor": 1, "medoide": 2}
        xs = [x for x in self.p.presets if x.get("lista_corta")]
        return [
            x["nombre"]
            for x in sorted(
                xs, key=lambda x: (orden.get(x.get("rol"), 3), -x.get("representa", 0), x["nombre"])
            )
        ]

    def info_preset(self, nombre: str) -> dict:
        return next((x for x in self.p.presets if x["nombre"] == nombre), {})

    def rango_reales(self, ilimitado: bool = False) -> dict:
        """Dónde está la mayoría (del 10 al 90 %) de los técnicos reales en la escala de cada deslizador (la misma escala del deslizador, normal o sin límites)."""
        out = {}
        for k in mejes.CLAVES_EJES:
            e = self.ejes[k]
            pos = np.array([e._pos_de_z(z, ilimitado) for z in e.z_tec])
            out[k] = (int(np.floor(np.quantile(pos, 0.10))), int(np.ceil(np.quantile(pos, 0.90))))
        return out

    def tipos_de_jugada(self) -> list[dict]:
        """Promedios de la liga de los tres tipos de jugada (directo, toque sin profundidad, elaborado). Los cuatro datos (% de jugadas, toques promedio, % que termina en
        remate y goles por cada 100 jugadas) salen de la FUENTE si `perfiles_tecnicos.json` trae `tipos_fuente` (exportado de mezcla_K3.npz con la cadena completa: π 35.4 / 26.3 / 38.3 %,
        remate 14.0 / 2.6 / 12.2 %); lo que no traiga se calcula de la cadena de `cadenas.npz` (probabilidades de absorción: toques promedio, % que termina en remate y goles por 100 jugadas),
        y el % de jugadas, de `mezcla_liga` (juego abierto, sin pelota parada)."""
        L = self.p.liga
        fuente = (self.perfiles() or {}).get("tipos_fuente") or {}
        pi = fuente.get("pi") or self.p.meta["mezcla_liga"]
        out = []
        for k in range(3):
            Q = L.P_cadenas[k][:, :20]
            R = L.P_cadenas[k][:, 20:25]
            N = np.linalg.inv(np.eye(20) - Q)
            B = N @ R  # (20, 5): GOL, REMATE, PERDIDA, FUERA, INTERRUPCION
            uno = N @ np.ones(20)
            mu = L.mu_cadenas[k]
            if L.P0_cadenas is not None:
                P0 = L.P0_cadenas[k]
                toques = float(1 + mu @ (P0[:, :20] @ uno))
                absor = mu @ P0[:, 20:25] + mu @ (P0[:, :20] @ B)
            else:
                toques = float(mu @ uno)
                absor = mu @ B
            d = {
                "pct": 100 * float(pi[k]),
                "toques": toques,
                "remate": 100 * float(absor[0] + absor[1]),
                "goles100": 100 * float(absor[0]),
            }
            for clave, dest in (
                ("toques", "toques"),
                ("remate", "remate"),
                ("goles100", "goles100"),
            ):
                v = fuente.get(clave)
                if v is not None and len(v) == 3:
                    d[dest] = float(v[k])
            out.append(d)
        return out

    def perfiles(self) -> dict | None:
        """`perfiles_tecnicos.json` (lo que dicen los datos del equipo de cada técnico, D-058) si viene con los artefactos."""
        import json

        if not hasattr(self, "_perfiles"):
            f = self.dir / "perfiles_tecnicos.json"
            self._perfiles = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
        return self._perfiles

    def nombre_perilla_defensa(self) -> str | None:
        pf = self.perfiles()
        return (pf or {}).get("perilla_defensa", {}).get("nombre")

    def validacion_total(self):
        """(graficas_validacion.json, validacion.json, ruta del reporte técnico) o (None, None, None): de SIMDT_VALIDACION, de la carpeta de los artefactos o de reportes/validacion/."""
        import json
        import os

        carpetas = (
            [Path(os.environ["SIMDT_VALIDACION"])] if os.environ.get("SIMDT_VALIDACION") else []
        )
        carpetas += [self.dir, config.VALIDACION]
        for d in carpetas:
            f = Path(d) / "graficas_validacion.json"
            if f.exists():
                g = json.loads(f.read_text(encoding="utf-8"))
                v = Path(d) / "validacion.json"
                val = json.loads(v.read_text(encoding="utf-8")) if v.exists() else None
                md = (
                    Path(d) / g["reporte"]
                    if g.get("reporte") and (Path(d) / g["reporte"]).exists()
                    else None
                )
                return g, val, md
        return None, None, None

    def validacion(self):
        """(datos de las gráficas de confiabilidad, ruta del reporte técnico) o (None, None). Busca en SIMDT_VALIDACION, en la carpeta de los artefactos y en reportes/validacion/."""
        import json
        import os

        carpetas = (
            [Path(os.environ["SIMDT_VALIDACION"])] if os.environ.get("SIMDT_VALIDACION") else []
        )
        carpetas += [self.dir, config.VALIDACION]
        for d in carpetas:
            f = Path(d) / "graficas_validacion.json"
            if f.exists():
                datos = json.loads(f.read_text(encoding="utf-8"))
                md = (
                    Path(d) / datos["reporte"]
                    if datos.get("reporte") and (Path(d) / datos["reporte"]).exists()
                    else None
                )
                return datos, md
        return None, None

    def tecnico_preset(self, nombre: str) -> Tecnico:
        if nombre in (CREA, NEUTRO):
            return self.tecnico_promedio(nombre)
        th = self.p.piezas.theta_tec[nombre]
        return Tecnico(nombre, th, observado=True, perillas=self.ejes.posiciones(th.mean(0)))

    def tecnico_promedio(self, nombre: str = NEUTRO) -> Tecnico:
        return Tecnico(
            nombre, np.zeros(Q), observado=False, perillas=self.ejes.posiciones(np.zeros(Q))
        )

    def tecnico_perillas(
        self,
        perillas: dict,
        base: Tecnico | None = None,
        nombre: str = "Tu técnico",
        ilimitado: bool = False,
    ) -> Tecnico:
        """Técnico a partir de las perillas. Con `base`, solo se mueve lo que difiere de las perillas de la base (en la MISMA escala: normal o sin límites)."""
        if base is None:
            th0 = np.zeros(Q)
        else:
            th0 = base.theta.mean(0) if base.theta.ndim == 2 else base.theta
        p0 = self.ejes.posiciones(th0, ilim=ilimitado)
        th = mejes.aplicar_perillas(self.ejes, perillas, th0, p0, ilimitado)
        return Tecnico(nombre, th, observado=False, perillas=dict(perillas), ilimitado=ilimitado)

    def posicion_en_mapa(self, perillas: dict) -> tuple[float, float]:
        return float(perillas["ataca"]), float(perillas["defiende"])

    def fuera_de_la_zona(self, perillas: dict, ilimitado: bool = False) -> bool:
        """¿Esa combinación de «cómo ataca» y «cómo defiende» queda fuera de donde han jugado los técnicos reales (la zona NO se ajusta al punto)?
        Con el modo sin límites, cualquier perilla más allá de ±100 también es «fuera de lo visto»."""
        if ilimitado and any(abs(perillas[k]) > 100 for k in mejes.CLAVES_EJES):
            return True
        return not self.ejes.en_zona(perillas["ataca"], perillas["defiende"])

    def perillas_de(self, t: Tecnico, ilimitado: bool = False) -> dict:
        """Perillas del técnico en la escala pedida (la normal, o la del modo sin límites para los cuatro ejes)."""
        if not ilimitado:
            return dict(t.perillas or {})
        th = t.theta.mean(0) if t.theta.ndim == 2 else t.theta
        return {
            **(t.perillas or {}),
            **{
                k: v
                for k, v in self.ejes.posiciones(th, ilim=True).items()
                if k in mejes.CLAVES_EJES
            },
        }

    def perillas_cambiadas(self, t: Tecnico, perillas: dict, ilimitado: bool = False) -> bool:
        base = (
            self.perillas_de(t, ilimitado)
            if not (t.ilimitado and ilimitado)
            else (t.perillas or {})
        )
        if not base:
            return True
        for k, v in perillas.items():
            a = base.get(k)
            if isinstance(v, (tuple, list)):
                if (
                    a is None
                    or np.max(np.abs(np.asarray(v, float) - np.asarray(a, float))) > 0.0051
                ):  # resolución del deslizador: 1 %
                    return True
            elif v != a:
                return True
        return False

    def es_extremo(self, t: Tecnico) -> bool:
        if self.coherencia is None or t.observado:
            return False
        return self.coherencia.es_extremo(t.theta if t.theta.ndim == 1 else t.theta.mean(0))

    # ---------------------------------------------------------------- simulación
    def _modo(self, modo: str):
        m = self.cfg["simulacion"][modo if modo in ("preciso", "profundo") else "rapido"]
        return int(m["R"]), int(m["S"])

    def _precalculo(self, idx, R):
        with (
            _CANDADO_PRE
        ):  # dos sesiones pueden pedirlo a la vez (la simulación corre en un hilo, D-084)
            if R not in self._pre:
                # rápido (R = 100) y preciso (R = 1000) vienen precalculados en la carpeta de ESTOS artefactos (D-046, D-052)
                ruta = self.dir / f"cache_rivales_R{R}.npz"
                self._pre[R] = precalcular(
                    self.p.liga,
                    self.p.piezas.fichas,
                    self.calendario,
                    self.elo,
                    self.foco,
                    indices=idx,
                    ruta=ruta,
                )
            return self._pre[R]

    def n_versiones(self, modo: str) -> tuple[int, int]:
        """(versiones de los equipos que hay, distintas que usa ese modo): lo que limita la precisión de los puntos esperados (D-084)."""
        n = self.p.piezas.fichas.shape[0]
        R, _ = self._modo(modo)
        return int(n), int(len(np.unique(muestras_replicas(n, R, self.semilla))))

    def tam_bloque(self, modo: str = "rapido") -> int:
        """Réplicas por bloque de la simulación en segundo plano: `simulacion.torneos_por_bloque` ÷ S (al menos una). Así la memoria de un bloque no crece con S (D-095)."""
        return max(1, int(self.cfg["simulacion"]["torneos_por_bloque"]) // self._modo(modo)[1])

    def cifras_modo(self, modo: str) -> dict:
        """Lo que se simula en ese modo, para decirlo en pantalla: torneos (R × S), partidos por torneo y partidos en total; todo sale de R, S y el calendario."""
        R, S = self._modo(modo)
        n_partidos = int(len(self.calendario))
        return {
            "R": R,
            "S": S,
            "torneos": R * S,
            "partidos_por_torneo": n_partidos,
            "partidos": R * S * n_partidos,
        }

    def simular(
        self,
        t: Tecnico,
        modo: str = "rapido",
        con_estilo: bool = True,
        tam_bloque: int | None = None,
        progreso=None,
        cancelar=None,
    ) -> Resultado:
        """`tam_bloque`: réplicas por bloque (None = todas en uno); el resultado es EXACTAMENTE el mismo con cualquier tamaño (D-084). `progreso(hechos, total)` y `cancelar()`
        se consultan entre bloques."""
        t0 = time.perf_counter()
        R, S = self._modo(modo)
        idx = muestras_replicas(self.p.piezas.fichas.shape[0], R, self.semilla)
        pre = self._precalculo(idx, R)
        obs = t.nombre if t.observado else None
        ff = ficha_foco(self.p.piezas, t.theta, idx, obs)
        res = simular_temporada(
            self.p.liga,
            self.p.piezas.fichas,
            ff,
            self.calendario,
            self.elo,
            self.foco,
            idx,
            S,
            self.semilla,
            pre,
            con_estilo=con_estilo,
            tam_bloque=tam_bloque,
            progreso=progreso,
            cancelar=cancelar,
        )
        estilo = self._estilo(res, ff) if con_estilo else {}
        return Resultado(res, estilo, t, time.perf_counter() - t0)

    def _estilo(self, res, ff) -> dict:
        e = res.estilo
        L = self.p.liga
        alpha = float(ff[:, BLOQUES["alpha"][0]].mean())
        gamma = float(ff[:, BLOQUES["gamma"][0]].mean())
        camb = mcambios.resumen(L, alpha, gamma, e["ocupacion_t"])
        out = {
            "pi": e["pi_i"].tolist(),
            "pi_rival": e["pi_j"].tolist(),
            "goles_k_favor": e["goles_k_i"].tolist(),
            "goles_k_contra": e["goles_k_j"].tolist(),
            "goles_bp_favor": e["goles_bp_i"].tolist(),
            "goles_bp_contra": e["goles_bp_j"].tolist(),
            "N_k": e["N_k_i"].tolist(),
            "N_k_rival": e["N_k_j"].tolist(),
            "eg_favor": e["eg_favor"],
            "eg_contra": e["eg_contra"],
            "cambios": camb,
        }
        return out

    def comparar(self, t1: Tecnico, t2: Tecnico, modo: str = "rapido"):
        r1 = self.simular(t1, modo)
        r2 = self.simular(t2, modo)
        return comparar(r1.temporada, r2.temporada), r1, r2
