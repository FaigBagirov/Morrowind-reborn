# Run and look at the game from THIS worktree, without touching any config.
#
#     powershell -File tools/scripts/play2.ps1 status
#     powershell -File tools/scripts/play2.ps1 start   [-Save TEST1]
#     powershell -File tools/scripts/play2.ps1 shot    [-Name charge]
#     powershell -File tools/scripts/play2.ps1 stop
#
# The other worktree of this project - "D:\Work\Morrowind reborn" - runs its own
# game, and Faig wants both running at once, each session driving and
# photographing its own. That works, but not by simply starting a second copy of
# the same profile. The play profile is one directory, and two instances sharing
# it would interleave one openmw.log, one player_storage.bin, one 1.6 GB
# navmesh.db and one screenshots folder - and a screenshot could then be
# attributed to neither.
#
# So this one runs isolated instead. `run/` holds our own config directory and
# our own user-data directory, and every launch regenerates the config by
# copying the play profile's openmw.cfg verbatim - so the mod list is always
# whatever the other worktree last configured, and his file is never written to.
# That copy is safe because the file names only absolute paths and carries no
# config=, user-data= or data-local= line of its own. Measured, not assumed.
#
# What ends up isolated: log, screenshots, saves, Lua storage, navmesh cache,
# settings. What is still genuinely shared, and cannot be:
#
#   * the foreground. Only one window is frontmost, and F12 goes there. So each
#     session must front its own window immediately before pressing - which is
#     what `shot` does, and it says so when the front did not take.
#   * the machine. Two fully loaded 240-plugin instances is twice the memory.
#     Ours runs windowed at 1280x720 with a 30 fps cap and the navmesh cache
#     switched off, so it stays the cheap one.
#
# What makes this worktree's build the one that loads: OpenMW appends
# command-line values for multi-value settings *after* the config's, and a later
# data directory wins in the VFS. Passing our mod/ and tools/build/ last is
# therefore enough. Same mechanism as run-play-2.bat, which stays for Faig to
# run by hand against his own profile.
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
  [ValidateSet('status','start','shot','stop','console','press','click','type')]
  [string]$Do = 'status',
  [string]$Save = 'TEST1',
  [string]$Name = '',
  [string]$Text = '',
  [int]$Times = 1,
  [switch]$F12,
  [switch]$Inject
)

# Physical key positions, so the layout Windows believes in cannot change what
# the game receives. Values are PC/XT set-1 scan codes, which is what SendInput
# takes and what SDL turns back into its own scancodes.
$Scan = @{ 'console' = 0x29; 'grave' = 0x29; 'enter' = 0x1C; 'esc' = 0x01
           'i' = 0x17; 'space' = 0x39; 'tab' = 0x0F; 'w' = 0x11
           'back' = 0x0E; 'up' = 0xC8; 'down' = 0xD0
           'e' = 0x12; 'j' = 0x24; 'r' = 0x13 }

$ErrorActionPreference = 'Stop'

$Here    = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # the worktree
$Exe     = "D:\Program Files\OpenMW 0.51.0\openmw.exe"
$Play    = "D:\Documents\My Games\OpenMW\play"  # his, read only
$Saves   = "D:\Documents\My Games\OpenMW\saves\Faig"
$MyCfg   = Join-Path $Here 'run\config'
$MyData  = Join-Path $Here 'run\userdata'
$Shots   = Join-Path $MyData 'screenshots'
$PidFile = Join-Path $Here 'logs\play2.pid'
$ShotDir = Join-Path $Here 'logs\shots'

# Settings we impose on our instance, on top of a verbatim copy of his. Every
# other line of his settings.cfg is kept, so what we look at is what he sees.
$Force = [ordered]@{
  'Video'     = [ordered]@{ 'window mode' = '2'          # 2 = Windowed, per defaults.bin
                            'resolution x' = '1280'
                            'resolution y' = '720'
                            'framerate limit' = '30' }   # his game gets the GPU
  'Navigator' = [ordered]@{ 'write to navmeshdb' = 'false' }   # his cache is 1.6 GB
}

