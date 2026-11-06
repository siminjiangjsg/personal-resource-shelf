$ErrorActionPreference = 'Stop'
$recordPath = Join-Path $PSScriptRoot '.runtime\server.json'
if (-not (Test-Path -LiteralPath $recordPath)) { Write-Output 'No launcher-owned server is recorded.'; exit 0 }
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
$serverProcess = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
if ($null -eq $serverProcess) {
    Remove-Item -LiteralPath $recordPath
    Write-Output 'Toolbox is already stopped.'
    exit 0
}
if ($serverProcess.StartTime.ToUniversalTime().Ticks.ToString() -ne $record.start_ticks) {
    throw 'The recorded process no longer matches. No process was stopped.'
}
Stop-Process -Id $serverProcess.Id
Remove-Item -LiteralPath $recordPath
Write-Output 'Toolbox stopped. Your saved data is retained.'
