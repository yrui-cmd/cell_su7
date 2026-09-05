# Four platform combinations

| Platform / application | Runtime | Validation status |
|---|---|---|
| Windows PowerPoint | Native OOXML file generation; optional simple-path COM | Complex 2,614-object sample opened and visually checked in PowerPoint; white compound holes preserved |
| macOS PowerPoint | Same native OOXML file generation; open saved PPTX | Shared file/structure tests; actual Mac PowerPoint not tested here |
| Windows Illustrator | Existing COM + native compound paths, one redraw per batch | Shared cache and JSX syntax tested; updated desktop drawing not yet revalidated |
| macOS Illustrator | `osascript` Apple Events + same JSX compound/batch runtime | Bridge routing/resume tests mocked; actual Mac Illustrator not tested here |

## Commands

`python scripts/run_cell_su7.py --input-image cleaned.png --text-manifest text.json --output-root output --application ppt`

Change `ppt` to `ai` for Illustrator. For approved vector input use `--input-svg master.svg` without `--text-manifest`.

Illustrator must already be running with the target document open. Windows uses `Illustrator.Application.30`; macOS resolves the installed app by bundle id `com.adobe.illustrator`. macOS may require Automation permission for the launching host to control Illustrator. A denied or unavailable bridge is an explicit failure, not permission to launch another app or silently fall back to raster artwork.

PowerPoint file generation does not need PowerPoint running. To append to a saved deck, the lower-level PPT backend accepts `--input-pptx` and `--slide-index`; save to a new output path. The Windows legacy COM path remains available explicitly for simple non-compound illustrations. WPS is experimental and is not the default.

## Geometry and speed

Keep compound contours together, source order unchanged, and native editable text. PPT is written once; Illustrator is redrawn once per 20–50-object batch. Do not use a white-cover workaround or split a failed compound into filled child shapes. Arbitrary masks, gradients, non-canvas clips and even-odd PPT fills require preprocessing or explicit rejection.

AppleScript uses Illustrator's `do javascript` command on a JSX file. Reference: [Adobe-hosted scripting example](https://community.adobe.com/questions-652/how-to-pass-arguments-from-applescript-to-javascript-jsx-illustrator-extendscript-809731). Runtime availability must still be checked on the destination Mac.
