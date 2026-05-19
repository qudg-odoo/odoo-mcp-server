import pytest
from odoo_mcp.odoo_client import OdooClient, OdooError


def make_client():
    return OdooClient("https://x.odoo.com/", "db", "user", "key",
                      allowed_models=["crm.lead", "res.partner"])


def test_check_model_rejects_unlisted():
    client = make_client()
    with pytest.raises(OdooError) as exc:
        client.execute_kw("res.users", "search", [[]])
    assert "non autorisé" in str(exc.value)


def test_execute_kw_uses_uid_and_returns_result(monkeypatch):
    client = make_client()
    monkeypatch.setattr(client, "_ensure_uid", lambda: 2)

    captured = {}

    class FakeModels:
        def execute_kw(self, db, uid, key, model, method, args, kwargs):
            captured.update(db=db, uid=uid, model=model, method=method)
            return [42]

    client._models = FakeModels()
    result = client.execute_kw("crm.lead", "search", [[]])
    assert result == [42]
    assert captured == {"db": "db", "uid": 2, "model": "crm.lead", "method": "search"}
