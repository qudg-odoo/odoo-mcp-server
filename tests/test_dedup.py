from odoo_mcp.dedup import find_duplicates
from tests.conftest import FakeOdoo


def test_find_duplicates_by_email_and_phone():
    odoo = FakeOdoo(responses={
        ("res.partner", "search_read"): [{"id": 4, "name": "ACME", "email": "a@acme.com"}],
    })
    client_like = type("C", (), {"search": lambda self, m, domain=None, fields=None, **k:
                                 odoo(m, "search_read", [domain], {"fields": fields})})()
    matches = find_duplicates(client_like, "res.partner",
                              {"email": "a@acme.com", "phone": "0612"})
    assert matches == [{"id": 4, "name": "ACME", "email": "a@acme.com"}]


def test_find_duplicates_none_when_no_identifiers():
    odoo = FakeOdoo()
    client_like = type("C", (), {"search": lambda self, *a, **k: []})()
    assert find_duplicates(client_like, "res.partner", {"comment": "x"}) == []


def test_find_duplicates_skips_unsupported_model():
    client_like = type("C", (), {"search": lambda self, *a, **k: [{"id": 1}]})()
    assert find_duplicates(client_like, "sale.order", {"email": "a@acme.com"}) == []
