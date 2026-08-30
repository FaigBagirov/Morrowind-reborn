# Run and look at the game from THIS worktree, without touching any config.
#
#     powershell -File tools/scripts/play2.ps1 status
#     powershell -File tools/scripts/play2.ps1 start   [-Save TEST1]
#     powershell -File tools/scripts/play2.ps1 shot    [-Name charge]
#     powershell -File tools/scripts/play2.ps1 stop
#
# The other worktree of this project - "D:\Work\Morrowind reborn" - runs its own
# game from the same play profile. That profile is one directory: one openmw.log,
# one player_storage.bin, one navmesh.db, one saves folder and one screenshots
# folder. Two instances at once would interleave all six, and a screenshot could
# not be attributed to either.
#
# So the rule here is not "pass the right pid", it is "there is only ever one".
# `start` refuses while any other OpenMW has a window, and says which worktree
# the one it found belongs to, read off its own command line.
#
# What makes this worktree's build the one that loads: OpenMW appends
# command-line values for multi-value settings *after* the config's, and a later
# data directory wins in the VFS. Passing our mod/ and tools/build/ last is
# therefore enough, and openmw.cfg is left exactly as the other worktree wrote
# it. Same mechanism as run-play-2.bat, which stays for Faig to run by hand.
#
# Two things measured by the other worktree and taken as given here:
#
#   * Never redirect the game's output. With -RedirectStandardOutput the same
#     save took fourteen minutes and never finished; without it, ~25 seconds.
#   * A grab of a hardware-accelerated window returns the last composed frame
#     unless the window is in the foreground and rendering. F12 - the game's own
#     screenshot - is the better picture, and it is full resolution.

param(
  [Parameter(Position=0)]
  [ValidateSet('status','start','shot','stop')]
  [string]$Do = 'status',
  [string]$Save = 'TEST1',
  [string]$Name = ''
)

$ErrorActionPreference = 'Stop'

$Here    = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # the worktree
$Exe     = "D:\Program Files\OpenMW 0.51.0\openmw.exe"
$Cfg     = "D:\Backups\OneDrive\All\Documents\My Games\OpenMW\play"
$UserDir = "D:\Backups\OneDrive\All\Documents\My Games\OpenMW"     # no user-data= in openmw.cfg
$Shots   = Join-Path $UserDir 'screenshots'
$PidFile = Join-Path $Here 'logs\play2.pid'
$ShotDir = Join-Path $Here 'logs\shots'

function Windowed { @(Get-Process openmw -ErrorAction SilentlyContinue |
                      Where-Object { $_.MainWindowHandle -ne 0 }) }

function OurPid {
  if (-not (Test-Path $PidFile)) { return 0 }
  $id = [int](Get-Content $PidFile | Select-Object -First 1)
  if (Get-Process -Id $id -ErrorAction SilentlyContinue) { return $id }
  return 0
}

# Whose game is this? Only one answer is reliable: the pid we recorded when we
# started it. The other worktree launches with --config alone and no --data - it
# relies on openmw.cfg, which points at its own directory - so its command line
# says nothing about where its content came from. Anything not in our pid file
# is therefore reported as not ours, and the command line only ever adds detail.
function Describe($p) {
  $c = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)").CommandLine
  $where = if ($p.Id -eq (OurPid)) { 'THIS worktree' }
           elseif ($c -match [regex]::Escape($Here)) { 'this directory, but not started by us' }
           else { 'not ours - another session, or Faig by hand' }
  $save = if ($c -match '--load-savegame\s+"?([^"]+)') { ', save ' + (Split-Path $Matches[1] -Leaf) } else { '' }
  "  pid $($p.Id)  started $($p.StartTime.ToString('HH:mm:ss'))  -  $where$save"
}

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class Play {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int w, int t, uint f);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] i, int cb);

  [StructLayout(LayoutKind.Sequential)]
  public struct KEYBDINPUT { public ushort wVk, wScan; public uint dwFlags, time; public IntPtr extra; }
  [StructLayout(LayoutKind.Sequential)]
  public struct MOUSEINPUT { public int dx, dy; public uint data, flags, time; public IntPtr extra; }
  // Explicit layout so Marshal.SizeOf gives the size of the whole union, 40 on
  // x64. SendInput rejects a cbSize measured off the keyboard variant alone.
  [StructLayout(LayoutKind.Explicit)]
  public struct INPUT {
    [FieldOffset(0)] public uint type;
    [FieldOffset(8)] public KEYBDINPUT ki;
    [FieldOffset(8)] public MOUSEINPUT mi;
  }

  public static void Front(IntPtr h) {
    ShowWindow(h, 9);                                    // SW_RESTORE
    SetWindowPos(h, new IntPtr(-1), 0,0,0,0, 0x0003);    // HWND_TOPMOST
    SetForegroundWindow(h);
    SetWindowPos(h, new IntPtr(-2), 0,0,0,0, 0x0003);    // HWND_NOTOPMOST
  }

  public static bool IsFront(IntPtr h) { return GetForegroundWindow() == h; }

  public static uint Key(ushort vk) {
    INPUT[] i = new INPUT[2];
    i[0].type = 1; i[0].ki.wVk = vk; i[0].ki.dwFlags = 0;
    i[1].type = 1; i[1].ki.wVk = vk; i[1].ki.dwFlags = 2;   // KEYEVENTF_KEYUP
    return SendInput(2, i, Marshal.SizeOf(typeof(INPUT)));
  }
}
'@

