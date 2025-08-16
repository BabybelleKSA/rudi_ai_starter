Set-Location "$PSScriptRoot"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
uvicorn app:app --reload --port 5000
