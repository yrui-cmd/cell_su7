# PowerPoint post-processing

Default on Windows and macOS: `run_cell_ppt_ooxml.py` writes native custom-geometry shapes and editable text boxes in one atomic PPTX save. Reopen the file for verification. This is fast file generation, not live drawing. Existing decks must be supplied as saved input files and written to a new output copy.

Preserve each SVG atom in source back-to-front order. Each paint of a compound atom uses one DrawingML path containing all contours and original winding; never emit one solid shape per contour. The inner contours are holes. Current PPT export accepts nonzero winding and rejects even-odd fills needing preprocessing. Do not conceal unsupported geometry in a raster image.

Only collapse adjacent identical opaque whole atoms, keeping the first. Preserve non-adjacent repetitions and transparency. Non-rendering display/visibility and zero-opacity paint are excluded by the parser. Regenerate old split-contour caches from SVG before using this backend.

Legacy Windows COM (`run_cell_ppt.ps1`) is opt-in for live demonstration of simple single-contour artwork. It rejects compound caches before touching PowerPoint because the old per-subpath API route destroys holes. It is slower for many paths. Never select it automatically for a complex scientific figure merely because PowerPoint is installed.

Verify: no raster media, all expected native text, preserved contour counts, correct source stacking, saved PPTX reopens, and PowerPoint's rendered slide has no accidental opaque covers. Inspect label positions against the original. Existing user artwork must remain intact.
