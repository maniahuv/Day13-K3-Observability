# Checkpoint 3 — Điều tra challenge chính thức

- Challenge: `day13-k3-observability-v1` (cohort K3)
- Incident được release: `rag_slow`
- Feature bị ảnh hưởng: `refund`
- Workload chính thức: 5 request, concurrency 5
- Threshold latency được release: 2000 ms
- `config/challenge.json` không bị sửa (xem `git log -- config/challenge.json`).

## 0. Chỉ mục các lần chạy

Nhóm chạy workload chính thức nhiều lần trên hai máy. Các con số latency khác nhau giữa
các lần chạy là có thật và được giải thích ở mục 4, không phải số liệu mâu thuẫn.

| Run | Máy / cấu hình | Evidence | latency_p50 | latency_p95 |
|---|---|---|---|---|
| A | Host có Langfuse key, `tracing_enabled=true` | `checkpoint3_metrics.png` | 2651 ms | 5799 ms |
| B | Host có Langfuse key, `tracing_enabled=true` | `checkpoint3_metrics_run_b.json` | 2651 ms | 4279 ms |
| C | Máy này, `tracing_enabled=false` — **lần chạy chuẩn để tái lập** | `checkpoint3_challenge_run.txt`, `checkpoint3_metrics.json`, `checkpoint3_log_excerpt.jsonl` | 2651 ms | 2652 ms |

- `checkpoint3_trace_waterfall.png` được chụp trên host có Langfuse key (run A hoặc B — nhóm
  không khẳng định được chính xác run nào, nên không gán). Điều kiểm chứng được là trace này
  thuộc đúng challenge chính thức: session `k3-challenge-s01`, câu hỏi trong `config/challenge.json`,
  `prompt_source` = `langfuse`.
- `checkpoint3_log_excerpt_earlier_runs.jsonl` giữ nguyên hai cặp log thu được trên host đó
  (`req-7aaa16b3` / `k3-challenge-s03` và `req-bb644f78` / `k3-challenge-s05`, latency 2650 và
  2651 ms). Chúng xác nhận cùng một triệu chứng nhưng không thuộc run C.

Run C là bản tái lập sạch: không có network call của Langfuse nằm trong cửa sổ đo, nên
latency phản ánh đúng một mình chi phí của incident. Các trích dẫn số bên dưới lấy từ run C
trừ khi ghi rõ khác.

## 1. Triệu chứng — từ Metrics

`GET /metrics` ngay sau workload chính thức (run C, `checkpoint3_challenge_run.txt`):

```json
{"traffic":5,"latency_p50":2651.0,"latency_p95":2652.0,"latency_p99":2652.0,
 "avg_cost_usd":0.0019,"total_cost_usd":0.0093,"tokens_in_total":162,
 "tokens_out_total":585,"error_breakdown":{},"quality_avg":0.86}
```

Đọc ra ba điều:

- **Latency vi phạm SLO**: P95 = 2652 ms, vượt threshold 2000 ms là 652 ms. Cả 5/5 request
  đều vượt (log cho thấy 2651–2652 ms mỗi request), nên đây là lỗi hệ thống, không phải outlier.
- **Không phải sự cố lỗi**: `error_breakdown` rỗng, error rate 0%. Loại bỏ giả thuyết
  dependency chết hoặc exception.
- **Không phải sự cố chất lượng hay chi phí**: `quality_avg` 0.86 (SLO ≥ 0.75) và
  `total_cost_usd` 0.0093 đều bình thường. Loại bỏ giả thuyết `cost_spike` và prompt hỏng.

Kết luận triệu chứng: **latency degradation đơn thuần, ảnh hưởng 100% request của feature `refund`**.

Một tín hiệu thứ hai từ client: `load_test.py` đo 11.0–13.7 giây mỗi request, trong khi server
chỉ ghi 2651–2652 ms. Chênh lệch này là thời gian xếp hàng, được phân tích ở mục 4.

## 2. Khoanh vùng — từ Traces

Metrics chỉ nói "chậm", không nói chậm ở đâu. Trace waterfall
(`checkpoint3_trace_waterfall.png`, thu trên host có Langfuse key) khoanh vùng được:

