$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Project Python environment is missing. Run: uv venv --python 3.11 .venv; uv pip install --python .venv\Scripts\python.exe -r requirements.txt"
}

# Preserve the older data/chroma store and run on the clean, compatible store.
$env:PYTHONUTF8 = "1"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:CHROMA_PATH = Join-Path $projectRoot "data\chroma_active"
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
