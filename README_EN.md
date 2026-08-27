# Cell_ppt

Cell_ppt `v0.1.1` is a Windows Codex skill and plugin that draws reconstructed scientific figures as editable native Microsoft PowerPoint paths and live text. It draws retained paths from back to front while preserving objects already present on the active slide.

## Stable contract

- Install from immutable Git tag `v0.1.1` or the matching release ZIP and SHA256 file.
- Use exact Python dependencies and verify the frozen runtime manifest.
- Support Microsoft PowerPoint 16.x on Windows as the stable backend; WPS is experimental.
- Parse the SVG once, cull fully hidden and duplicate drawing paths, retain partially visible paths, and draw each retained object exactly once.
- Never preload, hide/reveal, duplicate-cover, replace, or clear completed artwork.
- Keep API credentials out of the repository and store only Windows DPAPI ciphertext.

## Install

```powershell
git clone --branch v0.1.1 --depth 1 https://github.com/yrui-cmd/cell-ppt.git
Set-Location .\cell-ppt
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

After Codex configures and verifies the API key, restart Codex and start a new task:

```text
Use $cell-ppt to reconstruct my uploaded content in the current PowerPoint slide while preserving existing objects.
```

The repository freezes the local workflow and drawing behavior. Built-in Image 2 and the remote vector service are nondeterministic, so newly generated geometry may vary slightly across runs.
