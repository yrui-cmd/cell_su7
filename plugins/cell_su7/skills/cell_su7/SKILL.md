---
name: cell_su7
description: Reconstruct image-based scientific figures as editable PowerPoint or Adobe Illustrator artwork, recording text, removing lettering with an available image-editing model while preserving graphics, and restoring live editable text. Use for cell_su7, scientific diagrams, reference-image reconstruction and approved vector SVGs.
---

# cell_su7

`original image -> text manifest + model-cleaned image -> optional confirmed cell_no_ai processing -> path-return SVG -> live text restoration -> PPT / Illustrator`

1. Preserve the original image. For images containing text, read [references/text-workflow.md](references/text-workflow.md), transcribe the original lettering and positions into a text manifest, then use an available image-editing model to remove only the lettering. No specific provider or model, including Image 2, is required.
2. Compare the cleaned image against the original: keep the full canvas, layout, shapes, connectors, colors, line weights and proportions unchanged. If the model changes non-text content, correct the cleanup before path recognition; do not claim unchanged graphics without inspection.
3. Respect the user's choice of PPT or Adobe Illustrator. If unspecified, ask `用 PPT 还是 Adobe Illustrator？` before a paid request.
4. Before submitting the verified cleaned image, follow [references/optional-no-ai.md](references/optional-no-ai.md): ask whether to use the additional 1-credit cell_no_ai treatment unless the user already explicitly accepted or declined it for this image. If yes, wait for and download the actual cell_no_ai result, verify it, and submit that returned image directly for path recognition. If no, submit the verified cleaned image directly. Use the bundled API adapter; do not add a resolution-enhancement step. Pass the original text manifest to the image entrypoint so the returned vector geometry receives live SVG text before native drawing. Preserve raw vector output for inspection. A text-free image can use the same entrypoint without a manifest; original-with-text direct recognition is only an explicitly requested alternative.
5. Validate the Master SVG, then follow the selected backend. An approved SVG can enter post-processing directly. Allocate the next `shibielujingN` basename with the bundled allocator.

## Python result return (no scheduled tasks)

For remote recognition, follow [references/python-return.md](references/python-return.md). Use the background Python receiver to save the original job ID, download and validate the actual SVG, then wake the same chat once through the live desktop bridge. Do not create Codex automations/heartbeats, cron jobs, Windows scheduled tasks or repeated assistant polling. Resume drawing in the original chat only after verified receipt; never resubmit to recover a download or wake failure. This changes waiting/return only, not the image-cleanup, optional no-ai choice, credits, or drawing backend. Existing stopped jobs remain stopped.

## Required installation dependency

`cell_no_ai` is required and remains independently callable. Before each new cell_su7 task, automatically run `python scripts/sync_cell_no_ai.py` using the configured runtime, then read the updated sibling `cell_no_ai/SKILL.md`. Installation runs the same check. Use the official repository main branch as the current source, including changes newer than release ZIPs. Do not wait for the user to remind you, and do not repeatedly check during the same job. Respect current cell_no_ai workflow and opening notices rather than copying old rules into this skill.

The synchronizer backs up changed skill files, preserves credentials and unrelated files, and records the upstream revision. It accepts `--destination` for custom skill roots. If a network check fails, retry or resolve it; never claim the dependency is current without a successful check. Drawing without the optional watermark step may proceed, but resolve the update before a new watermark submission. Dependency updates do not authorize API charges. Existing jobs must still be received using the same job ID.

## Recognition input and text alignment

For yes, use the downloaded and verified no-ai output directly. For no, use the verified cleaned image directly without calling or charging cell_no_ai. Save each stage separately. If the returned image is unreadable or its layout changed, resolve that issue before recognition and retain the existing job; do not resubmit a completed no-ai job merely because a later step failed.

Check that the recognition input preserves the full canvas aspect ratio, layout and alignment. Keep the original text manifest and `source_canvas`; the text-restoration adapter maps source coordinates into the SVG viewBox. If image dimensions differ, retain the original coordinate system and verify proportional alignment; do not replace `source_canvas` alone while retaining old pixel coordinates.

