$env:PYTHONUTF8 = "1"
Set-Location (Join-Path $PSScriptRoot "..")
python -m resolver.serve @args
