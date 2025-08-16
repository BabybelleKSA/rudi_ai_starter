# Launch backend and frontend in separate PowerShell windows
Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass','-File', (Join-Path $PSScriptRoot 'backend\start_backend.ps1')
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass','-File', (Join-Path $PSScriptRoot 'frontend\start_frontend.ps1')
