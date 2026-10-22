# Starts backend (port 8000) and frontend (port 5173) for local development on Windows.
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "ml"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; python -m uvicorn app.main:app --app-dir backend --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
