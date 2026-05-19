import base64

import odoo_mcp.runtime as runtime
from odoo_mcp.runtime import Deps
from odoo_mcp.config import Config
from odoo_mcp.tools.actions import run_action, send_email, list_skills_tool, get_skill_tool


def _config(tmp_path, actions=None):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(exist_ok=True)
    (skills_dir / "demo.md").write_text(
        "---\nname: demo\ndescription: Démo\n---\nCorps", encoding="utf-8")
    return Config(
        odoo_url="https://x", odoo_db="db", odoo_username="u", odoo_api_key="k",
        access_secret="s", allowed_models=["sale.order", "crm.lead"],
        allowed_actions=actions or {"sale.order": ["action_confirm"]},
        mass_op_cap=50, audit_log_path=str(tmp_path / "audit.log"),
        skills_dir=str(skills_dir),
    )


class FakeClient:
    def __init__(self, **methods):
        self._m = methods
    def __getattr__(self, name):
        return self._m[name]


def test_run_action_blocked_when_not_whitelisted(tmp_path):
    client = FakeClient(call_action=lambda *a: 1 / 0)
    runtime.deps = Deps(config=_config(tmp_path), odoo=client)
    result = run_action("sale.order", [3], "action_cancel")
    assert result["status"] == "refuse"
    assert "non autoris" in result["message"].lower()


def test_run_action_executes_whitelisted(tmp_path):
    called = []
    client = FakeClient(call_action=lambda m, ids, act: called.append((m, ids, act)) or True)
    runtime.deps = Deps(config=_config(tmp_path), odoo=client)
    result = run_action("sale.order", [3], "action_confirm")
    assert result["status"] == "executed"
    assert called == [("sale.order", [3], "action_confirm")]


def test_send_email_requires_confirmation(tmp_path):
    sent = []
    client = FakeClient(send_email=lambda *a: sent.append(a) or True)
    runtime.deps = Deps(config=_config(tmp_path), odoo=client)

    first = send_email("crm.lead", 8, [12], "Sujet", "<p>Corps</p>")
    assert first["status"] == "confirmation_requise"
    assert sent == []

    second = send_email("crm.lead", 8, [12], "Sujet", "<p>Corps</p>",
                         confirmation_token=first["confirmation_token"])
    assert second["status"] == "sent"
    assert len(sent) == 1


def test_skill_tools(tmp_path):
    runtime.deps = Deps(config=_config(tmp_path), odoo=FakeClient())
    skills = list_skills_tool()
    assert any(s["name"] == "demo" for s in skills)
    assert "Corps" in get_skill_tool("demo")