switch ($Do) {

'status' {
  $all = Windowed
  if (-not $all) { Write-Output "No OpenMW is running." }
  else { Write-Output "OpenMW running:"; $all | ForEach-Object { Write-Output (Describe $_) } }
  $mine = OurPid
  Write-Output $(if ($mine) { "This worktree's game: pid $mine" }
                 else       { "This worktree has no game running." })
}

'start' {
  if (-not (Test-Path $Exe)) { throw "OpenMW not found: $Exe" }
  $savePath = Join-Path $UserDir "saves\Faig\$Save.omwsave"
  if (-not (Test-Path $savePath)) { throw "No such save: $savePath" }
  if (-not (Test-Path (Join-Path $Here 'mod\scripts\rewrite\rules.lua'))) {
    throw "rules.lua is not built. Run: python tools\scripts\transform.py --write"
  }
  if (-not (Test-Path (Join-Path $Here 'tools\build\scifi-rewrite-momw.esp'))) {
    throw "scifi-rewrite-momw.esp is not built in this worktree. Without it the plugin half silently reverts to whatever the other worktree built."
  }

  $mine = OurPid
  if ($mine) { Write-Output "Already running here: pid $mine"; break }
  $other = Windowed
  if ($other) {
    Write-Output "REFUSED: another OpenMW has a window, and the play profile is"
    Write-Output "one directory - one log, one save folder, one screenshots"
    Write-Output "folder. Close it first, or let that session finish."
    $other | ForEach-Object { Write-Output (Describe $_) }
    exit 1
  }

  $argv = @('--replace','config','--config',$Cfg,
            '--data',(Join-Path $Here 'mod'),
            '--data',(Join-Path $Here 'tools\build'),
            '--skip-menu','--load-savegame',$savePath)
  # No redirection. See the header - it cost the other worktree an hour.
  $p = Start-Process -FilePath $Exe -ArgumentList $argv -PassThru
  New-Item -ItemType Directory -Force -Path (Split-Path $PidFile) | Out-Null
  Set-Content -Path $PidFile -Value $p.Id -Encoding ascii
  Write-Output "Started pid $($p.Id), loading $Save. Give it ~25 seconds."
}

'shot' {
  $id = OurPid
  if (-not $id) { throw "This worktree has no game running. Run: play2.ps1 start" }
  $p = Get-Process -Id $id
  if ($p.MainWindowHandle -eq 0) { throw "pid $id has no window yet" }

  [Play]::Front($p.MainWindowHandle)
  Start-Sleep -Milliseconds 1200
  if (-not [Play]::IsFront($p.MainWindowHandle)) {
    Write-Output "WARNING: the window did not come to the front. F12 will not"
    Write-Output "reach the game, and any grab would be the last composed frame."
  }

  $mark = Get-Date
  $sent = [Play]::Key(0x7B)                       # VK_F12
  if ($sent -ne 2) { throw "SendInput accepted $sent of 2 events" }

  $new = $null
  for ($i = 0; $i -lt 40 -and -not $new; $i++) {
    Start-Sleep -Milliseconds 250
    $new = Get-ChildItem $Shots -Filter *.png -ErrorAction SilentlyContinue |
           Where-Object { $_.LastWriteTime -gt $mark } |
           Sort-Object LastWriteTime | Select-Object -Last 1
  }
  if (-not $new) { throw "No new PNG appeared in $Shots within 10s" }

  New-Item -ItemType Directory -Force -Path $ShotDir | Out-Null
  $stamp = $new.LastWriteTime.ToString('HHmmss')
  $leaf  = if ($Name) { "$stamp-$Name.png" } else { "$stamp-$($new.BaseName).png" }
  $dest  = Join-Path $ShotDir $leaf
  Copy-Item $new.FullName $dest -Force
  Write-Output ("{0}  ({1:N0} bytes, written {2})" -f $dest, $new.Length,
                $new.LastWriteTime.ToString('HH:mm:ss'))
}

'stop' {
  $id = OurPid
  if (-not $id) { Write-Output "Nothing of ours is running."; break }
  $p = Get-Process -Id $id
  $null = $p.CloseMainWindow()
  if (-not $p.WaitForExit(15000)) { $p.Kill(); Write-Output "Killed pid $id" }
  else { Write-Output "Closed pid $id" }
  Remove-Item $PidFile -ErrorAction SilentlyContinue

  $log = Join-Path $Cfg 'openmw.log'
  if (Test-Path $log) {
    $dest = Join-Path $Here 'logs\openmw-play-2.log'
    Copy-Item $log $dest -Force
    Write-Output "Log -> logs\openmw-play-2.log"
    $r = Select-String -Path $dest -SimpleMatch '[REWRITE]'
    Write-Output $(if ($r) { "$($r.Count) [REWRITE] lines" }
                   else    { "WARNING: no [REWRITE] lines - the Lua half did not run." })
  }
}

}
