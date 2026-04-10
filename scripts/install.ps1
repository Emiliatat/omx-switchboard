$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$targetDir = Join-Path $codexHome "skills\\omx-switchboard"
$legacyTargetDir = Join-Path $codexHome "skills\\omx-router"
$sourceDir = Join-Path $repoRoot "skills\\omx-switchboard"
$binDir = if ($env:BIN_DIR) { $env:BIN_DIR } else { Join-Path $HOME ".local\\bin" }

New-Item -ItemType Directory -Force (Join-Path $codexHome "skills") | Out-Null
New-Item -ItemType Directory -Force $binDir | Out-Null
if (Test-Path $targetDir) {
    Remove-Item -Recurse -Force $targetDir
}
if (Test-Path $legacyTargetDir) {
    Remove-Item -Recurse -Force $legacyTargetDir
}
Copy-Item -Recurse -Force $sourceDir $targetDir
Copy-Item -Force (Join-Path $repoRoot "scripts\\omxr.py") (Join-Path $binDir "omxr.py")
@'
@echo off
py -3 -c "import sys" >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0omxr.py" %*
  exit /b %errorlevel%
)
python "%~dp0omxr.py" %*
'@ | Set-Content -NoNewline (Join-Path $binDir "omxr.cmd")
@'
@echo off
py -3 -c "import sys" >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0omxr.py" %*
  exit /b %errorlevel%
)
python "%~dp0omxr.py" %*
'@ | Set-Content -NoNewline (Join-Path $binDir "omx-switchboard.cmd")
if (Test-Path (Join-Path $binDir "codex-omx-router.cmd")) {
    Remove-Item -Force (Join-Path $binDir "codex-omx-router.cmd")
}

Write-Host "Installed omx-switchboard to $targetDir"
Write-Host "Installed launchers to $(Join-Path $binDir 'omxr.cmd') and $(Join-Path $binDir 'omx-switchboard.cmd')"
