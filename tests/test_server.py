from odoo_mcp.server import is_authorized


def test_is_authorized_accepts_correct_bearer():
    assert is_authorized("Bearer good-secret", "good-secret") is True


def test_is_authorized_rejects_wrong_or_missing():
    assert is_authorized("Bearer wrong", "good-secret") is False
    assert is_authorized(None, "good-secret") is False
    assert is_authorized("Basic good-secret", "good-secret") is False
