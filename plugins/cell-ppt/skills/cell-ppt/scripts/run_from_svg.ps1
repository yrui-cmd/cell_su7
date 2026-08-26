#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputSvg,

    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,

    [ValidateSet('auto', 'powerpoint', 'wps')]
    [string]$HostApplication = 'auto',

    [switch]$UseActivePresentation,

    [switch]$Foreground,

    [switch]$CreateNewPresentation,

    [switch]$KeepBackground,

    [ValidateRange(0, 10000)]
    [int]$StepDelayMs = 80
)

$ErrorActionPreference = 'Stop'
$inputPath = (Resolve-Path -LiteralPath $InputSvg).Path
$outputRootPath = [IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Force -Path $outputRootPath | Out-Null

$allocator = Join-Path $PSScriptRoot 'allocate_shibielujing_name.py'
$validator = Join-Path $PSScriptRoot 'validate_vector_svg.py'
$cacheBuilder = Join-Path $PSScriptRoot 'prepare_geometry_cache.py'
$visibilityCuller = Join-Path $PSScriptRoot 'cull_hidden_geometry.py'
$pptRuntime = Join-Path $PSScriptRoot 'run_cell_ppt.ps1'
foreach ($required in @($allocator, $validator, $cacheBuilder, $visibilityCuller, $pptRuntime)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing runtime file: $required" }
}

$baseName = (& py -3 -X utf8 $allocator --root $outputRootPath | Select-Object -Last 1).Trim()
if ($baseName -notmatch '^shibielujing\d+$') { throw 'Could not allocate output name.' }
$jobRoot = Join-Path $outputRootPath $baseName
$cacheRoot = Join-Path $jobRoot '.cell-ppt-cache'
$outputPptx = Join-Path $jobRoot "$baseName.pptx"
New-Item -ItemType Directory -Force -Path $jobRoot | Out-Null

& py -3 -X utf8 $validator --svg $inputPath | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'SVG validation failed.' }
& py -3 -X utf8 $cacheBuilder --input $inputPath --output-dir $cacheRoot --job-id $baseName | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Geometry cache preparation failed.' }
& py -3 -X utf8 $visibilityCuller --cache (Join-Path $cacheRoot 'geometry-cache.json') --state (Join-Path $cacheRoot 'playback.json') | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Visible-path culling failed.' }

$runtimeArgs = @{
    GeometryCache = (Join-Path $cacheRoot 'geometry-cache.json')
    OutputPptx = $outputPptx
    HostApplication = $HostApplication
    StepDelayMs = $StepDelayMs
}
$drawIntoActive = -not $CreateNewPresentation
if ($UseActivePresentation) { $drawIntoActive = $true }
if ($drawIntoActive) { $runtimeArgs.UseActivePresentation = $true }
$bringForwardOnce = -not $KeepBackground
if ($Foreground) { $bringForwardOnce = $true }
if ($bringForwardOnce) { $runtimeArgs.Foreground = $true }
& $pptRuntime @runtimeArgs | Out-Null

[pscustomobject][ordered]@{
    ok = $true
    base_name = $baseName
    pptx = $outputPptx
    source_svg = $inputPath
    cache = (Join-Path $cacheRoot 'geometry-cache.json')
} | ConvertTo-Json -Compress
