"""Perillas de la app v3: cada una es UN eje en la escala de los técnicos reales (D-057).

Un eje junta varias componentes de θ en una sola dirección (en unidades de σ_θ de cada componente) y se mueve entre el técnico
más bajo y el más alto de los que tienen suficientes partidos: de ahí no se puede salir. Mover un eje cambia solo la parte de θ
que va a lo largo del eje; lo demás del técnico elegido se conserva.

  ataca       int_at[Directa], int_at[Ataque elaborado]            componente principal de los técnicos reales; -100 = el más directo, +100 = el más elaborado
  defiende    int_co[Directa], int_co[Ataque elaborado], u_co[Directa]    ídem; -100 = deja jugar al rival, +100 = lo obliga a jugar largo y apurado
  pp_contra   nu_co[*]   percentil 1-99 (1 = de las peores defendiendo pelota parada, 99 = de las mejores)
  pp_favor    rho[*] y nu_at[*]   percentil 1-99 (1 = de las peores, 99 = de las mejores)
Aparte, en «ajustes finos»: reaccion (s_marcador y s_rival juntas), cambios_momento (alpha) y cambios_tipo (gamma), con el mapeo de siempre.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .. import config
from ..tipos import BLOQUES, COMPONENTES, Q
from . import mapeo

MIN_PARTIDOS = 30  # los técnicos que definen la escala
CLAVES_EJES = ("ataca", "defiende", "pp_contra", "pp_favor")
CLAVES_FINAS = ("reaccion", "cambios_momento", "cambios_tipo")
CLAVES = CLAVES_EJES + CLAVES_FINAS
BIPOLARES = ("ataca", "defiende")
# componente -> perilla que la mueve (el resto no tiene perilla; ver D-057)
COMPONENTES_DE = {
    "ataca": ["int_at[Directa]", "int_at[Ataque elaborado]"],
    "defiende": ["int_co[Directa]", "int_co[Ataque elaborado]", "u_co[Directa]"],
    "pp_contra": [c for c in COMPONENTES if c.startswith("nu_co[")],
    "pp_favor": [c for c in COMPONENTES if c.startswith("rho[") or c.startswith("nu_at[")],
    "reaccion": ["s_marcador", "s_rival"],
    "cambios_momento": ["alpha"],
    "cambios_tipo": ["gamma"],
}


def _idx(nombres) -> np.ndarray:
    return np.array([COMPONENTES.index(n) for n in nombres], dtype=int)


@dataclass
class Eje:
    clave: str
    idx: np.ndarray
    sig: np.ndarray  # σ_θ de cada componente del eje
    v: np.ndarray  # vector unitario en unidades de σ_θ
    z_tec: np.ndarray  # proyección de cada técnico de la escala (orden de `nombres`)
    nombres: list = field(default_factory=list)
    invertido: bool = False  # percentil: True si z alto es «peor»

    @property
    def bipolar(self) -> bool:
        return self.clave in BIPOLARES

    @property
    def z_lo(self) -> float:
        return float(self.z_tec.min())

    @property
    def z_hi(self) -> float:
        return float(self.z_tec.max())

    def z(self, theta: np.ndarray) -> float:
        return float((np.asarray(theta, float)[self.idx] / self.sig) @ self.v)

    def posicion(self, theta: np.ndarray, ilim: bool = False) -> int:
        """Valor del deslizador de un θ: -100..100 (bipolar, 0 = promedio de la liga) o 1..99 (percentil). Con `ilim` (modo sin límites, D-062) todos los ejes
        usan la escala bipolar -300..300: ±100 = el técnico real más extremo, 0 = el promedio de la liga, ±300 = tres veces eso."""
        return self._pos_de_z(self.z(theta), ilim)

    def _s(self, z):
        """Puntaje «mejor hacia arriba»: en pelota parada en contra un z alto es peor."""
        return -z if self.invertido else z

    def _pos_de_z(self, z: float, ilim: bool = False) -> int:
        if self.bipolar or ilim:
            s = self._s(z) if not self.bipolar else z
            s_tec = self._s(self.z_tec) if not self.bipolar else self.z_tec
            den = s_tec.max() if s > 0 else -s_tec.min()
            tope = 300 if ilim else 100
            return int(np.clip(round(100 * s / den), -tope, tope)) if den > 1e-12 else 0
        p = 100 * (np.sum(self.z_tec < z) + 0.5 * np.sum(self.z_tec == z)) / len(self.z_tec)
        return int(np.clip(round(100 - p if self.invertido else p), 1, 99))

    def pct(self, z: float) -> float:
        """De cada 100 técnicos reales, a cuántos supera este z (0-100)."""
        return float(
            100 * (np.sum(self.z_tec < z) + 0.5 * np.sum(self.z_tec == z)) / len(self.z_tec)
        )

    def z_de_posicion(self, pos: float, ilim: bool = False) -> float:
        if self.bipolar or ilim:
            s_tec = self._s(self.z_tec) if not self.bipolar else self.z_tec
            s = float(pos / 100 * (s_tec.max() if pos > 0 else -s_tec.min()))
            return -s if (self.invertido and not self.bipolar) else s
        p = 100 - pos if self.invertido else pos
        return float(np.quantile(self.z_tec, np.clip(p, 0, 100) / 100))

    def aplicar(self, theta: np.ndarray, pos: float, ilim: bool = False) -> np.ndarray:
        """θ con el componente a lo largo del eje puesto en `pos`; la parte perpendicular al eje no cambia."""
        th = np.array(theta, dtype=float)
        u = th[self.idx] / self.sig
        z_nuevo = self.z_de_posicion(pos, ilim)
        u = u - (u @ self.v) * self.v + z_nuevo * self.v
        th[self.idx] = u * self.sig
        return th

    def limites_de(self, ilim: bool = False) -> tuple[int, int]:
        return (-300, 300) if ilim else self.limites

    @property
    def limites(self) -> tuple[int, int]:
        return (-100, 100) if self.bipolar else (1, 99)


def _orienta_presion(v: np.ndarray) -> np.ndarray:
    """Eje de «¿Qué tanto presiona?» (D-058): más presión = int_co[Directa] arriba (el rival juega más directo) y u_co[Directa] abajo (concede menos
    remates). El eje principal se voltea para que sea así; si una de las dos cargas quedara con el signo contrario se anula (y se renormaliza),
    para que en el extremo máximo int_co[Directa] > 0 y u_co[Directa] < 0 siempre. Orden de las cargas: int_co[Directa], int_co[Ataque elaborado], u_co[Directa]."""
    v = np.array(v, dtype=float)
    if v[0] - v[2] < 0:
        v = -v
    v[0], v[2] = max(v[0], 0.0), min(v[2], 0.0)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else np.array([1.0, 0.0, -1.0]) / np.sqrt(2)


def _pca1(X: np.ndarray) -> np.ndarray:
    Xc = X - X.mean(0)
    _, _, vt = np.linalg.svd(Xc, full_matrices=False)
    return vt[0] / np.linalg.norm(vt[0])


@dataclass
class Ejes:
    ejes: dict
    nombres: list
    puntos: (
        np.ndarray
    )  # (n_tecnicos, 2): posición en «ataca» y «defiende» de cada técnico de la escala
    esc: object = None
    esc_liga: object = None  # la Liga, para el mapeo de los ajustes finos

    def __getitem__(self, k: str) -> Eje:
        return self.ejes[k]

    def posiciones(
        self, theta: np.ndarray, base_fina: dict | None = None, ilim: bool = False
    ) -> dict:
        th = np.asarray(theta, float)
        out = {k: self.ejes[k].posicion(th, ilim) for k in CLAVES_EJES}
        out.update(mapeo_fino_a_perillas(th, self.esc, base_fina))
        return out

    def en_zona(self, ataca: float, defiende: float) -> bool:
        """¿La combinación cae dentro del casco convexo de los técnicos reales (con una pizca de tolerancia)?"""
        h = self.casco()
        if h is None:
            return True
        from scipy.spatial import Delaunay

        return bool(Delaunay(h).find_simplex(np.array([[ataca, defiende]]), tol=1e-6)[0] >= 0)

    def casco(self) -> np.ndarray | None:
        """Vértices del casco convexo de los técnicos reales en el plano (ataca, defiende); None si hay menos de 3 o están alineados."""
        from scipy.spatial import ConvexHull

        if len(self.puntos) < 3:
            return None
        try:
            h = ConvexHull(self.puntos)
        except Exception:  # puntos alineados
            return None
        return self.puntos[h.vertices]


def mapeo_fino_a_perillas(th: np.ndarray, esc, base_fina: dict | None = None) -> dict:
    cfg = config.cargar()["perillas"]
    qm, qr = BLOQUES["s_marcador"][0], BLOQUES["s_rival"][0]
    s = 1 + 0.5 * (esc.b0[qm] + th[qm] + esc.b0[qr] + th[qr])
    out = {"reaccion": mapeo._cercana(s, cfg["reactividad"])}
    qa = BLOQUES["alpha"][0]
    out["cambios_momento"] = (
        int(np.clip(round(100 * mapeo.norm.cdf(-th[qa] / esc.tau(qa))), 1, 99))
        if esc.tau(qa) > 0
        else 50
    )
    qg = BLOQUES["gamma"][0]
    if esc.tau(qg) > 0:
        out["cambios_tipo"] = mapeo._cercana(
            100 * mapeo.norm.cdf(th[qg] / esc.tau(qg)), cfg["tipo_cambio_percentil"]
        )
    else:
        out["cambios_tipo"] = "Mismo puesto"
    return out


def construir(
    theta_tec: dict, partidos: dict, esc, liga=None, min_partidos: int = MIN_PARTIDOS
) -> Ejes:
    """Ejes a partir de las medias posteriores de θ de los técnicos con al menos `min_partidos` partidos."""
    nombres = [n for n in theta_tec if partidos.get(n, 0) >= min_partidos]
    if len(nombres) < 4:  # artefactos de demostración chicos: se usan todos
        nombres = list(theta_tec)
    M = np.array(
        [
            np.asarray(theta_tec[n]).mean(0)
            if np.asarray(theta_tec[n]).ndim == 2
            else np.asarray(theta_tec[n])
            for n in nombres
        ]
    )
    ejes = {}
    for clave in CLAVES_EJES:
        idx = _idx(COMPONENTES_DE[clave])
        sig = np.array(
            [
                max(esc.tau(q), 1e-6) if esc.tau(q) > 0 else max(float(esc.sigma_theta[q]), 1e-6)
                for q in idx
            ]
        )
        U = M[:, idx] / sig
        if clave == "ataca":
            v = _pca1(U)
            if v @ np.array([-1.0, 1.0]) < 0:
                v = -v
        elif clave == "defiende":
            v = _orienta_presion(_pca1(U))
        else:
            v = np.ones(len(idx)) / np.sqrt(len(idx))
        ejes[clave] = Eje(clave, idx, sig, v, U @ v, nombres, invertido=(clave == "pp_contra"))
    puntos = np.array([[ejes["ataca"].posicion(t), ejes["defiende"].posicion(t)] for t in M])
    return Ejes(ejes, nombres, puntos, esc, liga)


def aplicar_perillas(
    ejes: Ejes, perillas: dict, theta_base: np.ndarray, perillas_base: dict, ilim: bool = False
) -> np.ndarray:
    """θ de un técnico a partir de las perillas. Solo se tocan las perillas que difieren de las del técnico de partida
    (si no, se conserva su θ exacto). Siempre dentro de la caja de técnicos plausibles (`Escalas.limitar`)."""
    th = np.array(theta_base, dtype=float)
    tocadas: list[int] = []
    for k in CLAVES_EJES:
        if k in perillas and perillas[k] != perillas_base.get(k):
            e = ejes[k]
            th = e.aplicar(th, perillas[k], ilim)
            tocadas += list(e.idx)
    fino = {}
    if "reaccion" in perillas and perillas["reaccion"] != perillas_base.get("reaccion"):
        fino["reaccion_marcador"] = fino["reaccion_rival"] = perillas["reaccion"]
    for k in ("cambios_momento", "cambios_tipo"):
        if k in perillas and perillas[k] != perillas_base.get(k):
            fino[k] = perillas[k]
    if fino:
        th = mapeo.perillas_a_tecnico(fino, ejes.esc_liga, ejes.esc, th)
    return (
        ejes.esc.limitar(th, tocadas) if (tocadas and not ilim) else th
    )  # sin límites: no se acota a los técnicos plausibles
