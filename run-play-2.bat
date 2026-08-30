@echo off
setlocal

rem Launch the real modded game against THIS worktree's build, without editing
rem any config file.
rem
rem The play profile's openmw.cfg is shared with the other worktree and points
rem at "D:\Work\Morrowind reborn". Editing it to point here would fight with
rem whatever that line of work is doing, and would have to be undone afterwards.
rem
rem So nothing is edited. OpenMW appends command-line values for multi-value
rem settings *after* the ones in the config, and a later data directory wins in
rem the virtual file system. Passing this worktree's mod/ last therefore makes
rem its scripts/rewrite/rules.lua the one that loads, and the file on disk is
rem left exactly as the other worktree wrote it.
rem
rem What that does and does not cover:
rem
rem   Lua half     THIS worktree's rules.lua wins. That is the whole magicka
rem                rename - every one of its 59 records is on the load-context
rem                route, so this is the half that matters here.
rem   Plugin half  still the other worktree's scifi-rewrite-momw.esp, named by
rem                the config. Untouched by the magicka work, which writes no
rem                plugin records at all.

set "OPENMW_EXE=D:\Program Files\OpenMW 0.51.0\openmw.exe"
set "PLAY_CFG=D:\Backups\OneDrive\All\Documents\My Games\OpenMW\play"
set "HERE=%~dp0"

if not exist "%OPENMW_EXE%" (
    echo [run-play-2] ERROR: OpenMW not found at:
    echo                 %OPENMW_EXE%
    exit /b 1
)
if not exist "%HERE%mod\scripts\rewrite\rules.lua" (
    echo [run-play-2] ERROR: rules.lua is not built. Run:
    echo                 python tools\scripts\transform.py --write
    exit /b 1
)
if not exist "%HERE%logs" mkdir "%HERE%logs"

echo.
echo   [run-play-2] Launching against this worktree.
echo   [run-play-2]   config    : %PLAY_CFG%   (not modified)
echo   [run-play-2]   overriding: %HERE%mod
echo.
echo   Magicka is now Charge where the game speaks in its own voice, and
echo   stays Magicka where people do. Worth checking, in this order:
echo.
echo     1. The stat sheet and the bar: "Charge", not "Magicka".
echo     2. Cast with an empty bar: "You do not have enough Charge..."
echo     3. player-^>AddItem "p_restore_magicka_q" 1   -^> Quality Restore Charge
echo     4. Magic menu, an effect line: "Resist Discharge"
echo     5. A BOOK or a spoken line that mentions magicka - it must NOT change.
echo.

start /wait "" "%OPENMW_EXE%" --replace config --config "%PLAY_CFG%" ^
    --data "%HERE%mod"

echo.
echo [run-play-2] Game exited. Collecting the log...
if not exist "%PLAY_CFG%\openmw.log" (
    echo [run-play-2] ERROR: no openmw.log in "%PLAY_CFG%".
    exit /b 1
)
copy /y "%PLAY_CFG%\openmw.log" "%HERE%logs\openmw-play-2.log" >nul
echo [run-play-2] Copied -^> logs\openmw-play-2.log
echo.
echo [run-play-2] What the Lua half reported:
findstr /c:"[REWRITE]" "%HERE%logs\openmw-play-2.log"
if errorlevel 1 echo [run-play-2] WARNING: no [REWRITE] lines. The Lua half did not run.

endlocal
