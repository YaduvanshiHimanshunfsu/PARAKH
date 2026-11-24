Write-Host "=== TCP connections on port 8000 ===" -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize

Write-Host "`n=== All python.exe processes (CommandLine) ===" -ForegroundColor Cyan
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, ParentProcessId, CommandLine | Format-List

Write-Host "`n=== Check if PID 31476 exists ===" -ForegroundColor Cyan
Get-Process -Id 31476 -ErrorAction SilentlyContinue

Write-Host "`n=== Processes with uvicorn in command line ===" -ForegroundColor Cyan
Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like "*uvicorn*" } | Select-Object ProcessId, ParentProcessId, CommandLine | Format-List

Write-Host "`n=== Who actually owns port 8000 (deep check) ===" -ForegroundColor Cyan
$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
foreach ($c in $conn) {
    $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "PID $($c.OwningProcess) = $($proc.Name) | $($proc.Path)"
    } else {
        Write-Host "PID $($c.OwningProcess) = [PROCESS NOT FOUND - zombie socket]" -ForegroundColor Red
    }
}

Write-Host "`n=== HTTP probe on port 8000 ===" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "RESPONSE $($r.StatusCode): $($r.Content.Substring(0, [Math]::Min(200, $r.Content.Length)))"
} catch {
    Write-Host "No HTTP response: $_" -ForegroundColor Yellow
}
