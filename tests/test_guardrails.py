import pytest
from odoo_mcp.guardrails import (
    GuardrailError, enforce_cap, confirmation_token, needs_confirmation,
)


def test_enforce_cap_allows_within_limit():
    enforce_cap(50, 50)  # ne lève pas


def test_enforce_cap_blocks_above_limit():
    with pytest.raises(GuardrailError) as exc:
        enforce_cap(51, 50)
    assert "plafond" in str(exc.value).lower()


def test_confirmation_token_is_stable_and_short():
    t1 = confirmation_token("delete:crm.lead:[1, 2]")
    t2 = confirmation_token("delete:crm.lead:[1, 2]")
    assert t1 == t2
    assert len(t1) == 16
    assert confirmation_token("delete:crm.lead:[1, 3]") != t1


def test_needs_confirmation_flow():
    descriptor = "delete:crm.lead:[9]"
    token = needs_confirmation(descriptor, None)
    assert token == confirmation_token(descriptor)        # 1er appel : jeton renvoyé
    assert needs_confirmation(descriptor, token) is None  # 2e appel : confirmé
    assert needs_confirmation(descriptor, "mauvais") == token
