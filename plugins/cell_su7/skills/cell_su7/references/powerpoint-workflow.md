# PowerPoint post-processing

Default on Windows and macOS: `run_cell_ppt_ooxml.py` writes native custom-geometry shapes and editable text boxes in one atomic PPTX save. Reopen the file for verification. This is fast file generation, not live drawing. Existing decks must be supplied as saved input files and written to a new output copy.

Preserve each SVG atom in source back-to-front order. Each paint of a compound atom uses one DrawingML path containing all contours and original winding; never emit one solid shape per contour. The inner contours are holes. Current PPT export accepts nonzero winding and rejects even-odd fills needing preprocessing. Do not conceal unsupported geometry in a raster image.

Only collapse adjacent identical opaque whole atoms, keeping the first. Preserve non-adjacent repetitions and transparency. Non-rendering display/visibility and zero-opacity paint are excluded by the parser. Regenerate old split-contour caches from SVG before using this backend.

Legacy Windows COM (`run_cell_ppt.ps1`) is opt-in for live demonstration of simple single-contour artwork. It rejects compound caches before touching PowerPoint because the old per-subpath API route destroys holes. It is slower for many paths. Never select it automatically for a complex scientific figure merely because PowerPoint is installed.

Verify: no raster media, all expected native text, preserved contour counts, correct source stacking, saved PPTX reopens, and PowerPoint's rendered slide has no accidental opaque covers. Inspect label positions against the original. Existing user artwork must remain intact.

## Native reconstruction playback on Windows

After preparing the editable deck, run `scripts/run_ppt_path_playback.ps1 -InputPptx <prepared.pptx> -OutputPptx <new-unique-name.pptx>`. Choose a mode per replay.

| 展示方式 | 参数 | 画面 |
| --- | --- | --- |
| 快速描摹（默认） | `-Mode Drag` | Expanding drag boxes reveal the finished graphics. |
| 细节描摹 | `-Mode Trace` | The arrow starts on the native contour and the partial stroke extends to its tip. The finished graphic replaces the temporary outline. |

In 细节描摹, each pointer is capped at 3 cm/s by default. The player derives the display scale from PowerPoint zoom and Windows monitor dimensions. When physical dimensions are unavailable, it uses the nominal display scale and records that calibration in the playback metrics. Pass `-MaxCursorCmPerSecond 2` for a lower ceiling. Pointers hide during travel between separate contours, and already drawn segments remain visible.

Both modes split the source path/object sequence into 12 contiguous slices. Each pointer progresses independently in source order and disappears when its slice finishes. Text appears character by character. Separate contours keep their own starts and strokes in 细节描摹. Objects without a supported contour are revealed in source order. Cursor visuals share a temporary overlay, native reveals are batched, and glyph operations are cached.

The default startup opens the prepared copy, maximizes both the PowerPoint application and document, enables the editor's full-screen ribbon state, fits the slide, and requests foreground activation once. `HideRibbon` is a toggle: query `GetPressedMso` before executing it so replay does not turn full screen off. Fit after the ribbon and window layout change, then freeze the scale during drawing. Keep `ppViewSlide` editor view for live native mutations. F5 slide-show playback is not the verified reconstruction route. `-Windowed` skips the full-screen request; `-Mode Visibility` selects the previous simple visibility-only route.

If `ELEMENT_PLAYBACK_WAITING_FOR_FOREGROUND` appears, use the computer-use skill to locate and activate the exact preview window. Read `<output-directory>/window-ready.json` for the copy path, run ID and HWND; select the corresponding window from the desktop inventory. Do not activate an unrelated user deck. A later user window switch pauses playback. When this preview returns to the foreground, the full-screen mode restores the fitted slide layout before playback resumes.

For a setup or recording that must be checked before the first frame, add `-WaitForStart`. Once `ELEMENT_PLAYBACK_WAITING_FOR_START` appears, inspect and foreground the full-screen blank canvas, then create the exact `start_file` named in `window-ready.json`. Its name includes the run ID, so an old start signal cannot release a new run. This optional gate times out after 15 minutes; `playback.cancel` in the output directory stops the run. After release, the player refits the slide once before its first frame. Use a fresh output directory when using cancellation or the legacy recording gate.

For "replay" or "demonstrate again", rerun from the complete prepared native deck into another new copy with a unique basename. Reusing the completed output as a live blank canvas or opening multiple copies with the same title can hide the wrong document or make window selection ambiguous. Keep all existing user artwork and source files intact. Wait for `PATH_PLAYBACK_OK`, verify the final native objects/text and absence of preview helpers, and report the measured time. Example timings from one diagram do not establish a fixed playback duration. This helper has no macOS desktop implementation.
