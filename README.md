# cell_su7

保留文字为可编辑对象，使用模型去字后的图进行路径识别，使用者选择 **PPT 或 Adobe Illustrator**，随后沿用原 cell-ppt / cell-lct 的绘图与后处理。

## 流程

绘制顺序：**先从后面画，再往前画——底层先出现，前景逐层叠上去。** 按原图实际层叠顺序执行，批次内外都保持一致；底板属于最底层时首先绘制。清理冗余重复路径时保留首次出现，相邻不透明重复可直接合并；跨层重复及透明叠加须保留其遮挡效果，不能盲删。

1. 提供原始 PNG、JPEG 或 WebP。
2. 选择 PPT 或 Adobe Illustrator。
3. 去字前记录原图尺寸、每段文字的像素坐标、边界框、基线、对齐、旋转、字号和颜色，保存文字清单；使用可用的图像编辑模型仅去掉文字，不限定 Image 2。
4. 对照原图检查图形、布局、配色、连线和画布尺寸未改变，再将去字图上传路径识别；把文字作为可编辑文本回填后进入绘图分支。
5. PPT 保存可编辑 PPTX；Illustrator 保存 AI，并在完成后导出 PNG。

PPT 默认一次写入原生可编辑矢量，保留复合路径镂空，避免逐点 COM 绘制耗时。Illustrator 按 20–50 对象批次绘制、每批刷新，保留复合路径、续画和最终导出。

## 安装

Windows：运行 `setup.ps1`；macOS：运行 `bash setup.sh`。安装后的 skill 名和目录均为 `cell_su7`。本仓库统一提供 PPT 和 Adobe Illustrator 两个绘图后端，运行一次安装即可。原 cell-ppt / cell-lct 独立仓库保持原有用途。

Windows / macOS 均提供 PPT 和 Illustrator 入口。Windows PPT 已用复杂图实测；Mac PPT 复用同一 OOXML 文件后端。Mac Illustrator 已实现 AppleScript 桥接，但仅完成模拟测试，尚未在 Mac 桌面实测。Illustrator 需先打开目标文档。

API 密钥配置和额度规则沿用原适配器。原有安全凭据命名空间保持兼容。

## 调用

告诉 Codex：`用 cell_su7 处理这张原图，用 PPT 绘制。` 或 `用 cell_su7 处理这张原图，用 Adobe Illustrator 绘制。`

由 Codex 完成文字记录、模型去字和对照检查后，调用脚本入口（脚本本身不调用去字模型）：
```powershell
.\plugins\cell_su7\skills\cell_su7\scripts\run_cell_su7.ps1 -InputImage .\cleaned.png -TextManifest .\text.json -OutputRoot .\output -Application ppt
```
把 `ppt` 改为 `ai` 选择 Illustrator。需要自定义放置、批次或续画时，使用各分支原运行脚本。已认可的 SVG 可直接进入后处理。

macOS PPT：
```bash
python plugins/cell_su7/skills/cell_su7/scripts/run_from_image.py --input-image cleaned.png --text-manifest text.json --output-root output
```

源码仓库：[yrui-cmd/cell_su7](https://github.com/yrui-cmd/cell_su7)。

## 余额显示

每次图片识别完成后自动显示服务端返回的剩余额度，例如 `剩余额度：20`；余额为零显示 `剩余额度：0`。接口未提供有效余额时显示 `剩余额度：暂不可用`。Windows 的 PPT、Illustrator 和 macOS 图片入口均显示该信息，不额外发起计费请求。该数值是本次识别完成时的额度快照。

文字清单随结果保存为 `text-manifest.json`。回填位置由原图坐标映射到 SVG 画布，再与图形使用同一套缩放和定位；最终逐段对照原图检查，字体替换造成的偏差需要校正。

## 白板、顺序与性能修复（0.4.0）

白板问题来自把带镂空的白色复合路径拆成独立填充，不能只靠移到底层解决。现在保持复合路径完整，按源文件从后往前排列；PPT 使用快速原生文件写入，Illustrator 每批刷新。旧版拆分缓存必须从 SVG 重新生成。四种运行组合及实测范围见 [平台说明](plugins/cell_su7/skills/cell_su7/references/backends.md)。

跨平台入口：`python plugins/cell_su7/skills/cell_su7/scripts/run_cell_su7.py --input-image cleaned.png --text-manifest text.json --output-root output --application ppt`，`ppt` 可改为 `ai`。

### 逐路径显示（Windows PowerPoint）

默认先生成原生可编辑对象，再按原图层次逐个显示，零额外延时，不使用逐对象剪贴板复制。带镂空的复合路径保持完整。macOS PowerPoint 当前仍交付可编辑文件，未实现该可见播放入口。

安装会同时安装必需依赖 **cell_no_ai**；插件包内包含两个独立 skill。已有的 cell_no_ai 会保留，不会覆盖。手动安装时请同时复制两个 skill 目录。安装依赖不代表同意付费去水印，提交前仍必须查询实时余额并确认 1 额度费用。

独立依赖源码：[cell_no_ai](https://github.com/yrui-cmd/cell_no_ai)。新版必须等待领取结果后交付，并在每次调用时说明两项功能；收到结果直接提供图片或链接。
