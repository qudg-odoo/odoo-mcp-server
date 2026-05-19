from odoo_mcp.audit import record, read_recent


def test_record_then_read(tmp_path):
    log = str(tmp_path / "audit.log")
    record(log, "create", "crm.lead", [7], "Lead 'ACME' créé", "success")
    record(log, "delete", "crm.lead", [7], "Lead supprimé", "success")
    entries = read_recent(log, limit=10)
    assert len(entries) == 2
    assert entries[0]["operation"] == "create"
    assert entries[0]["model"] == "crm.lead"
    assert entries[0]["record_ids"] == [7]
    assert entries[1]["operation"] == "delete"
    assert "timestamp" in entries[0]


def test_read_recent_missing_file_returns_empty(tmp_path):
    assert read_recent(str(tmp_path / "absent.log")) == []


def test_read_recent_respects_limit(tmp_path):
    log = str(tmp_path / "audit.log")
    for i in range(5):
        record(log, "create", "res.partner", [i], f"n{i}", "success")
    entries = read_recent(log, limit=2)
    assert len(entries) == 2
    assert entries[-1]["record_ids"] == [4]
