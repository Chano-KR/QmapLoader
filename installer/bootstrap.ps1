param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,
    [string]$Branch = "main",
    [string]$InstallRoot = (Join-Path $HOME "QmapLoader")
)

$ErrorActionPreference = "Stop"

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

function Write-Step([string]$Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "   [OK] $Message" -ForegroundColor Green }
function Write-Warn2([string]$Message) { Write-Host "   [WARN] $Message" -ForegroundColor Yellow }
function Write-Err([string]$Message) { Write-Host "   [ERROR] $Message" -ForegroundColor Red }

function Normalize-RepoUrl([string]$Url) {
    $normalized = $Url.Trim().TrimEnd("/")
    if ($normalized.EndsWith(".git")) {
        $normalized = $normalized.Substring(0, $normalized.Length - 4)
    }
    return $normalized
}

$RepoUrl = Normalize-RepoUrl $RepoUrl

if ($RepoUrl -notmatch "^https://github\.com/[^/]+/[^/]+$") {
    Write-Err "RepoUrl must look like https://github.com/owner/repo"
    exit 1
}

$ZipUrl = "$RepoUrl/archive/refs/heads/$Branch.zip"
$SessionId = [guid]::NewGuid().ToString("N")
$TempRoot = Join-Path $env:TEMP "qmaploader-bootstrap-$SessionId"
$ZipPath = Join-Path $TempRoot "repo.zip"
$ExtractRoot = Join-Path $TempRoot "extract"

New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null

Write-Host ""
Write-Host "QmapLoader bootstrap installer" -ForegroundColor White
Write-Host "Repository : $RepoUrl"
Write-Host "Branch     : $Branch"
Write-Host "Install to : $InstallRoot"

try {
    Write-Step "[1/4] Downloading repository archive"
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath
    Write-Ok "Downloaded $ZipUrl"

    Write-Step "[2/4] Extracting archive"
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractRoot -Force
    $SourceRoot = Get-ChildItem -LiteralPath $ExtractRoot -Directory | Select-Object -First 1
    if (-not $SourceRoot) {
        throw "Could not find extracted repository folder."
    }
    Write-Ok "Extracted to $($SourceRoot.FullName)"

    Write-Step "[3/4] Copying files into install directory"
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

    foreach ($item in Get-ChildItem -LiteralPath $SourceRoot.FullName -Force) {
        if ($item.Name -in @(".venv", ".env", "logs")) {
            Write-Warn2 "Skipping runtime item: $($item.Name)"
            continue
        }
        $destination = Join-Path $InstallRoot $item.Name
        Copy-Item -LiteralPath $item.FullName -Destination $destination -Recurse -Force
    }
    Write-Ok "Repository files copied"

    Write-Step "[4/4] Running local installer"
    $InstallerPath = Join-Path $InstallRoot "installer\install.ps1"
    if (-not (Test-Path $InstallerPath)) {
        throw "install.ps1 not found under $InstallRoot\installer"
    }

    & $InstallerPath
    if ($LASTEXITCODE -ne 0) {
        throw "install.ps1 exited with code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "Bootstrap install completed." -ForegroundColor Green
    Write-Host "You can now launch QmapLoader from the desktop shortcut." -ForegroundColor Green
}
finally {
    Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
