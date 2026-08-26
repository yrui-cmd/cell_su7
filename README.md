# Cell_ppt

Cell_ppt `v0.1.0` 是面向 Windows、Codex Desktop 与 Microsoft PowerPoint 的稳定版科研矢量绘图插件。它把参考图重建为当前幻灯片中的原生自由曲线和真实可编辑文字，并按最终层级从底到顶逐条显示。

## 稳定版保证

- 固定源码版本：Git Tag `v0.1.0`。
- 固定 Python 依赖、运行契约和关键文件 SHA256。
- 一键安装与诊断：`setup.ps1`、`doctor.ps1`。
- Windows 离线测试与 PowerPoint COM 真机测试。
- Release ZIP 配套独立 SHA256 文件。
- 不提供 Marketplace 安装入口；从固定 Tag 或 Release ZIP 安装。
- API Key 不随项目分发，只由 Codex通过标准输入配置，并使用当前 Windows 账户的 DPAPI 加密保存。

## 环境要求

- Windows 10/11 x64
- Codex Desktop，且当前任务具备内置 Image 2 图片编辑能力
- Microsoft PowerPoint 16.x 桌面版
- PowerShell 5.1 或更高版本
- Python 3.11–3.14

WPS Presentation 保留实验性兼容入口，但不属于 `v0.1.0` 稳定承诺。

## 从固定 Tag 安装

```powershell
git clone --branch v0.1.0 --depth 1 https://github.com/yrui-cmd/cell-ppt.git
Set-Location .\cell-ppt
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

安装器会安装锁定依赖、复制 Skill 并运行诊断。API Key 由 Codex自动通过标准输入配置；Codex不得复述密钥，也不得把密钥写入命令行、环境变量、项目、日志、缓存或交付文件。

如果已经存在同名 Skill，并确认替换：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Force
```

安装和密钥验证完成后重启 Codex，新建任务并发送：

```text
使用 $cell-ppt，根据我上传的内容或图片在当前 PowerPoint 幻灯片中作图，保留全部已有内容。
```

给另一台电脑 Codex 的完整安装指令：

```text
请从固定版本 v0.1.0 安装 https://github.com/yrui-cmd/cell-ppt，完成依赖安装；使用我提供的 API Key 自动进行 DPAPI 配置，不要复述或显示密钥。配置验证通过后重启 Codex，并使用 $cell-ppt 在当前 PowerPoint 幻灯片中根据我上传的内容开始作图。
```

## 固定播放规则

- 最终不可见、被后续不透明对象完全覆盖或与后续路径重复的对象不进入播放缓存。
- 部分可见的路径保留。
- 每条保留路径只缓存一次、只生成一个原生对象一次。
- 按源 SVG 的最终绘制顺序从底层到顶层逐条出现，默认间隔 80 ms。
- 不预载、不隐藏揭示、不复制覆盖、不事后替换。
- 不清空、不隐藏、不删除或移动当前幻灯片的已有对象。
- 文字为原生文本框，路径为原生自由曲线；不使用整图位图回退。

## 诊断与测试

```powershell
.\doctor.ps1
.\doctor.ps1 -VerifyApi -RequirePowerPointOpen
.\doctor.ps1 -Json
.\tests\test-package.ps1
.\tests\test-windows-e2e.ps1
```

PowerPoint 真机测试会创建并关闭一次性测试文稿：

```powershell
.\tests\test-powerpoint-e2e.ps1 -ConfirmDisposablePresentation
```

构建发行包：

```powershell
.\build-release.ps1
```

生成的 ZIP 与 SHA256 位于 `dist`。

## 可复现性边界

仓库冻结的是 Skill、脚本、依赖、缓存筛选、PPT 播放和交互规则。Codex 内置 Image 2 与小描是远程生成服务，因此新图片的生成细节允许差异；路径显示方式、编辑能力和已有内容保护必须一致。

感谢小红书：木纹小路。
