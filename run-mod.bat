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
echo   THE ZENAR TOPIC -- what to check
echo   =====================================================================
echo.
echo   The plugin now carries a topic of its own with six answers under it.
echo   Only people who know it have a reply, so it should appear for them
echo   and for nobody else.
echo.
echo   LOAD YOUR SAVE, wait a moment, then console with ~:
echo.
echo   1. SOMEONE WHO KNOWS.
echo        player-^>PlaceAtPC "sinnammu mirpal" 1 1 1
echo      Talk to her. "Zenar" should be in her topic list. Her answer is
echo      about the Temple dividing them into good and bad because a divided
echo      thing is easier to own.
echo.
echo   2. THE WORD ITSELF, clickable. Ask her about "Daedric summonings"
echo      first - if the topic is missing, give it to yourself:
echo        player-^>AddTopic "Daedric summonings"
echo      In that reply the word Zenar should now be highlighted and
echo      clickable, because the player knows the topic.
echo.
echo   3. SOMEONE WHO DOES NOT KNOW. Talk to any guard or commoner nearby.
echo      There should be no Zenar in their list at all. That silence is the
echo      point: the word belongs to the few.
echo.
echo   4. OPTIONAL, other voices:
echo        player-^>PlaceAtPC "divayth fyr" 1 1 1
echo        player-^>PlaceAtPC "yagrum bagarn" 1 1 1
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
