# Báo cáo Day 13 — AI Observability

## 1. Thông tin nhóm

- Tên nhóm: C61
- Repository URL: `https://github.com/maniahuv/Day13-K3-Observability-C61.git`
- Commit SHA cuối: f1c9da10ba94a2397c014a0d2201a017546a3e39
- Thành viên và vai trò: xem bảng ở mục 7.

## 2. Kết quả kỹ thuật

- `validate_logs.py`: 100/100; không phát hiện PII leak.
- `validate_dashboard.py`: hợp lệ, đủ 6/6 panel.
- Langfuse: trace thực tế đã được tạo với metadata prompt/version/label.
- Dashboard evidence: `submission/evidence/checkpoint2_dashboard.html`.

## 3. Logging và tracing

- Correlation ID và PII redaction: `submission/evidence/checkpoint1_log_excerpt.jsonl`.
- Kết quả validator logs: `submission/evidence/checkpoint1_validate_logs.txt`.
- Waterfall challenge: `submission/evidence/checkpoint3_trace_waterfall.png`.
- Span đáng chú ý: `rag_retrieve` kéo dài 2.50 giây trong trace challenge, trong khi span `run` là 2.65 giây. Điều này khoanh vùng phần lớn latency ở tầng retrieval.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Version 1: labels `baseline`, `production`; trace ID `44edd1b506c9ccb049a7070cfc581eee`; evidence `submission/evidence/checkpoint2_trace_baseline.png`.
- Version 2: label `candidate`; trace ID `49655327f4d694684555067bc3a962bc`; evidence `submission/evidence/checkpoint2_trace_candidate.png`.
- Rollout `production` sang v2: `submission/evidence/checkpoint2_production_v2.png`.
- Rollback `production` về v1: `submission/evidence/checkpoint2_rollback_v1.png`.
- Ảnh rollback cũng hiển thị đồng thời v1 (`baseline`, `production`) và v2 (`candidate`, `latest`), nên đáp ứng evidence danh sách versions.

## 5. Dashboard, SLO và alerts

- Dashboard validator: `submission/evidence/checkpoint2_validate_dashboard.txt`.
- Dashboard gồm latency, traffic, error, cost, tokens và quality; SLO/threshold đặt trong `config/dashboard.yaml` và `config/slo.yaml`.
- Alert rules và runbook: `config/alert_rules.yaml`, `docs/alerts.md`.

## 6. Điều tra challenge

Báo cáo điều tra đầy đủ: [`submission/evidence/checkpoint3_investigation.md`](evidence/checkpoint3_investigation.md).

- Challenge ID: `day13-k3-observability-v1` (cohort K3); `config/challenge.json` không bị sửa.
- Incident: `rag_slow`, ảnh hưởng feature `refund`.
- **Metrics (triệu chứng)**: workload chính thức 5 request/concurrency 5 cho P50 2651 ms, P95 2652 ms — vượt threshold chính thức 2000 ms ở cả 5/5 request; error rate 0% và quality average 0.86 vẫn đạt SLO, nên triệu chứng là latency degradation đơn thuần. Evidence: `submission/evidence/checkpoint3_challenge_run.txt` và `checkpoint3_metrics.json`.
- **Traces (khoanh vùng)**: trace `167b57a4d303e7c672261d8d77341976`, session `k3-challenge-s01`, user hash `026c7a407135`. Waterfall `run` (2.65 s) → generation → `rag_retrieve` (**2.50 s**), tức 94% latency nằm ở tầng retrieval. Evidence: `submission/evidence/checkpoint3_trace_waterfall.png`.
- **Logs (chứng minh)**: `req-77b41a40` — cùng `session_id` `k3-challenge-s01`, cùng `user_id_hash` `026c7a407135` và cùng câu hỏi với trace ở trên — ghi `response_sent.latency_ms: 2652`. Evidence: `submission/evidence/checkpoint3_log_excerpt.jsonl` (đủ 10 bản ghi của 5 request).
- **Root cause**: incident bật `STATE["rag_slow"]`; `retrieve()` trong `app/mock_rag.py` chạy `time.sleep(2.5)` trước khi trả tài liệu. Hằng số 2.5 s trong source khớp span `rag_retrieve` 2.50 s, khớp `latency_ms` 2652 ms và khớp P95 2652 ms.
- **Yếu tố khuếch đại**: `/chat` là `async def` nhưng gọi `agent.run()` đồng bộ, nên `time.sleep()` chặn event loop và 5 request chạy nối đuôi. Client đo 11.0–13.7 s trong khi server chỉ ghi 2651–2652 ms; phần chênh là queueing time không được `latency_ms` tính vào.
- **Fix action + xác minh**: disable `rag_slow` rồi chạy lại đúng workload chính thức → P95 2652 ms giảm còn **151 ms**, client-side 13.7 s còn 1.18 s, quality giữ nguyên 0.86. Evidence: `submission/evidence/checkpoint3_fix_verification.txt`. Với hệ thống thật: bỏ lời gọi chặn khỏi đường request, đặt timeout có giới hạn và fallback cho retrieval.
- **Preventive measures**: alert `High user-facing latency` (P95 > 3000 ms trong 5 phút) trong `config/alert_rules.yaml`; thêm SLI riêng cho latency tầng retrieval; bounded timeout + fallback cho dependency; chuyển lời gọi chặn ra khỏi `async def`; đo latency từ middleware để bao gồm queueing time.

