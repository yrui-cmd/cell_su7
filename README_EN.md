# cell_su7

Record original lettering and positions, then use any available image-editing model to remove only the text. No specific model is required. Compare the result against the original to verify unchanged graphics, layout, colors and canvas. Send the cleaned image to path recognition and restore the recorded text as live editable objects before drawing in PowerPoint or Adobe Illustrator. Codex performs the model cleanup and visual comparison; the scripts consume the prepared image and text manifest.

This standalone repository contains the complete `cell_su7` skill with both drawing backends. Windows: run `setup.ps1`. macOS: run `bash setup.sh` for the editable PPTX backend. Illustrator has Windows COM and macOS AppleScript routes; the Mac bridge is implemented but desktop-unverified.

Use `scripts/run_cell_su7.ps1 -InputImage cleaned.png -TextManifest text.json -OutputRoot output -Application ppt` or `-Application ai`. On macOS use `scripts/run_from_image.py --input-image cleaned.png --text-manifest text.json --output-root output`.

PowerPoint retains exact-path deduplication, literal paint order, native editable objects, existing-artwork protection and OOXML output. Illustrator retains its cache, persistent connection, batching, resumable playback, periodic AI saving and final PNG export. The original secure credentials and credit gates remain in use.

PPT now defaults to fast native OOXML on both OSes, preserving compound holes. Illustrator refreshes per batch and never falls back to filled contour splitting. See the platform matrix in `references/backends.md` for validation limits.
