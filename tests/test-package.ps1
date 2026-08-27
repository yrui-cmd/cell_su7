#requires -Version 5.1

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pluginRoot = Join-Path $repoRoot 'plugins\cell-ppt'
$skillRoot = Join-Path $pluginRoot 'skills\cell-ppt'
$required = @(
    'README.md', 'README_EN.md', 'LICENSE', 'CHANGELOG.md', '.gitignore',
    'setup.ps1', 'install.ps1', 'doctor.ps1', 'build-release.ps1', 'update-frozen-manifest.ps1',
    'requirements.lock', 'runtime-lock.json', 'FROZEN-MANIFEST.json',
    'plugins\cell-ppt\.codex-plugin\plugin.json',
    'plugins\cell-ppt\skills\cell-ppt\SKILL.md',
    'plugins\cell-ppt\skills\cell-ppt\scripts\run_cell_ppt.ps1',
    'plugins\cell-ppt\skills\cell-ppt\scripts\run_from_svg.ps1',
    'plugins\cell-ppt\skills\cell-ppt\scripts\run_from_image.ps1',
    'plugins\cell-ppt\skills\cell-ppt\scripts\set-xiaomiao-key.ps1',
    'plugins\cell-ppt\skills\cell-ppt\scripts\cull_hidden_geometry.py'
)
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $relative) -PathType Leaf)) { throw "Required package file is missing: $relative" }
}

$plugin = Get-Content -LiteralPath (Join-Path $pluginRoot '.codex-plugin\plugin.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($plugin.name -ne 'cell-ppt' -or $plugin.version -ne '0.1.1' -or $plugin.skills -ne './skills/' -or $plugin.license -ne 'MIT') { throw 'Plugin identity is invalid.' }
if ($plugin.interface.displayName -ne 'Cell_ppt' -or $plugin.author.name -ne 'yrui-cmd') { throw 'Plugin display identity is invalid.' }
if (Test-Path -LiteralPath (Join-Path $repoRoot '.agents\plugins\marketplace.json')) { throw 'Marketplace metadata must not be included.' }

$runtime = Get-Content -LiteralPath (Join-Path $repoRoot 'runtime-lock.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($runtime.release -ne '0.1.1' -or $runtime.gitTag -ne 'v0.1.1' -or $runtime.codex.skillId -ne 'cell-ppt') { throw 'Runtime lock identity is invalid.' }
$expectedRequirements = "python-pptx==1.0.2`nfonttools==4.61.1`nshapely==2.1.2"
$actualRequirements = (Get-Content -LiteralPath (Join-Path $repoRoot 'requirements.lock') -Raw -Encoding UTF8).Trim() -replace "`r`n", "`n"
if ($actualRequirements -ne $expectedRequirements) { throw 'Python dependencies are not exactly locked.' }

$allFiles = Get-ChildItem -LiteralPath $repoRoot -Recurse -File -Force | Where-Object {
    $_.FullName -notmatch '[\\/]\.git[\\/]' -and $_.FullName -notmatch '[\\/]dist[\\/]'
}
$secretPattern = 'img_live_[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}'
foreach ($file in $allFiles) {
    if ($file.Extension -notin @('.md','.ps1','.py','.json','.yaml','.yml','.txt','.lock','.svg')) { continue }
    $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($content -and [regex]::IsMatch($content, $secretPattern)) { throw "A live API key marker was found in: $($file.FullName)" }
}

$legacyPattern = '(?i)cell(?:-|_)lct'
$legacy = rg -n $legacyPattern $repoRoot 2>$null
if ($LASTEXITCODE -eq 0 -and $legacy) { throw "Legacy identity remains:`n$legacy" }

$skillText = Get-Content -LiteralPath (Join-Path $skillRoot 'SKILL.md') -Raw -Encoding UTF8
foreach ($phrase in @(
    'name: cell-ppt',
    'Sole visibility rule',
    '部分可见的路径仍保留',
    'standard input',
    '感谢小红书：木纹小路。'
)) {
    if ($skillText -notlike "*$phrase*") { throw "Required Skill contract is missing: $phrase" }
}
foreach ($forbidden in @('Read-Host', 'Marketplace installation', 'stable WPS')) {
    if ($skillText -like "*$forbidden*") { throw "Conflicting Skill rule remains: $forbidden" }
}

& (Join-Path $repoRoot 'update-frozen-manifest.ps1') -Verify

$tempBase = Join-Path $repoRoot '.test-tmp'
$tempRoot = Join-Path $tempBase ([Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
try {
    $installRoot = Join-Path $tempRoot 'skills'
    & (Join-Path $repoRoot 'install.ps1') -Destination $installRoot
    $installed = Join-Path $installRoot 'cell-ppt\SKILL.md'
    if (-not (Test-Path -LiteralPath $installed -PathType Leaf)) { throw 'Install smoke test failed.' }
    if ((Get-Item -LiteralPath (Split-Path -Parent $installed)).LinkType) { throw 'Public installer created a link instead of a copy.' }

    $secretPath = Join-Path $tempRoot 'fake-key.dpapi'
    $setter = Join-Path $skillRoot 'scripts\set-xiaomiao-key.ps1'
    $fakeKey = ('img' + '_live_TESTKEY123456.TESTSECRET123456')
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = (Get-Process -Id $PID).Path
    $start.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$setter`" -FromStdin -SecretPath `"$secretPath`""
    $start.UseShellExecute = $false
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = [Diagnostics.Process]::Start($start)
    $process.StandardInput.WriteLine($fakeKey)
    $process.StandardInput.Close()
    $output = $process.StandardOutput.ReadToEnd()
    $errorOutput = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "Stdin credential setup failed: $errorOutput" }
    if ($output -notmatch 'KEY_CONFIG_OK' -or $output -match [regex]::Escape($fakeKey)) { throw 'Credential output contract failed.' }
    $cipher = Get-Content -LiteralPath $secretPath -Raw -Encoding UTF8
    if ($cipher -match [regex]::Escape($fakeKey)) { throw 'Credential plaintext was written to storage.' }
    $secure = ConvertTo-SecureString $cipher
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $decrypted = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
    if ($decrypted -ne $fakeKey) { throw 'DPAPI credential round-trip failed.' }
    $decrypted = $null
}
finally {
    if (Test-Path -LiteralPath $tempBase) {
        $checked = [IO.Path]::GetFullPath($tempBase)
        if (-not $checked.StartsWith($repoRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Refusing to remove a directory outside the project.' }
        Remove-Item -LiteralPath $checked -Recurse -Force
    }
}

Write-Output 'PACKAGE_OK|skill=cell-ppt|version=0.1.1|secret_scan=clean|install=copy|credential=stdin-dpapi|marketplace=absent'
