# Optional cell_no_ai step before path recognition

This branch is requested by the user. It runs after text removal and visual checking, before uploading the image for path recognition. Do not invoke it for already-approved vector inputs.

## Ask once for this image

Ask: “是否彻底消除 AI 水印？选择‘是’将调用 cell_no_ai 进行额外处理，需额外扣除 1 个额度，返回图片后先用 cell_high_solution 保真高清修复，再继续描摹；选择‘否’则直接继续。”

Explain if needed: AI image provenance can involve different marking mechanisms; tracing does not guarantee removal of every type. Do not assert every image contains exactly two watermark types, that tracing always removes one, or that the additional service guarantees complete removal without authoritative evidence. The question describes the user's requested treatment goal, not a verified outcome.

Wait for an explicit answer. No answer is pending, never consent or a default no. Existing consent for recognition does not authorize this extra charge. A yes authorizes one cell_no_ai treatment costing 1 additional credit for this image, separate from normal recognition cost. If the actual price is higher or unknown, resolve the cost before sending the image. Do not debit locally or report a charge before a real service response.

## Yes

1. Discover and read the installed `cell_no_ai` SKILL.md or its documented callable tool. Use its own authenticated submission, billing, status and download workflow; never invent an endpoint, command or response schema. This required dependency is bundled and installed alongside cell_su7. Always query its live balance before submitting.
2. If unavailable, explain that the yes branch cannot run and request its installation path/repository or interface documentation. Keep the decision pending execution. Do not silently switch to no or call another paid service.
3. Send the verified text-free image, not the original lettered image. Keep the original image and text manifest unchanged. Save the decision, input image identity and returned job identifier with the job, excluding credentials.
4. Wait for successful completion and download the returned image. Resume/poll the same job on transient errors; do not resubmit or charge again merely because a request timed out. On failure, report it and preserve the pending workflow.
5. Check that the returned image is readable and retains the coordinate frame, drawing, connectors and proportions. If it changed those, correct or resolve the mismatch before recognition; do not blindly reuse text coordinates on shifted artwork.
6. Mandatory: read the separately installed `cell-high-solution/SKILL.md` (display name `cell_high_solution`) and run its bundled enhancer once with the downloaded no-ai output as input and `--mode faithful`. Wait for the enhanced PNG; save it separately. Do not use auto/restore/redraw for this scientific-figure continuation. If unavailable or failed, resolve that step before recognition; keep the same no-ai result and do not resubmit a paid job.
7. Verify readable enhanced output and unchanged canvas aspect ratio, layout and alignment. Use the enhanced PNG, never the raw no-ai return, as path-recognition input. Keep the original manifest and `source_canvas` so the existing viewBox mapping restores labels proportionally; do not change `source_canvas` alone. Continue native drawing and editable text restoration normally. Report actual service billing/balance; do not claim verified removal of all watermark types.

## No

Do not call cell_no_ai and incur no extra watermark-treatment charge. Submit the already-verified cleaned image directly to the existing recognition workflow, retaining the same text manifest.

## Integration contract

Required order for the approved branch: text-free image -> cell_no_ai downloaded result -> cell_high_solution faithful PNG -> path recognition -> editable text restoration. `cell_no_ai` is bundled as a separate required skill; `cell-high-solution` is an external local dependency whose command must be resolved from its installed skill. This update defines orchestration and does not claim a new paid end-to-end test.
