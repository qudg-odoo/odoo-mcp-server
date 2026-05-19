from odoo_mcp.auth import verify_secret, extract_bearer


def test_verify_secret_matches():
    assert verify_secret("abc", "abc") is True


def test_verify_secret_rejects_wrong_or_empty():
    assert verify_secret("abc", "xyz") is False
    assert verify_secret(None, "xyz") is False
    assert verify_secret("abc", "") is False


def test_extract_bearer():
    assert extract_bearer("Bearer tok123") == "tok123"
    assert extract_bearer("bearer tok123") == "tok123"
    assert extract_bearer("Basic tok123") is None
    assert extract_bearer(None) is None
    assert extract_bearer("Bearer") is None
