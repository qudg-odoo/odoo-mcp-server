import pytest


class FakeOdoo:
    """Remplace OdooClient.execute_kw : enregistre les appels et renvoie des
    réponses scriptées par (model, method)."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def __call__(self, model, method, args, kwargs=None):
        self.calls.append((model, method, args, kwargs or {}))
        key = (model, method)
        value = self.responses.get(key, [])
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture
def fake_odoo():
    return FakeOdoo()
