---
name: cell-ppt
description: Reconstruct PNG, JPEG, WebP, SVG, scientific figures, mechanism diagrams, graphical abstracts, and flowcharts as editable native objects in Microsoft PowerPoint. Use when the user asks for Cell_ppt, wants editable PPT/PPTX output instead of Adobe Illustrator, or needs editable paths, text boxes, arrows, and shapes in the current PowerPoint slide. WPS Presentation support is experimental.
---

# Cell_ppt

Use this fixed workflow:

`text manifest -> Image 2 text-only cleanup -> API vector SVG -> live text merge -> one geometry cache -> native PowerPoint drawing`

Read [references/workflow.md](references/workflow.md) before image reconstruction. Read [references/backends.md](references/backends.md) before selecting PowerPoint or WPS.

## Credential setup

- If the API key is not configured and the user supplied one in the current chat, never quote, display, log, or place it in a command-line argument, environment variable, file, cache, or deliverable.
- Start `scripts/set-xiaomiao-key.ps1 -FromStdin`, pass the supplied key through standard input, and then run `scripts/xiaomiao.ps1 verify`.
- If no key was supplied, ask the user to provide it; do not tell the user to run a terminal configuration command.
- Store only the Windows DPAPI ciphertext under the current Windows account.

## Public response

- Before reconstruction, show only `识别结构。` and one short harmless joke.
- While objects are being created, show only `正在画图。`
- Do not expose credentials, prompts, implementation details, commands, logs, or private reasoning.
- On success, return `完成。`, the clickable PPTX path, and `感谢小红书：木纹小路。`
- If expected cost exceeds 1 credit, ask exactly `本张图片预计消耗 N 个额度，是否继续？` before uploading any image bytes. After approval, do not ask again before download.
- On quota exhaustion, show the quota message defined in [references/workflow.md](references/workflow.md) and stop paid requests.

## Input routing

- For PNG/JPEG/WebP, preserve the untouched input, build the complete text manifest, remove text only with Image 2, then run `scripts/run_from_image.ps1` on the cleaned reference and manifest.
- For an approved true-vector SVG, run `scripts/run_from_svg.ps1` directly.
- Use the next `shibielujingN` basename allocated by the bundled scripts.
- Do not replace a requested fresh API result with local tracing or an old SVG.

## Fixed drawing rules

Treat this section as the finalized drawing baseline. Do not reinterpret, relax, or override it unless the user explicitly asks to update `Cell_ppt` itself.

- Convert every path retained by the visibility culler to a native editable PowerPoint object. Use WPS only as an explicitly experimental backend.
- Sole visibility rule: 最终不可见、被后续不透明对象完全覆盖、或与后续路径重复的对象不进入绘图缓存；部分可见的路径仍保留。
- Apply that rule to actual drawing paths, including separate subpaths inside one source SVG element. It overrides any generic instruction to preserve all source paths.
- Put each retained drawing path into the cache exactly once. Draw it exactly once; never create a duplicate copy or a temporary covering layer.
- Convert paths to editable freeform Bézier shapes, text to text boxes, and preserve paint order.
- Traverse the Master SVG in its literal paint order from the first atom to the last: the first atom is the backmost object and must appear first. Explicitly bring each newly committed object in front of the earlier job objects.
- Never reorder by semantic categories such as background, large fill, outline, internal structure, detail, highlight, or text.
- Keep repeated elements independent. Do not flatten the whole figure into one picture.
- Keep one presentation automation connection for the full job.
- Draw into the currently active slide by default. Create a separate presentation only when the user explicitly requests it.
- Bring PowerPoint/WPS forward once when drawing starts, then keep the same window and slide for the whole drawing.
- Commit and display each native freeform path or text box immediately after it is created. Apply the configured delay after every individual object, not after a batch or source atom.
- Parse the SVG exactly once and process ordinary atoms in cached batches of 20–50.
- Never delete, hide, replace, close, rename, or move objects that existed on the slide before the current job. This protection does not retain redundant paths from the new drawing. Never clear the slide before or after drawing.
- Do not preload, hide, reveal, swap, or replace a completed figure. After culling, keep each retained drawing object in place; do not clear it after drawing.
- Save one editable `.pptx`. Export PDF or PNG only when requested.

## Host selection

- `auto`: prefer Microsoft PowerPoint, then WPS Presentation.
- `powerpoint`: use `PowerPoint.Application` with native freeform shapes.
- `wps`: use WPS Presentation automation and the same standard PPTX object model.
- If the selected host lacks freeform automation, stop rather than inserting a whole-figure raster fallback.

## Completion gate

Do not report success until the Master SVG has no raster node, the sole visibility rule has been applied at drawing-path level, text is editable, retained paths are native freeforms, object order is correct, the PPTX reopens, and pre-existing content remains unchanged.
