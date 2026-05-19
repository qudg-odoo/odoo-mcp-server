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


def test_read_methods_delegate_to_execute_kw(monkeypatch):
    client = make_client()
    seen = []
    monkeypatch.setattr(client, "execute_kw",
                        lambda m, meth, a, k=None: seen.append((m, meth, a, k)) or "OK")

    client.search("crm.lead", domain=[["name", "=", "x"]], fields=["name"],
                  limit=5, offset=2, order="id desc")
    client.read("crm.lead", [1, 2], fields=["name"])
    client.fields("crm.lead")
    client.count("crm.lead", domain=[])
    client.read_group("crm.lead", domain=[], fields=["expected_revenue:sum"],
                      groupby=["stage_id"])

    assert seen[0] == ("crm.lead", "search_read",
                       [[["name", "=", "x"]]],
                       {"fields": ["name"], "limit": 5, "offset": 2, "order": "id desc"})
    assert seen[1] == ("crm.lead", "read", [[1, 2]], {"fields": ["name"]})
    assert seen[2] == ("crm.lead", "fields_get", [], {"attributes": ["string", "type", "required", "selection", "relation"]})
    assert seen[3] == ("crm.lead", "search_count", [[]], None)
    assert seen[4] == ("crm.lead", "read_group", [[], ["expected_revenue:sum"], ["stage_id"]], None)
