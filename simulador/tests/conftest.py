import numpy as np
import pytest

from simdt.datos import sintetico


@pytest.fixture(scope="session")
def sint_pequeno():
    """Dos temporadas: rápido para pruebas de estructura y motor."""
    return sintetico.generar(n_temporadas=2)


@pytest.fixture(scope="session")
def liga():
    return sintetico.liga_sintetica()


@pytest.fixture(scope="session")
def rng():
    return np.random.default_rng(20261008)


@pytest.fixture(autouse=True)
def _trabajo_sincrono(request, monkeypatch):
    """Las pruebas de la app que hacen clic en «Simular torneo» esperan el resultado en la siguiente ejecución: el trabajo en segundo plano se espera al lanzarlo (el hilo es el mismo;
    solo se junta). Las pruebas marcadas `asincrono` lo usan tal cual (D-084)."""
    if request.node.get_closest_marker("asincrono"):
        return
    from simdt.trabajo import Trabajo

    original = Trabajo.iniciar

    def iniciar_y_esperar(self):
        original(self)
        self.esperar()
        return self

    monkeypatch.setattr(Trabajo, "iniciar", iniciar_y_esperar)