# Rewrite an ini so the forced keys appear exactly once, in the right section.
# Every existing occurrence is deleted first rather than overridden in place, so
# nothing depends on how OpenMW resolves a repeated key.
function Impose($srcPath, $dstPath, $force) {
  $out = New-Object System.Collections.Generic.List[string]
  $sec = ''
  foreach ($ln in Get-Content $srcPath) {
    $t = $ln.Trim()
    if ($t -match '^\[(.+)\]$') { $sec = $Matches[1] }
    elseif ($force.Contains($sec) -and $t -match '^\s*([^#=]+?)\s*=') {
      if ($force[$sec].Contains($Matches[1])) { continue }
    }
    $out.Add($ln)
  }
  foreach ($s in $force.Keys) {
    $out.Add(''); $out.Add("[$s]")
    $out.Add("# Imposed by tools/scripts/play2.ps1 - this is the second instance.")
    foreach ($k in $force[$s].Keys) { $out.Add("$k = $($force[$s][$k])") }
  }
  Set-Content -Path $dstPath -Value $out -Encoding ascii
}

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

  // By scan code, not virtual key. The game reads SDL scancodes, which are
  // physical positions - so this means the same key whatever layout Windows
  // thinks is active, which matters on a machine that has a Russian one.
  public static uint Scan(ushort sc) {
    INPUT[] i = new INPUT[2];
    i[0].type = 1; i[0].ki.wScan = sc; i[0].ki.dwFlags = 0x0008;          // SCANCODE
    i[1].type = 1; i[1].ki.wScan = sc; i[1].ki.dwFlags = 0x0008 | 0x0002; // + KEYUP
    return SendInput(2, i, Marshal.SizeOf(typeof(INPUT)));
  }

  // Text goes in as Unicode, which the console receives as SDL text input and
  // which no layout can reinterpret.
  public static uint Text(string s) {
    INPUT[] i = new INPUT[s.Length * 2];
    for (int n = 0; n < s.Length; n++) {
      i[n*2  ].type = 1; i[n*2  ].ki.wScan = s[n]; i[n*2  ].ki.dwFlags = 0x0004;
      i[n*2+1].type = 1; i[n*2+1].ki.wScan = s[n]; i[n*2+1].ki.dwFlags = 0x0004 | 0x0002;
    }
    return SendInput((uint)i.Length, i, Marshal.SizeOf(typeof(INPUT)));
  }

  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern int GetSystemMetrics(int i);
  [DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT p);
  [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint f);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X,Y; }

  // Is our window the one actually on screen at its own centre? A screen-space
  // grab copies whatever is painted there, so an overlapping window would be
  // photographed instead of ours, silently and plausibly.
  public static bool Visible(IntPtr h) {
    RECT c; GetClientRect(h, out c);
    POINT p; p.X = c.R / 2; p.Y = c.B / 2; ClientToScreen(h, ref p);
    IntPtr top = WindowFromPoint(p);
    return GetAncestor(top, 2) == h;                      // GA_ROOT
  }

  // ---- Input posted straight to the window, no foreground needed ----
  //
  // SendInput goes to whoever is frontmost, which is the one thing two sessions
  // cannot both have. Measured on 2026-08-30: while our window was in front,
  // the other session's F12 was received by OUR game, which dutifully wrote
  // screenshot004-006 into our folder, and its Escape opened our options menu.
  // Neither session did anything wrong; global injection simply has no address.
  //
  // A posted message does have one. These go to a named window whether or not
  // it has focus, so both games can be driven at once and neither sees the
  // other's keys.
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint type);

  public static void PostKey(IntPtr h, ushort sc) {
    uint vk = MapVirtualKey(sc, 1);                       // MAPVK_VSC_TO_VK
    IntPtr down = (IntPtr)(1 | (sc << 16));
    IntPtr up   = (IntPtr)(1 | (sc << 16) | (3 << 30));   // bits 30,31: was-down, released
    PostMessage(h, 0x0100, (IntPtr)vk, down);             // WM_KEYDOWN
    System.Threading.Thread.Sleep(70);
    PostMessage(h, 0x0101, (IntPtr)vk, up);               // WM_KEYUP
  }

  public static void PostText(IntPtr h, string s) {
    foreach (char c in s) {
      PostMessage(h, 0x0102, (IntPtr)c, (IntPtr)1);       // WM_CHAR
      System.Threading.Thread.Sleep(15);
    }
  }

  // times=1 is a click; times=2 is a real double-click, which is a different
  // message rather than two of the same one. Windows sends WM_LBUTTONDBLCLK for
  // the second press, SDL counts its clicks from that message alone, and MyGUI
  // asks SDL. Two plain presses are therefore two single clicks however close
  // together, which in the inventory picks an item up and then drops it.
  //
  // Reading a book from the inventory is not a double-click at all. Faig gave
  // the real gesture: click once to lift the book onto the cursor, move to the
  // player figure without holding the button, and click again. What I did
  // instead - place a copy in the world, pitch the camera down with
  // player->SetAngle X, and activate it - also works and needs no drag.
  public static void PostClick(IntPtr h, int x, int y, int times) {
    IntPtr lp = (IntPtr)((y << 16) | (x & 0xFFFF));
    PostMessage(h, 0x0200, IntPtr.Zero, lp);              // WM_MOUSEMOVE
    System.Threading.Thread.Sleep(120);
    for (int n = 0; n < times; n++) {
      uint down = (n == 0) ? 0x0201u : 0x0203u;           // WM_LBUTTONDOWN / DBLCLK
      PostMessage(h, down, (IntPtr)1, lp);
      System.Threading.Thread.Sleep(80);
      PostMessage(h, 0x0202, IntPtr.Zero, lp);            // WM_LBUTTONUP
      System.Threading.Thread.Sleep(80);
    }
  }

  // Click in client coordinates of the given window.
  public static void Click(IntPtr h, int cx, int cy, int times) {
    POINT p; p.X = cx; p.Y = cy; ClientToScreen(h, ref p);
    int w = GetSystemMetrics(0), t = GetSystemMetrics(1);
    int ax = (int)((p.X * 65535.0) / (w - 1)), ay = (int)((p.Y * 65535.0) / (t - 1));
    INPUT[] mv = new INPUT[1];
    mv[0].type = 0; mv[0].mi.dx = ax; mv[0].mi.dy = ay;
    mv[0].mi.flags = 0x0001 | 0x8000;                     // MOVE | ABSOLUTE
    SendInput(1, mv, Marshal.SizeOf(typeof(INPUT)));
    for (int n = 0; n < times; n++) {
      INPUT[] b = new INPUT[1];
      INPUT[] u = new INPUT[1];
      b[0].type = 0; b[0].mi.dx = ax; b[0].mi.dy = ay; b[0].mi.flags = 0x0002 | 0x0001 | 0x8000;
      u[0].type = 0; u[0].mi.dx = ax; u[0].mi.dy = ay; u[0].mi.flags = 0x0004 | 0x0001 | 0x8000;
      // Hold the button across at least one frame. The game runs at 30 fps here
      // and its GUI samples input per frame, so a press and release delivered
      // in the same instant can be seen as neither.
      SendInput(1, b, Marshal.SizeOf(typeof(INPUT)));
      System.Threading.Thread.Sleep(90);
      SendInput(1, u, Marshal.SizeOf(typeof(INPUT)));
      System.Threading.Thread.Sleep(90);
    }
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
  $savePath = Join-Path $Saves "$Save.omwsave"
  if (-not (Test-Path $savePath)) { throw "No such save: $savePath" }
  if (-not (Test-Path (Join-Path $Here 'mod\scripts\rewrite\rules.lua'))) {
    throw "rules.lua is not built. Run: python tools\scripts\transform.py --write"
  }
  if (-not (Test-Path (Join-Path $Here 'tools\build\scifi-rewrite-momw.esp'))) {
    throw "scifi-rewrite-momw.esp is not built in this worktree. Without it the plugin half silently reverts to whatever the other worktree built."
  }
  $mine = OurPid
  if ($mine) { Write-Output "Already running here: pid $mine"; break }

  # Our own config, rebuilt every launch from his, so the mod list never goes
  # stale and his file is only ever read.
  New-Item -ItemType Directory -Force -Path $MyCfg, $MyData | Out-Null
  Copy-Item (Join-Path $Play 'openmw.cfg') (Join-Path $MyCfg 'openmw.cfg') -Force
  Impose (Join-Path $Play 'settings.cfg') (Join-Path $MyCfg 'settings.cfg') $Force
  # His key bindings, not the engine defaults. They differ - his are customised
  # - and a fresh profile silently gets the defaults, so a key pressed here
  # would not mean what it means in his game. (input_v3.xml and the Lua storage
  # bins live in the config directory, not user-data. Read off our own log.)
  Copy-Item (Join-Path $Play 'input_v3.xml') (Join-Path $MyCfg 'input_v3.xml') -Force

  $other = Windowed
  if ($other) {
    Write-Output "Another OpenMW is already running. Ours is isolated, so this"
    Write-Output "is allowed - but it is a second full modlist in memory:"
    $other | ForEach-Object { Write-Output (Describe $_) }
  }

  $argv = @('--replace','config','--config',$MyCfg,'--user-data',$MyData,
            '--data',(Join-Path $Here 'mod'),
            '--data',(Join-Path $Here 'tools\build'),
            '--skip-menu','--load-savegame',$savePath)
  # Quote every argument that contains a space, ourselves. Windows PowerShell's
  # -ArgumentList joins an array with spaces and does NOT quote the elements, so
  # "...\Morrowind reborn 2\run\config" arrived as three arguments and OpenMW
  # exited before it had opened a log to say so. Measured, 2026-08-30.
  $quoted = $argv | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }
  # No redirection. See the header - it cost the other worktree an hour.
  $p = Start-Process -FilePath $Exe -ArgumentList $quoted -PassThru
  New-Item -ItemType Directory -Force -Path (Split-Path $PidFile) | Out-Null
  Set-Content -Path $PidFile -Value $p.Id -Encoding ascii
  Write-Output "Started pid $($p.Id), loading $Save windowed at 1280x720."
  Write-Output "  config    $MyCfg"
  Write-Output "  user-data $MyData"
  Write-Output "Give it ~25 seconds."
}

