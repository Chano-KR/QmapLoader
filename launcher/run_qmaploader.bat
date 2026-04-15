@echo off
setlocal
title QmapLoader

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_qmaploader.ps1"
set "EXITCODE=%ERRORLEVEL%"

endlocal & exit /b %EXITCODE%
