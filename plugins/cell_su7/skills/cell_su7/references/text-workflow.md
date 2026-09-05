# Editable lettering workflow

Use this workflow by default for an image containing text. Preserve the untouched original as the reference throughout. Before cleanup, record `source_canvas` width and height, and for every label its original pixel bounding box (`source_bbox: [left, top, width, height]`), baseline anchor x/y, alignment, rotation and font size. Save the manifest before editing; do not re-estimate positions from the cleaned image. The entrypoint copies the manifest into the output job folder for later comparison and correction.

1. Read the original lettering and record every label, panel letter, legend, unit and symbol in a JSON manifest. Preserve spelling, capitalization, line breaks, position, rotation, color, font family and size as closely as the source supports. Mark uncertain transcription for clarification instead of inventing text.
2. Use an available image-editing model with the original as its reference to produce a separate cleaned image. The skill does not require Image 2 or any particular provider. A suitable prompt is: “仅删除所有文字、字母、数字与标注字符，并修复其覆盖的小范围背景。其余图形、图标、曲线、箭头、连线、边框、纹理、颜色、布局、比例、画布尺寸与裁切完全保持原样。不要重绘、优化、美化、移动或新增任何非文字元素。” Keep arrows and legend swatches even when adjacent to labels.
3. Visually compare both complete images and inspect text regions at readable scale. Check for residual lettering, changed non-text content, damaged connectors and canvas or alignment drift. If cleanup changes the drawing, correct the affected regions before uploading. Model editing does not itself prove preservation. If a suitable editing model is unavailable, report the limitation; do not silently skip text restoration.
4. Pass the verified cleaned image and the original text manifest to the entrypoint. The scripts recognize the cleaned image, preserve its raw vector result, add live SVG text to the Master SVG, then draw native editable text in the chosen backend. They do not invoke an image model themselves.
5. Compare the final text and drawing against the original. Check every label against its saved bounding box and baseline, including placement and style, and absence of duplicate outlined text underneath. Keep the raw vector SVG and manifest for corrections. Text-free images may omit the manifest. Approved SVGs with existing live text do not need image cleanup.

## Manifest

UTF-8 JSON, `schema_version: "1.0"`, and `text_elements` array:

```json
{
  "schema_version": "1.0",
  "source_canvas": {"width": 1200, "height": 800},
  "text_elements": [{
    "id": "label-1",
    "content": "Sample\ncondition",
    "source_bbox": [300, 300, 140, 50],
    "x": 300,
    "y": 320,
    "coordinate_space": "pixels",
    "font_size": 20,
    "font_size_space": "pixels",
    "font_family": "Arial",
    "font_weight": "normal",
    "font_style": "normal",
    "fill": "#111111",
    "text_anchor": "start",
    "rotation": 0,
    "line_height": 1.2,
    "paint_order": 9999
  }]
}
```

Pixel x/y are converted using `source_canvas` to the SVG viewBox, including its origin and scale. Use the baseline anchor, not the bounding-box top-left; `source_bbox` is a retained comparison reference, not an automatic replacement for the baseline. Normalized x/y are also supported and use the full unchanged canvas, with y at the text baseline. Normalized font size is a fraction of canvas height. Each id must be unique and distinct from geometry ids. `paint_order` selects the SVG insertion position; choose it to match source overlap (a large value places text above the geometry). A model's returned image must retain the original coordinate frame before reusing these positions.

Windows selector: `run_cell_su7.ps1 -InputImage cleaned.png -TextManifest text.json -OutputRoot output -Application ppt` (or `ai`). Backend scripts also accept `-TextManifest`.

macOS PPT: `run_from_image.py --input-image cleaned.png --text-manifest text.json --output-root output`.

When fonts are unavailable or text metrics differ in the target app, inspect and adjust the editable text against the original label region. Passing coordinate tests does not replace this visual check. Do not freely rearrange labels or “improve” their layout.
