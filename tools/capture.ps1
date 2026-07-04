<#
.SYNOPSIS
  Run "This Is Not A Weapon", capture a screenshot + console log, and report.

.DESCRIPTION
  One-shot feedback tool for agent-driven iteration: launch the game via the
  headless-ish capture harness (tools/agent_capture.tscn), let it run, grab a
  PNG of the rendered frame plus all console + GDScript-error output, then print
  a compact PASS/FAIL summary and the paths. Blocks until the game exits so the
  caller gets everything in a single invocation.

  Edits nothing in the game; safe to run anytime.

.EXAMPLE
  ./tools/capture.ps1
  ./tools/capture.ps1 -Keys "w,d" -Warmup 2.5 -Duration 3
#>
[CmdletBinding()]
param(
  [string]$Keys = "",          # keys to hold, comma list e.g. "w,d" or "space"
  [double]$Warmup = 1.5,       # seconds before the first capture
  [double]$Duration = 0,       # extra seconds, then a second "frame_end" capture
  [string]$Size = "1600x900",  # capture resolution
  [string]$OutDir = "",        # defaults to tools/captures
  [string]$Godot = ""          # override Godot exe path
)

$ErrorActionPreference = "Stop"

# --- locate things ----------------------------------------------------------
$toolsDir = $PSScriptRoot
$projDir  = Split-Path -Parent $toolsDir

if (-not $Godot) {
  $candidates = @(
    "C:\Users\rewfu\Godot\Godot_v4.7-stable_win64_console.exe",
    "C:\Users\rewfu\Godot\Godot_v4.7-stable_win64.exe"
  )
  $Godot = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Godot -or -not (Test-Path $Godot)) {
  Write-Error "Godot executable not found. Pass -Godot <path>."
  exit 3
}

if (-not $OutDir) { $OutDir = Join-Path $toolsDir "captures" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$log = Join-Path $OutDir "console.log"

# clear stale artifacts so the caller never reads a previous run's frame
Remove-Item (Join-Path $OutDir "*.png") -ErrorAction SilentlyContinue
Remove-Item $log -ErrorAction SilentlyContinue

# --- config to harness via env ---------------------------------------------
$env:NAW_OUT      = $OutDir
$env:NAW_KEYS     = $Keys
$env:NAW_WARMUP   = "$Warmup"
$env:NAW_DURATION = "$Duration"
$env:NAW_SIZE     = $Size

# --- run --------------------------------------------------------------------
# Positional scene arg runs that scene instead of the project's main scene.
# --quit-after is a hard backstop in case the harness never reaches quit().
$maxFrames = [int](( ($Warmup + $Duration + 8) ) * 60)
$godotArgs = @("--path", $projDir, "res://tools/agent_capture.tscn",
               "--resolution", $Size, "--quit-after", "$maxFrames")

& $Godot @godotArgs *>&1 | Tee-Object -FilePath $log | Out-Null
$code = $LASTEXITCODE

# --- assess -----------------------------------------------------------------
$logText = if (Test-Path $log) { Get-Content $log -Raw } else { "" }
$scriptErrors = @()
if ($logText) {
  $scriptErrors = Select-String -Path $log -Pattern "SCRIPT ERROR|Parse Error|HARNESS-ERROR" `
                    -SimpleMatch:$false | ForEach-Object { $_.Line.Trim() }
}
$shots = Get-ChildItem (Join-Path $OutDir "*.png") -ErrorAction SilentlyContinue

$pass = ($code -eq 0) -and ($shots.Count -gt 0) -and ($scriptErrors.Count -eq 0)

# --- report -----------------------------------------------------------------
Write-Host ""
Write-Host ("=" * 60)
if ($pass) { Write-Host "RESULT: PASS" -ForegroundColor Green }
else       { Write-Host "RESULT: FAIL" -ForegroundColor Red }
Write-Host ("exit code : {0}" -f $code)
Write-Host ("screenshots ({0}):" -f $shots.Count)
foreach ($s in $shots) { Write-Host ("  {0}" -f $s.FullName) }
Write-Host ("console log: {0}" -f $log)
if ($scriptErrors.Count -gt 0) {
  Write-Host "errors:" -ForegroundColor Red
  foreach ($e in ($scriptErrors | Select-Object -First 20)) { Write-Host "  $e" -ForegroundColor Red }
}
Write-Host ("=" * 60)

if (-not $pass) { exit 1 }
exit 0
