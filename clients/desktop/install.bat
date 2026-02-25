@echo off
setlocal

REM ── AEGIS Desktop Monitor — One-Click Install ──────────────────
REM    Must be run as Administrator.

REM ── 1. Admin check ─────────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] This script must be run as Administrator.
    echo         Right-click and select "Run as administrator".
    pause
    exit /b 1
)

echo ============================================================
echo   AEGIS Desktop Monitor — Installer
echo ============================================================
echo.

REM ── 2. Create directories ─────────────────────────────────────
echo [1/14] Creating data directories...
if not exist "C:\ProgramData\AEGIS" mkdir "C:\ProgramData\AEGIS"
if not exist "C:\ProgramData\AEGIS\logs" mkdir "C:\ProgramData\AEGIS\logs"
echo        Done.

REM ── 3. Copy config to ProgramData (for watchdog access) ───────
echo [2/14] Copying configuration...
copy /Y "%~dp0config.yaml" "C:\ProgramData\AEGIS\config.yaml" >nul
echo        Done.

REM ── 4. Build executables with PyInstaller ──────────────────────
echo [3/14] Building AEGISMonitor.exe...
pyinstaller --onefile --hidden-import win32timezone "%~dp0service.py" -n AEGISMonitor --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" -y >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller failed for AEGISMonitor.exe
    pause
    exit /b 1
)
echo        Done.

echo [4/14] Building AEGISWatchdog.exe...
pyinstaller --onefile "%~dp0watchdog.py" -n AEGISWatchdog --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" -y >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller failed for AEGISWatchdog.exe
    pause
    exit /b 1
)
echo        Done.

REM ── 5. Copy executables to ProgramData ─────────────────────────
echo [5/14] Deploying executables...
copy /Y "%~dp0dist\AEGISMonitor.exe" "C:\ProgramData\AEGIS\AEGISMonitor.exe" >nul
copy /Y "%~dp0dist\AEGISWatchdog.exe" "C:\ProgramData\AEGIS\AEGISWatchdog.exe" >nul
echo        Done.

REM ── 6. Install service ────────────────────────────────────────
echo [6/14] Installing Windows Service...
"C:\ProgramData\AEGIS\AEGISMonitor.exe" install
if %errorlevel% neq 0 (
    echo [ERROR] Service install failed.
    pause
    exit /b 1
)
echo        Done.

REM ── 7. Set startup type to delayed auto ────────────────────────
echo [7/14] Configuring delayed auto-start...
sc config AEGISMonitor start= delayed-auto
echo        Done.

REM ── 8. Set service to run as current user ──────────────────────
echo [8/14] Configuring service account...
echo        The service needs to run as your user account.
set /p USER_PASS="        Enter your Windows password: "
sc config AEGISMonitor obj= ".\%USERNAME%" password= "%USER_PASS%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to set service account. Check password.
    pause
    exit /b 1
)
echo        Done.

REM ── 9. Configure failure recovery ──────────────────────────────
echo [9/14] Configuring crash recovery...
sc failure AEGISMonitor reset= 86400 actions= restart/60000/restart/60000/restart/60000
echo        Done.

REM ── 10. Set DACL + SACL ────────────────────────────────────────
echo [10/14] Setting access control and audit logging...
sc sdset AEGISMonitor "D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWLOCRRC;;;IU)S:(AU;FA;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;WD)"
echo        Done.

REM ── 11. Enable audit policy ────────────────────────────────────
echo [11/14] Enabling audit policy for access events...
auditpol /set /subcategory:"Other Object Access Events" /failure:enable /success:enable
echo        Done.

REM ── 12. Register watchdog as Scheduled Task ────────────────────
echo [12/14] Registering AEGISWatchdog scheduled task...
schtasks /create /tn "AEGISWatchdog" /tr "C:\ProgramData\AEGIS\AEGISWatchdog.exe" /sc minute /mo 1 /ru SYSTEM /rl HIGHEST /f
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create scheduled task.
    pause
    exit /b 1
)
echo        Done.

REM ── 13. Start the service ──────────────────────────────────────
echo [13/14] Starting AEGIS Desktop Monitor...
sc start AEGISMonitor
echo        Done.

REM ── 14. Verify ─────────────────────────────────────────────────
echo [14/14] Verifying...
timeout /t 3 /nobreak >nul
sc query AEGISMonitor

echo.
echo ============================================================
echo   AEGIS Desktop Monitor installed and running.
echo ============================================================
echo.
pause
