# One fitting round in the dev profile, start to contact sheet.
#
#     powershell -File tools/scripts/fitcheck.ps1 [-Kill <pid>]
#
# Launches the clean dev profile with this worktree's plugin and armour build,
# no sound, straight into ToddTest. `tools/viewer/equip.txt` runs through the
# console at startup and dresses the player in the Daedric set, and the
# `zenar_viewer` player script parks the camera at front, side, back and other
# side in turn. F12 is pressed on a timer and the eight pictures are put on one
# small sheet, `tools/reports/fitcheck.jpg`, which is what gets looked at.
#
# No console typing: with a Russian keyboard layout active the console key
# never reaches the game, and --script-run does not need it.
param(
  [int]$Kill = 0,
  [int]$LoadSeconds = 45
)
$ErrorActionPreference = "Stop"
$wt = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$exe = "D:\Program Files\OpenMW 0.51.0\openmw.exe"
$cfg = "D:\Documents\My Games\OpenMW\dev"
if ($Kill) { Stop-Process -Id $Kill -Force -ErrorAction SilentlyContinue; Start-Sleep 2 }

$argline = @(
  '--replace', 'config', '--config', "`"$cfg`"",
  '--data', "`"$wt\tools\build`"",
  '--data', "`"$wt\tools\build\armour-vanilla`"",
  '--data', "`"$wt\tools\viewer`"",
  '--content', 'scifi-rewrite.esp', '--content', 'zenar_viewer.omwscripts',
  '--skip-menu', '--start', 'ToddTest', '--no-sound',
  '--script-run', "`"$wt\tools\viewer\equip.txt`""
) -join ' '
$p = Start-Process $exe -ArgumentList $argline -PassThru
Write-Output "pid $($p.Id)"
Start-Sleep -Seconds $LoadSeconds

# The profile writes screenshots wherever its user data lives; ask the log.
$log = Get-Content (Join-Path $cfg 'openmw.log') -TotalCount 12 |
  Select-String 'Screenshots dir: (.*)$'
$dir = $log.Matches[0].Groups[1].Value.Trim()
& (Join-Path $PSScriptRoot 'shot.ps1') -Target $p.Id -Count 8 -GapSeconds 3 -Dir $dir |
  Out-Null
python -c @"
import os, sys
from PIL import Image
d = sys.argv[1]
fs = sorted((f for f in os.listdir(d) if f.endswith('.png')),
            key=lambda f: os.path.getmtime(os.path.join(d, f)))[-8:]
tiles = [Image.open(os.path.join(d, f)).convert('RGB').crop((740, 180, 1180, 1080))
         .resize((180, 368)) for f in fs]
sheet = Image.new('RGB', (720, 736))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % 4) * 180, (i // 4) * 368))
out = os.path.join(sys.argv[2], 'tools', 'reports', 'fitcheck.jpg')
sheet.save(out, quality=82)
print(out)
"@ $dir $wt
Write-Output "pid $($p.Id)"
# Done looking: close it straight away, by pid, never by name.
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Write-Output "closed"
