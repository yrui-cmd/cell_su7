# Cell_ppt

Cell_ppt `v0.1.0` 是面向 Windows、Codex Desktop 与 Microsoft PowerPoint 的稳定版科研矢量绘图插件。它将参考图重建为可编辑路径和原生文本框，并续画到用户已经打开的 PowerPoint 幻灯片中。

## 稳定版保证

- 固定源码版本：Git Tag `v0.1.0`。
- 固定 Python 依赖：`requirements.lock`。
- 固定运行契约：`runtime-lock.json`。
- 一键安装与诊断：`setup.ps1`、`doctor.ps1`。
- Windows 自动端到端测试，另提供 PowerPoint 人工触发真机测试。
- Release ZIP 配套独立 SHA256 文件。
- 不提供 Marketplace 安装入口；从固定 Tag 或 Release ZIP 安装。
- API Key 不随项目分发，只通过当前 Windows 账户的 DPAPI 加密保存。
- 单张图片预计消耗超过 1 额度时，必须在上传 API 前取得用户确认；拒绝时不上传。确认后处理与下载不再重复询问。

## 环境要求

- Windows 10/11 x64
- Codex Desktop，且当前任务具备内置 Image 2 图片编辑能力
- Microsoft PowerPoint 16.x 桌面版
- PowerShell 5.1 或更高版本
- Python 3.11–3.14

WPS Presentation 保留实验性兼容入口，但不属于 `v0.1.0` 稳定承诺。

## 从固定 Tag 一键安装

```powershell
git clone --branch v0.1.0 --depth 1 https://github.com/yrui-cmd/cell-ppt.git
Set-Location .\cell-ppt
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

首次安装会安装锁定依赖、复制 Skill，并运行诊断。API Key 由 Codex 通过标准输入安全配置，不应写进命令、仓库、截图或聊天记录。

如果已经存在同名 Skill，并确认要替换：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Force
```

安装后重启 Codex，并新建任务。先由用户打开 PowerPoint 和目标文稿，然后发送：

```text
使用 $cell-ppt，根据我上传的内容或图片在当前 PowerPoint 幻灯片中作图，保留全部已有内容。
```

## 从 Release ZIP 安装

下载同一版本的两个文件：

- `cell-ppt-v0.1.0.zip`
- `cell-ppt-v0.1.0.zip.sha256`

验证后解压并运行 `setup.ps1`：

```powershell
$zip = '.\cell-ppt-v0.1.0.zip'
$expected = ((Get-Content "$zip.sha256") -split '\s+')[0]
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'SHA256 校验失败，停止安装。' }
Expand-Archive $zip -DestinationPath .\cell-ppt-v0.1.0
Set-Location .\cell-ppt-v0.1.0\cell-ppt-v0.1.0
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

## 诊断

```powershell
.\doctor.ps1
.\doctor.ps1 -VerifyApi -RequirePowerPointOpen
.\doctor.ps1 -Json
```

诊断只检查 PowerPoint 注册和进程状态，不会启动、重启、聚焦、最大化或关闭 PowerPoint。

## 工作方式

- 先记录参考图文字的内容、位置、尺寸、字体、字重、颜色、旋转、对齐和层级。
- Image 2 只清除文字，保留箭头、框、坐标轴、热图、图例、科研主体和原布局。
- 完整清理图进入矢量识别；返回后先在 Master SVG 中合并真实可编辑 `<text>`。
- SVG 只解析一次并建立几何缓存，全程复用一个 PowerPoint 连接。
- 普通批次为 20–50 条路径，复杂路径可单独处理。
- 从底层到顶层将每条保留路径直接画成原生可编辑对象；不预载、不隐藏揭示、不重复覆盖。
- 不删除、不隐藏、不替换已有幻灯片内容；PNG 只在结束时按需导出。

## 测试与发行

```powershell
.\tests\test-package.ps1
.\tests\test-windows-e2e.ps1
.\build-release.ps1
```

PowerPoint 真机测试会向一次性测试文稿写入测试图，只能显式运行：

```powershell
.\tests\test-powerpoint-e2e.ps1 -ConfirmDisposablePresentation
```

生成的 ZIP 与 SHA256 位于 `dist`。CI 使用 Windows runner 执行离线绘图链路测试；PowerPoint 真机链路仅在带 PowerPoint 16 的自托管 Windows runner 上人工触发。

## 可复现性边界

仓库可以固定 Skill、脚本、依赖、测试和发行文件，但无法把 Codex 内置 Image 2 或 Microsoft PowerPoint 本体打包进去。另一台电脑要获得一致流程，必须满足 `runtime-lock.json` 中的环境契约，并自行配置 DPAPI API Key。

完整插件源码位于 `plugins/cell-ppt`，安装器只把其中的 `cell-ppt` Skill 部署到用户的 Codex Skills 目录。

感谢小红书：木纹小路。
