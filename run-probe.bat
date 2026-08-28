@echo off
setlocal enabledelayedexpansion

rem Work Order 1 -- book name and book render probe runner.
rem
rem Launches OpenMW against the clean vanilla dev profile with
rem mod\wo1-bookname.omwscripts, waits for it to exit, then copies the log
rem into logs\ and extracts the [WO1] lines.
rem
rem Unlike run-spike.bat this does NOT overwrite logs\openmw.log -- that copy
rem is the archived WO0 run. This one lands beside it under its own name.
rem
rem The probe content file is added with --content on the command line rather
rem than by editing dev\openmw.cfg, so the three masters still load first and
rem nothing outside this project is modified. The WO0 spike sitting in mod\ is
rem not referenced here and does not load.

set "OPENMW_EXE=D:\Program Files\OpenMW 0.51.0\openmw.exe"
set "DEV_CFG=D:\Backups\OneDrive\All\Documents\My Games\OpenMW\dev"
set "PROJECT=%~dp0"

if not exist "%OPENMW_EXE%" (
    echo [run-probe] ERROR: OpenMW not found at:
    echo               %OPENMW_EXE%
    echo               Edit OPENMW_EXE at the top of this file.
    exit /b 1
)

if not exist "%DEV_CFG%\openmw.cfg" (
    echo [run-probe] ERROR: dev profile not found at:
    echo               %DEV_CFG%
    echo               Edit DEV_CFG at the top of this file.
    exit /b 1
)

if not exist "%PROJECT%logs" mkdir "%PROJECT%logs"

echo.
echo   =====================================================================
echo   WO1 BOOK PROBE -- what to check on screen
echo   =====================================================================
echo.
echo   LOAD YOUR SAVE. No new game needed - the probe applies at load time,
echo   wherever you are standing.
echo.
echo   Then open the console with ~ and paste:
echo.
echo       player-^>AddItem "bk_BriefHistoryEmpire1" 1
echo.
echo   The record ID never changes, so this works even after the rename.
echo.
echo   1. NAME. Look at the book in your inventory.
echo      Expected: PROBE_BOOKNAME_OK
echo      If it still says "Brief History of the Empire v 1", the name is
echo      NOT writable and the routing table changes.
echo.
echo   2. PAGE. Open the book.
echo      Expected: a normal page, centered heading, same layout as vanilla,
echo      and the title line reading "A Brief History of the Domain".
echo      A BLANK page is the important failure -- it would mean substring
echo      substitution is not enough either, and WO2 needs rethinking.
echo.
echo   Do not save afterwards. Quit the game when done.
echo   =====================================================================
echo.
pause

echo [run-probe] Launching OpenMW with the dev profile...
echo [run-probe]   config : %DEV_CFG%
echo [run-probe]   content: wo1-bookname.omwscripts
echo.

start /wait "" "%OPENMW_EXE%" --replace config --config "%DEV_CFG%" --content wo1-bookname.omwscripts

echo.
echo [run-probe] Game exited. Collecting log...

if not exist "%DEV_CFG%\openmw.log" (
    echo [run-probe] ERROR: no openmw.log in "%DEV_CFG%".
    echo               The game may not have started. Nothing copied.
    exit /b 1
)

copy /y "%DEV_CFG%\openmw.log" "%PROJECT%logs\openmw-wo1-bookname.log" >nul
echo [run-probe] Copied -^> logs\openmw-wo1-bookname.log

findstr /c:"[WO1]" "%PROJECT%logs\openmw-wo1-bookname.log" > "%PROJECT%logs\wo1-bookname.txt"
if errorlevel 1 (
    echo [run-probe] WARNING: no [WO1] lines found in the log.
    echo               The probe did not run. Check the log for a
    echo               "Loading content file wo1-bookname.omwscripts" line.
) else (
    echo [run-probe] Probe output -^> logs\wo1-bookname.txt
)

echo.
echo [run-probe] Done. Tell Claude what you saw on screen -- the log alone
echo [run-probe] cannot answer either question.
endlocal
