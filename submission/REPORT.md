# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py` (baseline): 30/100
- Điểm `validate_logs.py` (checkpoint 1): 100/100 - `submission/evidence/checkpoint1_validate_logs.txt`
- Tổng số traces: 0 trong workspace hiện tại; Langfuse key đang trống, xem `submission/evidence/checkpoint2_langfuse_blocker.txt`
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: `submission/evidence/checkpoint2_dashboard.html`

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/checkpoint1_log_excerpt.jsonl`
- Evidence PII redaction: `submission/evidence/checkpoint1_log_excerpt.jsonl`
- Evidence trace waterfall: Chưa có do `tracing_enabled=false`; xem `submission/evidence/checkpoint2_langfuse_blocker.txt`
- Giải thích một span đáng chú ý: Chưa có trace thật để phân tích.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: Cần tạo trên Langfuse sau khi cấu hình key.
- Version/label candidate: Cần tạo trên Langfuse sau khi cấu hình key.
- Trace ID của mỗi version: Chưa có do `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` đang trống.
- Bằng chứng đổi label hoặc rollback: Chưa có; xem `submission/evidence/checkpoint2_langfuse_blocker.txt`.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ: 6/6 panel - `submission/evidence/checkpoint2_validate_dashboard.txt`
- Evidence dashboard: `submission/evidence/checkpoint2_dashboard.html`; summary ở `submission/evidence/checkpoint2_dashboard_summary.txt`
- SLO đã chọn và lý do: latency P95 <= 3000 ms, error rate <= 2%, daily cost <= 2.5 USD, quality avg >= 0.75; các ngưỡng này bám `config/dashboard.yaml` và `config/slo.yaml`.
- Alert rules và runbook: `config/alert_rules.yaml` và `docs/alerts.md`

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