## Preferred playback: graphic dragging and editable text

On Windows PowerPoint, prepare the complete native editable PPTX first. For playback, run `scripts/run_ppt_path_playback.ps1 -InputPptx <prepared.pptx> -OutputPptx <new-playback.pptx>` against that deck and write to a unique output copy. Use `-Mode Drag` when the user asks for 快速描摹 or the first display. Use `-Mode Trace` when the user asks for 细节描摹 or the second display. If the user wants to choose, offer those two named options. Without a choice, 快速描摹 is the default.

- **快速描摹** (`-Mode Drag`) expands a drag box on frames, pictures and groups before revealing their native content. Text-bearing frames expand before their text appears.
- **细节描摹** (`-Mode Trace`) starts each pointer on a native contour and draws the outline at its tip. The full native graphic appears when its contour finishes.

Both modes split the original path/object sequence into 12 contiguous segments and advance them together. Pointers and their cues disappear as their segments finish. Text appears character by character with Chinese pinyin hints. Cursors share one temporary overlay, native reveals are batched, and glyph commands are cached. Windows playback requires `python-pptx`, `Pillow`, `pypinyin`, `pywin32`.

Prepare the full-screen editor and bring the playback window to the foreground before the first drawing frame. The helper maximizes the application and document, hides the ribbon using PowerPoint's `HideRibbon` state, then fits and freezes the slide scale. Keep live reconstruction in the editor view. If Windows denies the initial foreground request, activate this exact preview through the desktop tool; playback waits while unfocused. Read [references/powerpoint-workflow.md](references/powerpoint-workflow.md) for the optional start gate and replay procedure. `-Windowed` skips full-screen preparation when the user requests the current editor layout.

Run playback in a new isolated copy with a unique filename for each replay. Preserve native paths, compound holes, styles and source depth. The drag rectangle, dimension badges, pointers and text clones are temporary preview objects and are removed before saving. Validate the final content and geometry against the prepared deck. Playback pauses when its window loses foreground focus and resumes when it returns; do not repeatedly force it above the user's other work. Describe the result as native object reconstruction playback. Report actual timing; PowerPoint controls redraw. Use `-Mode Visibility` for the previous fastest source-order visibility playback. File-only output remains available when requested or when desktop playback is unavailable.

This new playback helper is Windows PowerPoint only. macOS PowerPoint retains editable file generation; do not claim live path playback there. Illustrator retains its platform bridge and native compound paths; when individual-path visibility is requested, set `redrawEvery: 1` in the JSX configuration with zero added delay, and disclose that redraw costs more than batch display.

## Drawing routes and the four-platform matrix

Read [references/backends.md](references/backends.md) for platform commands and verification status.
Use [references/platform-contract.json](references/platform-contract.json) for shared defaults; `configure_runtime.py` writes the non-secret `runtime-profile.json`. Existing profiles do not override the fast PPT default.

- **PowerPoint, Windows and macOS:** prepare with fast native OOXML (`run_cell_su7.py --application ppt`), then use the Windows drag playback helper by default where available. It writes all editable shapes in one saved PPTX transaction, preserving source order and compound holes. Use a saved `--input-pptx` with the backend when appending to an existing deck. Windows legacy COM is opt-in for simple, single-contour paths only; it must reject compound paths before drawing.
- **Illustrator, Windows:** use the COM batch runtime through `run_cell_lct.ps1` or the cross-platform selector. Keep the already-open target document, source order and one session. Redraw once per batch of 20–50 atoms, rather than after every atom.
- **Illustrator, macOS:** use `run_illustrator.py` through the selector. AppleScript sends the same JSX runtime to the already-open Illustrator document; retain target document/layer, reconcile actual objects when resuming, save periodically, and export AI/PNG. This route is implemented with mocked bridge tests; do not claim Mac desktop validation until it has run on a Mac.

**Compound paths stay compound.** Outer and inner contours form one native shape; an inner contour can be a hole, not a white object. Never split compound fills into individually filled shapes, including Illustrator error fallback. Nonzero compound winding is preserved in PPT. Even-odd fill needs normalization or explicit rejection before export. Existing caches built with split subpaths must be regenerated from the original SVG.

