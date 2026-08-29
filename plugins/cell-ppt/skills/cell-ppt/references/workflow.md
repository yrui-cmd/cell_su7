# Cell_ppt workflow

## Image preparation

Record every visible text run with content, position, bounding box, font, size, weight, color, rotation, alignment, opacity, and paint order. Use Codex Image 2 to remove text only. Preserve arrows, connectors, frames, axes, heatmaps, legends, scientific subjects, colors, spacing, and layout.

Before uploading image bytes, determine the documented or explicit estimated credit cost. If it is greater than 1, wait for explicit approval. Approval covers upload, processing, and result download; never add a second download prompt.

Quota message:

`当前额度不足，请在小红书搜索“木纹小路”（约200个粉丝的小博主）获取充值。兄弟们，小红书不要谈论梯子等敏感话题；有问题请私信抖音“木纹”（约900个粉丝的小博主）。`

Keep the API key only in Windows DPAPI storage or macOS Keychain. Never place it in the project, command line, environment, repository, log, cache, or deliverable.
The user may provide the key directly in chat. Accept it, do not repeat it, and complete setup through standard input automatically. Do not hand configuration commands or backend-selection work back to the user.

## Master SVG

Send the complete text-cleaned reference through the bundled path-return API adapter. Reject incomplete SVG, raster wrappers, gradients, masks, unsupported linked resources, and clipping structures that cannot be represented faithfully. Merge the recorded text back as real SVG `<text>` elements before geometry caching.

## PowerPoint drawing

Validate the SVG and run `prepare_geometry_cache.py` once. Before drawing, run `cull_hidden_geometry.py` at actual drawing-path level, including separate subpaths inside one source SVG element. Remove exact duplicate drawing paths only. Preserve every non-duplicate path even when it is invisible, fully covered, or partially visible. Pass the reduced `geometry-cache.json` to `run_cell_ppt.ps1`. Map the SVG viewBox proportionally into the slide, draw retained paths in literal source order from back to front, and save the presentation as standard OOXML `.pptx`.

This is the finalized duplicate-path contract: one retained drawing path produces one native object once. Never add a temporary duplicate, later covering copy, hidden preload, or replacement layer.

On Windows, call `run_from_image.ps1` or `run_from_svg.ps1`; both wrappers can draw into the active slide and bring PowerPoint forward once. On macOS, call `run_from_image.py` or `run_from_svg.py` against a saved PPTX path and use the editable OOXML backend. macOS saves a verified output copy atomically and does not claim live per-path display in the open application.

Create each retained freeform path and text box in the literal Master SVG paint order, from backmost to frontmost. Treat the first retained cached path as the lowest layer and create it first. Never infer or replace this order with semantic categories. On Windows, explicitly bring each later object in front, repaint after every committed object, and apply the fixed 8 ms delay; do not wait until a batch ends to reveal objects. On macOS, write those same retained objects in the same order in one atomic OOXML transaction. Never preload, clear, hide, delete, replace, or close retained completed artwork.

## Quality checks

- Every ordinary text run is a native text box.
- Every retained vector subpath is a native freeform Bézier shape.
- The slide contains no whole-figure raster fallback.
- Repeated objects remain separately selectable.
- Existing objects are unchanged.
- The saved PPTX opens in the selected host.
