# Presentation backends

## Microsoft PowerPoint

Use `PowerPoint.Application`. Keep one COM application object and one presentation reference for the entire drawing job. `Shapes.BuildFreeform` creates native editable curves; `Shapes.AddTextbox` creates live text. This is the preferred Windows backend.

## WPS Presentation

Treat WPS as experimental. Try `KWPP.Application`, then `WPP.Application`. Use the same standard PowerPoint object model and save as `.pptx`. WPS editions differ in automation coverage. Require working `Presentations`, `Slides`, `Shapes.BuildFreeform`, `AddTextbox`, and `SaveAs`; if any required method is unavailable, stop and report the missing capability. Never describe WPS as stable until its live end-to-end suite passes on a declared WPS build.

## Compatibility boundary

Solid fills, solid strokes, cubic Bézier paths, basic opacity, rotations, and text boxes are supported. Gradients, masks, clipping paths, patterns, linked resources, embedded raster nodes, and compound-hole semantics require preprocessing or explicit rejection. Never conceal an unsupported feature by inserting the complete figure as an image.
