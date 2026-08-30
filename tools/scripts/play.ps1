# Start the game the way this project always wants it, and say which process.
#
#     powershell -File tools/scripts/play.ps1
#
# Straight into TEST1 with the menu skipped, because that is what Faig asked
# for and the save loads in about twenty-five seconds.
#
# **Never redirect the game's output.** With -RedirectStandardOutput the same
# load ran fourteen minutes and never finished. The profile writes openmw.log
# anyway, and this waits on that.
#
# Prints the pid last, which is what `shot.ps1 -Target` needs. Everything in
# this project that touches the game must name its process: the game can be open
# more than once, and Faig runs a second session of this project in parallel.

param(
  [string]$Config = 'D:\Backups\OneDrive\All\Documents\My Games\OpenMW\play',
  [string]$Save   = 'D:\Backups\OneDrive\All\Documents\My Games\OpenMW\saves\Faig\TEST1.omwsave',
  [string]$Exe    = 'D:\Program Files\OpenMW 0.51.0\openmw.exe',
  [int]$SettleSeconds = 30
)

Get-Process openmw -ErrorAction SilentlyContinue |
  ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Seconds 4
Get-Process openmw -ErrorAction SilentlyContinue |
  Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$log = Join-Path $Config "openmw.log"
if (Test-Path $log) { Remove-Item $log -ErrorAction SilentlyContinue }

$p = Start-Process -FilePath $Exe -PassThru -ArgumentList (
  '--replace config --config "{0}" --skip-menu --load-savegame "{1}"' -f $Config, $Save)

for ($i = 1; $i -le 20; $i++) {
  Start-Sleep -Seconds 10
  if (-not (Get-Process -Id $p.Id -ErrorAction SilentlyContinue)) {
    Write-Output "the game exited while loading"; exit 1
  }
  if (Select-String -Path $log -Pattern "Loading cell" -Quiet -ErrorAction SilentlyContinue) {
    break
  }
}
Start-Sleep -Seconds $SettleSeconds

# **Report the process that owns the window, not the one Start-Process
# returned.** OpenMW runs as two processes per game, and the window can belong
# to the sibling; the foreground check in shot.ps1 caught exactly that. The
# window owner is the one every other script needs.
$mine = @(Get-Process openmw -ErrorAction SilentlyContinue |
          Where-Object { $_.MainWindowHandle -ne 0 -and
                         [Math]::Abs(($_.StartTime - $p.StartTime).TotalSeconds) -lt 15 })
if ($mine) { Write-Output $mine[0].Id } else { Write-Output $p.Id }
