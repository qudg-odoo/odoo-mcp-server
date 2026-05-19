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


def test_write_methods_delegate(monkeypatch):
    client = make_client()
    seen = []
    monkeypatch.setattr(client, "execute_kw",
                        lambda m, meth, a, k=None: seen.append((m, meth, a)) or 99)

    client.create("crm.lead", {"name": "ACME"})
    client.write("crm.lead", [5], {"name": "ACME2"})
    client.unlink("crm.lead", [5])

    assert seen[0] == ("crm.lead", "create", [{"name": "ACME"}])
    assert seen[1] == ("crm.lead", "write", [[5], {"name": "ACME2"}])
    assert seen[2] == ("crm.lead", "unlink", [[5]])


def test_action_message_email_delegate(monkeypatch):
    client = make_client()
    seen = []
    monkeypatch.setattr(client, "execute_kw",
                        lambda m, meth, a, k=None: seen.append((m, meth, a, k)) or True)

    client.call_action("sale.order", [3], "action_confirm")
    client.post_message("crm.lead", 8, "Note interne")
    client.send_email("crm.lead", 8, [12], "Bonjour", "<p>Corps</p>")

    assert seen[0] == ("sale.order", "action_confirm", [[3]], None)
    assert seen[1][:3] == ("crm.lead", "message_post", [[8]])
    assert seen[1][3]["body"] == "Note interne"
    assert seen[2][1] == "message_post"
    assert seen[2][3]["partner_ids"] == [12]
    assert seen[2][3]["subject"] == "Bonjour"
