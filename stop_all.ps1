# Kills anything using ports 5000 (backend) and 3000 (frontend), if running.
$ports = 5000,3000
foreach ($p in $ports) {
  $lines = netstat -ano | Select-String ":$p\s"
  foreach ($line in $lines) {
    $pid = ($line.ToString().Trim().Split() | Select-Object -Last 1)
    try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {}
  }
}

# Also try common process names (dev convenience)
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "uvicorn" -Force -ErrorAction SilentlyContinue
