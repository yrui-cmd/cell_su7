# Python 接收后唤醒原对话

不创建 Codex automation/heartbeat、cron、Windows 计划任务或定时聊天。等待属于该任务的后台 Python 进程：查询原任务、下载、校验、保存结果，确认接收后调用桌面公开的 `send_message_to_thread` 接续原对话。不要用独立 `codex exec/resume` 会话冒充原聊天。

## 提交与接收

图片及文字清理、可选去水印和额度确认仍按原流程进行；去水印结果必须真实下载并检查后才提交识别。以下后台入口只负责识别阶段，不新增去水印调用。

在支持桌面唤醒的环境默认使用：

```text
python scripts/run_cell_su7.py --input-image 已核验图片.png --text-manifest text.json --output-root 输出目录 --application ppt --background --thread-id 原对话ID --authorize-wake
```

无文字时不传 `--text-manifest`；选Illustrator时用 `--application ai`。预计超过1额度沿用原来的真实确认并加 `--approve-high-cost`，不能把该参数当作客户答复。`--authorize-wake` 表示本任务已获原对话接续授权，不授权给其他聊天发消息。

入口先只读检查桌面通道，再保存输入副本、清单、原对话及提交状态，随后只提交一次，记录真实 `image_id`。网络超时导致上传回执未知时停在 `submit_unknown`，先核对原请求，不再次上传。返回任务目录后结束等待轮次；由 Python 接收，不让助手或其他代理继续轮询。

若已有识别任务编号，**不再上传**，用以下方式接收：

```text
python scripts/receive_and_wake.py start --job-dir 原任务接收目录 --image-id 已有任务ID --application ppt --thread-id 原对话ID --authorize-wake
```

需要恢复文字时同时传原 `--text-manifest`。保存画布坐标，不改写原manifest。后续恢复直接 `resume --job-dir 原目录 --thread-id 原对话ID`，不能重新运行新图片入口。每个目录只有一个接收进程锁。

## 确认收到的条件

- 远端已完成，真实SVG已下载到临时文件；通过 `validate_vector_svg`，不是栅格包装或损坏文本。
- 原始SVG落盘为 `received-vector.svg`，保存SHA-256和真实 `credits_left`，才标记 `ready`。
- Python确认原对话身份；对话忙时在本进程内稍后重试，空闲后发送一次接续消息。发送前持久化 `sending`；确认后标 `sent`。超时或回执未知标 `uncertain`，不盲目重发。
- 文件接收失败、桥接不可用等保留原单。接收最多24小时，连续异常最多12次，之后记 `attention`；不得声称已收到或已唤醒。桥接失败不得悄悄退回定时任务。

## 原对话继续

接续消息不是新的绘图要求；读取本任务 `receive-state.json`，核对当前thread、原任务ID、nonce和SVG摘要，检查用户后续是否要求停止。确认后运行：

```text
python scripts/receive_and_wake.py ack --job-dir 原目录 --thread-id 原对话ID --nonce 接续标记
```

有 `text-manifest.json` 时用原来的 `merge_live_text.py` 将文字恢复到新的Master SVG；保留下载原件。之后按已选PPT/Illustrator后端继续校验、绘图、保存与预览，不重新识别、去水印或扣费。SVG接收并不代表已绘制完成。用户要求停止时，执行 `stop --job-dir 原目录 --thread-id 原对话ID`；停止后不唤醒、不画图，只有用户明确要求恢复才 `resume`。

`status --job-dir 原目录` 仅看本地状态。`probe --thread-id 原对话ID` 仅检验桌面连接，不发消息、不收费。Windows桌面管道可本机验证；其他平台只有实际可用桌面通道时才能宣称自动接续可用，否则保留结果并说明限制。
