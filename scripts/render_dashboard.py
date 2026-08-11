from __future__ import annotations

import argparse
import html
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio


def parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * pct / 100
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - pos) + ordered[high] * (pos - low)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def minute_key(record: dict[str, Any]) -> str:
    ts = parse_ts(str(record.get("ts", "")))
    return ts.strftime("%H:%M") if ts else "unknown"


def status_class(value: float, operator: str, threshold: float) -> str:
    ok = value <= threshold if operator == "lte" else value >= threshold
    return "ok" if ok else "bad"


def render_dashboard(records: list[dict[str, Any]], config: dict[str, Any]) -> str:
    dashboard = config["dashboard"]
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    requests = [r for r in records if r.get("event") == "request_received"]
    responses = [r for r in records if r.get("event") == "response_sent"]
    errors = [r for r in records if r.get("event") == "request_failed"]
    latencies = [float(r.get("latency_ms", 0)) for r in responses]
    qualities = [float(r.get("quality_score", 0)) for r in responses]
    total_cost = sum(float(r.get("cost_usd", 0)) for r in responses)
    tokens_in = sum(int(r.get("tokens_in", 0)) for r in responses)
    tokens_out = sum(int(r.get("tokens_out", 0)) for r in responses)
    error_rate = (len(errors) / len(requests) * 100) if requests else 0.0
    traffic_by_min = Counter(minute_key(r) for r in requests)
    cost_by_min: dict[str, float] = defaultdict(float)
    for record in responses:
        cost_by_min[minute_key(record)] += float(record.get("cost_usd", 0))
    error_breakdown = Counter(str(r.get("error_type", "unknown")) for r in errors)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    quality_avg = statistics.mean(qualities) if qualities else 0.0
    traffic_rate = max(traffic_by_min.values(), default=0)

    latency_cfg = panels["latency"]["threshold"]
    traffic_cfg = panels["traffic"]["threshold"]
    errors_cfg = panels["errors"]["threshold"]
    cost_cfg = panels["cost"]["threshold"]
    tokens_cfg = panels["tokens"]["threshold"]
    quality_cfg = panels["quality"]["threshold"]
    total_tokens = tokens_in + tokens_out

    def row(label: str, value: str, threshold: str, state: str) -> str:
        return (
            f"<div class='metric {state}'><span>{html.escape(label)}</span>"
            f"<strong>{html.escape(value)}</strong><em>{html.escape(threshold)}</em></div>"
        )

    traffic_items = "".join(
        f"<li><span>{html.escape(k)}</span><b>{v}</b></li>"
        for k, v in sorted(traffic_by_min.items())
    ) or "<li><span>No traffic</span><b>0</b></li>"
    cost_items = "".join(
        f"<li><span>{html.escape(k)}</span><b>${v:.4f}</b></li>"
        for k, v in sorted(cost_by_min.items())
    ) or "<li><span>No cost</span><b>$0.0000</b></li>"
    error_items = "".join(
        f"<li><span>{html.escape(k)}</span><b>{v}</b></li>"
        for k, v in sorted(error_breakdown.items())
    ) or "<li><span>No errors</span><b>0</b></li>"

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cards = [
        (
            "Latency percentiles",
            row("P50", f"{p50:.0f} ms", "", "neutral")
            + row(
                "P95",
                f"{p95:.0f} ms",
                f"SLO <= {latency_cfg['value']} ms",
                status_class(p95, latency_cfg["operator"], float(latency_cfg["value"])),
            )
            + row("P99", f"{p99:.0f} ms", "", "neutral"),
        ),
        (
            "Request traffic",
            row(
                "Peak requests/min",
                str(traffic_rate),
                f"SLO >= {traffic_cfg['value']} req/min",
                status_class(traffic_rate, traffic_cfg["operator"], float(traffic_cfg["value"])),
            )
            + f"<ul>{traffic_items}</ul>",
        ),
        (
            "Error rate and breakdown",
            row(
                "Error rate",
                f"{error_rate:.2f}%",
                f"SLO <= {errors_cfg['value']}%",
                status_class(error_rate, errors_cfg["operator"], float(errors_cfg["value"])),
            )
            + f"<ul>{error_items}</ul>",
        ),
        (
            "Cost over time",
            row(
                "Total cost",
                f"${total_cost:.4f}",
                f"SLO <= ${cost_cfg['value']}",
                status_class(total_cost, cost_cfg["operator"], float(cost_cfg["value"])),
            )
            + f"<ul>{cost_items}</ul>",
        ),
        (
            "Input and output tokens",
            row(
                "Total tokens",
                str(total_tokens),
                f"SLO <= {tokens_cfg['value']} tokens",
                status_class(total_tokens, tokens_cfg["operator"], float(tokens_cfg["value"])),
            )
            + row("Input tokens", str(tokens_in), "", "neutral")
            + row("Output tokens", str(tokens_out), "", "neutral"),
        ),
        (
            "Quality proxy",
            row(
                "Average quality",
                f"{quality_avg:.2f}",
                f"SLO >= {quality_cfg['value']}",
                status_class(quality_avg, quality_cfg["operator"], float(quality_cfg["value"])),
            ),
        ),
    ]
    card_html = "\n".join(
        f"<section class='panel'><h2>{html.escape(title)}</h2>{body}</section>"
        for title, body in cards
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(dashboard['title'])}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: #f5f7fb;
      color: #1f2937;
    }}
    body {{ margin: 0; padding: 28px; }}
    header {{ display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 20px; }}
    h1 {{ font-size: 28px; margin: 0 0 6px; }}
    p {{ margin: 0; color: #526071; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .panel {{ background: #ffffff; border: 1px solid #d9e0ea; border-radius: 8px; padding: 16px; }}
    h2 {{ font-size: 16px; margin: 0 0 12px; }}
    .metric {{ border-left: 4px solid #8da2bd; padding: 8px 10px; margin: 8px 0; background: #f8fafc; }}
    .metric span {{ display: block; color: #526071; font-size: 12px; }}
    .metric strong {{ display: block; font-size: 24px; margin: 2px 0; }}
    .metric em {{ display: block; color: #667085; font-style: normal; font-size: 12px; }}
    .ok {{ border-left-color: #16815d; }}
    .bad {{ border-left-color: #c0392b; }}
    ul {{ list-style: none; padding: 0; margin: 10px 0 0; border-top: 1px solid #edf1f7; }}
    li {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #edf1f7; }}
    footer {{ margin-top: 18px; color: #667085; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>{html.escape(dashboard['title'])}</h1>
      <p>Source: data/logs.jsonl | Time range: {dashboard['time_range_minutes']} minutes | Refresh: {dashboard['refresh_seconds']} seconds</p>
    </div>
    <p>Generated: {html.escape(generated_at)}</p>
  </header>
  <main class="grid">
    {card_html}
  </main>
  <footer>Each panel shows the threshold from config/dashboard.yaml.</footer>
</body>
</html>
"""


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Render a static dashboard evidence file.")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "dashboard.yaml")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "submission" / "evidence" / "checkpoint2_dashboard.html",
    )
    args = parser.parse_args()

    records = load_jsonl(args.logs)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_dashboard(records, config), encoding="utf-8")
    print(f"Rendered dashboard evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
