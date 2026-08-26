#requires -Version 5.1

[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$requirements = Join-Path $projectRoot 'requirements.lock'
$installer = Join-Path $projectRoot 'install.ps1'
$doctor = Join-Path $projectRoot 'doctor.ps1'
foreach ($required in @($requirements, $installer, $doctor)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing setup component: $required" }
}

& py -3 -m pip install --disable-pip-version-check --requirement $requirements
if ($LASTEXITCODE -ne 0) { throw 'Locked Python dependency installation failed.' }

& $installer -Force:$Force
& $doctor
Write-Output 'SETUP_OK|skill=cell-ppt|restart_codex=true|api_key_configured_by_codex=true'
