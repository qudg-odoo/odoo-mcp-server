import os

import pytest

from odoo_mcp.odoo_client import OdooClient

pytestmark = pytest.mark.integration

ALLOWED = ["crm.lead", "res.partner"]


def _client():
    for k in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_API_KEY"):
        if not os.environ.get(k):
            pytest.skip(f"{k} non défini — test d'intégration ignoré")
    return OdooClient(os.environ["ODOO_URL"], os.environ["ODOO_DB"],
                      os.environ["ODOO_USERNAME"], os.environ["ODOO_API_KEY"],
                      allowed_models=ALLOWED)


def test_authentication_and_count():
    client = _client()
    count = client.count("res.partner", domain=[])
    assert isinstance(count, int)


def test_create_read_delete_lead_roundtrip():
    client = _client()
    lead_id = client.create("crm.lead", {"name": "MCP TEST — à supprimer"})
    try:
        rows = client.read("crm.lead", [lead_id], fields=["name"])
        assert rows[0]["name"] == "MCP TEST — à supprimer"
    finally:
        client.unlink("crm.lead", [lead_id])
    assert client.count("crm.lead", domain=[["id", "=", lead_id]]) == 0
