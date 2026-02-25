@echo off
setlocal

REM ── AEGIS Desktop Monitor — Uninstaller ────────────────────────
REM    Must be run as Administrator.

REM ── Admin check ────────────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] This script must be run as Administrator.
    echo         Right-click and select "Run as administrator".
    pause
    exit /b 1
)

echo ============================================================
echo   AEGIS Desktop Monitor — Uninstaller
echo ============================================================
echo.

REM ── 1. Stop the service ────────────────────────────────────────
echo [1/4] Stopping service...
sc stop AEGISMonitor >nul 2>&1
timeout /t 3 /nobreak >nul
echo       Done.

REM ── 2. Remove the service ──────────────────────────────────────
echo [2/4] Removing service...
"C:\ProgramData\AEGIS\AEGISMonitor.exe" remove >nul 2>&1
echo       Done.

REM ── 3. Delete the scheduled task ───────────────────────────────
echo [3/4] Deleting AEGISWatchdog scheduled task...
schtasks /delete /tn "AEGISWatchdog" /f >nul 2>&1
echo       Done.

REM ── 4. Optional: delete all data ──────────────────────────────
echo.
set /p CONFIRM="[4/4] Delete all AEGIS data in C:\ProgramData\AEGIS? (Y/N): "
if /i "%CONFIRM%"=="Y" (
    rmdir /s /q "C:\ProgramData\AEGIS"
    echo       Data deleted.
) else (
    echo       Data preserved.
)

echo.
echo ============================================================
echo   AEGIS Desktop Monitor uninstalled.
echo ============================================================
echo.
pause
