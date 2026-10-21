# Abre el simulador en http://localhost:8501 con los parámetros publicados (simulador/artefactos/).
# Uso, desde cualquier carpeta:  .\simulador\correr_app.ps1
# Python: el de $env:SIMDT_PYTHON si está definido; si no, simulador\.venv o .venv en la raíz.
$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot
$Py = $env:SIMDT_PYTHON
if (-not $Py) {
    foreach ($v in @((Join-Path $Raiz "simulador\.venv"), (Join-Path $Raiz ".venv"))) {
        foreach ($c in @((Join-Path $v "Scripts\python.exe"), (Join-Path $v "bin/python"))) {
            if (Test-Path $c) { $Py = $c; break }
        }
        if ($Py) { break }
    }
}
if (-not $Py) {
    Write-Error "No encontré un entorno de Python. Créalo con: cd simulador; python -m venv .venv; .venv\Scripts\python -m pip install -e ."
    exit 1
}
$Puerto = if ($env:PUERTO) { $env:PUERTO } else { "8501" }
Set-Location $Raiz  # Streamlit lee .streamlit/config.toml de la carpeta desde donde corre
& $Py -m streamlit run simulador/app.py --server.headless true --server.port $Puerto
