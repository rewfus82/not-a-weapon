<#
.SYNOPSIS
  Launch the interactive Godot control server for "This Is Not A Weapon".

.DESCRIPTION
  Starts a persistent Godot process running the game + a TCP command server
  (tools/agent_server.gd) that the client (tools/naw.py) drives command by
  command. Waits until the port is accepting connections, then returns, leaving
  the server running in the background.

  Stop it with:  python tools/naw.py quit   (or close the game window)

.EXAMPLE
  ./tools/serve.ps1
  python tools/naw.py state
  python tools/naw.py key w down
  python tools/naw.py screenshot
  python tools/naw.py quit
#>
[CmdletBinding()]
param(
  [int]$Port = 8899,
  [string]$Size = "1600x900",
  [string]$OutDir = "",
  [string]$Godot = ""
)

$ErrorActionPreference = "Stop"
$toolsDir = $PSScriptRoot
$projDir  = Split-Path -Parent $toolsDir

if (-not $Godot) {
  $candidates = @(
    "C:\Users\rewfu\Godot\Godot_v4.7-stable_win64_console.exe",
    "C:\Users\rewfu\Godot\Godot_v4.7-stable_win64.exe"
  )
  $Godot = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Godot -or -not (Test-Path $Godot)) { Write-Error "Godot not found. Pass -Godot <path>."; exit 3 }

if (-not $OutDir) { $OutDir = Join-Path $toolsDir "captures" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$log = Join-Path $OutDir "server.log"

# Refuse to double-start on the same port.
if ((Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet)) {
  Write-Host "A server is already listening on port $Port." -ForegroundColor Yellow
  exit 0
}

$env:NAW_PORT = "$Port"
$env:NAW_OUT  = $OutDir
$env:NAW_SIZE = $Size

$godotArgs = @("--path", $projDir, "res://tools/agent_server.tscn", "--resolution", $Size)
$proc = Start-Process -FilePath $Godot -ArgumentList $godotArgs `
          -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru

# Wait for the port to come up.
$up = $false
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 250
  if (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet) { $up = $true; break }
  if ($proc.HasExited) { break }
}

if ($up) {
  Write-Host "Server up on 127.0.0.1:$Port (pid $($proc.Id))." -ForegroundColor Green
  Write-Host "Drive it:  python tools/naw.py state   |   stop:  python tools/naw.py quit"
  Write-Host "Logs: $log"
  exit 0
} else {
  Write-Host "Server did not come up. See $log / $log.err" -ForegroundColor Red
  exit 1
}
