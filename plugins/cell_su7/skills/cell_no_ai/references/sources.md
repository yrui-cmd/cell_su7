# 核实来源与限制



核实日期：2026-09-06。



- OpenAI 官方验证页面：https://openai.com/zh-Hans-CN/research/verify/

  当前说明明确支持检查 C2PA 元数据和 SynthID 水印，检测受支持的 OpenAI 内容溯源信号。未检测到并不等于不是 AI 内容，也不保证没有其他来源的水印。检测时应保留原文件，每次一个文件。

- SynthID 技术来源：https://deepmind.google/science/synthid/

  OpenAI 官方验证页链接到 Google DeepMind 的 SynthID。区别技术来源与采用该技术的生成服务。

- 小描正式去水印文档：https://xiaomiao-ai.com/watermark-api.html
- OpenAPI：https://xiaomiao-ai.com/openapi.json
  去水印接口已发布，使用 /api/watermark-jobs，与路径识别接口分开。2026-09-06 已实测成功领取去水印结果；官方 /docs#balance 已新增 GET /api/balance，提交前必须查询。
