#requires -Version 5.1

[CmdletBinding()]
param([switch]$Verify)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$manifestPath = Join-Path $repoRoot 'FROZEN-MANIFEST.json'
$tracked = @(
    'requirements.lock',
    'runtime-lock.json',
    'plugins/cell-ppt/.codex-plugin/plugin.json',
    'plugins/cell-ppt/skills/cell-ppt/SKILL.md',
    'plugins/cell-ppt/skills/cell-ppt/references/workflow.md',
    'plugins/cell-ppt/skills/cell-ppt/references/backends.md',
    'plugins/cell-ppt/skills/cell-ppt/scripts/prepare_geometry_cache.py',
    'plugins/cell-ppt/skills/cell-ppt/scripts/cull_hidden_geometry.py',
    'plugins/cell-ppt/skills/cell-ppt/scripts/merge_live_text.py',
    'plugins/cell-ppt/skills/cell-ppt/scripts/run_cell_ppt.ps1',
    'plugins/cell-ppt/skills/cell-ppt/scripts/run_from_svg.ps1',
    'plugins/cell-ppt/skills/cell-ppt/scripts/run_from_image.ps1',
    'plugins/cell-ppt/skills/cell-ppt/scripts/set-xiaomiao-key.ps1',
    'plugins/cell-ppt/skills/cell-ppt/scripts/vectorize-xiaomiao.ps1',
    'plugins/cell-ppt/skills/cell-ppt/scripts/xiaomiao.ps1'
)

$files = [ordered]@{}
foreach ($relative in $tracked) {
    $absolute = Join-Path $repoRoot ($relative -replace '/', '\')
    if (-not (Test-Path -LiteralPath $absolute -PathType Leaf)) { throw "Frozen file is missing: $relative" }
    $files[$relative] = (Get-FileHash -LiteralPath $absolute -Algorithm SHA256).Hash.ToLowerInvariant()
}
$expected = [ordered]@{ schemaVersion = '1.0'; product = 'Cell_ppt'; version = '0.1.1'; tag = 'v0.1.1'; files = $files }

if ($Verify) {
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'FROZEN-MANIFEST.json is missing.' }
    $actual = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($actual.schemaVersion -ne '1.0' -or $actual.product -ne 'Cell_ppt' -or $actual.version -ne '0.1.1' -or $actual.tag -ne 'v0.1.1') { throw 'Frozen manifest identity is invalid.' }
    foreach ($relative in $tracked) {
        if ([string]$actual.files.$relative -ne [string]$files[$relative]) { throw "Frozen hash mismatch: $relative" }
    }
    Write-Output "FROZEN_OK|files=$($tracked.Count)|version=0.1.1"
    exit 0
}

$expected | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Output "FROZEN_UPDATED|files=$($tracked.Count)|version=0.1.1"
