# En Windows sin make: usa  python -m simdt.tareas <objetivo>  (mismos objetivos)
PY ?= .venv/Scripts/python
ifeq ($(OS),)
PY = .venv/bin/python
endif

instalar:
	python -m venv .venv && $(PY) -m pip install -e .
sintetico:
	$(PY) -m simdt.tareas sintetico
calibrar:
	$(PY) -m simdt.calibrar --datos $(DATOS)
validar:
	$(PY) -m simdt.tareas validar
pruebas:
	$(PY) -m pytest -q
app:
	$(PY) -m streamlit run app.py
todo:
	$(PY) -m simdt.correr_todo
.PHONY: instalar sintetico calibrar validar pruebas app todo
