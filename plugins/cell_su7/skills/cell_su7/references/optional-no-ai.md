# Optional cell_no_ai step before path recognition

This branch is requested by the user. It runs after text removal and visual checking, before uploading the image for path recognition. Do not invoke it for already-approved vector inputs.

## Ask once for this image

Ask: “是否彻底消除 AI 水印？选择‘是’将调用 cell_no_ai 进行额外处理，需额外扣除 1 个额度，返回图片后再继续描摹；选择‘否’则直接继续。”

Explain if needed: AI image provenance can involve different marking mechanisms; tracing does not guarantee removal of every type. Do not assert every image contains exactly two watermark types, that tracing always removes one, or that the additional service guarantees complete removal without authoritative evidence. The question describes the user's requested treatment goal, not a verified outcome.

Wait for an explicit answer. No answer is pending, never consent or a default no. Existing consent for recognition does not authorize this extra charge. A yes authorizes one cell_no_ai treatment costing 1 additional credit for this image, separate from normal recognition cost. If the actual price is higher or unknown, resolve the cost before sending the image. Do not debit locally or report a charge before a real service response.

## Yes

1. Discover and read the installed `cell_no_ai` SKILL.md or its documented callable tool. Use its own authenticated submission, billing, status and download workflow; never invent an endpoint, command or response schema. This dependency is not bundled in cell_su7.
2. If unavailable, explain that the yes branch cannot run and request its installation path/repository or interface documentation. Keep the decision pending execution. Do not silently switch to no or call another paid service.
3. Send the verified text-free image, not the original lettered image. Keep the original image and text manifest unchanged. Save the decision, input image identity and returned job identifier with the job, excluding credentials.
4. Wait for successful completion and download the returned image. Resume/poll the same job on transient errors; do not resubmit or charge again merely because a request timed out. On failure, report it and preserve the pending workflow.
5. Check that the returned image is readable and retains the coordinate frame, drawing, connectors and proportions. If it changed those, correct or resolve the mismatch before recognition; do not blindly reuse text coordinates on shifted artwork.
6. Use that returned image as the input to the existing path-recognition entrypoint, with the original text manifest. Continue native drawing and editable text restoration normally. Report the service's actual billing/balance when returned; do not infer a shared balance across services or claim all watermark types are removed without verification.

## No

Do not call cell_no_ai and incur no extra watermark-treatment charge. Submit the already-verified cleaned image directly to the existing recognition workflow, retaining the same text manifest.

## Integration status

The user-facing decision and continuation rules are installed. At this update, no local cell_no_ai skill or callable tool was found, so its submission/billing adapter has not been integrated or tested. A yes branch must wait for that dependency; documentation alone is not a working service connection.
