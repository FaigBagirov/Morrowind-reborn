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
echo   GATE 3 -- what to check on screen
echo   =====================================================================
echo.
echo   LOAD YOUR SAVE. Stay in game a few seconds. Then open the console
echo   with ~ and paste these one at a time.
echo.
echo   1. BOOK, five rules at once, and the markup has to survive.
echo        player-^>AddItem "bk_darkestdarkness" 1
echo      Open it. Expect normal formatting, and page one to read
echo      "summon lesser Zenar and bound Zenar as servants".
echo      A BLANK page is the failure that matters.
echo.
echo   2. ITEM NAME, and this one comes from the PLUGIN half.
echo        player-^>AddItem "daedric_cuirass" 1
echo      Inventory should read "Zenaric Cuirass".
echo.
echo   3. INGREDIENT, the one rule written by hand.
echo        player-^>AddItem "ingred_daedras_heart_01" 1
echo      Expect "Zenar Heart", not "Zenar's Heart".
echo.
echo   4. SPELL NAME and GAME SETTING in one hover.
echo        player-^>AddSpell "summon daedroth"
echo      Magic menu: the spell should read "Summon Zenaroth", and the
echo      effect line under it should also say Zenaroth. The effect line
echo      comes from a GMST, so this checks two stores at once.
echo.
echo   5. CREATURE NAME, plugin half. It is hostile - type tgm first if you
echo      do not want the fight.
echo        player-^>PlaceAtPC "daedroth" 1 1 1
echo      The crosshair name should read "Zenaroth".
echo.
echo   6. DIALOGUE, plugin half, and the topic link. Spawns a copy of an
echo      NPC next to you; do not save afterwards.
echo        player-^>PlaceAtPC "vala catraso" 1 1 1
echo      Talk to her, click the topic "Daedric summonings". The reply
echo      should keep that phrase once - that is what keeps the link
echo      working - and say "Good Zenar are the Zenar associated with
echo      Boethiah, Azura, and Mephala".
echo.
echo   Do not save. Quit the game when done.
echo   =====================================================================
echo.
pause

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