- Trace ID: `167b57a4d303e7c672261d8d77341976`
- Session: `k3-challenge-s01`, User ID (đã hash): `026c7a407135`
- Cây span: `run` (2.65 s) → `run` generation (2.65 s) → **`rag_retrieve` (2.50 s)**
- Metadata: `query_preview` = "What is your refund policy?", `prompt_name` = `day13-chat`,
  `prompt_version` = 2, `prompt_label` = `candidate`, `prompt_source` = `langfuse`, `doc_count` = 1

Span `rag_retrieve` chiếm 2.50 s trên tổng 2.65 s, tức **94% latency nằm ở tầng retrieval**.
Phần generation và phần còn lại chỉ chiếm ~150 ms — đúng bằng latency của hệ thống khi khỏe mạnh
(xem mục 5). Đến đây đã loại được LLM, prompt và network egress ra khỏi danh sách nghi vấn.

## 3. Chứng minh — từ Logs

Log của cùng session `k3-challenge-s01` và cùng `user_id_hash` `026c7a407135` với trace ở mục 2
(`checkpoint3_log_excerpt.jsonl`, run C):

```json
{"event":"request_received","correlation_id":"req-77b41a40","session_id":"k3-challenge-s01",
 "user_id_hash":"026c7a407135","feature":"refund","model":"fake-gpt","env":"dev",
 "payload":{"message_preview":"What is your refund policy?"},"ts":"2026-08-11T15:19:28.680470Z"}

{"event":"response_sent","correlation_id":"req-77b41a40","session_id":"k3-challenge-s01",
 "user_id_hash":"026c7a407135","feature":"refund","latency_ms":2652,"tokens_in":29,
 "tokens_out":149,"cost_usd":0.002322,"quality_score":0.9,"ts":"2026-08-11T15:19:31.732265Z"}
```

Ba điểm khớp giữa log và trace: cùng `session_id`, cùng `user_id_hash`, cùng câu hỏi
("What is your refund policy?"). `latency_ms` 2652 ms khớp với tổng thời lượng span `run` 2.65 s,
và phần chênh so với span `rag_retrieve` 2.50 s chính là ~150 ms còn lại của generation.

Lưu ý minh bạch: trace ở mục 2 thu trên host có Langfuse key, còn log ở đây thuộc run C, vì
máy chạy run C không có Langfuse key nên không sinh trace. Hai bản ghi mô tả **cùng một request chính thức**
(`k3-u01` / `k3-challenge-s01`) của cùng một challenge, nối bằng `session_id` và `user_id_hash`,
chứ không nối bằng `correlation_id` — nhóm không gán ghép correlation ID giữa hai lần chạy.

Cả 5 correlation ID của run C đều cho thấy cùng một hình ảnh:

| session | correlation_id | latency_ms |
|---|---|---|
| k3-challenge-s01 | `req-77b41a40` | 2652 |
| k3-challenge-s02 | `req-328efbc9` | 2651 |
| k3-challenge-s03 | `req-1ba19b73` | 2651 |
| k3-challenge-s04 | `req-091a833c` | 2651 |
| k3-challenge-s05 | `req-8ee43c69` | 2651 |

Log không chứa PII nguyên văn: `user_id` đã được hash, message chỉ lưu preview đã qua `scrub_text`.

## 4. Root cause

Incident chính thức bật `STATE["rag_slow"]`. Trong `app/mock_rag.py`, hàm `retrieve()` kiểm tra
state này và chạy `time.sleep(2.5)` trước khi trả tài liệu:

```python
@observe(name="rag_retrieve", as_type="tool", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
```

Chuỗi bằng chứng khép kín: hằng số 2.5 giây trong source = 2.50 s của span `rag_retrieve` trên
trace = phần lớn 2652 ms trong log = P95 2652 ms trên metrics.

**Yếu tố khuếch đại (phát hiện thêm khi chạy concurrency 5):** `time.sleep()` là lời gọi chặn,
và `/chat` trong `app/main.py` là `async def` gọi thẳng `agent.run()` đồng bộ. Vì vậy mỗi request
chặn event loop 2.5 giây và 5 request chạy nối đuôi nhau thay vì song song — log run C cho thấy
các request bắt đầu cách nhau đúng ~2.65 s. Đây là lý do client đo 11.0–13.7 s trong khi server
chỉ ghi 2651–2652 ms: phần chênh là **thời gian xếp hàng, không được tính vào `latency_ms`**.

