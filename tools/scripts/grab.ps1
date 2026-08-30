# Take a picture of the running game, so Claude can look without being sent one.
#
#     powershell -File tools/scripts/grab.ps1 -Target <pid> [-Front] [-Out x.png]
#
# Every round of the armour work was decided by Faig photographing his screen
# with a phone, which is slow, dark and loses detail. This grabs the OpenMW
# window straight from Windows.
#
# **It captures that one window and nothing else** - not the desktop, not other
# applications - and it only reads. It cannot click or type, so driving the game
# still needs hands, or the computer-use permission, which has to be approved in
# the desktop app rather than from a phone.
#
# **Always name the instance with -Target.** Faig runs a second session of this
# project in parallel and its game is a different copy with different work in
# it; without a pid the first version took whichever OpenMW answered first and
# grabbed his other window. (`$Pid` is read-only in PowerShell, hence -Target.)
#
# ## Why the obvious ways return a picture of the past
#
# Two were tried and both lie on this machine:
#
# * **PrintWindow** came back with a full, plausible 1920x1080 frame that was
#   simply out of date - the same loading screen twice while the game's own log
#   showed it had long since entered its cell.
# * **Graphics.CopyFromScreen** did the same: two grabs a minute apart, byte for
#   byte identical, while the game played on.
#
# A hardware-accelerated window does not paint into the surface those read; they
# hand back whatever was last composed. It is the same defect Faig hits with
# Ctrl+PrintScreen, where he presses two or three times before the picture
# catches up.
#
# The cure is CAPTUREBLT, a raster-op flag that makes Windows compose the
# layered content before copying. .NET will not accept it - CopyPixelOperation
# rejects the combined value - so the blit goes through GDI directly.

param(
  [string]$Out = "$env:TEMP\openmw-grab.png",
  [int]$Target = 0,
  [switch]$Front,
  [switch]$Print
)

Add-Type -TypeDefinition @'
using System;
using System.Drawing;
using System.Runtime.InteropServices;
public class Grab {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int w, int t, uint f);
  [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr h);
  [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr h, IntPtr dc);
  [DllImport("gdi32.dll")] public static extern IntPtr CreateCompatibleDC(IntPtr dc);
  [DllImport("gdi32.dll")] public static extern IntPtr CreateCompatibleBitmap(IntPtr dc, int w, int h);
  [DllImport("gdi32.dll")] public static extern IntPtr SelectObject(IntPtr dc, IntPtr o);
  [DllImport("gdi32.dll")] public static extern bool BitBlt(IntPtr d, int dx, int dy, int w, int h, IntPtr s, int sx, int sy, uint rop);
  [DllImport("gdi32.dll")] public static extern bool DeleteObject(IntPtr o);
  [DllImport("gdi32.dll")] public static extern bool DeleteDC(IntPtr dc);

  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }

  public static void Front(IntPtr h) {
    ShowWindow(h, 9);                                    // SW_RESTORE
    SetWindowPos(h, new IntPtr(-1), 0,0,0,0, 0x0003);    // HWND_TOPMOST
    SetForegroundWindow(h);
    SetWindowPos(h, new IntPtr(-2), 0,0,0,0, 0x0003);    // HWND_NOTOPMOST
  }

  // SRCCOPY | CAPTUREBLT - the flag is the whole point, see the header.
  const uint ROP = 0x00CC0020 | 0x40000000;

  public static Bitmap Screen(IntPtr h) {
    RECT r; GetWindowRect(h, out r);
    int w = r.R - r.L, t = r.B - r.T;
    IntPtr src = GetDC(IntPtr.Zero);
    IntPtr dst = CreateCompatibleDC(src);
    IntPtr bmp = CreateCompatibleBitmap(src, w, t);
    IntPtr old = SelectObject(dst, bmp);
    BitBlt(dst, 0, 0, w, t, src, r.L, r.T, ROP);
    SelectObject(dst, old);
    Bitmap outp = Image.FromHbitmap(bmp);
    DeleteObject(bmp); DeleteDC(dst); ReleaseDC(IntPtr.Zero, src);
    return outp;
  }

  public static Bitmap Window(IntPtr h) {
    RECT r; GetWindowRect(h, out r);
    Bitmap bmp = new Bitmap(r.R-r.L, r.B-r.T);
    using (Graphics g = Graphics.FromImage(bmp)) {
      IntPtr dc = g.GetHdc(); PrintWindow(h, dc, 2); g.ReleaseHdc(dc);
    }
    return bmp;
  }
}
'@ -ReferencedAssemblies System.Drawing, System.Windows.Forms

$all = @(Get-Process openmw -ErrorAction SilentlyContinue |
         Where-Object { $_.MainWindowHandle -ne 0 })
if (-not $all) { Write-Output "OpenMW is not running, or has no window yet"; exit 1 }
if ($Target) {
  $p = $all | Where-Object { $_.Id -eq $Target } | Select-Object -First 1
  if (-not $p) { Write-Output "No OpenMW window belongs to process $Target"; exit 1 }
} elseif ($all.Count -gt 1) {
  Write-Output ("More than one OpenMW is running - " + ($all.Id -join ", ") +
                ". Pass -Target to say which.")
  exit 1
} else { $p = $all[0] }

if ($Front) { [Grab]::Front($p.MainWindowHandle); Start-Sleep -Milliseconds 1500 }
$bmp = if ($Print) { [Grab]::Window($p.MainWindowHandle) }
       else { [Grab]::Screen($p.MainWindowHandle) }
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output ("{0}x{1} by {2}" -f $bmp.Width, $bmp.Height,
              $(if ($Print) { "PrintWindow" } else { "BitBlt with CAPTUREBLT" }))
Write-Output $Out
$bmp.Dispose()
