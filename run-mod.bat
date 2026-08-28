@echo off
setlocal enabledelayedexpansion

rem Gate 3 -- the game run. Architecture Part 14.
rem
rem Loads both halves of the conversion against the clean vanilla dev profile:
rem   Lua half    mod\scifi-rewrite.omwscripts   (mod\ is a data dir already)
rem   Plugin half tools\build\scifi-rewrite.esp  (added with --data below)
rem
rem Nothing outside this project is modified: the content files are passed on
rem the command line rather than written into dev\openmw.cfg, and per the
rem OpenMW docs command line values for multi-value settings are appended after
rem config file values, so the three masters still load first.
rem
rem The log is copied under its own name; the WO0 and WO1 logs are not touched.

set "OPENMW_EXE=D:\Program Files\OpenMW 0.51.0\openmw.exe"
set "DEV_CFG=D:\Backups\OneDrive\All\Documents\My Games\OpenMW\dev"
set "PROJECT=%~dp0"

if not exist "%OPENMW_EXE%" (
    echo [run-mod] ERROR: OpenMW not found at:
    echo             %OPENMW_EXE%
    exit /b 1
)
if not exist "%DEV_CFG%\openmw.cfg" (
    echo [run-mod] ERROR: dev profile not found at:
    echo             %DEV_CFG%
    exit /b 1
)
if not exist "%PROJECT%tools\build\scifi-rewrite.esp" (
    echo [run-mod] ERROR: the plugin is not built. Run:
    echo             python tools\scripts\transform.py --write
    echo             tools\bin\tes3conv.exe tools\build\scifi-rewrite.json tools\build\scifi-rewrite.esp
    exit /b 1
)
if not exist "%PROJECT%logs" mkdir "%PROJECT%logs"

echo.
echo   =====================================================================
echo   GATE 3, RUN 2 -- what to check
echo   =====================================================================
echo.
echo   Run 1 passed everything except dialogue, which never loaded: the
echo   plugin shipped 187 reply records with no topic records to own them
echo   and OpenMW rejected all of them. Both that and the effect-name line
echo   are fixed. Three things to look at.
echo.
echo   LOAD YOUR SAVE, then console with ~:
echo.
echo   1. DIALOGUE. Give yourself the topic first - a level 1 character has
echo      not learned it yet - then spawn the speaker and talk to her.
echo        player-^>AddTopic "Daedric summonings"
echo        player-^>PlaceAtPC "vala catraso" 1 1 1
echo      The reply should keep the phrase "Daedric summonings" once, which
echo      is what keeps the topic clickable, and then read
echo      "Good Zenar are the Zenar associated with Boethiah, Azura, and
echo      Mephala".
echo.
echo   2. THE EFFECT LINE, the one you caught.
echo        player-^>AddSpell "summon daedroth"
echo      Magic menu: both the spell name AND the effect line under it
echo      should now read Zenaroth. Last run the bottom line still said
echo      Daedroth.
echo.
echo   3. Nothing else has to be re-checked - book, items, ingredient,
echo      creature all passed.
echo.
echo   Do not save. Quit when done; this window collects the log by itself.
echo   =====================================================================
echo.

echo [run-mod] Launching OpenMW...
echo [run-mod]   config : %DEV_CFG%
echo [run-mod]   lua    : scifi-rewrite.omwscripts
echo [run-mod]   plugin : scifi-rewrite.esp
echo.

start /wait "" "%OPENMW_EXE%" --replace config --config "%DEV_CFG%" --data "%PROJECT%tools\build" --content scifi-rewrite.esp --content scifi-rewrite.omwscripts

echo.
echo [run-mod] Game exited. Collecting log...

if not exist "%DEV_CFG%\openmw.log" (
    echo [run-mod] ERROR: no openmw.log in "%DEV_CFG%".
    exit /b 1
)

copy /y "%DEV_CFG%\openmw.log" "%PROJECT%logs\openmw-gate3.log" >nul
echo [run-mod] Copied -^> logs\openmw-gate3.log

findstr /c:"[REWRITE]" "%PROJECT%logs\openmw-gate3.log" > "%PROJECT%logs\gate3-rewrite.txt"
if errorlevel 1 (
    echo [run-mod] WARNING: no [REWRITE] lines. The Lua half did not run.
) else (
    echo [run-mod] Lua half output -^> logs\gate3-rewrite.txt
    type "%PROJECT%logs\gate3-rewrite.txt"
)

echo.
echo [run-mod] Done. Tell Claude what you saw - the log cannot see the screen.
endlocal
