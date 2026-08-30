# Take a picture of the running game, so Claude can look without being sent one.
#
#     powershell -File tools/scripts/grab.ps1 [-Out path.png]
#
# Every round of the armour work was decided by Faig photographing his screen
# with a phone, which is slow and loses detail. This grabs the OpenMW window
# straight from Windows.
#
# **It captures that one window and nothing else** - not the desktop, not other
# applications - and it only reads. It cannot click or type; driving the game
# still needs either Faig's hands or the computer-use permission, and that
# permission has to be approved in the desktop app, not from a phone.
#
# PrintWindow with PW_RENDERFULLCONTENT is tried first because it works on a
# window that is behind another one. Some drivers hand back a black frame for a
# hardware-accelerated window, so the result is checked - if too little of it is
# lit, it falls back to reading that rectangle off the screen, which needs the
# game to be visible.

param(
  [string]$Out = "$env:TEMP\openmw-grab.png",
  [int]$Pid = 0,
  [double]$MinLit = 0.02
)

Add-Type -TypeDefinition @'
using System;
using System.Drawing;
using System.Runtime.InteropServices;
public class Grab {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
  public static Bitmap Shot(IntPtr h, bool full) {
    RECT r; GetWindowRect(h, out r);
    Bitmap bmp = new Bitmap(r.R-r.L, r.B-r.T);
    using (Graphics g = Graphics.FromImage(bmp)) {
      if (full) { IntPtr dc = g.GetHdc(); PrintWindow(h, dc, 2); g.ReleaseHdc(dc); }
      else { g.CopyFromScreen(r.L, r.T, 0, 0, bmp.Size); }
    }
    return bmp;
  }
}
'@ -ReferencedAssemblies System.Drawing, System.Windows.Forms

function Lit($bmp) {
  $n = 0; $lit = 0
  for ($x = 0; $x -lt $bmp.Width; $x += 17) {
    for ($y = 0; $y -lt $bmp.Height; $y += 17) {
      $c = $bmp.GetPixel($x, $y); $n++
      if ($c.R + $c.G + $c.B -gt 24) { $lit++ }
    }
  }
  if ($n -eq 0) { 0 } else { $lit / $n }
}

# **Always name the instance.** Faig runs a second session of this project in
# parallel, and its game is a different copy with different work in it. Without
# -Pid this took whichever OpenMW answered first and grabbed his other window.
$all = @(Get-Process openmw -ErrorAction SilentlyContinue |
         Where-Object { $_.MainWindowHandle -ne 0 })
if (-not $all) { Write-Output "OpenMW is not running, or has no window yet"; exit 1 }
if ($Pid) {
  $p = $all | Where-Object { $_.Id -eq $Pid } | Select-Object -First 1
  if (-not $p) { Write-Output "No OpenMW window belongs to process $Pid"; exit 1 }
} elseif ($all.Count -gt 1) {
  Write-Output ("More than one OpenMW is running - " +
                ($all.Id -join ", ") + ". Pass -Pid to say which.")
  exit 1
} else { $p = $all[0] }

$bmp = [Grab]::Shot($p.MainWindowHandle, $true)
$how = "PrintWindow"
if ((Lit $bmp) -lt $MinLit) {
  $bmp.Dispose()
  $bmp = [Grab]::Shot($p.MainWindowHandle, $false)
  $how = "off the screen (the window has to be visible)"
}
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output ("{0}x{1}, {2:P0} lit, by {3}" -f $bmp.Width, $bmp.Height, (Lit $bmp), $how)
Write-Output $Out
$bmp.Dispose()
