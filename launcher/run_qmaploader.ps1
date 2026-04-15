$ErrorActionPreference = "Stop"

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$LaunchScript = Join-Path $Root "launcher\launch.py"

Set-Location $Root

if (-not (Test-Path $VenvPy)) {
    Write-Host "[Error] Could not find .venv\Scripts\python.exe." -ForegroundColor Red
    Write-Host ""
    Write-Host "Run installer\install.ps1 first to finish setup."
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}

& $VenvPy $LaunchScript
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "QmapLoader exited unexpectedly. Exit code: $exitCode" -ForegroundColor Yellow
    Read-Host "Press Enter to close"
}

exit $exitCode
