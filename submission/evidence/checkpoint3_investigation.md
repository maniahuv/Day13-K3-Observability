# Checkpoint 3 — Official challenge investigation

## Reproduction

- Challenge: `day13-k3-observability-v1` (K3)
- Incident enabled: `rag_slow`
- Affected feature: `refund`
- Official workload: 5 challenge requests, concurrency 5
- Configured latency threshold: 2000 ms

## Metrics evidence

`GET /metrics` immediately after the workload returned:

```json
{"traffic":5,"latency_p50":2650.0,"latency_p95":2651.0,"latency_p99":2651.0,"avg_cost_usd":0.0024,"total_cost_usd":0.012,"tokens_in_total":162,"tokens_out_total":769,"error_breakdown":{},"quality_avg":0.86}
```

P95 was 2651 ms, 651 ms above the released 2000 ms threshold. No request errors occurred, and quality remained 0.86; therefore the symptom is isolated latency degradation.

## Logs evidence

`checkpoint3_log_excerpt.jsonl` links one official request and response through correlation ID `req-7aaa16b3`. The response has `latency_ms: 2650`, feature `refund`, and a hashed user ID; no raw PII is retained.

## Root cause and remediation

Root cause: the official incident enables `STATE["rag_slow"]`. In `app/mock_rag.py`, `retrieve()` checks this state and executes `time.sleep(2.5)` before retrieval. The fixed 2.5-second delay explains the approximately 2650 ms end-to-end latency seen in metrics and logs.

Immediate mitigation: disable the `rag_slow` incident after evidence capture.

Preventive measure: add latency instrumentation around retrieval, alert when retrieval or request P95 exceeds the SLO, and use a bounded retrieval timeout/fallback so a slow dependency does not block the request path.

## Trace evidence status

Trace evidence is not available in this workspace because `/health` reported `tracing_enabled=false` and no Langfuse credentials are configured. The metrics-to-logs conclusion above is reproducible; a real Langfuse trace ID must be added after credentials are supplied, rather than fabricated.