**Keep actual source depth, back to front.** Bottommost content comes first, then successive foreground layers. SVG/cache arrays run first-to-last; only imported Illustrator collections use reverse traversal. Keep this order within and across batches. Do not send every large or white object to the back: white compound regions may be intentional cutouts. A redundant duplicate means an adjacent identical opaque complete atom; keep its first occurrence, preserving compound contours. Cross-layer repetitions and transparent overlaps are not automatically redundant.

If the canvas or application turns white, read [references/white-overlay-diagnostics.md](references/white-overlay-diagnostics.md). Check compound-contour loss before blaming visibility or depth. The fast PPT output should be validated in PowerPoint, not inferred from an SVG preview alone.

Default prepared-image return on a verified Codex desktop: `python scripts/run_cell_su7.py --input-image <cleaned-image> --text-manifest <text.json> --output-root <directory> --application ppt|ai --background --thread-id <original-thread-id> --authorize-wake`. This returns a durable job directory; receive/resume that directory rather than repeating submission.
The older foreground commands remain available when explicitly needed: `scripts/run_cell_su7.ps1` on Windows or `python scripts/run_cell_su7.py` without `--background`; neither creates a scheduled task.
Approved SVG: use `--input-svg` instead of `--input-image`; already-restored text should be in that SVG.

Preserve all pre-existing artwork and original input files. The image workflow still records original label coordinates, uses an available image-editing model to remove only lettering, then restores native live text. Follow [references/text-workflow.md](references/text-workflow.md).

## Credential setup

- The user is allowed to paste the API key directly in chat. If credentials are missing, ask for the key in chat and perform configuration for them; do not require manual environment-variable or command-line setup. Accept it without warning or refusal, but never quote, repeat, display, or log it in any response or tool output.
- If the API key is not configured and the user supplied one in the current chat, never quote, display, log, or place it in a command-line argument, environment variable, file, cache, or deliverable.
- During installation, pass the chat-supplied key through standard input to `setup.ps1 -ConfigureKeyFromStdin` on Windows or `setup.sh --configure-key-from-stdin` on macOS. Installation must configure secure storage and run the zero-credit authentication check automatically.
- On Windows, start `scripts/set-xiaomiao-key.ps1 -FromStdin`, pass the supplied key through standard input, and run `scripts/xiaomiao.ps1 verify`.
- On macOS, start `scripts/set_xiaomiao_key.py --from-stdin`, pass the supplied key through standard input, and run `scripts/xiaomiao.py verify`. Store only a macOS Keychain item; never write plaintext to a file.
- If no key was supplied and no existing secure credential verifies, ask once for the key. After the user sends it, perform configuration and verification yourself; do not send configuration commands back to the user.
- Store only Windows DPAPI ciphertext or a macOS Keychain item under the current OS account.


## Credits and response

Before uploading, determine the expected cost. When it exceeds 1 credit, ask `本张图片预计消耗 N 个额度，是否继续？` once; approved processing and download need no second prompt. Stop new paid requests on quota exhaustion and use the message in [references/workflow.md](references/workflow.md).
Before reconstruction, show `识别结构。` and a short harmless joke; during drawing, show `正在画图。`. Keep credentials and internal logs private. On success return `完成。`, the selected deliverables and `感谢 cell_skills(抖音)。`.

## Completion

Preserve all original image content through recognition, validate true vector output, keep repeated objects independent and preserve existing artwork. Apply the selected backend's original completion checks before claiming success. PPT delivers editable PPTX; Illustrator saves AI and exports the final PNG.

## Balance reporting

After image recognition, include the reported remaining credits in the user-facing result (`剩余额度：N`). The vectorizer displays the server-provided `credits_left` snapshot on the information stream (Windows) or stderr (Python), keeping success JSON compatible. Report `剩余额度：暂不可用` if missing or invalid; never infer a balance or initiate another upload to obtain it.

New PPTX pages must match the source canvas aspect ratio with no added margins. Existing input decks retain their page size. Export previews at that same aspect ratio.