**Vì sao P95 khác nhau giữa các run:** ở run A và B (`tracing_enabled=true`), `resolve_prompt()`
được gọi *bên trong* cửa sổ đo của `agent.run()` và thực hiện `client.get_prompt(...)` với
`fetch_timeout_seconds=2`, `cache_ttl_seconds=60`. Request đầu tiên sau khi cache hết hạn phải
chờ network fetch, nên latency của nó cộng thêm 1.6–3.1 s, đẩy P95 lên 4279 ms và 5799 ms.
Run C không có key nên dùng prompt local, không có network call trong cửa sổ đo, và P95 rơi về
đúng 2652 ms. Điều này không đổi kết luận root cause — mọi run đều vượt threshold 2000 ms — nhưng
nó chỉ ra một vấn đề đo lường thứ hai đáng sửa (xem mục 6).

## 5. Fix action và xác minh

Mitigation tức thời: tắt incident sau khi đã thu đủ evidence.

```bash
python scripts/inject_incident.py --disable
python scripts/load_test.py --challenge --concurrency 5
```

Kết quả sau khi tắt, cùng workload chính thức (`checkpoint3_fix_verification.txt`, server đã
restart để counter `/metrics` về 0):

```json
{"traffic":5,"latency_p50":150.0,"latency_p95":151.0,"latency_p99":151.0,
 "error_breakdown":{},"quality_avg":0.86}
```

| Chỉ số | Khi có incident | Sau khi fix | SLO |
|---|---|---|---|
| latency_p50 | 2651 ms | 150 ms | — |
| latency_p95 | 2652 ms | 151 ms | ≤ 2000 ms (challenge) / ≤ 3000 ms (`config/slo.yaml`) |
| Client-side latency | 11.0–13.7 s | 1.17–1.18 s | — |
| error rate | 0% | 0% | ≤ 2% |
| quality_avg | 0.86 | 0.86 | ≥ 0.75 |

P95 trở lại dưới threshold và quality không đổi, xác nhận `rag_slow` là nguyên nhân duy nhất
chứ không phải một trong nhiều nguyên nhân cộng dồn.

Với hệ thống thật, fix tương đương là: bỏ lời gọi chặn trong đường request, đặt timeout có
giới hạn cho retrieval và trả fallback khi vector store chậm, thay vì để request chờ vô điều kiện.

## 6. Preventive measures

1. **Alert trên triệu chứng đã có**: `High user-facing latency` trong `config/alert_rules.yaml`
   (P95 > 3000 ms trong 5 phút, severity page, runbook `docs/alerts.md#alert-1`) sẽ bắt được
   sự cố này mà không cần biết trước nguyên nhân là RAG.
2. **Thêm SLI cho riêng tầng retrieval**: hiện chỉ có latency đầu-cuối. Một metric
   `rag_retrieve_latency_p95` sẽ khoanh vùng ngay ở bước metrics, không phải chờ mở trace.
3. **Bounded timeout + fallback cho dependency retrieval**, để một dependency chậm làm giảm
   chất lượng câu trả lời thay vì kéo sập latency toàn hệ thống.
4. **Không đặt lời gọi chặn trong `async def`**: chuyển `agent.run()` sang threadpool
   (`def` endpoint hoặc `run_in_threadpool`) để một request chậm không xếp hàng cả các request khác.
   Nếu không sửa, mọi sự cố latency sẽ bị khuếch đại theo concurrency như quan sát ở mục 4.
5. **Đo và cảnh báo cả queueing time**: `latency_ms` hiện chỉ tính từ khi `agent.run()` bắt đầu,
   nên bỏ sót toàn bộ thời gian chờ. Đo từ lúc middleware nhận request sẽ khiến metrics phản ánh
   đúng thứ người dùng cảm nhận (13.7 s chứ không phải 2.65 s).
6. **Đưa network call của prompt fetch ra ngoài cửa sổ đo** hoặc tách thành span riêng, để
   latency của model không bị lẫn latency của prompt management (nguyên nhân P95 lệch ở run A/B).
