@echo off
REM =====================================================================
REM  GenScan2.0 - handige wrapper om de WordPress-setup te starten.
REM  Voert het Python-script uit met "py" (Windows) of "python".
REM =====================================================================
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py setup_wordpress.py %*
) else (
    python setup_wordpress.py %*
)
