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
echo   CAIUS, AND THE CHAIN -- what to check
echo   =====================================================================
echo.
echo   Two of his lines are written by hand now. Together with the topic and
echo   the book they make one chain: hear the word, be told who to ask, ask.
echo.
echo   LOAD YOUR SAVE, wait a moment, then console with ~:
echo.
echo        player-^>PlaceAtPC "caius cosades" 1 1 1
echo.
echo   1. Topic "little advice". His answer should end with:
echo        "And if Zenar is a new word to you, good. It means you've been
echo         reading something besides Temple pamphlets. Ask a wise woman
echo         what it means. Don't ask a priest."
echo      Zenar should be highlighted - the topic is known to you.
echo.
echo   2. Topic "Blades". Should now carry:
echo        "The Temple says Daedra... The things themselves say Zenar. Both
echo         words are in my files. Only one of them is a fact."
echo.
echo   3. CLICK Zenar in either reply. Caius has no answer of his own, so
echo      the topic should be absent from HIS list - he knows the word, he
echo      is not the man who explains it. If it is there, the filter leaked.
echo.
echo   4. Then the one who does explain:
echo        player-^>PlaceAtPC "sinnammu mirpal" 1 1 1
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
