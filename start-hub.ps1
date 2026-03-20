$ErrorActionPreference = "Stop"
$modulePath = $PWD.Path

# Start the hub + dashboard API in a separate PowerShell window
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "powershell.exe"
$psi.Arguments = "-NoExit -Command `"Set-Location '$modulePath'; npm run start:hub`""
$psi.UseShellExecute = $true
$psi.WindowStyle = "Normal"
[void][System.Diagnostics.Process]::Start($psi)

# Start vite dashboard dev server
$dashPsi = New-Object System.Diagnostics.ProcessStartInfo
$dashPsi.FileName = "powershell.exe"
$dashPsi.Arguments = "-NoExit -Command `"Set-Location '$modulePath\dashboard'; npm run dev`""
$dashPsi.UseShellExecute = $true
$dashPsi.WindowStyle = "Normal"
[void][System.Diagnostics.Process]::Start($dashPsi)

Write-Host "Started hub and dashboard windows."
