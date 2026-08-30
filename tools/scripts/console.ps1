# Type commands into the running game's console.
#
#     powershell -File tools/scripts/console.ps1 -Target <pid> -Lines 'player->SetStrength 200','player->Equip "daedric_cuirass"'
#
# So a check can be set up without asking Faig to stand at the keyboard: give
# the character the pieces, wear them, then photograph. Characters go in as
# Unicode key events, which is what SDL reads as text; the console is opened
# with the grave key and closed again afterwards.
#
# **-Target is required and is verified**, and the foreground is checked after
# asking for it - the same rule as `shot.ps1`, for the same reason. A console
# line typed into the wrong window is worse than a screenshot of one.

param(
  [Parameter(Mandatory = $true)][int]$Target,
  [Parameter(Mandatory = $true)][string[]]$Lines,
  [int]$SettleMs = 900
)

Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public class Con {
  [StructLayout(LayoutKind.Sequential)] public struct KI { public ushort vk, sc; public uint fl, time; public IntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct IN { public uint type; public KI ki; public int pad1, pad2; }
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, IN[] a, int size);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint c, uint t);
  public static uint Owner(IntPtr h) { uint p; GetWindowThreadProcessId(h, out p); return p; }

  public static void Key(ushort vk) {
    uint sc = MapVirtualKey(vk, 0);
    IN[] a = new IN[2];
    a[0].type = 1; a[0].ki.vk = vk; a[0].ki.sc = (ushort)sc; a[0].ki.fl = 0x0008;
    a[1].type = 1; a[1].ki.vk = vk; a[1].ki.sc = (ushort)sc; a[1].ki.fl = 0x0008 | 0x0002;
    SendInput(2, a, Marshal.SizeOf(typeof(IN)));
  }

  public static void Text(string s) {
    foreach (char c in s) {
      IN[] a = new IN[2];
      a[0].type = 1; a[0].ki.sc = (ushort)c; a[0].ki.fl = 0x0004;             // UNICODE
      a[1].type = 1; a[1].ki.sc = (ushort)c; a[1].ki.fl = 0x0004 | 0x0002;    // and up
      SendInput(2, a, Marshal.SizeOf(typeof(IN)));
      System.Threading.Thread.Sleep(8);
    }
  }
}
'@

$p = Get-Process -Id $Target -ErrorAction SilentlyContinue
if (-not $p) { Write-Output "no process $Target"; exit 1 }
if ($p.ProcessName -ne "openmw") { Write-Output "$Target is $($p.ProcessName), not openmw"; exit 1 }
if ($p.MainWindowHandle -eq 0) { Write-Output "$Target has no window"; exit 1 }

[Con]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
[Con]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 1800
$owner = [Con]::Owner([Con]::GetForegroundWindow())
if ($owner -ne $Target) {
  # The other half of the same game is acceptable - OpenMW runs two processes
  # and either may own the window. Anything else is somebody else's game, or
  # another application entirely, and gets nothing.
  $him = Get-Process -Id $owner -ErrorAction SilentlyContinue
  $me  = Get-Process -Id $Target -ErrorAction SilentlyContinue
  $sibling = $him -and $me -and $him.ProcessName -eq "openmw" -and
             [Math]::Abs(($him.StartTime - $me.StartTime).TotalSeconds) -lt 15
  if (-not $sibling) {
    Write-Output "the foreground window belongs to $owner, not $Target - typing nothing"
    exit 1
  }
}

[Con]::Key(0xC0)                      # grave, opens the console
Start-Sleep -Milliseconds $SettleMs
foreach ($line in $Lines) {
  [Con]::Text($line)
  Start-Sleep -Milliseconds 250
  [Con]::Key(0x0D)                    # Return
  Start-Sleep -Milliseconds 350
  Write-Output "typed: $line"
}
Start-Sleep -Milliseconds $SettleMs
[Con]::Key(0xC0)                      # and closes it again
Start-Sleep -Milliseconds 600
