---
name: cell_su7
description: Reconstruct image-based scientific figures as editable PowerPoint or Adobe Illustrator artwork, recording text, removing lettering with an available image-editing model while preserving graphics, and restoring live editable text. Use for cell_su7, scientific diagrams, reference-image reconstruction and approved vector SVGs.
---

# cell_su7

`original image -> text manifest + model-cleaned image -> path-return SVG -> live text restoration -> PPT / Illustrator`

1. Preserve the original image. For images containing text, read [references/text-workflow.md](references/text-workflow.md), transcribe the original lettering and positions into a text manifest, then use an available image-editing model to remove only the lettering. No specific provider or model, including Image 2, is required.
2. Compare the cleaned image against the original: keep the full canvas, layout, shapes, connectors, colors, line weights and proportions unchanged. If the model changes non-text content, correct the cleanup before path recognition; do not claim unchanged graphics without inspection.
3. Respect the user's choice of PPT or Adobe Illustrator. If unspecified, ask `用 PPT 还是 Adobe Illustrator？` before a paid request.
4. Submit the verified cleaned image with the bundled API adapter. Pass its original text manifest to the image entrypoint so the returned vector geometry receives live SVG text before native drawing. Preserve raw vector output for inspection. A text-free image can use the same entrypoint without a manifest; original-with-text direct recognition is only an explicitly requested alternative.
5. Validate the Master SVG, then follow the selected backend. An approved SVG can enter post-processing directly. Allocate the next `shibielujingN` basename with the bundled allocator.

## Drawing routes

**Draw from back to front: the actual bottommost layer first, then each successively higher layer.** If the source background/baseboard is bottommost, it must appear before the foreground artwork. Determine depth from the source stacking order, never from path size, color, screen coordinates or names. SVG/cache arrays run first-to-last; only already-imported Illustrator collections use the reverse traversal described in the runtime reference. Preserve this order within and across batches throughout playback, not only after completion.

Remove genuinely redundant duplicate paths without delaying the first background. Collapse adjacent identical opaque paths by keeping the first. Do not treat a repeated shape separated by other layers, or translucent repeated paint, as redundant without proving that removing it preserves the composition. Before drawing, verify that the first cache atom and first batch match the source's bottommost rendered content; if the source stacking itself disagrees with the reference, inspect and correct that source before playback rather than blindly moving all white shapes to the back.

If the canvas or application suddenly turns white during drawing, read [references/white-overlay-diagnostics.md](references/white-overlay-diagnostics.md) before changing visibility, deleting shapes or retrying playback. A white application window is not evidence of hidden geometry.

- Windows, prepared image: `scripts/run_cell_su7.ps1 -InputImage <cleaned-image> -TextManifest <text.json> -OutputRoot <directory> -Application ppt|ai`. This dispatches to the matching original backend; normal rendering remains per-path, not a hidden completed-figure reveal.
- PPT: read [references/powerpoint-workflow.md](references/powerpoint-workflow.md), [references/backends.md](references/backends.md) and [references/platform-contract.json](references/platform-contract.json). Windows uses `run_from_image.ps1` / `run_from_svg.ps1`; macOS uses `run_from_image.py` / `run_from_svg.py`. Match the technical PPT backend with `configure_runtime.py` and `runtime-profile.json` automatically after the user chooses PPT. Native OOXML output is editable but does not provide live per-path screen drawing.
- Illustrator: read [references/illustrator-workflow.md](references/illustrator-workflow.md) and [references/illustrator-runtime.md](references/illustrator-runtime.md). Use `run_illustrator_from_image.ps1` for images or `run_cell_lct.ps1` for approved SVGs. The existing live runtime requires Windows and an already-open Illustrator 2026 document. Do not launch, restart, focus, resize or close Illustrator. Do not silently switch an unsupported Illustrator environment to PPT.
- Restore the recorded lettering as native text boxes in PPT and live text in Illustrator. Preserve native `<text>` already present in an approved SVG. Verify content, placement and styles; do not silently replace the recorded text with outlines.

## Credential setup

- The user is allowed to paste the API key directly in chat. Accept it without warning or refusal, but never quote, repeat, display, or log it in any response or tool output.
- If the API key is not configured and the user supplied one in the current chat, never quote, display, log, or place it in a command-line argument, environment variable, file, cache, or deliverable.
- During installation, pass the chat-supplied key through standard input to `setup.ps1 -ConfigureKeyFromStdin` on Windows or `setup.sh --configure-key-from-stdin` on macOS. Installation must configure secure storage and run the zero-credit authentication check automatically.
- On Windows, start `scripts/set-xiaomiao-key.ps1 -FromStdin`, pass the supplied key through standard input, and run `scripts/xiaomiao.ps1 verify`.
- On macOS, start `scripts/set_xiaomiao_key.py --from-stdin`, pass the supplied key through standard input, and run `scripts/xiaomiao.py verify`. Store only a macOS Keychain item; never write plaintext to a file.
- If no key was supplied and no existing secure credential verifies, ask once for the key. After the user sends it, perform configuration and verification yourself; do not send configuration commands back to the user.
- Store only Windows DPAPI ciphertext or a macOS Keychain item under the current OS account.


## Credits and response

Before uploading, determine the expected cost. When it exceeds 1 credit, ask `本张图片预计消耗 N 个额度，是否继续？` once; approved processing and download need no second prompt. Stop new paid requests on quota exhaustion and use the message in [references/workflow.md](references/workflow.md).
Before reconstruction, show `识别结构。` and a short harmless joke; during drawing, show `正在画图。`. Keep credentials and internal logs private. On success return `完成。`, the selected deliverables and `感谢小红书：木纹小路。`.

## Completion

Preserve all original image content through recognition, validate true vector output, keep repeated objects independent and preserve existing artwork. Apply the selected backend's original completion checks before claiming success. PPT delivers editable PPTX; Illustrator saves AI and exports the final PNG.

## Balance reporting

After image recognition, include the reported remaining credits in the user-facing result (`剩余额度：N`). The vectorizer displays the server-provided `credits_left` snapshot on the information stream (Windows) or stderr (Python), keeping success JSON compatible. Report `剩余额度：暂不可用` if missing or invalid; never infer a balance or initiate another upload to obtain it.