'shot' {
  # Read the window, do not press anything. Our window is 1280x720, which is the
  # size F12 would have written anyway, so the game's own screenshot key buys
  # nothing here and costs a keystroke sent into a live game. It is kept behind
  # -F12 for when the full-size picture is actually wanted.
  #
  # The first attempt sent F12 into an instance running the *default* bindings -
  # a fresh profile has no input_v3.xml, and his are customised - so it produced
  # no screenshot. `start` now copies his bindings in.
  #
  # I also blamed that keystroke for the game quitting a fifth of a second
  # later, and that was wrong. It happened twice, and the second time no input
  # had been sent for sixteen seconds. Both times the other session's game
  # started about five seconds afterwards: its launcher closes every running
  # OpenMW, not only its own, and ours went with it. Nothing here can prevent
  # that - the fix belongs in the other worktree, and is the pid discipline this
  # script already keeps.
  $id = OurPid
  if (-not $id) { throw "This worktree has no game running. Run: play2.ps1 start" }
  $p = Get-Process -Id $id
  if ($p.MainWindowHandle -eq 0) { throw "pid $id has no window yet" }

  New-Item -ItemType Directory -Force -Path $ShotDir | Out-Null
  $stamp = (Get-Date).ToString('HHmmss')
  $leaf  = if ($Name) { "$stamp-$Name.png" } else { "$stamp.png" }
  $dest  = Join-Path $ShotDir $leaf

  if (-not $F12) {
    # No fronting. Our window is an ordinary visible 1280x720 one, so the
    # desktop composites it every frame and a screen-space grab is current -
    # which is exactly what the other worktree's window, going minimised on
    # focus loss, could not give it. Not fronting means his game keeps the
    # foreground and his own session is undisturbed.
    if (-not [Play]::Visible($p.MainWindowHandle)) {
      Write-Output "WARNING: something is covering our window, so the grab would"
      Write-Output "be a picture of that instead. Fronting ours for one frame."
      [Play]::Front($p.MainWindowHandle); Start-Sleep -Milliseconds 800
    }
    & (Join-Path $PSScriptRoot 'grab.ps1') -Target $id -Out $dest
    break
  }

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

  # OpenMW puts openmw.log in one of the two directories we gave it, and which
  # one is not worth remembering wrongly - take whichever is ours and newer.
  $log = @((Join-Path $MyData 'openmw.log'), (Join-Path $MyCfg 'openmw.log')) |
         Where-Object { Test-Path $_ } |
         Sort-Object { (Get-Item $_).LastWriteTime } | Select-Object -Last 1
  if (-not $log) { Write-Output "No openmw.log under run\ - nothing to collect."; break }

  $dest = Join-Path $Here 'logs\openmw-play-2.log'
  Copy-Item $log $dest -Force
  Write-Output "Log ($log) -> logs\openmw-play-2.log"
  $r = Select-String -Path $dest -SimpleMatch '[REWRITE]'
  Write-Output $(if ($r) { "$($r.Count) [REWRITE] lines" }
                 else    { "WARNING: no [REWRITE] lines - the Lua half did not run." })
}

