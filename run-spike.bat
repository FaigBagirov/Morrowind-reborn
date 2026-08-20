@echo off
setlocal enabledelayedexpansion

rem Work Order 0 -- load context writability spike runner.
rem
rem Launches OpenMW against the clean vanilla dev profile, waits for it to
rem exit, then copies the log into logs\ and extracts the spike lines.
rem
rem The spike content file is added with --content on the command line rather
rem than by editing dev\openmw.cfg. Per the OpenMW docs, command line values
rem for multi-value settings are appended after config file values, so the
rem three masters still load first and nothing outside this project is
rem modified. Remove the spike by deleting mod\ contents.

set "OPENMW_EXE=D:\Program Files\OpenMW 0.51.0\openmw.exe"
set "DEV_CFG=D:\Backups\OneDrive\All\Documents\My Games\OpenMW\dev"
set "PROJECT=%~dp0"

if not exist "%OPENMW_EXE%" (
    echo [run-spike] ERROR: OpenMW not found at:
    echo              %OPENMW_EXE%
    echo              Edit OPENMW_EXE at the top of this file.
    exit /b 1
)

if not exist "%DEV_CFG%\openmw.cfg" (
    echo [run-spike] ERROR: dev profile not found at:
    echo              %DEV_CFG%
    echo              Edit DEV_CFG at the top of this file.
    exit /b 1
)

if not exist "%PROJECT%logs" mkdir "%PROJECT%logs"

echo [run-spike] Launching OpenMW with the dev profile...
echo [run-spike]   config : %DEV_CFG%
echo [run-spike]   content: wo0-spike.omwscripts
echo.
echo [run-spike] Play through the verification card, then QUIT the game.
echo [run-spike] Do not save -- the spike needs nothing saved.
echo.

start /wait "" "%OPENMW_EXE%" --replace config --config "%DEV_CFG%" --content wo0-spike.omwscripts

echo.
echo [run-spike] Game exited. Collecting log...

if not exist "%DEV_CFG%\openmw.log" (
    echo [run-spike] ERROR: no openmw.log in "%DEV_CFG%".
    echo              The game may not have started. Nothing copied.
    exit /b 1
)

copy /y "%DEV_CFG%\openmw.log" "%PROJECT%logs\openmw.log" >nul
echo [run-spike] Copied -^> logs\openmw.log

findstr /c:"[WO0]" "%PROJECT%logs\openmw.log" > "%PROJECT%logs\wo0-spike.txt"
if errorlevel 1 (
    echo [run-spike] WARNING: no [WO0] lines found in the log.
    echo              The spike script did not run. Check logs\openmw.log for
    echo              a "Loading content file wo0-spike.omwscripts" line.
) else (
    echo [run-spike] Spike output -^> logs\wo0-spike.txt
)

echo.
echo [run-spike] Done.
endlocal
