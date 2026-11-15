# PowerPoint post-processing

Default on Windows and macOS: `run_cell_ppt_ooxml.py` writes native custom-geometry shapes and editable text boxes in one atomic PPTX save. Reopen the file for verification. This is fast file generation, not live drawing. Existing decks must be supplied as saved input files and written to a new output copy.

Preserve each SVG atom in source back-to-front order. Each paint of a compound atom uses one DrawingML path containing all contours and original winding; never emit one solid shape per contour. The inner contours are holes. Current PPT export accepts nonzero winding and rejects even-odd fills needing preprocessing. Do not conceal unsupported geometry in a raster image.

Only collapse adjacent identical opaque whole atoms, keeping the first. Preserve non-adjacent repetitions and transparency. Non-rendering display/visibility and zero-opacity paint are excluded by the parser. Regenerate old split-contour caches from SVG before using this backend.

Legacy Windows COM (`run_cell_ppt.ps1`) is opt-in for live demonstration of simple single-contour artwork. It rejects compound caches before touching PowerPoint because the old per-subpath API route destroys holes. It is slower for many paths. Never select it automatically for a complex scientific figure merely because PowerPoint is installed.

Verify: no raster media, all expected native text, preserved contour counts, correct source stacking, saved PPTX reopens, and PowerPoint's rendered slide has no accidental opaque covers. Inspect label positions against the original. Existing user artwork must remain intact.

## Native reconstruction playback on Windows

After preparing the complete editable deck, run `scripts/run_ppt_path_playback.ps1 -InputPptx <prepared.pptx> -OutputPptx <new-unique-name.pptx>`. The default `Drag` mode uses 12 contiguous, nearly equal slices of the original path/object sequence, each advanced by its own pointer. Do not substitute spatial grid regions or send every pointer through the same sequence. Frames expand with width/height cues before revealing their native contents; lettering appears character by character. Each pointer and its cues disappear immediately when that slice finishes. Cursor visuals share one temporary overlay, reveals are batched per frame, and glyph operations are cached before playing.

The default startup opens the prepared copy, maximizes both the PowerPoint application and document, enables the editor's full-screen ribbon state, fits the slide, and requests foreground activation once. `HideRibbon` is a toggle: query `GetPressedMso` before executing it so replay does not turn full screen off. Fit after the ribbon and window layout change, then freeze the scale during drawing. Keep `ppViewSlide` editor view for live native mutations. F5 slide-show playback is not the verified reconstruction route. `-Windowed` skips the full-screen request; `-Mode Visibility` selects the previous simple visibility-only route.

If `ELEMENT_PLAYBACK_WAITING_FOR_FOREGROUND` appears, use the computer-use skill to locate and activate the exact preview window. Read `<output-directory>/window-ready.json` for the copy path, run ID and HWND; select the corresponding window from the desktop inventory. Do not activate an unrelated user deck. A later user window switch pauses playback until this preview returns to the foreground.

For a setup or recording that must be checked before the first frame, add `-WaitForStart`. Once `ELEMENT_PLAYBACK_WAITING_FOR_START` appears, inspect and foreground the full-screen blank canvas, then create the exact `start_file` named in `window-ready.json`. Its name includes the run ID, so an old start signal cannot release a new run. This optional gate times out after 15 minutes; `playback.cancel` in the output directory stops the run. After release, the player refits the slide once before its first frame. Use a fresh output directory when using cancellation or the legacy recording gate.

For "replay" or "demonstrate again", rerun from the complete prepared native deck into another new copy with a unique basename. Reusing the completed output as a live blank canvas or opening multiple copies with the same title can hide the wrong document or make window selection ambiguous. Keep all existing user artwork and source files intact. Wait for `PATH_PLAYBACK_OK`, verify the final native objects/text and absence of preview helpers, and report the measured time. Example timings from one diagram do not establish a fixed playback duration. This helper has no macOS desktop implementation.
