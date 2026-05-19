import odoo_mcp.runtime as runtime
from odoo_mcp.runtime import Deps
from odoo_mcp.config import Config
from odoo_mcp.tools.write import create, delete


def _config(tmp_path):
    return Config(
        odoo_url="https://x", odoo_db="db", odoo_username="u", odoo_api_key="k",
        access_secret="s", allowed_models=["crm.lead"], allowed_actions={},
        mass_op_cap=3, audit_log_path=str(tmp_path / "audit.log"),
        skills_dir=str(tmp_path),
    )


class FakeClient:
    def __init__(self, **methods):
        self._m = methods
    def __getattr__(self, name):
        return self._m[name]


def test_create_blocked_by_existing_duplicate(tmp_path):
    client = FakeClient(
        search=lambda model, **kw: [{"id": 9, "name": "ACME"}],
        create=lambda model, values: 1 / 0,  # ne doit pas être appelé
    )
    runtime.deps = Deps(config=_config(tmp_path), odoo=client)
    result = create("crm.lead", {"email_from": "a@acme.com", "name": "ACME"})
    assert result["status"] == "doublon_possible"
    assert result["matches"] == [{"id": 9, "name": "ACME"}]


def test_create_forced_ignores_duplicate(tmp_path):
    client = FakeClient(
        search=lambda model, **kw: [{"id": 9, "name": "ACME"}],
        create=lambda model, values: 55,
    )
    runtime.deps = Deps(config=_config(tmp_path), odoo=client)
    result = create("crm.lead", {"email_from": "a@acme.com", "name": "ACME"},
                    force_duplicate=True)
    assert result["status"] == "created"
    assert result["ids"] == [55]


def test_delete_requires_confirmation_then_executes(tmp_path):
    deleted = []
    client = FakeClient(unlink=lambda model, ids: deleted.append(list(ids)) or True)
    runtime.deps = Deps(config=_config(tmp_path), odoo=client)

    first = delete("crm.lead", [1, 2])
    assert first["status"] == "confirmation_requise"
    assert deleted == []

    second = delete("crm.lead", [1, 2], confirmation_token=first["confirmation_token"])
    assert second["status"] == "deleted"
    assert deleted == [[1, 2]]


def test_delete_blocked_above_cap(tmp_path):
    client = FakeClient(unlink=lambda model, ids: True)
    runtime.deps = Deps(config=_config(tmp_path), odoo=client)
    result = delete("crm.lead", [1, 2, 3, 4])  # cap = 3
    assert result["status"] == "refuse"
    assert "plafond" in result["message"].lower()
