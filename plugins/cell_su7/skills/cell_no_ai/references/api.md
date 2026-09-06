# 小描去水印 API

已核实的官方文档：
- https://xiaomiao-ai.com/watermark-api.html
- https://xiaomiao-ai.com/openapi.json
- https://xiaomiao-ai.com/ （当前服务开放状态）

Base URL: https://xiaomiao-ai.com
鉴权：Authorization: Bearer，沿用现有小描 API Key。

| 动作 | 方法与路径 | 处理 |
|---|---|---|
| 提交 | POST /api/watermark-jobs | multipart/form-data，单个 image；201 返回 job_id、status_url、result_file_url、expires_at |
| 状态 | GET /api/watermark-jobs/{job_id} | received / processing / completed；查询不计费 |
| 领取 | GET /api/watermark-jobs/{job_id}/result | 同一鉴权，返回图片二进制；X-Xiaomiao-Charged 为 1 或 0 |
| 取消 | DELETE /api/watermark-jobs/{job_id} | 取消并删除，未领取的预留额度退回；不要自动调用 |

用户输入支持 PNG/JPG；官方还支持 WebP。最大 10 MB、3200 万像素。预留 1 个额度，首次领取正式扣除；重复领取不再扣费；失败/取消/过期释放未消耗额度。数据自提交起保留 15 分钟。

401 密钥无效；402 额度不足；404 不存在或过期；409 仍在处理；413 太大；415 格式无效。503 或明确服务未开放时停止，保留输入与状态，不重试提交以碰运气。

安全调用要点：只向固定 HTTPS 官方源发送鉴权，禁用自动跨站重定向；服务器给出的 status_url/result_file_url 先验证同源及任务 ID，优先按上表构造同任务路径。job_id 进行 URL path 编码。网络错误不能输出完整带凭据请求。下载及时写入工作区，并校验 MIME 与实际图片解码结果。

## 实时余额接口（每次提交前必查）

官方依据：https://xiaomiao-ai.com/docs#balance （2026-09-06 核实）。

GET https://xiaomiao-ai.com/api/balance
Authorization: Bearer <same API Key>

只读、query_cost=0。HTTP 200 且 ok=true 时读取 available_credits：必须是有效非负数，去水印至少 1 才能提交。available_credits 已扣除预留额度；不能使用 credits_used 作为余额，也不能再次扣减 reserved credits。响应另含 credits_used、checked_at、query_cost、services；services 的 can_submit 仅表示额度和权限，不保证处理人员在线。若服务明确不允许提交则停止。

401 表示无效 Key，503 表示查询失败。任何非 200、ok 不为 true、字段缺失、布尔值、非数值或非法数值均停止，不上传。每次新任务重新查询，不缓存。余额足够后显示实际数值和本次 1 额度费用，按已有授权提交一次；提交时服务端仍会再次核验余额。
