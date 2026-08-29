# Cell_ppt

Cell_ppt supports Windows and macOS with one shared core pipeline:

`text manifest → Image 2 text-only cleanup → Xiaomiao path-return SVG → editable text merge → one parse → duplicate-path removal → literal source order from back to front → native editable PPTX`

- Windows supports PowerPoint 2016, 2019, 2021, LTSC 2021, LTSC 2024, and Microsoft 365 desktop through the common `PowerPoint.Application` COM interface.
- macOS supports desktop PowerPoint 2019, 2021, 2024, and Microsoft 365 versions that open standard `.pptx` files. It writes the same geometry cache as native editable DrawingML custom geometry into a saved PPTX; file-backed output is not presented as fake live animation.
- WPS Presentation remains experimental.

## Fixed defaults

- Python 3.11–3.14.
- `python-pptx==1.0.2`, `fonttools==4.61.1`, `shapely==2.1.2`.
- Geometry cache schema 3; text manifest schema 1.0.
- Ordinary batches contain 20–50 paths; slide margin is 18 pt.
- Output names use `shibielujingN`.
- Windows credentials use DPAPI; macOS credentials use Keychain service `cell-ppt-xiaomiao`.

## Codex-managed installation

The user may provide the API key directly in chat. Codex must never repeat or display it. Codex passes it to setup through standard input; setup installs dependencies, copies the Skill, detects the operating system and available presentation host, writes `runtime-profile.json`, stores the credential with DPAPI or Keychain, runs a zero-credit authentication check, and selects the backend automatically. The user is not asked to choose Python, a PowerPoint version, a ProgID, or a backend.
- Existing slide objects are preserved.

## Windows install

```powershell
git clone https://github.com/yrui-cmd/cell-ppt.git
Set-Location .\cell-ppt
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

## macOS install

```bash
git clone https://github.com/yrui-cmd/cell-ppt.git
cd cell-ppt
bash ./setup.sh
```

Restart Codex after installation. For an existing macOS deck, save it first and provide its PPTX path.

## Cross-platform test

```bash
python3 ./tests/test_cross_platform.py
```
