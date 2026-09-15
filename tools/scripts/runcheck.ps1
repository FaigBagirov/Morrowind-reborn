# Photograph the suit while the character runs - where rigid pieces part.
#
#     powershell -File tools/scripts/runcheck.ps1 [-Equip equip_wolf.txt]
#
# Faig saw the lower back open while running, which no standing screenshot
# shows. This launches the dev profile like fitcheck.ps1 but with the normal
# camera, switches to third person (Tab), holds W and presses F12 during the
# run, then closes the game by pid. Sheet: tools/reports/runcheck.jpg.
param(
  [string]$Equip = "equip.txt",
  [int]$LoadSeconds = 55
)
$ErrorActionPreference = "Stop"
$wt = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$exe = "D:\Program Files\OpenMW 0.51.0\openmw.exe"
$cfg = "D:\Documents\My Games\OpenMW\dev"

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Keys {
  [StructLayout(LayoutKind.Sequential)] struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Explicit)] struct INPUT { [FieldOffset(0)] public uint type; [FieldOffset(8)] public KEYBDINPUT ki; [FieldOffset(8)] public long pad1; [FieldOffset(16)] public long pad2; [FieldOffset(24)] public long pad3; [FieldOffset(32)] public long pad4; }
  [DllImport("user32.dll")] static extern uint SendInput(uint n, INPUT[] i, int size);
  public static int Size() { return Marshal.SizeOf(typeof(INPUT)); }
  public static void Scan(ushort code, bool up) {
    var i = new INPUT[1]; i[0].type = 1; i[0].ki.wScan = code;
    i[0].ki.dwFlags = 0x0008 | (up ? 0x0002u : 0u);
    SendInput(1, i, Marshal.SizeOf(typeof(INPUT)));
  }
}
"@

$argline = @(
  '--replace', 'config', '--config', "`"$cfg`"",
  '--data', "`"$wt\tools\build`"",
  '--data', "`"$wt\tools\build\armour-vanilla`"",
  '--content', 'scifi-rewrite.esp',
  '--skip-menu', '--start', 'ToddTest', '--no-sound',
  '--script-run', "`"$wt\tools\viewer\$Equip`""
) -join ' '
$p = Start-Process $exe -ArgumentList $argline -PassThru
Write-Output "pid $($p.Id)"
Start-Sleep -Seconds $LoadSeconds
$log = Get-Content (Join-Path $cfg 'openmw.log') -TotalCount 12 |
  Select-String 'Screenshots dir: (.*)$'
$dir = $log.Matches[0].Groups[1].Value.Trim()
$shot = Join-Path $PSScriptRoot 'shot.ps1'

& $shot -Target $p.Id -Count 1 -Dir $dir 2>&1 | Select-Object -Last 1   # fronts the window
[Keys]::Scan(0x0F, $false); Start-Sleep -Milliseconds 80; [Keys]::Scan(0x0F, $true)   # Tab
Start-Sleep -Seconds 2
Write-Output "INPUT size $([Keys]::Size())"
# S, not W: ToddTest starts facing a wall, so run backwards into the room
[Keys]::Scan(0x1F, $false)                                                  # S down
Start-Sleep -Milliseconds 700
& $shot -Target $p.Id -Count 3 -GapSeconds 1 -Dir $dir 2>&1 | Select-Object -Last 1
[Keys]::Scan(0x1F, $true)                                                   # S up

python -c @"
import os, sys
from PIL import Image
d = sys.argv[1]
fs = sorted((f for f in os.listdir(d) if f.endswith('.png')),
            key=lambda f: os.path.getmtime(os.path.join(d, f)))[-3:]
tiles = [Image.open(os.path.join(d, f)).convert('RGB').crop((560, 120, 1360, 1080))
         .resize((300, 360)) for f in fs]
sheet = Image.new('RGB', (900, 360))
for i, t in enumerate(tiles):
    sheet.paste(t, (i * 300, 0))
out = os.path.join(sys.argv[2], 'tools', 'reports', 'runcheck.jpg')
sheet.save(out, quality=82)
print(out)
"@ $dir $wt
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
Write-Output "closed"
