"""Lightweight in-process telemetry for serverless API responses.

This deliberately avoids OpenTelemetry/protobuf imports because Vercel's local
Python runtime can crash on those packages under newer Python versions.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any


GLOBAL_TRACE_CONSOLE: list[dict[str, Any]] = []


class LocalTelemetryClient:
    endpoint_url = "local://aegis-codex"

    def create_trace(self, name: str, ticker: str) -> dict[str, Any]:
        trace = {
            "trace_id": str(uuid.uuid4()),
            "name": name,
            "ticker": ticker,
            "start_time": datetime.utcnow().isoformat() + "Z",
            "end_time": None,
            "duration_ms": 0,
            "status": "RUNNING",
            "spans": [],
        }
        GLOBAL_TRACE_CONSOLE.append(trace)
        return trace

    def start_span(self, trace_id: str, name: str, parent_span_id: str | None = None) -> dict[str, Any]:
        span = {
            "span_id": str(uuid.uuid4()),
            "parent_span_id": parent_span_id,
            "name": name,
            "start_time": time.time(),
            "end_time": None,
            "duration_ms": 0,
            "inputs": {},
            "outputs": {},
            "status": "RUNNING",
            "metadata": {},
        }
        for trace in GLOBAL_TRACE_CONSOLE:
            if trace["trace_id"] == trace_id:
                trace["spans"].append(span)
                break
        return span

    def complete_span(
        self,
        trace_id: str,
        span_id: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        status: str = "SUCCESS",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = time.time()
        for trace in GLOBAL_TRACE_CONSOLE:
            if trace["trace_id"] != trace_id:
                continue
            for span in trace["spans"]:
                if span["span_id"] == span_id:
                    span["end_time"] = now
                    span["duration_ms"] = round((now - float(span["start_time"])) * 1000, 2)
                    span["inputs"] = inputs
                    span["outputs"] = outputs
                    span["status"] = status
                    span["metadata"] = metadata or {}
                    return

    def complete_trace(self, trace_id: str, final_status: str = "COMPLETED") -> None:
        for trace in GLOBAL_TRACE_CONSOLE:
            if trace["trace_id"] != trace_id:
                continue
            trace["end_time"] = datetime.utcnow().isoformat() + "Z"
            trace["status"] = final_status
            spans = trace.get("spans") or []
            if spans:
                starts = [float(span["start_time"]) for span in spans if isinstance(span.get("start_time"), (int, float))]
                ends = [float(span.get("end_time") or time.time()) for span in spans]
                if starts and ends:
                    trace["duration_ms"] = round((max(ends) - min(starts)) * 1000, 2)
                for span in spans:
                    if isinstance(span.get("start_time"), (int, float)):
                        span["start_time"] = datetime.fromtimestamp(span["start_time"]).isoformat() + "Z"
                    if isinstance(span.get("end_time"), (int, float)):
                        span["end_time"] = datetime.fromtimestamp(span["end_time"]).isoformat() + "Z"
            return


arize_client = LocalTelemetryClient()
