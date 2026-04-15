<#
    QmapLoader installer
    Usage:
      - Local repo: 우클릭 → "PowerShell로 실행"
      - GitHub bootstrap: called by installer\bootstrap.ps1
#>

$ErrorActionPreference = "Stop"

# Ensure console shows Korean correctly
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Root      = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Venv      = Join-Path $Root ".venv"
$VenvPy    = Join-Path $Venv "Scripts\python.exe"
$Launcher  = Join-Path $Root "launcher\run_qmaploader.bat" # ASCII shim -> PowerShell launcher
$Reqs      = Join-Path $Root "requirements.txt"
$EnvFile   = Join-Path $Root ".env"
$EnvExample= Join-Path $Root ".env.example"

function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "   [OK] $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg){ Write-Host "   [경고] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg)  { Write-Host "   [오류] $msg" -ForegroundColor Red }

function Find-PythonCommand {
    foreach ($candidate in @(@("py","-3"), @("python"), @("python3"))) {
        try {
            $out = & $candidate[0] $candidate[1..($candidate.Length-1)] -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) {
                return @{
                    Command = $candidate
                    Version = $out.Trim()
                }
            }
        } catch {}
    }

    return $null
}

function Refresh-ProcessPath {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path","Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path","User")
    if ($machinePath -and $userPath) {
        $env:Path = "$machinePath;$userPath"
    } elseif ($machinePath) {
        $env:Path = $machinePath
    } elseif ($userPath) {
        $env:Path = $userPath
    }
}

Write-Host ""
Write-Host "QmapLoader 설치를 시작합니다." -ForegroundColor White
Write-Host "대상 폴더: $Root"

# ---------- 1. Python ----------
Write-Step "[1/4] Python 확인"
$pythonInfo = Find-PythonCommand
if ($pythonInfo) {
    $pythonCmd = $pythonInfo.Command
    $pyVersion = $pythonInfo.Version
}

if (-not $pythonCmd) {
    Write-Warn2 "Python이 설치되어 있지 않습니다."

    $wingetOk = $false
    try { $null = Get-Command winget -ErrorAction Stop; $wingetOk = $true } catch {}

    if ($wingetOk) {
        Write-Host ""
        Write-Host "   Python 3.11을 winget으로 자동 설치할 수 있습니다."
        $ans = Read-Host "   지금 설치하시겠습니까? (Y/N)"
        if ($ans -match '^[Yy]') {
            Write-Host "   winget으로 Python 설치 중... (UAC 권한 창이 뜰 수 있습니다)"
            & winget install --id Python.Python.3.11 -e --silent --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) {
                Refresh-ProcessPath
                Start-Sleep -Seconds 2
                $pythonInfo = Find-PythonCommand
                if ($pythonInfo) {
                    $pythonCmd = $pythonInfo.Command
                    $pyVersion = $pythonInfo.Version
                    Write-Ok "Python $pyVersion 설치 완료"
                } else {
                    Write-Warn2 "Python 설치는 성공했지만 현재 창에서 인식되지 않습니다."
                    Write-Host "   이 창을 닫고 다시 실행하거나, 컴퓨터를 재시작해 주세요."
                    Read-Host "`nEnter 키를 누르면 종료합니다"
                    exit 1
                }
            } else {
                Write-Warn2 "winget 설치가 실패했습니다 (종료 코드: $LASTEXITCODE)."
                Write-Host "   수동 설치: https://www.python.org/downloads/"
                Read-Host "`nEnter 키를 누르면 종료합니다"
                exit 1
            }
        } else {
            Write-Host "   건너뜁니다. Python 3.10 이상 설치 후 다시 실행해 주세요."
            Write-Host "   수동 설치: https://www.python.org/downloads/"
            Read-Host "`nEnter 키를 누르면 종료합니다"
            exit 1
        }
    } else {
        Write-Err "winget이 감지되지 않았습니다."
        Write-Host "   https://www.python.org/downloads/ 에서 Python 3.10 이상 설치 후 다시 실행해 주세요."
        Write-Host "   설치 시 'Add python.exe to PATH' 옵션을 반드시 체크하세요."
        Read-Host "`nEnter 키를 누르면 종료합니다"
        exit 1
    }
}

$parts = $pyVersion.Split(".")
$major = [int]$parts[0]; $minor = [int]$parts[1]
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
    Write-Err "Python $pyVersion 감지됨. 3.10 이상이 필요합니다."
    Read-Host "`nEnter 키를 누르면 종료합니다"
    exit 1
}
Write-Ok "Python $pyVersion"

# ---------- 2. Java ----------
Write-Step "[2/4] Java 확인 (OpenDataLoader 구동용)"

