param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimePath = Join-Path $projectRoot '.runtime'
$dataDirectory = if ($env:TOOLBOX_DATA_DIR) { $env:TOOLBOX_DATA_DIR } else { Join-Path $projectRoot 'data' }
$expectedDatabase = [IO.Path]::GetFullPath((Join-Path $dataDirectory 'library.sqlite3'))
$servicePort = if ($env:TOOLBOX_PORT) { [int]$env:TOOLBOX_PORT } else { 8765 }
$localUrl = "http://127.0.0.1:$servicePort"
New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null

function Get-ToolboxInfo {
    try { return Invoke-RestMethod -Uri "$localUrl/api/info" -TimeoutSec 2 }
    catch { return $null }
}

$existing = Get-ToolboxInfo
if ($null -ne $existing) {
    if ($existing.app -ne 'personal-resource-shelf' -or $existing.data_path -ne $expectedDatabase) {
        throw "Port $servicePort is used by another service or toolbox data directory."
    }
    if (-not $NoBrowser) { Start-Process $localUrl }
    Write-Output "Toolbox is ready: $localUrl"
    exit 0
}

$env:TOOLBOX_DATA_DIR = Split-Path -Parent $expectedDatabase
$launch = @{
    FilePath = Join-Path $projectRoot 'runtime\toolbox-server.exe'
    WorkingDirectory = $projectRoot
    WindowStyle = 'Hidden'
    PassThru = $true
    RedirectStandardOutput = Join-Path $runtimePath 'server-output.log'
    RedirectStandardError = Join-Path $runtimePath 'server-error.log'
}
if (-not (Test-Path -LiteralPath $launch.FilePath)) {
    $pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) { throw 'Python 3.13+ is required. Install Python or run uv sync first.' }
        $pythonPath = $pythonCommand.Source
    }
    & $pythonPath -c "import sys, fastapi, pydantic, uvicorn; assert sys.version_info >= (3, 13)"
    if ($LASTEXITCODE -ne 0) { throw 'Dependencies are missing. Run uv sync in this folder, then start again.' }
    $launch.FilePath = $pythonPath
    $launch.ArgumentList = @('-m', 'toolbox')
}

$serverProcess = Start-Process @launch
$processRecord = @{
    pid = $serverProcess.Id
    start_ticks = $serverProcess.StartTime.ToUniversalTime().Ticks.ToString()
    port = $servicePort
    data_path = $expectedDatabase
}
$processRecord | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath 'server.json') -Encoding UTF8
$deadline = (Get-Date).AddSeconds(25)
while ((Get-Date) -lt $deadline) {
    $serverProcess.Refresh()
    if ($serverProcess.HasExited) {
        $logTail = Get-Content -LiteralPath (Join-Path $runtimePath 'server-error.log') -Tail 12
        throw ("Toolbox could not start. " + ($logTail -join [Environment]::NewLine))
    }
    $info = Get-ToolboxInfo
    if ($null -ne $info -and $info.app -eq 'personal-resource-shelf' -and $info.data_path -eq $expectedDatabase) {
        if (-not $NoBrowser) { Start-Process $localUrl }
        Write-Output "Toolbox is ready: $localUrl"
        exit 0
    }
    Start-Sleep -Milliseconds 200
}
Stop-Process -Id $serverProcess.Id
throw 'Startup timed out. See .runtime/server-error.log.'