Ghi chú về số liệu: nhóm chạy workload chính thức nhiều lần trên hai máy, P95 lần lượt là 5799 ms, 4279 ms và 2652 ms. Chênh lệch đến từ `resolve_prompt()` gọi `client.get_prompt()` (`fetch_timeout_seconds=2`) *bên trong* cửa sổ đo khi `tracing_enabled=true`. Bảng chỉ mục đầy đủ các run nằm ở mục 0 của `checkpoint3_investigation.md`; run C (P95 2652 ms) là bản tái lập sạch được trích dẫn ở trên.

### Câu trả lời phản biện

Nhóm khẳng định root cause bằng chuỗi evidence khép kín và kiểm chứng được: metrics chỉ ra latency vượt threshold nhưng error rate và quality vẫn đạt (loại bỏ giả thuyết dependency chết và prompt hỏng); trace khoanh vùng 94% latency vào span `rag_retrieve`; log cùng session và cùng user hash với trace ghi `latency_ms` khớp tổng span; source `app/mock_rag.py` cho thấy đúng hằng số 2.5 giây. Cuối cùng, tắt incident và chạy lại cùng workload đưa P95 về 151 ms — chứng minh đây là nguyên nhân duy nhất chứ không phải một trong nhiều nguyên nhân cộng dồn.

Nếu chỉ có metrics, nhóm chỉ biết "chậm" mà không biết chậm ở tầng nào, không phân biệt được RAG, LLM hay network. Nếu chỉ có trace, nhóm biết span nào chậm nhưng không biết sự cố ảnh hưởng bao nhiêu phần trăm request hay có vi phạm SLO không. Log là thứ nối hai lớp đó về một request cụ thể có định danh.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
|Vũ Hải Nam| CP1: logging, correlation ID, PII redaction | PR #1, PR #3 | Structured logging và redaction |
|Ong Xuân Sơn| CP2: dashboard, SLO, alerts, prompt/version evidence | PR #2 | Metrics, Langfuse prompt labels và rollback |
|Nguyễn Duy Dũng| CP3: incident investigation, RAG trace span, report | Commit b074e7a | Metrics → traces → logs để xác định root cause |

## 8. Checklist trước khi nộp

- [x] Public tests pass.
- [x] Logging và dashboard validators pass.
- [x] Prompt baseline/candidate traces, rollout và rollback evidence.
- [x] Challenge metrics, trace waterfall và correlated log evidence.
- [x] Transcript challenge chính thức và bằng chứng xác minh fix (before/after).
- [x] Evidence danh sách prompt versions, rollout và rollback.
- [x] Điền tên nhóm, ba thành viên/commit và final commit SHA.
- [x] Commit toàn bộ thay đổi hợp lệ; không commit `.env`, `venv/` hoặc log chứa PII.
