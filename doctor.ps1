#requires -Version 5.1

[CmdletBinding()]
param(
    [switch]$VerifyApi,
    [switch]$RequirePowerPointOpen,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$skillRoot = Join-Path $projectRoot 'plugins\cell-ppt\skills\cell-ppt'
$required = @(
    'SKILL.md',
    'scripts\run_cell_ppt.ps1',
    'scripts\run_from_svg.ps1',
    'scripts\run_from_image.ps1',
    'scripts\prepare_geometry_cache.py',
    'scripts\cull_hidden_geometry.py',
    'scripts\merge_live_text.py',
    'scripts\vectorize-xiaomiao.ps1',
    'scripts\set-xiaomiao-key.ps1'
)
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $skillRoot $relative) -PathType Leaf)) { throw "Missing: $relative" }
}

& py -3 -X utf8 -c "import sys, pptx, fontTools, shapely; assert (3,11) <= sys.version_info[:2] < (3,15); assert pptx.__version__ == '1.0.2'; assert fontTools.__version__ == '4.61.1'; assert shapely.__version__ == '2.1.2'" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Locked Python dependencies are unavailable or mismatched.' }

$powerPointRegistered = [type]::GetTypeFromProgID('PowerPoint.Application') -ne $null
$wpsRegistered = ([type]::GetTypeFromProgID('KWPP.Application') -ne $null) -or ([type]::GetTypeFromProgID('WPP.Application') -ne $null)
$powerPointOpen = @(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
if (-not $powerPointRegistered) { throw 'Microsoft PowerPoint desktop COM automation is unavailable.' }
if ($RequirePowerPointOpen -and -not $powerPointOpen) { throw 'Microsoft PowerPoint is not open.' }

$apiAuthenticated = $null
if ($VerifyApi) {
    $verification = & (Join-Path $skillRoot 'scripts\xiaomiao.ps1') verify
    $apiAuthenticated = $verification.authenticated -eq $true
    if (-not $apiAuthenticated) { throw 'Xiaomiao API authentication failed.' }
}

$result = [ordered]@{
    ok = $true
    skill = 'cell-ppt'
    powerPointRegistered = $powerPointRegistered
    powerPointOpen = $powerPointOpen
    wpsExperimentalRegistered = $wpsRegistered
    apiVerified = [bool]$VerifyApi
    apiAuthenticated = $apiAuthenticated
}
if ($Json) { $result | ConvertTo-Json -Compress }
else { Write-Output "DOCTOR_OK|skill=cell-ppt|powerpoint=$($powerPointRegistered.ToString().ToLowerInvariant())|powerpoint_open=$($powerPointOpen.ToString().ToLowerInvariant())|wps_experimental=$($wpsRegistered.ToString().ToLowerInvariant())|api_verified=$($VerifyApi.ToString().ToLowerInvariant())" }
