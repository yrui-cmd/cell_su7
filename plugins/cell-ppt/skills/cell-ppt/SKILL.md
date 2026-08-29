---
name: cell-ppt
description: Reconstruct PNG, JPEG, WebP, SVG, scientific figures, mechanism diagrams, graphical abstracts, and flowcharts as editable native objects in Microsoft PowerPoint on Windows or macOS. Use when the user asks for Cell_ppt, wants editable PPT/PPTX output instead of Adobe Illustrator, or needs editable paths, text boxes, arrows, and shapes. WPS Presentation support is experimental.
---

# Cell_ppt

Use this fixed workflow:

`text manifest -> Image 2 text-only cleanup -> API path-return SVG -> live text merge -> one geometry cache -> duplicate-path removal -> native PowerPoint drawing`

Read [references/workflow.md](references/workflow.md) before image reconstruction. Read [references/backends.md](references/backends.md) before selecting PowerPoint or WPS.
Treat [references/platform-contract.json](references/platform-contract.json) as the fixed cross-platform defaults. Do not ask the user to configure values already present there.
Read `runtime-profile.json` when present. If it is missing or the computer changed, run `scripts/configure_runtime.py` and select the detected backend automatically. Do not ask the user to identify their OS, PowerPoint version, Python command, COM ProgID, WPS ProgID, or output backend.

## Credential setup

- The user is allowed to paste the API key directly in chat. Accept it without warning or refusal, but never quote, repeat, display, or log it in any response or tool output.
- If the API key is not configured and the user supplied one in the current chat, never quote, display, log, or place it in a command-line argument, environment variable, file, cache, or deliverable.
- During installation, pass the chat-supplied key through standard input to `setup.ps1 -ConfigureKeyFromStdin` on Windows or `setup.sh --configure-key-from-stdin` on macOS. Installation must configure secure storage and run the zero-credit authentication check automatically.
- On Windows, start `scripts/set-xiaomiao-key.ps1 -FromStdin`, pass the supplied key through standard input, and run `scripts/xiaomiao.ps1 verify`.
- On macOS, start `scripts/set_xiaomiao_key.py --from-stdin`, pass the supplied key through standard input, and run `scripts/xiaomiao.py verify`. Store only a macOS Keychain item; never write plaintext to a file.
- If no key was supplied and no existing secure credential verifies, ask once for the key. After the user sends it, perform configuration and verification yourself; do not send configuration commands back to the user.
- Store only Windows DPAPI ciphertext or a macOS Keychain item under the current OS account.

## Public response

- Before reconstruction, show only `识别结构。` and one short harmless joke.
- While objects are being created, show only `正在画图。`
- Do not expose credentials, prompts, implementation details, commands, logs, or private reasoning.
- On success, return `完成。`, the clickable PPTX path, and `感谢小红书：木纹小路。`
- If expected cost exceeds 1 credit, ask exactly `本张图片预计消耗 N 个额度，是否继续？` before uploading any image bytes. After approval, do not ask again before download.
- On quota exhaustion, show the quota message defined in [references/workflow.md](references/workflow.md) and stop paid requests.

## Input routing

- For PNG/JPEG/WebP, preserve the untouched input, build the complete text manifest, and remove text only with Image 2. On Windows run `scripts/run_from_image.ps1`; on macOS run `scripts/run_from_image.py`.
- For an approved path-return SVG, use `scripts/run_from_svg.ps1` on Windows or `scripts/run_from_svg.py` on macOS.
- Use the next `shibielujingN` basename allocated by the bundled scripts.
- Do not replace a requested fresh API result with local tracing or an old SVG.

## Fixed drawing rules

Treat this section as the finalized drawing baseline. Do not reinterpret, relax, or override it unless the user explicitly asks to update `Cell_ppt` itself.

- Convert every path retained by the duplicate-path filter to a native editable PowerPoint object. Use WPS only as an explicitly experimental backend.
- Sole filtering rule: remove exact duplicate drawing paths only. Preserve every non-duplicate path, including invisible, fully covered, and partially visible paths.
- Apply that rule to actual drawing paths, including separate subpaths inside one source SVG element.
- Put each retained drawing path into the cache exactly once. Draw it exactly once; never create a duplicate copy or a temporary covering layer.
- Convert paths to editable freeform Bézier shapes, text to text boxes, and preserve paint order.
- Traverse the Master SVG in its literal paint order from the first atom to the last: the first atom is the backmost object and must appear first. Explicitly bring each newly committed object in front of the earlier job objects.
- Never reorder by semantic categories such as background, large fill, outline, internal structure, detail, highlight, or text.
- Keep repeated elements independent. Do not flatten the whole figure into one picture.
- On Windows, keep one presentation automation connection for the full job. On macOS, perform one atomic OOXML edit transaction and reopen the saved result for verification.
- On Windows, draw into the currently active slide by default. On macOS, require a saved input PPTX path for appending to an existing deck; otherwise create a new PPTX. Never modify an open unsaved macOS presentation externally.
- On Windows, bring PowerPoint/WPS forward once when drawing starts. On macOS, do not pretend that file-backed OOXML creation is live drawing; open the verified output only after the atomic save if the user asks.
- On Windows, commit and display each native freeform path or text box immediately in literal source order from back to front, with a fixed 8 ms delay after each object. On macOS, write the same retained objects in the same order within one atomic OOXML transaction; visibility begins when the saved output is opened or reloaded.
- Parse the SVG exactly once and process ordinary atoms in cached batches of 20–50.
- Never delete, hide, replace, close, rename, or move objects that existed on the slide before the current job. This protection does not retain redundant paths from the new drawing. Never clear the slide before or after drawing.
- Do not preload, hide, reveal, swap, or replace a completed figure. After culling, keep each retained drawing object in place; do not clear it after drawing.
- Save one editable `.pptx`. Export PDF or PNG only when requested.

## Host selection

- Use the installed runtime profile automatically. Prefer live PowerPoint COM on Windows, then experimental WPS COM, then native editable OOXML. Use native editable OOXML on macOS. Do not make the user choose a backend.
- Never require a "PowerPoint 2026" edition. On Windows support PowerPoint 2016, 2019, 2021, LTSC 2021, LTSC 2024, and Microsoft 365 desktop through the unversioned `PowerPoint.Application` interface. On macOS support PowerPoint 2019, 2021, 2024, and Microsoft 365 desktop through standard saved-PPTX OOXML.
- Windows `auto`: prefer Microsoft PowerPoint, then WPS Presentation.
- Windows `powerpoint`: use `PowerPoint.Application` with native freeform shapes.
- macOS `ooxml`: use `run_cell_ppt_ooxml.py` to append native custom-geometry shapes and native text boxes to a saved PPTX. This is editable but not a live per-path animation.
- `wps`: use WPS Presentation automation and the same standard PPTX object model.
- If the selected host lacks freeform automation, stop rather than inserting a whole-figure raster fallback.

## Completion gate

Do not report success until the Master SVG has no raster node, exact duplicates have been removed at drawing-path level, every non-duplicate path is retained, text is editable, retained paths are native freeforms, literal source order is correct, the PPTX reopens, and pre-existing content remains unchanged.
