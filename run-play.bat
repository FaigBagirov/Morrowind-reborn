@echo off
setlocal

rem Launch the real modded game with the conversion installed.
rem
rem This is not a test harness like run-mod.bat. It starts the `play` profile
rem exactly as it is on disk - 240-odd plugins, the graphics-overhaul list, and
rem our three lines at the end of its openmw.cfg. Nothing is passed on the
rem command line except which config to use, because the mod is already
rem registered in that file:
rem
rem     data="...\Morrowind reborn\mod"                 Lua half
rem     data="...\Morrowind reborn\tools\build"         the plugin
rem     data="...\Morrowind reborn\tools\build\vfx-momw"  particle textures
rem     content=scifi-rewrite-momw.esp
rem     content=scifi-rewrite.omwscripts
rem
rem To play without the conversion, restore the untouched backup that sits
rem beside it: copy openmw.cfg.bak over openmw.cfg.
rem
rem --replace config matters. Without it OpenMW also reads the parent
rem My Games\OpenMW\openmw.cfg and the two load orders are merged.

set "OPENMW_EXE=D:\Program Files\OpenMW 0.51.0\openmw.exe"
set "PLAY_CFG=D:\Backups\OneDrive\All\Documents\My Games\OpenMW\play"
set "PROJECT=%~dp0"

if not exist "%OPENMW_EXE%" (
    echo [run-play] ERROR: OpenMW not found at:
    echo               %OPENMW_EXE%
    pause
    exit /b 1
)
if not exist "%PLAY_CFG%\openmw.cfg" (
    echo [run-play] ERROR: play profile not found at:
    echo               %PLAY_CFG%
    pause
    exit /b 1
)

findstr /c:"scifi-rewrite.omwscripts" "%PLAY_CFG%\openmw.cfg" >nul
if errorlevel 1 (
    echo [run-play] WARNING: the conversion is NOT in this profile's openmw.cfg.
    echo               The game will start, but vanilla.
    echo.
)

if not exist "%PROJECT%logs" mkdir "%PROJECT%logs"

echo.
echo   [run-play] Launching the modded game.
echo   [run-play]   config : %PLAY_CFG%
echo.
echo   On the first load OpenMW says the plugin list does not match the save.
echo   That is normal whenever a mod is added. Continue.
echo.
echo   Do not save while testing - some checks move the main quest on.
echo.

start /wait "" "%OPENMW_EXE%" --replace config --config "%PLAY_CFG%"

echo.
echo [run-play] Game exited. Collecting the log...

if not exist "%PLAY_CFG%\openmw.log" (
    echo [run-play] ERROR: no openmw.log in "%PLAY_CFG%".
    exit /b 1
)

copy /y "%PLAY_CFG%\openmw.log" "%PROJECT%logs\openmw-play.log" >nul
echo [run-play] Copied -^> logs\openmw-play.log

echo.
echo [run-play] What the Lua half reported:
findstr /c:"[REWRITE]" "%PROJECT%logs\openmw-play.log"
if errorlevel 1 echo [run-play] WARNING: no [REWRITE] lines. The Lua half did not run.

endlocal