'console' {
  # Open the console, type, run, close. The console key is sent by position -
  # the key left of 1 - because Faig's machine carries a second layout.
  if (-not $Text) { throw "console needs -Text '<command>'" }
  $id = OurPid; if (-not $id) { throw "No game of ours is running." }
  $h = (Get-Process -Id $id).MainWindowHandle
  if ($Inject) {
    [Play]::Front($h); Start-Sleep -Milliseconds 900
    if (-not [Play]::IsFront($h)) { throw "Could not take the foreground; input would go elsewhere." }
    [Play]::Scan($Scan['console']); Start-Sleep -Milliseconds 500
    [Play]::Text($Text);            Start-Sleep -Milliseconds 300
    [Play]::Scan($Scan['enter']);   Start-Sleep -Milliseconds 400
    [Play]::Scan($Scan['console']); Start-Sleep -Milliseconds 400
  } else {
    [Play]::PostKey($h, $Scan['console']); Start-Sleep -Milliseconds 500
    [Play]::PostText($h, $Text);           Start-Sleep -Milliseconds 300
    [Play]::PostKey($h, $Scan['enter']);   Start-Sleep -Milliseconds 400
    [Play]::PostKey($h, $Scan['console']); Start-Sleep -Milliseconds 400
  }
  Write-Output "ran: $Text"
}

