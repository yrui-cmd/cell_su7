#requires -Version 5.1

[CmdletBinding()]
param(
    [string]$Destination = "$env:USERPROFILE\.codex\skills",
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$sourceRoot = Join-Path $PSScriptRoot 'plugins\cell-ppt\skills\cell-ppt'
$destinationRoot = [IO.Path]::GetFullPath($Destination)
$target = Join-Path $destinationRoot 'cell-ppt'
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) { throw "Plugin skill directory is missing: $sourceRoot" }
New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null

if (Test-Path -LiteralPath $target) {
    if (-not $Force) { throw "Skill already exists: $target. Re-run with -Force only if replacement is intended." }
    $allowedPrefix = $destinationRoot.TrimEnd('\') + '\'
    $resolvedTarget = [IO.Path]::GetFullPath($target)
    if (-not $resolvedTarget.StartsWith($allowedPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Refusing to replace a target outside the destination root.' }
    Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
}

Copy-Item -LiteralPath $sourceRoot -Destination $target -Recurse
Write-Output "INSTALLED|skill=cell-ppt|destination=$target|copy=true"
Write-Output 'Restart Codex and start a new task before first use.'
