param(
    [Parameter(Mandatory = $true)][string]$Archive,
    [int]$Port = 18765
)
$ErrorActionPreference = 'Stop'
$archivePath = (Resolve-Path -LiteralPath $Archive).Path
$originalPath = $env:PATH
$originalPort = $env:TOOLBOX_PORT
$originalDataDirectory = $env:TOOLBOX_DATA_DIR
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('toolbox ' + [char]0x4E2D + [char]0x6587 + ' ' + [guid]::NewGuid().ToString('N'))
Expand-Archive -LiteralPath $archivePath -DestinationPath $testRoot
$packageRoot = (Get-ChildItem -LiteralPath $testRoot -Directory | Select-Object -First 1).FullName
$url = "http://127.0.0.1:$Port"
$recordPath = Join-Path $packageRoot '.runtime\server.json'

function Start-PackagedToolbox {
    $launcher = Start-Process -FilePath $powershell -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$packageRoot\start.ps1`"", '-NoBrowser') -WindowStyle Hidden -PassThru -RedirectStandardOutput "$testRoot\launcher-output.log" -RedirectStandardError "$testRoot\launcher-error.log"
    if (-not $launcher.WaitForExit(40000)) { throw 'Packaged launcher did not exit.' }
    if ($launcher.ExitCode -ne 0) {
        Get-Content -LiteralPath "$testRoot\launcher-error.log"
        throw 'Packaged startup failed without system Python.'
    }
}

try {
    # Given an extracted archive in a Unicode path, with no Python or uv on PATH.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot\System32\WindowsPowerShell\v1.0"
    $env:TOOLBOX_PORT = $Port.ToString()
    $env:TOOLBOX_DATA_DIR = $null
    foreach ($command in @('python', 'python3', 'uv')) {
        if (Get-Command $command -ErrorAction SilentlyContinue) { throw "$command is still on PATH." }
    }
    if (Test-Path -LiteralPath "$packageRoot\data") { throw 'The archive contains user data.' }
    if (Test-Path -LiteralPath "$packageRoot\.venv") { throw 'The archive contains a development environment.' }
    # When the normal launcher starts the packaged server.
    Start-PackagedToolbox
    # Then the runtime, web assets and initially empty database come from this package.
    $info = Invoke-RestMethod "$url/api/info"
    if ($info.data_path -ne "$packageRoot\data\library.sqlite3") { throw 'Unexpected database location.' }
    $state = Invoke-RestMethod "$url/api/state"
    if ($state.resources.Count -ne 0 -or $state.collections.Count -ne 0) { throw 'First launch was not empty.' }
    foreach ($route in @('/', '/assets/app.js', '/assets/styles.css')) {
        if ((Invoke-WebRequest "$url$route" -UseBasicParsing).StatusCode -ne 200) { throw "Missing asset: $route" }
    }
    $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    $serverProcess = Get-Process -Id $record.pid
    if ($serverProcess.Path -ne "$packageRoot\runtime\toolbox-server.exe") { throw 'The server is not the packaged executable.' }
    $pythonModule = @($serverProcess.Modules | Where-Object { $_.ModuleName -match '^python3\d+\.dll$' })
    if ($pythonModule.Count -ne 1 -or -not $pythonModule[0].FileName.StartsWith("$packageRoot\runtime\", [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Python was not loaded from the bundled runtime.'
    }
    Write-Output 'PASS: starts without Python/uv, serves bundled assets and uses embedded Python.'

    # Given a running copy; when started again; then it reuses the same process.
    Start-PackagedToolbox
    $secondRecord = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    if ($secondRecord.pid -ne $record.pid) { throw 'Repeated launch created another server.' }
    Write-Output 'PASS: repeated launch reuses the running instance.'

    # Given selected and unselected resources with private fields.
    $resource = Invoke-RestMethod "$url/api/resources" -Method Post -ContentType 'application/json' -Body (@{
        url = 'https://example.com/portable?keep=1#part'; title = 'Portable resource'
        note = 'PRIVATE_PORTABLE_SENTINEL'; category = 'PRIVATE_CATEGORY'; tags = @('HIDDEN_TAG')
    } | ConvertTo-Json)
    Invoke-RestMethod "$url/api/resources" -Method Post -ContentType 'application/json' -Body '{"url":"https://example.com/unselected"}' | Out-Null
    # When only the selected public snapshot is exported.
    $collection = Invoke-RestMethod "$url/api/collections" -Method Post -ContentType 'application/json' -Body (@{
        title = 'Portable selection'; show_tags = $false
        items = @(@{resource_id = $resource.id; title = $resource.title; url = $resource.url; recommendation = 'Public recommendation'; tags = $resource.tags})
    } | ConvertTo-Json -Depth 5)
    # Then both export formats exclude private and unselected content.
    foreach ($format in @('html', 'markdown')) {
        $export = (Invoke-WebRequest "$url/api/collections/$($collection.id)/$format" -UseBasicParsing).Content
        if ($export -match 'PRIVATE_PORTABLE_SENTINEL|PRIVATE_CATEGORY|HIDDEN_TAG|unselected') { throw 'Private data leaked into the export.' }
        if ($export -notmatch 'Public recommendation' -or $export -notmatch 'https://example.com/portable\?keep=1#part') { throw 'Selected content is missing.' }
    }
    Write-Output 'PASS: selective HTML/Markdown exports preserve only public selected content.'

    # Given saved resources; when the service is stopped and restarted; then data persists.
    & $powershell -NoProfile -ExecutionPolicy Bypass -File "$packageRoot\stop.ps1"
    if ($LASTEXITCODE -ne 0) { throw 'Packaged stop failed.' }
    Start-PackagedToolbox
    $restored = Invoke-RestMethod "$url/api/state"
    $saved = @($restored.resources | Where-Object { $_.id -eq $resource.id })
    if ($saved.Count -ne 1 -or $saved[0].note -ne 'PRIVATE_PORTABLE_SENTINEL' -or $restored.collections.Count -ne 1) {
        throw 'Saved records did not survive restart.'
    }
    Write-Output 'PASS: resources, private notes and share collections survive restart.'

    # Given another copy using another data directory; when its port conflicts; then it refuses reuse.
    $otherRoot = Join-Path $testRoot 'other copy'
    New-Item -ItemType Directory -Path $otherRoot | Out-Null
    Copy-Item -LiteralPath "$packageRoot\start.ps1" -Destination $otherRoot
    $conflictOutput = & $powershell -NoProfile -ExecutionPolicy Bypass -File "$otherRoot\start.ps1" -NoBrowser 2>&1
    if ($LASTEXITCODE -eq 0) { throw 'A different data directory reused the running server.' }
    if ((Invoke-RestMethod "$url/api/info").data_path -ne $info.data_path) { throw 'Port conflict affected the original server.' }
    Write-Output 'PASS: conflicting data directory is rejected without affecting the running copy.'
    Write-Output "Package smoke test passed: $archivePath"
    Write-Output "Test evidence directory: $testRoot"
} finally {
    if (Test-Path -LiteralPath $recordPath) {
        & $powershell -NoProfile -ExecutionPolicy Bypass -File "$packageRoot\stop.ps1"
        if ($LASTEXITCODE -ne 0) { Write-Warning "Could not stop test server. See $recordPath" }
    }
    $env:PATH = $originalPath
    $env:TOOLBOX_PORT = $originalPort
    $env:TOOLBOX_DATA_DIR = $originalDataDirectory
}
