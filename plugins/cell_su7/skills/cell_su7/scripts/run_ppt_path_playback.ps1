#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$InputPptx,
    [Parameter(Mandatory=$true)][string]$OutputPptx,
    [ValidateSet('Drag','Trace','Visibility')][string]$Mode = 'Drag',
    [ValidateScript({ $_ -gt 0 -and $_ -le 3.0 })][double]$MaxCursorCmPerSecond = 3.0,
    [switch]$Windowed,
    [switch]$WaitForStart
)
$ErrorActionPreference='Stop'
if ($Mode -ne 'Trace' -and $PSBoundParameters.ContainsKey('MaxCursorCmPerSecond')) {
    throw 'MaxCursorCmPerSecond requires Trace mode'
}
$inputPath=(Resolve-Path -LiteralPath $InputPptx).Path
$outputPath=[IO.Path]::GetFullPath($OutputPptx)
$python=Get-Command py -ErrorAction SilentlyContinue
$prefix=@('-3','-X','utf8')
if (-not $python) { $python=Get-Command python -ErrorAction Stop; $prefix=@('-X','utf8') }
if ($Mode -ne 'Visibility') {
    $playbackArgs=@('--input-pptx',$inputPath,'--output-pptx',$outputPath,'--mode',$Mode.ToLowerInvariant())
    if ($Mode -eq 'Trace') {
        $playbackArgs += @('--max-cursor-cm-per-second', $MaxCursorCmPerSecond.ToString([Globalization.CultureInfo]::InvariantCulture))
    }
    if ($Windowed) { $playbackArgs += '--windowed' }
    if ($WaitForStart) { $playbackArgs += '--wait-for-start' }
    & $python.Source @prefix (Join-Path $PSScriptRoot 'ppt_swarm_playback.py') @playbackArgs
    if ($LASTEXITCODE -ne 0) { throw "PowerPoint $Mode playback failed" }
    return
}
if ($Windowed -or $WaitForStart) { throw 'Windowed and WaitForStart require Drag or Trace mode' }
& $python.Source @prefix (Join-Path $PSScriptRoot 'prepare_path_playback.py') --input-pptx $inputPath --output-pptx $outputPath
if ($LASTEXITCODE -ne 0) { throw 'Path playback preparation failed' }
$app=New-Object -ComObject PowerPoint.Application
$app.Visible=-1
$deck=$app.Presentations.Open($outputPath,0,0,-1)
$slide=$deck.Slides.Item(1)
$timer=[Diagnostics.Stopwatch]::StartNew()
# Every shape is already a complete native object. No clipboard, artificial
# sleep, path splitting, or reordering; only visibility changes in source order.
for ($i=1; $i -le $slide.Shapes.Count; $i++) {
    $slide.Shapes.Item($i).Visible=-1
    if ($i % 100 -eq 0) { Write-Output "PATH_PROGRESS|$i/$($slide.Shapes.Count)" }
}
$deck.Save()
Write-Output "PATH_PLAYBACK_OK|objects=$($slide.Shapes.Count)|seconds=$($timer.Elapsed.TotalSeconds)|file=$outputPath"
