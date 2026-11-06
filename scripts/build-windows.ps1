param([string]$OutputDirectory = 'dist')
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'Build this package on Windows x64.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousEnvironment = $env:UV_PROJECT_ENVIRONMENT
Push-Location $projectRoot
try {
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $projectRoot '.runtime\windows-build-venv'
    & uv sync --frozen --no-dev --group build --python 3.13 --managed-python
    if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
    $python = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts\python.exe'
    & $python -c 'import struct; assert struct.calcsize("P") == 8, "Windows x64 Python is required"'
    if ($LASTEXITCODE -ne 0) { throw 'Windows x64 Python is required.' }
    $version = & $python -c 'import tomllib; from pathlib import Path; print(tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the project version.' }
    $packageName = "personal-resource-shelf-v$version-windows-x64"
    $outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
    $packageRoot = Join-Path $outputRoot $packageName
    $archive = "$packageRoot.zip"
    foreach ($destination in @($packageRoot, $archive, "$archive.sha256")) {
        if (Test-Path -LiteralPath $destination) { throw "Output already exists: $destination" }
    }
    $workRoot = Join-Path $projectRoot ("build\windows-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
    & $python -m PyInstaller --onedir --name toolbox-server --paths $projectRoot --add-data "${projectRoot}\web:web" --collect-submodules uvicorn --noupx --distpath "$workRoot\dist" --workpath "$workRoot\work" --specpath $workRoot toolbox/__main__.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }

    New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
    Copy-Item -LiteralPath "$workRoot\dist\toolbox-server" -Destination "$packageRoot\runtime" -Recurse
    Copy-Item -LiteralPath 'start.ps1', 'stop.ps1', 'LICENSE' -Destination $packageRoot
    Get-ChildItem -LiteralPath $projectRoot -Filter '*.cmd' | Copy-Item -Destination $packageRoot
    Get-ChildItem -LiteralPath 'packaging\windows' -Filter '*.txt' | Copy-Item -Destination $packageRoot

    $licensesRoot = Join-Path $packageRoot 'licenses'
    New-Item -ItemType Directory -Path $licensesRoot | Out-Null
    $sitePackages = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Lib\site-packages'
    foreach ($distribution in (Get-ChildItem -LiteralPath $sitePackages -Directory -Filter '*.dist-info')) {
        $licenseFiles = @(Get-ChildItem -LiteralPath $distribution.FullName | Where-Object { $_.Name -match '^(licenses?|copying|notice)(\..*)?$' })
        if ($licenseFiles.Count -gt 0) {
            $destination = Join-Path $licensesRoot $distribution.BaseName
            New-Item -ItemType Directory -Path $destination | Out-Null
            $licenseFiles | Copy-Item -Destination $destination -Recurse
        }
    }
    $pythonRoot = & $python -c 'import sys; print(sys.base_prefix)'
    $pythonLicenses = Join-Path $licensesRoot 'Python'
    New-Item -ItemType Directory -Path $pythonLicenses | Out-Null
    Get-ChildItem -LiteralPath $pythonRoot | Where-Object { $_.Name -match '^(licenses?|copying|notice)(\..*)?$' } | Copy-Item -Destination $pythonLicenses -Recurse
    $dependencies = & $python -c 'from importlib.metadata import distributions; print("\n".join(sorted(d.metadata["Name"] + " " + d.version for d in distributions())))'
    $pythonVersion = & $python --version
    @(
        'Personal Resource Shelf: MIT (see LICENSE).'
        "Bundled runtime: $pythonVersion (see licenses/Python)."
        'Runtime and build dependency license texts are included in licenses/.'
        'PyInstaller uses its bootloader distribution exception.'
        'The following versions describe the isolated build environment:'
        ''
        $dependencies
    ) | Set-Content -LiteralPath "$packageRoot\THIRD_PARTY_NOTICES.txt" -Encoding UTF8
    Compress-Archive -LiteralPath $packageRoot -DestinationPath $archive -CompressionLevel Optimal
    $checksum = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    "$checksum  $packageName.zip" | Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
    Write-Output "Package: $archive"
    Write-Output "SHA256: $checksum"
} finally {
    $env:UV_PROJECT_ENVIRONMENT = $previousEnvironment
    Pop-Location
}