'type' {
  # Type into whatever field the game has focused. Distinct from `console`,
  # which opens the console first - a click can quietly focus something else,
  # and then a console command is typed into that instead. That happened: a
  # click meant for the item filter opened the inventory search box, and two
  # console commands went into it.
  $id = OurPid; if (-not $id) { throw "No game of ours is running." }
  $h = (Get-Process -Id $id).MainWindowHandle
  if ($Inject) {
    [Play]::Front($h); Start-Sleep -Milliseconds 700
    if (-not [Play]::IsFront($h)) { throw "Could not take the foreground." }
    [Play]::Text($Text)
  } else { [Play]::PostText($h, $Text) }
  Write-Output "typed: $Text"
}

'press' {
  if (-not $Scan.ContainsKey($Text.ToLower())) {
    throw "No scan code known for '$Text'. Known: $($Scan.Keys -join ', ')"
  }
  $id = OurPid; if (-not $id) { throw "No game of ours is running." }
  $h = (Get-Process -Id $id).MainWindowHandle
  if ($Inject) {
    [Play]::Front($h); Start-Sleep -Milliseconds 700
    if (-not [Play]::IsFront($h)) { throw "Could not take the foreground." }
    for ($n = 0; $n -lt $Times; $n++) { [Play]::Scan($Scan[$Text.ToLower()]); Start-Sleep -Milliseconds 250 }
  } else {
    for ($n = 0; $n -lt $Times; $n++) { [Play]::PostKey($h, $Scan[$Text.ToLower()]); Start-Sleep -Milliseconds 180 }
  }
  Write-Output "pressed $Text x$Times"
}

'click' {
  if ($Text -notmatch '^\s*(\d+)\s*,\s*(\d+)\s*$') { throw "click needs -Text 'x,y' in client pixels" }
  $cx = [int]$Matches[1]; $cy = [int]$Matches[2]
  $id = OurPid; if (-not $id) { throw "No game of ours is running." }
  $h = (Get-Process -Id $id).MainWindowHandle
  if ($Inject) {
    [Play]::Front($h); Start-Sleep -Milliseconds 700
    if (-not [Play]::IsFront($h)) { throw "Could not take the foreground." }
    [Play]::Click($h, $cx, $cy, $Times)
  } else { [Play]::PostClick($h, $cx, $cy, $Times) }
  Write-Output "clicked $cx,$cy x$Times"
}

}
