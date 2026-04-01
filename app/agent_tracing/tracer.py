from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from app.utils.helpers import now_iso


@dataclass
class TraceSession:
    trace_id: str
    operation: str
    log_path: Path
    started_at: float = field(default_factory=perf_counter)
    events: list[dict] = field(default_factory=list)

    def add_event(self, name: str, payload: dict | None = None) -> None:
        self.events.append(
            {
                "name": name,
                "payload": payload or {},
                "timestamp": now_iso(),
            }
        )

    def finish(self, payload: dict | None = None) -> str:
        # Write one JSONL record per completed operation so traces stay append
        # only and easy to inspect with standard tools.
        record = {
            "trace_id": self.trace_id,
            "operation": self.operation,
            "duration_ms": round((perf_counter() - self.started_at) * 1000, 2),
            "events": self.events,
            "result": payload or {},
            "timestamp": now_iso(),
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        return self.trace_id


class AgentTracer:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path

    def start_trace(self, operation: str) -> TraceSession:
        # A trace session is just a lightweight in-memory collector until finish()
        # flushes it to disk.
        return TraceSession(trace_id=uuid4().hex, operation=operation, log_path=self.log_path)
