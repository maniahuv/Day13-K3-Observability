# Alert và Runbook

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: High user-facing latency
- Severity: page
- SLI/SLO liên quan: latency P95 <= 3000 ms
- Điều kiện và thời gian duy trì: latency P95 > 3000 ms trong 5 phút
- Ảnh hưởng tới người dùng: phản hồi chat chậm, người dùng có thể retry hoặc bỏ phiên.
- Ba bước kiểm tra đầu tiên: mở dashboard latency; chọn trace chậm trong cùng khoảng thời gian; tìm log cùng correlation ID.
- Mitigation tạm thời: tắt incident đang bật, giảm concurrency hoặc rollback prompt/logic gây tăng latency.
- Owner: on-call-support

## Alert 2

- Tên: Elevated chat error rate
- Severity: page
- SLI/SLO liên quan: error rate <= 2%
- Điều kiện và thời gian duy trì: error_rate_pct > 2 trong 5 phút
- Ảnh hưởng tới người dùng: request chat lỗi hoặc không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên: xem panel error breakdown; mở log `request_failed`; đối chiếu trace và correlation ID của request lỗi.
- Mitigation tạm thời: rollback thay đổi gần nhất, disable incident/tool lỗi, hoặc chuyển sang fallback local nếu dependency ngoài lỗi.
- Owner: on-call-support

## Alert 3

- Tên: Quality proxy below SLO
- Severity: ticket
- SLI/SLO liên quan: quality_score_avg >= 0.75
- Điều kiện và thời gian duy trì: quality_score_avg < 0.75 trong 15 phút
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu tài liệu, format kém hoặc không bám câu hỏi.
- Ba bước kiểm tra đầu tiên: xem panel quality; mở các trace có điểm thấp; kiểm tra prompt_name, prompt_label và prompt_version.
- Mitigation tạm thời: rollback label `production` về prompt baseline hoặc tắt candidate prompt.
- Owner: ai-platform
