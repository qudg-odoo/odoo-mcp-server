import pytest
from odoo_mcp.config import Config


def _write(tmp_path, toml_text):
    p = tmp_path / "config.toml"
    p.write_text(toml_text, encoding="utf-8")
    return str(p)


def test_load_reads_env_and_toml(tmp_path, monkeypatch):
    for k, v in {
        "ODOO_URL": "https://magin.odoo.com/",
        "ODOO_DB": "magin",
        "ODOO_USERNAME": "team@magin.com",
        "ODOO_API_KEY": "key123",
        "MCP_ACCESS_SECRET": "secret123",
    }.items():
        monkeypatch.setenv(k, v)
    toml = _write(tmp_path, """
[models]
allowed = ["crm.lead", "res.partner"]
[actions]
"sale.order" = ["action_confirm"]
[guardrails]
mass_op_cap = 25
""")
    cfg = Config.load(toml_path=toml, env_path=str(tmp_path / "nonexistent.env"))
    assert cfg.odoo_url == "https://magin.odoo.com"  # slash final retiré
    assert cfg.allowed_models == ["crm.lead", "res.partner"]
    assert cfg.allowed_actions == {"sale.order": ["action_confirm"]}
    assert cfg.mass_op_cap == 25


def test_load_fails_on_missing_secret(tmp_path, monkeypatch):
    for k in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_API_KEY", "MCP_ACCESS_SECRET"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ODOO_URL", "https://x")
    with pytest.raises(RuntimeError) as exc:
        Config.load(toml_path=str(tmp_path / "none.toml"), env_path=str(tmp_path / "none.env"))
    assert "ODOO_DB" in str(exc.value)
