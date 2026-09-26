# cell_su7

Rebuild one scientific image as editable paths and live text in **PowerPoint or Adobe Illustrator**.

`cell_su7` records every label and its source position, asks an available image-editing model to remove only the text, verifies the remaining graphics against the original, and enhances the checked working image before path recognition. It then draws from background to foreground and restores the recorded labels as editable objects. The original image remains unchanged.

## What you get

- native editable PPTX, or editable AI plus a final PNG;
- a text manifest with source coordinates;
- preserved canvas ratio and source layer order;
- exact-path deduplication without flattening valid occlusion or compound holes;
- the balance snapshot returned by the recognition service.

This standalone repository contains both drawing backends. On Windows, run `setup.ps1`; on macOS, run `bash setup.sh`. Illustrator uses Windows COM or a macOS AppleScript bridge. The Mac bridge is implemented but has not yet been verified on a physical Mac desktop.

Use `scripts/run_cell_su7.ps1 -InputImage cleaned.png -TextManifest text.json -OutputRoot output -Application ppt` or `-Application ai`. On macOS use `scripts/run_from_image.py --input-image cleaned.png --text-manifest text.json --output-root output`.

PowerPoint retains exact-path deduplication, literal paint order, native editable objects, existing-artwork protection and OOXML output. Illustrator retains its cache, persistent connection, batching, resumable playback, periodic AI saving and final PNG export. The original secure credentials and credit gates remain in use.

PPT now defaults to fast native OOXML on both OSes, preserving compound holes. Illustrator refreshes per batch and never falls back to filled contour splitting. See the platform matrix in `references/backends.md` for validation limits.

Installation includes the required **cell_no_ai** dependency as a separate skill. Existing standalone installations are synchronized with the official main branch; changed files are backed up and credentials are preserved. For manual installation, copy both skill directories. Installing this dependency does not authorize paid processing: its live balance check and one-credit authorization remain required.

Path recognition always requires the separately installed **cell-high-solution** skill in `faithful` mode. If the user approves cell_no_ai, enhance its downloaded result; if the user declines, enhance the verified cleaned image without calling or charging cell_no_ai. Validate unchanged aspect ratio and alignment, then use only the enhanced PNG for path recognition. Keep the original text manifest and `source_canvas` coordinate system so restored labels remain aligned.
