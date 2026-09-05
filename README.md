# cell_gd

保留文字为可编辑对象，使用模型去字后的图进行路径识别，使用者选择 **PPT 或 Adobe Illustrator**，随后沿用原 cell-ppt / cell-lct 的绘图与后处理。

## 流程

1. 提供原始 PNG、JPEG 或 WebP。
2. 选择 PPT 或 Adobe Illustrator。
3. 去字前记录原图尺寸、每段文字的像素坐标、边界框、基线、对齐、旋转、字号和颜色，保存文字清单；使用可用的图像编辑模型仅去掉文字，不限定 Image 2。
4. 对照原图检查图形、布局、配色、连线和画布尺寸未改变，再将去字图上传路径识别；把文字作为可编辑文本回填后进入绘图分支。
5. PPT 保存可编辑 PPTX；Illustrator 保存 AI，并在完成后导出 PNG。

PPT 保留原逐路径去重、绘制顺序、8 ms 间隔、已有对象保护及 macOS OOXML 后端。Illustrator 保留原缓存、20–50 对象批次、单连接续画、断点恢复、定时保存与最终导出。

## 安装

Windows：运行 `setup.ps1`；macOS：运行 `bash setup.sh`。安装后的 skill 名和目录均为 `cell_gd`。本仓库统一提供 PPT 和 Adobe Illustrator 两个绘图后端，只需安装这一份。原 cell-ppt / cell-lct 独立仓库保持原有用途。

Windows 支持 PPT 和 Illustrator；Illustrator 沿用已有 Windows / Illustrator 2026 运行要求，需先打开目标文档。macOS 沿用 PPT 的可编辑 OOXML 后端。

API 密钥配置和额度规则沿用原适配器。原有安全凭据命名空间保持兼容。

## 调用

告诉 Codex：`用 cell_gd 处理这张原图，用 PPT 绘制。` 或 `用 cell_gd 处理这张原图，用 Adobe Illustrator 绘制。`

由 Codex 完成文字记录、模型去字和对照检查后，调用脚本入口（脚本本身不调用去字模型）：
```powershell
.\plugins\cell_gd\skills\cell_gd\scripts\run_cell_gd.ps1 -InputImage .\cleaned.png -TextManifest .\text.json -OutputRoot .\output -Application ppt
```
把 `ppt` 改为 `ai` 选择 Illustrator。需要自定义放置、批次或续画时，使用各分支原运行脚本。已认可的 SVG 可直接进入后处理。

macOS PPT：
```bash
python plugins/cell_gd/skills/cell_gd/scripts/run_from_image.py --input-image cleaned.png --text-manifest text.json --output-root output
```

源码仓库：[yrui-cmd/cell_gd](https://github.com/yrui-cmd/cell_gd)。

## 余额显示

每次图片识别完成后自动显示服务端返回的剩余额度，例如 `剩余额度：20`；余额为零显示 `剩余额度：0`。接口未提供有效余额时显示 `剩余额度：暂不可用`。Windows 的 PPT、Illustrator 和 macOS 图片入口均显示该信息，不额外发起计费请求。该数值是本次识别完成时的额度快照。

文字清单随结果保存为 `text-manifest.json`。回填位置由原图坐标映射到 SVG 画布，再与图形使用同一套缩放和定位；最终逐段对照原图检查，字体替换造成的偏差需要校正。
