# Make the game take its own screenshot, and hand back the file.
#
#     powershell -File tools/scripts/shot.ps1 -Target <pid> [-Count 3]
#
# F12 is OpenMW's screenshot key. Sent with SendInput - which injects below the
# window message queue, where SDL is listening - the engine writes a full
# 2.5 MB PNG into the profile's screenshots folder. That file is the honest
# picture: every way of grabbing the window from outside returned frames that
# were minutes out of date.
#
# **-Target is required and is not a formality.** Faig runs a second session of
# this project in parallel and the game can be open more than once; an earlier
# version of this took whichever OpenMW answered first, which meant pressing a
# key into somebody else's window and reading back the wrong picture. If the pid
# given is not a game window, this stops rather than guessing.

param(
  [Parameter(Mandatory = $true)][int]$Target,
  [int]$Count = 1,
  [int]$GapSeconds = 8,
  [string]$Dir = "D:\Backups\OneDrive\All\Documents\My Games\OpenMW\screenshots"
)

Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public class Shot {
  [StructLayout(LayoutKind.Sequential)] public struct KI { public ushort vk, sc; public uint fl, time; public IntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct IN { public uint type; public KI ki; public int pad1, pad2; }
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, IN[] a, int size);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint c, uint t);
  public static uint Owner(IntPtr h) { uint p; GetWindowThreadProcessId(h, out p); return p; }
  public static void Tap(ushort vk) {
    uint sc = MapVirtualKey(vk, 0);
    IN[] a = new IN[2];
    a[0].type = 1; a[0].ki.vk = vk; a[0].ki.sc = (ushort)sc; a[0].ki.fl = 0x0008;
    a[1].type = 1; a[1].ki.vk = vk; a[1].ki.sc = (ushort)sc; a[1].ki.fl = 0x0008 | 0x0002;
    SendInput(2, a, Marshal.SizeOf(typeof(IN)));
  }
}
'@

$p = Get-Process -Id $Target -ErrorAction SilentlyContinue
if (-not $p) { Write-Output "no process $Target"; exit 1 }
if ($p.ProcessName -ne "openmw") { Write-Output "$Target is $($p.ProcessName), not openmw"; exit 1 }
if ($p.MainWindowHandle -eq 0) { Write-Output "$Target has no window yet"; exit 1 }

$before = @(Get-ChildItem $Dir -Filter *.png -ErrorAction SilentlyContinue).Name
[Shot]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
[Shot]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 1800

# Check who actually ended up in front. Windows can refuse a foreground change,
# and a keypress then lands somewhere else entirely.
$owner = [Shot]::Owner([Shot]::GetForegroundWindow())
if ($owner -ne $Target) {
  # OpenMW runs two processes per game and either may own the window. Only the
  # ones `play.ps1` wrote down are ours - **counting processes proves nothing**,
  # because the single game that is running may belong to Faig's other session.
  $ours = @()
  $note = Join-Path $env:TEMP "zenar-game.txt"
  if (Test-Path $note) { $ours = (Get-Content $note) -split "," }
  if ($ours -notcontains [string]$owner) {
    Write-Output "the foreground window belongs to process $owner, which this session did not start - not pressing anything"
    exit 1
  }
}

for ($i = 1; $i -le $Count; $i++) {
  [Shot]::Tap(0x7B)                        # VK_F12
  if ($i -lt $Count) { Start-Sleep -Seconds $GapSeconds }
}
Start-Sleep -Seconds 3
$new = Get-ChildItem $Dir -Filter *.png | Where-Object { $before -notcontains $_.Name } |
       Sort-Object LastWriteTime
if (-not $new) { Write-Output "no new screenshot appeared"; exit 1 }
$new | ForEach-Object { $_.FullName }
