# Move the game's camera with the mouse, from a script.
#
#     powershell -File tools/scripts/mouse.ps1 -Target <pid> -Dx 1200
#     powershell -File tools/scripts/mouse.ps1 -Target <pid> -Wheel -4
#
# In third person a relative mouse motion orbits the camera around the
# character, and the wheel moves it in and out - which is how the suit gets
# looked at from every side without Faig standing at the keyboard. SendInput
# with plain MOUSEEVENTF_MOVE is relative motion, which is exactly what SDL
# reads; the motion is fed in small steps because the engine clamps a single
# huge jump.
#
# Same ownership rule as `shot.ps1` and `console.ps1`: only the processes
# `play.ps1` wrote down are ours, and nothing else gets touched. A single
# running game is not proof it is ours - it may be the other session's.

param(
  [Parameter(Mandatory = $true)][int]$Target,
  [int]$Dx = 0,
  [int]$Dy = 0,
  [int]$Wheel = 0,
  [int]$StepPx = 30,
  [int]$StepMs = 8
)

Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public class M {
  [StructLayout(LayoutKind.Sequential)] public struct MI { public int dx, dy; public uint data, flags, time; public IntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct IN { public uint type; public MI mi; }
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, IN[] a, int size);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  public static uint Owner(IntPtr h) { uint p; GetWindowThreadProcessId(h, out p); return p; }
  public static void Move(int dx, int dy) {
    IN[] a = new IN[1];
    a[0].type = 0; a[0].mi.dx = dx; a[0].mi.dy = dy; a[0].mi.flags = 0x0001;
    SendInput(1, a, Marshal.SizeOf(typeof(IN)));
  }
  public static void Turn(int notches) {
    IN[] a = new IN[1];
    a[0].type = 0; a[0].mi.data = unchecked((uint)(notches * 120));
    a[0].mi.flags = 0x0800;
    SendInput(1, a, Marshal.SizeOf(typeof(IN)));
  }
}
'@

$p = Get-Process -Id $Target -ErrorAction SilentlyContinue
if (-not $p -or $p.ProcessName -ne "openmw" -or $p.MainWindowHandle -eq 0) {
  Write-Output "$Target is not a game window"; exit 1
}
[M]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
[M]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 1200

$owner = [M]::Owner([M]::GetForegroundWindow())
$ours = @()
$note = Join-Path $env:TEMP "zenar-game.txt"
if (Test-Path $note) { $ours = (Get-Content $note) -split "," }
if ($ours -notcontains [string]$owner) {
  Write-Output "the foreground window belongs to process $owner, which this session did not start - not moving the mouse"
  exit 1
}

if ($Wheel -ne 0) {
  $way = if ($Wheel -gt 0) { 1 } else { -1 }
  for ($i = 0; $i -lt [Math]::Abs($Wheel); $i++) {
    [M]::Turn($way); Start-Sleep -Milliseconds 90
  }
}
$sx = if ($Dx -ge 0) { 1 } else { -1 }
$sy = if ($Dy -ge 0) { 1 } else { -1 }
$rx = [Math]::Abs($Dx); $ry = [Math]::Abs($Dy)
while ($rx -gt 0 -or $ry -gt 0) {
  $mx = [Math]::Min($StepPx, $rx); $my = [Math]::Min($StepPx, $ry)
  [M]::Move($sx * $mx, $sy * $my)
  $rx -= $mx; $ry -= $my
  Start-Sleep -Milliseconds $StepMs
}
Write-Output "moved dx=$Dx dy=$Dy wheel=$Wheel"
