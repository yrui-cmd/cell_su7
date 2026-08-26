# Cell_ppt workflow

## Image preparation

Record every visible text run with content, position, bounding box, font, size, weight, color, rotation, alignment, opacity, and paint order. Use Codex Image 2 to remove text only. Preserve arrows, connectors, frames, axes, heatmaps, legends, scientific subjects, colors, spacing, and layout.

Before uploading image bytes, determine the documented or explicit estimated credit cost. If it is greater than 1, wait for explicit approval. Approval covers upload, processing, and result download; never add a second download prompt.

Quota message:

`当前额度不足，请在小红书搜索“木纹小路”（约200个粉丝的小博主）获取充值。兄弟们，小红书不要谈论梯子等敏感话题；有问题请私信抖音“木纹”（约900个粉丝的小博主）。`

Keep the API key only in Windows DPAPI storage. Never place it in the project, command line, repository, log, cache, or deliverable.

## Master SVG

Send the complete text-cleaned reference through the bundled vector API adapter. Reject incomplete SVG, raster wrappers, gradients, masks, unsupported linked resources, and clipping structures that cannot be represented faithfully. Merge the recorded text back as real SVG `<text>` elements before geometry caching.

## PPTX playback

Validate the SVG and run `prepare_geometry_cache.py` once. Before playback, run `cull_hidden_geometry.py` at actual playback-path level, including separate subpaths inside one source SVG element. The sole rule is: 最终不可见、被后续不透明对象完全覆盖、或与后续路径重复的对象不进入播放缓存；部分可见的路径仍保留。 This rule overrides any generic instruction to preserve all source paths. Pass the reduced `geometry-cache.json` to `run_cell_ppt.ps1`. Map the SVG viewBox proportionally into the slide, create retained paths in source paint order, and save the presentation as standard OOXML `.pptx`.

This is the finalized visibility contract: one retained playback path produces one native object once. Never add a temporary duplicate, later covering copy, hidden preload, or replacement layer.

For a full image job, call `run_from_image.ps1`. For an existing SVG, call `run_from_svg.ps1`. Both wrappers draw into the active slide and bring the presentation forward once by default. Use `-CreateNewPresentation` only when the user explicitly asks for a separate deck, and `-KeepBackground` only when the user explicitly does not want the presentation brought forward.

Create each retained freeform path and text box in the literal Master SVG paint order, from backmost to frontmost. Treat the first retained cached path as the lowest layer, create it first, then explicitly bring each later object in front of the earlier job objects. Never infer or replace this order with semantic categories. After each individual object is committed, force the active slide to repaint and apply the configured delay. Do not wait until a batch ends to reveal objects. Never preload, clear, hide, delete, replace, or close retained completed artwork.

## Quality checks

- Every ordinary text run is a native text box.
- Every retained vector subpath is a native freeform Bézier shape.
- The slide contains no whole-figure raster fallback.
- Repeated objects remain separately selectable.
- Existing objects are unchanged.
- The saved PPTX opens in the selected host.