function Test-JavaMajor {
    try {
        $out = (& java -version 2>&1 | Select-Object -First 1)
        if ($out -match 'version "(\d+)') { return [int]$matches[1] }
    } catch {}
    return 0
}

$javaMajor = Test-JavaMajor
if ($javaMajor -ge 11) {
    Write-Ok "Java $javaMajor"
} else {
    if ($javaMajor -gt 0) {
        Write-Warn2 "Java $javaMajor 감지됨. OpenDataLoader는 Java 11 이상이 필요합니다."
    } else {
        Write-Warn2 "Java가 설치되어 있지 않거나 PATH에 등록되지 않았습니다."
    }

    $wingetOk = $false
    try { $null = Get-Command winget -ErrorAction Stop; $wingetOk = $true } catch {}

    if ($wingetOk) {
        Write-Host ""
        Write-Host "   Eclipse Temurin 17(JDK)을 winget으로 자동 설치할 수 있습니다."
        $ans = Read-Host "   지금 설치하시겠습니까? (Y/N)"
        if ($ans -match '^[Yy]') {
            Write-Host "   winget으로 설치 중... (UAC 권한 창이 뜰 수 있습니다)"
            & winget install --id EclipseAdoptium.Temurin.17.JDK -e --silent --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) {
                $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
                Start-Sleep -Seconds 1
                $javaMajor = Test-JavaMajor
                if ($javaMajor -ge 11) {
                    Write-Ok "Java $javaMajor 설치 완료"
                } else {
                    Write-Warn2 "Java 설치는 성공했지만 현재 창에서 인식되지 않습니다."
                    Write-Host "   이 창을 닫고 다시 실행하거나, 컴퓨터를 재시작해 주세요."
                }
            } else {
                Write-Warn2 "winget 설치가 실패했습니다 (종료 코드: $LASTEXITCODE)."
                Write-Host "   수동 설치: https://adoptium.net/"
            }
        } else {
            Write-Host "   건너뜁니다. PDF 변환 전에 Java 설치가 필요합니다."
            Write-Host "   수동 설치: https://adoptium.net/"
        }
    } else {
        Write-Host "   winget이 감지되지 않았습니다."
        Write-Host "   Eclipse Temurin 17을 수동으로 설치해 주세요: https://adoptium.net/"
        Write-Host "   (지금 계속 진행하되, PDF 변환 시에는 Java 설치가 필요합니다.)"
    }
}

# ---------- 3. venv + deps ----------
Write-Step "[3/4] 가상환경 및 의존성 설치"
if (-not (Test-Path $VenvPy)) {
    Write-Host "   .venv 생성 중..."
    & $pythonCmd[0] $pythonCmd[1..($pythonCmd.Length-1)] -m venv $Venv
    if ($LASTEXITCODE -ne 0) { Write-Err "가상환경 생성 실패"; exit 1 }
} else {
    Write-Host "   기존 .venv 재사용"
}

Write-Host "   pip 업그레이드..."
& $VenvPy -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) { Write-Err "pip 업그레이드 실패"; exit 1 }

Write-Host "   requirements.txt 설치 중 (수 분 걸릴 수 있습니다)..."
& $VenvPy -m pip install -r $Reqs
if ($LASTEXITCODE -ne 0) { Write-Err "의존성 설치 실패"; exit 1 }
Write-Ok "의존성 설치 완료"

# .env 생성
if (-not (Test-Path $EnvFile) -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample $EnvFile
    Write-Ok ".env 파일 생성"
}

# ---------- 4. Desktop shortcut ----------
Write-Step "[4/4] 바탕화면 바로가기 생성"
try {
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $LnkPath = Join-Path $Desktop "QmapLoader.lnk"
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($LnkPath)
    $Shortcut.TargetPath       = $Launcher
    $Shortcut.WorkingDirectory = $Root
    $Shortcut.IconLocation     = "$env:SystemRoot\System32\shell32.dll,13"
    $Shortcut.Description      = "QmapLoader - PDF to Markdown 변환기"
    $Shortcut.Save()
    Write-Ok "바탕화면에 'QmapLoader' 아이콘이 생성되었습니다."
} catch {
    Write-Warn2 "바로가기 생성 실패: $_"
    Write-Host "   대신 launcher\run_qmaploader.bat 을 직접 더블클릭하면 실행됩니다."
    Write-Host "   (내부적으로 run_qmaploader.ps1 을 호출합니다.)"
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host " 설치 완료!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host " 실행: 바탕화면의 'QmapLoader' 더블클릭"
Write-Host "       또는 launcher\run_qmaploader.bat 실행"
Write-Host "       (bat 파일은 내부적으로 PowerShell 런처를 호출합니다)"
Write-Host ""
Read-Host "Enter 키를 누르면 종료합니다"
