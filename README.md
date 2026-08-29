# Cell_ppt

Cell_ppt 支持 Windows 与 macOS，并保持同一套核心流程：

`文字清单 → Image 2 仅清文字 → 小描路径返回 SVG → 合并可编辑文字 → 单次解析 → 清除重复路径 → 按源顺序从底层到顶层绘制 → 原生可编辑 PPTX`

平台只在最后一步不同：

- Windows 10/11：支持 PowerPoint 2016、2019、2021、LTSC 2021、LTSC 2024 和 Microsoft 365 桌面版，使用 COM 在当前幻灯片中按路径顺序实时绘制。
- macOS 13+：支持可打开标准 `.pptx` 的 PowerPoint 2019、2021、2024 和 Microsoft 365 桌面版；使用原生 OOXML 写入同一几何缓存，路径和文字可编辑，但不伪装成实时逐路径动画。
- WPS Presentation：实验性兼容。

## 已固定的规则

- Python 3.11–3.14。
- 不限定 PowerPoint 2026；Windows 使用通用 `PowerPoint.Application` 接口，macOS 使用标准 `.pptx` OOXML。
- `python-pptx==1.0.2`、`fonttools==4.61.1`、`shapely==2.1.2`。
- 几何缓存 schema 3，文字清单 schema 1.0。
- 普通批次 20–50 条路径，画布安全边距 18 pt。
- 文件名统一为 `shibielujingN`。
- 源 SVG 只解析一次；保留路径严格按源绘制顺序写入。
- 只清除完全重复的路径；不可见、被覆盖和部分可见的非重复路径均保留。
- Windows 逐对象间隔固定为 8 ms，比原来的 80 ms 快 10 倍。
- 不删除、隐藏、移动或替换目标幻灯片已有对象。
- API Key 不进入命令参数、环境变量、仓库、日志、缓存或交付文件。
- Windows 密钥位置固定为当前账户 DPAPI；macOS 固定为系统 Keychain 服务 `cell-ppt-xiaomiao`。

这些值写在依赖锁、脚本和 `platform-contract.json` 中，不需要用户自行配置。

## 交给 Codex 自动安装

直接把下面一句和 API Key 一起发给目标电脑的 Codex：

```text
请安装 https://github.com/yrui-cmd/cell-ppt，并根据当前电脑自动匹配操作系统、Python、PowerPoint/WPS 与绘图后端；使用我在本条消息中提供的 API Key 完成安全配置，不要复述或显示密钥。安装、依赖、DPAPI/Keychain、认证验证和诊断全部由你完成，验证通过后使用 $cell-ppt 开始作图。
```

允许在聊天中提供 API Key。Codex 必须只通过标准输入传给安装程序，不得复述，也不得写入命令行参数、环境变量、项目、日志或交付文件。安装程序会自动安装固定依赖、复制 Skill、生成 `runtime-profile.json`、选择可用后端、保存加密凭据并执行零额度认证验证。

## Windows 安装

```powershell
git clone https://github.com/yrui-cmd/cell-ppt.git
Set-Location .\cell-ppt
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

覆盖已有 Skill：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Force
```

## macOS 安装

```bash
git clone https://github.com/yrui-cmd/cell-ppt.git
cd cell-ppt
bash ./setup.sh
```

覆盖已有 Skill：

```bash
bash ./setup.sh --force
```

安装后重启 Codex 并新建任务。API Key 由 Codex 通过标准输入配置；Windows 保存为 DPAPI 密文，macOS 保存到 Keychain。

用户无需判断 PowerPoint 版本或后端：Windows 自动选择 PowerPoint COM，其次尝试 WPS，均不可用时仍可生成原生可编辑 PPTX；macOS 自动使用原生 OOXML。

## 使用

Windows：先打开 PowerPoint 和目标文稿。

```text
使用 $cell-ppt，根据我上传的内容或图片在当前 PowerPoint 幻灯片中作图，保留已有内容。
```

macOS：先保存目标 PPTX，并把文件路径交给 Codex。

```text
使用 $cell-ppt，把上传内容重建为可编辑路径并追加到 /Users/me/project/deck.pptx。
```

## 诊断

Windows：

```powershell
.\doctor.ps1
.\doctor.ps1 -VerifyApi -RequirePowerPointOpen
```

macOS：

```bash
python3 ./doctor.py
python3 ./doctor.py --verify-api --json
```

## 测试

```powershell
.\tests\test-package.ps1
.\tests\test-windows-e2e.ps1
```

```bash
python3 ./tests/test_cross_platform.py
```

Windows PowerPoint 真机测试必须使用一次性测试文稿：

```powershell
.\tests\test-powerpoint-e2e.ps1 -ConfirmDisposablePresentation
```

完整插件源码位于 `plugins/cell-ppt`。感谢小红书：木纹小路。
