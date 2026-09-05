# Sudden white canvas or window

First establish the affected application and whether the white region covers only the document canvas or also menus and toolbars. Inspect a current screenshot or visible UI when available. Do not infer the cause from “white screen” alone.

- Entire application window, including chrome: investigate host responsiveness, active dialogs/windows and redraw timing. Document shapes alone do not explain menus being obscured. Let the outstanding drawing call finish or report its failure before issuing more calls; retain the same session and checkpoint. Do not keep queuing redraws, reactivations or duplicate drawing attempts. Do not close the user's unsaved document or restart the host automatically.
- Canvas only: inspect the last-created job objects, their bounds, fill, opacity and stacking order against the source SVG. A large opaque white source path, an incorrectly mapped path, or a temporary default fill are candidates to verify, not established causes. Match any suspect object to its source id before modifying it. Preserve intentional white fills, masks represented by source geometry and pre-existing artwork.
- Brief white flash during creation: determine whether it appears between native geometry creation and appearance assignment or during a long host call. Record the object/batch and check the completed result before treating the flash as persistent lost artwork.

The parser already skips non-rendering display/visibility and transparent paint. `cull_hidden_geometry.py` removes exact duplicate paths; it does not perform occlusion clipping or remove every fully covered path. Do not delete all hidden, white, background or large objects as a generic remedy. No blanket layer unlock/show/delete operation is part of this workflow.

The Illustrator runtime creates directly in the job group when possible; its “stagingLayer” parameter is the existing target layer, not a separate fullscreen overlay. PowerPoint foreground activation occurs once; its per-object step currently sleeps rather than explicitly pumping the host UI. These facts help locate a reproduction but do not establish which operation caused a particular white screen.

After a targeted fix, verify both host responsiveness and the complete artwork against the original, including text placement and pre-existing objects. Distinguish code inspection, mocked tests and actual desktop reproduction in the result.
