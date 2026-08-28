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
echo   WO1 BOOK PROBE, run 2 -- what to check on screen
echo   =====================================================================
echo.
echo   Run 1 answered P1: the book NAME is writable, confirmed on screen.
echo   P2 is still open, and this run separates the two ways it can fail.
echo.
echo   LOAD YOUR SAVE. No new game needed. STAY IN GAME a few seconds -
echo   run 1 was quit at the menu, so two of the three layers never ran.
echo.
echo   1. TWO MESSAGES appear at the bottom of the screen on load:
echo        WO1 name: ...
echo        WO1 text: ...
echo      These are read from the LIVE session. If the text line starts with
echo      PROBE TEXT OK, the running game holds the substitution and anything
echo      the book window shows differently is a rendering matter. If it
echo      starts with "A Brief History of the Empire", the write never
echo      reached the session at all. Report which one you see.
echo.
echo   2. Console with ~, then paste:
echo.
echo       player-^>AddItem "bk_BriefHistoryEmpire1" 1
echo.
echo   3. Open the book. Page one should begin:
echo        PROBE TEXT OK -- Domain Hist.
echo      A BLANK page, the vanilla heading, or the marker - each means
echo      something different, so report exactly what you see.
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
