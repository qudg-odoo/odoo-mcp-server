import json
from datetime import datetime, timezone
from pathlib import Path


def record(log_path, operation, model, record_ids, summary, status):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "model": model,
        "record_ids": list(record_ids or []),
        "summary": summary,
        "status": status,
    }
    with Path(log_path).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_recent(log_path, limit=50):
    path = Path(log_path)
    if not path.exists():
        return []
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [json.loads(l) for l in lines[-limit:]]
