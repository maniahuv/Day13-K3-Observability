# Báo cáo Day 13 — AI Observability

## 1. Thông tin nhóm

- Tên nhóm: C61
- Repository URL: `https://github.com/maniahuv/Day13-K3-Observability.git`
- Commit SHA cuối: _Điền sau khi commit toàn bộ evidence_
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

- Challenge ID: `day13-k3-observability-v1`.
- Incident: `rag_slow`, ảnh hưởng feature `refund`.
- Triệu chứng metrics: batch challenge 5 request có P50 2651 ms và P95 5799 ms, vượt threshold chính thức 2000 ms; error rate 0%, quality average 0.86. Evidence: `submission/evidence/checkpoint3_metrics.png`.
- Trace liên quan: `167b57a4d303e7c672261d8d77341976`; waterfall cho thấy `run` → `rag_retrieve` → generation, trong đó `rag_retrieve` kéo dài 2.50 giây. Evidence: `submission/evidence/checkpoint3_trace_waterfall.png`.
- Log/correlation ID liên quan: `req-bb644f78`, có `response_sent.latency_ms: 2651`; evidence: `submission/evidence/checkpoint3_latest_log_excerpt.jsonl`.
- Root cause: incident chính thức bật `STATE["rag_slow"]`; `app/mock_rag.py` thực thi `time.sleep(2.5)` trong `retrieve()` trước khi trả tài liệu. Thời gian 2.5 giây khớp với span retrieval trên trace và latency trong log.
- Fix action: disable `rag_slow` sau khi thu evidence; thay retrieval đồng bộ bằng call có timeout/fallback trong môi trường production.
- Preventive measure: theo dõi latency span retrieval riêng, alert khi request/retrieval P95 vượt SLO và giới hạn thời gian chờ dependency.

### Câu trả lời phản biện

Nhóm khẳng định root cause bằng chuỗi evidence đồng nhất: metrics chỉ ra latency vượt threshold, trace cùng thời điểm khoanh vùng span `rag_retrieve` 2.50 giây, log cùng correlation ID ghi latency cao, và source incident chứng minh `rag_slow` chủ động thêm `time.sleep(2.5)`. Nếu chỉ có metrics, nhóm chỉ biết latency tăng nhưng không xác định được request, correlation ID hay tầng gây chậm; do đó không thể phân biệt RAG, LLM hoặc network để chọn fix có căn cứ.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
|Vũ Hải Nam| CP1: logging, correlation ID, PII redaction | _Cần điền_ | Structured logging và redaction |
|Ong Xuân Sơn| CP2: dashboard, SLO, alerts, prompt/version evidence | _Cần điền_ | Metrics, Langfuse prompt labels và rollback |
|Nguyễn Duy Dũng| CP3: incident investigation, RAG trace span, report | _Cần điền_ | Metrics → traces → logs để xác định root cause |

## 8. Checklist trước khi nộp

- [x] Public tests pass.
- [x] Logging và dashboard validators pass.
- [x] Prompt baseline/candidate traces, rollout và rollback evidence.
- [x] Challenge metrics, trace waterfall và correlated log evidence.
- [x] Evidence danh sách prompt versions, rollout và rollback.
- [ ] Điền tên nhóm, ba thành viên/commit và final commit SHA.
- [ ] Commit toàn bộ thay đổi hợp lệ; không commit `.env`, `venv/` hoặc log chứa PII.
