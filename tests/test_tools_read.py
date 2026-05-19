import odoo_mcp.runtime as runtime
from odoo_mcp.runtime import Deps
from odoo_mcp.tools.read import search, inspect_model, count


class FakeClient:
    def __init__(self, **methods):
        self._m = methods
    def __getattr__(self, name):
        return self._m[name]


def test_search_returns_records(monkeypatch):
    client = FakeClient(search=lambda model, **kw: [{"id": 1, "name": "ACME"}])
    runtime.deps = Deps(config=object(), odoo=client)
    result = search("crm.lead", domain=[], fields=["name"])
    assert result == [{"id": 1, "name": "ACME"}]


def test_inspect_model_returns_fields():
    client = FakeClient(fields=lambda model: {"name": {"type": "char", "required": True}})
    runtime.deps = Deps(config=object(), odoo=client)
    result = inspect_model("crm.lead")
    assert result["name"]["type"] == "char"


def test_count_returns_int():
    client = FakeClient(count=lambda model, domain=None: 7)
    runtime.deps = Deps(config=object(), odoo=client)
    assert count("crm.lead", domain=[]) == 7
