Set-Location "$PSScriptRoot"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Start-Sleep -Seconds 1
Start-Process "http://127.0.0.1:3000"
python -m http.server 3000
