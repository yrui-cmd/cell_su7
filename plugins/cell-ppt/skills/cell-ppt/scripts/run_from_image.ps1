#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputImage,

    [Parameter(Mandatory = $true)]
    [string]$TextManifest,

    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,

    [ValidateSet('auto', 'powerpoint', 'wps')]
    [string]$HostApplication = 'auto',

    [ValidateRange(0, 1000000)]
    [int]$EstimatedCredits = 1,

    [switch]$ApproveHighCost,

    [switch]$UseActivePresentation,

    [switch]$Foreground,

    [switch]$CreateNewPresentation,

    [switch]$KeepBackground,

    [ValidateRange(0, 10000)]
    [int]$StepDelayMs = 80
)

$ErrorActionPreference = 'Stop'
$inputPath = (Resolve-Path -LiteralPath $InputImage).Path
$manifestPath = (Resolve-Path -LiteralPath $TextManifest).Path
$outputRootPath = [IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Force -Path $outputRootPath | Out-Null

$allocator = Join-Path $PSScriptRoot 'allocate_shibielujing_name.py'
$vectorizer = Join-Path $PSScriptRoot 'vectorize-xiaomiao.ps1'
$textMerger = Join-Path $PSScriptRoot 'merge_live_text.py'
$cacheBuilder = Join-Path $PSScriptRoot 'prepare_geometry_cache.py'
$visibilityCuller = Join-Path $PSScriptRoot 'cull_hidden_geometry.py'
$pptRuntime = Join-Path $PSScriptRoot 'run_cell_ppt.ps1'
foreach ($required in @($allocator, $vectorizer, $textMerger, $cacheBuilder, $visibilityCuller, $pptRuntime)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing runtime file: $required" }
}

$baseName = (& py -3 -X utf8 $allocator --root $outputRootPath | Select-Object -Last 1).Trim()
if ($baseName -notmatch '^shibielujing\d+$') { throw 'Could not allocate output name.' }
$jobRoot = Join-Path $outputRootPath $baseName
$cacheRoot = Join-Path $jobRoot '.cell-ppt-cache'
$rawSvg = Join-Path $jobRoot "$baseName-vector.svg"
$masterSvg = Join-Path $jobRoot "$baseName.svg"
$outputPptx = Join-Path $jobRoot "$baseName.pptx"
New-Item -ItemType Directory -Force -Path $jobRoot | Out-Null

$vectorizerArgs = @{
    InputImage = $inputPath
    OutputSvg = $rawSvg
    EstimatedCredits = $EstimatedCredits
}
if ($ApproveHighCost) { $vectorizerArgs.ApproveHighCost = $true }
& $vectorizer @vectorizerArgs | Out-Null
& py -3 -X utf8 $textMerger --input-svg $rawSvg --text-manifest $manifestPath --output-svg $masterSvg | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Editable text merge failed.' }
& py -3 -X utf8 $cacheBuilder --input $masterSvg --output-dir $cacheRoot --job-id $baseName | Out-Null
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
    svg = $masterSvg
    vector_svg = $rawSvg
    text_manifest = $manifestPath
    cache = (Join-Path $cacheRoot 'geometry-cache.json')
} | ConvertTo-Json -Compress
