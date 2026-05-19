# Plan d'implémentation — Socle du serveur MCP Odoo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire un serveur MCP distant, maison et sécurisé, qui expose Odoo (`magin.odoo.com`) à Claude pour 4 collègues sur mobile, avec parité CRUD totale, exécution d'actions Odoo, garde-fous et bibliothèque de savoir-faire.

**Architecture:** Serveur Python (FastMCP, transport HTTP streamable) hébergé sur un VPS, derrière Caddy (HTTPS). Modules à responsabilité unique : `config`, `auth`, `odoo_client` (seul point de contact Odoo via XML-RPC), `guardrails`, `dedup`, `audit`, `skills`, et un dossier `tools/` d'outils MCP. Le serveur ne contient aucune IA ; il exécute des appels d'outils déterministes.

**Tech Stack:** Python 3.11+, FastMCP, `xmlrpc.client` (stdlib), python-dotenv, uvicorn/Starlette (fournis par FastMCP), pytest. Déploiement : Caddy + systemd.

**Périmètre :** Phase 1 (le socle) uniquement. Référence : `docs/superpowers/specs/2026-05-19-socle-mcp-odoo-design.md`.

**Refinement vs. spec :** la *génération* de PDF/rapport Odoo (spec §6 groupe C) est **reportée à la Phase 3** — sa mise en œuvre fiable dépend de spécificités Odoo SaaS hors périmètre socle. Le socle livre `get_attachments`, qui permet déjà de **télécharger** les PDF qu'Odoo a générés (ex. factures comptabilisées). À valider avec le commettant avant exécution.

---

## Structure des fichiers

```
odoo-mcp-server/
├── requirements.txt              # dépendances runtime
├── requirements-dev.txt          # dépendances de test
├── pytest.ini                    # config pytest + marqueur "integration"
├── .gitignore
├── .env.example                  # gabarit des secrets
├── config.example.toml           # gabarit des listes blanches / plafonds
├── skills_library/
│   └── exemple-prospection.md    # un skill d'exemple
├── odoo_mcp/
│   ├── __init__.py
│   ├── config.py                 # chargement config + secrets
│   ├── auth.py                   # vérification du secret partagé
│   ├── audit.py                  # journal d'audit (écriture + lecture)
│   ├── guardrails.py             # plafond + jeton de confirmation
│   ├── odoo_client.py            # SEUL point de contact Odoo (XML-RPC)
│   ├── dedup.py                  # détection de doublons contacts/leads
│   ├── skills.py                 # chargement de la bibliothèque de savoir-faire
│   ├── runtime.py                # conteneur de dépendances partagé
│   ├── tools/
│   │   ├── __init__.py           # registre des outils
│   │   ├── read.py               # outils lecture/découverte
│   │   ├── write.py              # outils écriture
│   │   └── actions.py            # outils actions Odoo + skills + audit
│   └── server.py                 # assemblage FastMCP + middleware d'auth
├── tests/
│   ├── conftest.py               # FakeOdoo + fixtures
│   ├── test_config.py
│   ├── test_auth.py
│   ├── test_audit.py
│   ├── test_guardrails.py
│   ├── test_odoo_client.py
│   ├── test_dedup.py
│   ├── test_skills.py
│   ├── test_tools_read.py
│   ├── test_tools_write.py
│   ├── test_tools_actions.py
│   └── test_integration.py       # contre la base de test Odoo (marqueur)
├── deploy/
│   ├── Caddyfile
│   └── odoo-mcp.service
└── DEPLOY.md
```

---

## Milestone 0 — Mise en place du projet

### Task 1: Squelette du projet

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.gitignore`, `.env.example`, `config.example.toml`
- Create: `odoo_mcp/__init__.py`, `skills_library/exemple-prospection.md`

- [ ] **Step 1: Créer `requirements.txt`**

```
fastmcp>=2.0
python-dotenv>=1.0
tomli>=2.0 ; python_version < "3.11"
```

- [ ] **Step 2: Créer `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0
```

- [ ] **Step 3: Créer `pytest.ini`**

```ini
[pytest]
markers =
    integration: tests qui dialoguent avec une vraie base Odoo (désactivés par défaut)
addopts = -m "not integration"
testpaths = tests
```

- [ ] **Step 4: Créer `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.env
config.toml
audit.log
.pytest_cache/
```

- [ ] **Step 5: Créer `.env.example`**

```
# Secrets — copier en .env et remplir. Ne JAMAIS committer .env.
ODOO_URL=https://magin.odoo.com
ODOO_DB=magin
ODOO_USERNAME=la.team.magin@gmail.com
ODOO_API_KEY=remplacer_par_la_cle_api_odoo
MCP_ACCESS_SECRET=remplacer_par_un_secret_long_et_aleatoire
```

- [ ] **Step 6: Créer `config.example.toml`**

```toml
# Listes blanches et plafonds — copier en config.toml.

[models]
allowed = [
  "crm.lead", "crm.stage", "crm.team",
  "res.partner",
  "sale.order", "sale.order.line",
  "account.move", "account.move.line",
  "purchase.order", "purchase.order.line",
  "stock.picking",
  "product.product", "product.template",
  "mailing.mailing",
  "ir.attachment",
]

[actions]
"sale.order" = ["action_confirm", "action_quotation_send"]
"account.move" = ["action_post"]
"purchase.order" = ["button_confirm"]
"stock.picking" = ["button_validate"]

[guardrails]
mass_op_cap = 50
audit_log_path = "audit.log"

[skills]
dir = "skills_library"
```

- [ ] **Step 7: Créer `odoo_mcp/__init__.py`** (fichier vide)

- [ ] **Step 8: Créer `skills_library/exemple-prospection.md`**

```markdown
---
name: exemple-prospection
description: Exemple de savoir-faire — créer un lead propre à partir d'une note de terrain.
---

# Créer un lead de prospection

Quand on te demande d'enregistrer un nouveau prospect :

1. Identifie le nom de la société, le contact, le téléphone, l'email.
2. Crée le record dans le modèle `crm.lead`.
3. Si un téléphone ou un email est fourni, l'outil de création signalera
   tout doublon existant — propose alors de compléter le contact existant.
4. Résume au collègue ce qui a été créé, avec l'identifiant du lead.
```

- [ ] **Step 9: Commit**

```bash
git add requirements.txt requirements-dev.txt pytest.ini .gitignore .env.example config.example.toml odoo_mcp/__init__.py skills_library/exemple-prospection.md
git commit -m "chore: project scaffolding for the Odoo MCP server"
```

---

## Milestone 1 — Noyau (logique pure, testable sans Odoo)

### Task 2: `config.py` — chargement de la configuration

**Files:**
- Create: `odoo_mcp/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.config'`

- [ ] **Step 3: Écrire `odoo_mcp/config.py`**

```python
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

_REQUIRED_ENV = ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_API_KEY", "MCP_ACCESS_SECRET")


@dataclass
class Config:
    odoo_url: str
    odoo_db: str
    odoo_username: str
    odoo_api_key: str
    access_secret: str
    allowed_models: list
    allowed_actions: dict
    mass_op_cap: int
    audit_log_path: str
    skills_dir: str

    @classmethod
    def load(cls, toml_path="config.toml", env_path=".env"):
        if Path(env_path).exists():
            load_dotenv(env_path)
        missing = [k for k in _REQUIRED_ENV if not os.environ.get(k)]
        if missing:
            raise RuntimeError(
                "Variables d'environnement manquantes : " + ", ".join(missing)
            )
        data = {}
        if Path(toml_path).exists():
            data = tomllib.loads(Path(toml_path).read_text(encoding="utf-8"))
        guardrails = data.get("guardrails", {})
        return cls(
            odoo_url=os.environ["ODOO_URL"].rstrip("/"),
            odoo_db=os.environ["ODOO_DB"],
            odoo_username=os.environ["ODOO_USERNAME"],
            odoo_api_key=os.environ["ODOO_API_KEY"],
            access_secret=os.environ["MCP_ACCESS_SECRET"],
            allowed_models=list(data.get("models", {}).get("allowed", [])),
            allowed_actions={k: list(v) for k, v in data.get("actions", {}).items()},
            mass_op_cap=int(guardrails.get("mass_op_cap", 50)),
            audit_log_path=guardrails.get("audit_log_path", "audit.log"),
            skills_dir=data.get("skills", {}).get("dir", "skills_library"),
        )
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/config.py tests/test_config.py
git commit -m "feat: configuration loader (env secrets + toml whitelists)"
```

---

### Task 3: `auth.py` — vérification du secret partagé

**Files:**
- Create: `odoo_mcp/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_auth.py
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
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.auth'`

- [ ] **Step 3: Écrire `odoo_mcp/auth.py`**

```python
import secrets


def verify_secret(provided, expected):
    if not provided or not expected:
        return False
    return secrets.compare_digest(str(provided), str(expected))


def extract_bearer(authorization_header):
    if not authorization_header:
        return None
    parts = authorization_header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_auth.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/auth.py tests/test_auth.py
git commit -m "feat: shared-secret verification and bearer-token extraction"
```

---

### Task 4: `audit.py` — journal d'audit

**Files:**
- Create: `odoo_mcp/audit.py`
- Test: `tests/test_audit.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_audit.py
from odoo_mcp.audit import record, read_recent


def test_record_then_read(tmp_path):
    log = str(tmp_path / "audit.log")
    record(log, "create", "crm.lead", [7], "Lead 'ACME' créé", "success")
    record(log, "delete", "crm.lead", [7], "Lead supprimé", "success")
    entries = read_recent(log, limit=10)
    assert len(entries) == 2
    assert entries[0]["operation"] == "create"
    assert entries[0]["model"] == "crm.lead"
    assert entries[0]["record_ids"] == [7]
    assert entries[1]["operation"] == "delete"
    assert "timestamp" in entries[0]


def test_read_recent_missing_file_returns_empty(tmp_path):
    assert read_recent(str(tmp_path / "absent.log")) == []


def test_read_recent_respects_limit(tmp_path):
    log = str(tmp_path / "audit.log")
    for i in range(5):
        record(log, "create", "res.partner", [i], f"n{i}", "success")
    entries = read_recent(log, limit=2)
    assert len(entries) == 2
    assert entries[-1]["record_ids"] == [4]
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_audit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.audit'`

- [ ] **Step 3: Écrire `odoo_mcp/audit.py`**

```python
import json
from datetime import datetime, timezone
from pathlib import Path


def record(log_path, operation, model, record_ids, summary, status):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "model": model,
        "record_ids": list(record_ids or []),
        "summary": summary,
        "status": status,
    }
    with Path(log_path).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_recent(log_path, limit=50):
    path = Path(log_path)
    if not path.exists():
        return []
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [json.loads(l) for l in lines[-limit:]]
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_audit.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/audit.py tests/test_audit.py
git commit -m "feat: append-only audit log with recent-entries reader"
```

---

### Task 5: `guardrails.py` — plafond et jeton de confirmation

**Files:**
- Create: `odoo_mcp/guardrails.py`
- Test: `tests/test_guardrails.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_guardrails.py
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
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_guardrails.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.guardrails'`

- [ ] **Step 3: Écrire `odoo_mcp/guardrails.py`**

```python
import hashlib
import secrets


class GuardrailError(Exception):
    pass


def enforce_cap(count, cap):
    if count > cap:
        raise GuardrailError(
            f"Opération massive refusée : {count} records demandés, "
            f"plafond de {cap}. Découpez en lots plus petits."
        )


def confirmation_token(descriptor):
    return hashlib.sha256(descriptor.encode("utf-8")).hexdigest()[:16]


def needs_confirmation(descriptor, provided_token):
    """Renvoie None si l'opération est confirmée, sinon le jeton à ré-émettre."""
    expected = confirmation_token(descriptor)
    if provided_token and secrets.compare_digest(str(provided_token), expected):
        return None
    return expected
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_guardrails.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/guardrails.py tests/test_guardrails.py
git commit -m "feat: guardrails — mass-op cap and stateless confirmation token"
```

---

## Milestone 2 — Client Odoo

### Task 6: `conftest.py` + `odoo_client.py` (connexion, `execute_kw`, liste blanche)

**Files:**
- Create: `tests/conftest.py`
- Create: `odoo_mcp/odoo_client.py`
- Test: `tests/test_odoo_client.py`

- [ ] **Step 1: Écrire `tests/conftest.py` (faux Odoo pour les tests unitaires)**

```python
# tests/conftest.py
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
```

- [ ] **Step 2: Écrire le test qui échoue**

```python
# tests/test_odoo_client.py
import pytest
from odoo_mcp.odoo_client import OdooClient, OdooError


def make_client():
    return OdooClient("https://x.odoo.com/", "db", "user", "key",
                      allowed_models=["crm.lead", "res.partner"])


def test_check_model_rejects_unlisted():
    client = make_client()
    with pytest.raises(OdooError) as exc:
        client.execute_kw("res.users", "search", [[]])
    assert "non autorisé" in str(exc.value)


def test_execute_kw_uses_uid_and_returns_result(monkeypatch):
    client = make_client()
    monkeypatch.setattr(client, "_ensure_uid", lambda: 2)

    captured = {}

    class FakeModels:
        def execute_kw(self, db, uid, key, model, method, args, kwargs):
            captured.update(db=db, uid=uid, model=model, method=method)
            return [42]

    client._models = FakeModels()
    result = client.execute_kw("crm.lead", "search", [[]])
    assert result == [42]
    assert captured == {"db": "db", "uid": 2, "model": "crm.lead", "method": "search"}
```

- [ ] **Step 3: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_odoo_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.odoo_client'`

- [ ] **Step 4: Écrire `odoo_mcp/odoo_client.py`**

```python
import xmlrpc.client


class OdooError(Exception):
    pass


def _clean_fault(fault_string):
    lines = [l for l in (fault_string or "").splitlines() if l.strip()]
    return lines[-1].strip() if lines else "Erreur Odoo inconnue"


class OdooClient:
    def __init__(self, url, db, username, api_key, allowed_models):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.api_key = api_key
        self.allowed_models = set(allowed_models)
        self._uid = None
        self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def _ensure_uid(self):
        if self._uid is None:
            try:
                uid = self._common.authenticate(self.db, self.username, self.api_key, {})
            except (xmlrpc.client.ProtocolError, ConnectionError, OSError) as exc:
                raise OdooError(f"Odoo injoignable : {exc}") from exc
            if not uid:
                raise OdooError(
                    "Authentification Odoo échouée : clé API ou identifiants invalides."
                )
            self._uid = uid
        return self._uid

    def _check_model(self, model):
        if model not in self.allowed_models:
            raise OdooError(
                f"Modèle '{model}' non autorisé. Modèles autorisés : "
                + ", ".join(sorted(self.allowed_models))
            )

    def execute_kw(self, model, method, args, kwargs=None):
        self._check_model(model)
        uid = self._ensure_uid()
        attempts = 0
        while True:
            attempts += 1
            try:
                return self._models.execute_kw(
                    self.db, uid, self.api_key, model, method, args, kwargs or {}
                )
            except xmlrpc.client.Fault as exc:
                raise OdooError(_clean_fault(exc.faultString)) from exc
            except (xmlrpc.client.ProtocolError, ConnectionError, OSError) as exc:
                if attempts >= 2:
                    raise OdooError(f"Odoo injoignable : {exc}") from exc
```

- [ ] **Step 5: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_odoo_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py odoo_mcp/odoo_client.py tests/test_odoo_client.py
git commit -m "feat: Odoo XML-RPC client with model whitelist and one retry"
```

---

### Task 7: `odoo_client.py` — méthodes de lecture

**Files:**
- Modify: `odoo_mcp/odoo_client.py` (ajout de méthodes)
- Test: `tests/test_odoo_client.py` (ajout)

- [ ] **Step 1: Ajouter les tests qui échouent**

Ajouter à la fin de `tests/test_odoo_client.py` :

```python
def test_read_methods_delegate_to_execute_kw(monkeypatch):
    client = make_client()
    seen = []
    monkeypatch.setattr(client, "execute_kw",
                        lambda m, meth, a, k=None: seen.append((m, meth, a, k)) or "OK")

    client.search("crm.lead", domain=[["name", "=", "x"]], fields=["name"],
                  limit=5, offset=2, order="id desc")
    client.read("crm.lead", [1, 2], fields=["name"])
    client.fields("crm.lead")
    client.count("crm.lead", domain=[])
    client.read_group("crm.lead", domain=[], fields=["expected_revenue:sum"],
                      groupby=["stage_id"])

    assert seen[0] == ("crm.lead", "search_read",
                       [[["name", "=", "x"]]],
                       {"fields": ["name"], "limit": 5, "offset": 2, "order": "id desc"})
    assert seen[1] == ("crm.lead", "read", [[1, 2]], {"fields": ["name"]})
    assert seen[2] == ("crm.lead", "fields_get", [], {"attributes": ["string", "type", "required", "selection", "relation"]})
    assert seen[3] == ("crm.lead", "search_count", [[]], None)
    assert seen[4] == ("crm.lead", "read_group", [[], ["expected_revenue:sum"], ["stage_id"]], None)
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_odoo_client.py::test_read_methods_delegate_to_execute_kw -v`
Expected: FAIL — `AttributeError: 'OdooClient' object has no attribute 'search'`

- [ ] **Step 3: Ajouter les méthodes de lecture à `OdooClient`**

Ajouter ces méthodes dans la classe `OdooClient` :

```python
    def search(self, model, domain=None, fields=None, limit=None, offset=0, order=None):
        kwargs = {"fields": fields or []}
        if limit is not None:
            kwargs["limit"] = limit
        if offset:
            kwargs["offset"] = offset
        if order:
            kwargs["order"] = order
        return self.execute_kw(model, "search_read", [domain or []], kwargs)

    def read(self, model, ids, fields=None):
        return self.execute_kw(model, "read", [list(ids)], {"fields": fields or []})

    def fields(self, model):
        return self.execute_kw(model, "fields_get", [], {
            "attributes": ["string", "type", "required", "selection", "relation"]
        })

    def count(self, model, domain=None):
        return self.execute_kw(model, "search_count", [domain or []])

    def read_group(self, model, domain, fields, groupby):
        return self.execute_kw(model, "read_group", [domain or [], fields, groupby])
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_odoo_client.py -v`
Expected: PASS (tous les tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/odoo_client.py tests/test_odoo_client.py
git commit -m "feat: Odoo client read methods (search, read, fields, count, read_group)"
```

---

### Task 8: `odoo_client.py` — méthodes d'écriture

**Files:**
- Modify: `odoo_mcp/odoo_client.py`
- Test: `tests/test_odoo_client.py` (ajout)

- [ ] **Step 1: Ajouter les tests qui échouent**

Ajouter à la fin de `tests/test_odoo_client.py` :

```python
def test_write_methods_delegate(monkeypatch):
    client = make_client()
    seen = []
    monkeypatch.setattr(client, "execute_kw",
                        lambda m, meth, a, k=None: seen.append((m, meth, a)) or 99)

    client.create("crm.lead", {"name": "ACME"})
    client.write("crm.lead", [5], {"name": "ACME2"})
    client.unlink("crm.lead", [5])

    assert seen[0] == ("crm.lead", "create", [{"name": "ACME"}])
    assert seen[1] == ("crm.lead", "write", [[5], {"name": "ACME2"}])
    assert seen[2] == ("crm.lead", "unlink", [[5]])
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_odoo_client.py::test_write_methods_delegate -v`
Expected: FAIL — `AttributeError: 'OdooClient' object has no attribute 'create'`

- [ ] **Step 3: Ajouter les méthodes d'écriture à `OdooClient`**

```python
    def create(self, model, values):
        return self.execute_kw(model, "create", [values])

    def write(self, model, ids, values):
        return self.execute_kw(model, "write", [list(ids), values])

    def unlink(self, model, ids):
        return self.execute_kw(model, "unlink", [list(ids)])
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_odoo_client.py -v`
Expected: PASS (tous les tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/odoo_client.py tests/test_odoo_client.py
git commit -m "feat: Odoo client write methods (create, write, unlink)"
```

---

### Task 9: `odoo_client.py` — actions, message chatter, email

**Files:**
- Modify: `odoo_mcp/odoo_client.py`
- Test: `tests/test_odoo_client.py` (ajout)

- [ ] **Step 1: Ajouter les tests qui échouent**

Ajouter à la fin de `tests/test_odoo_client.py` :

```python
def test_action_message_email_delegate(monkeypatch):
    client = make_client()
    seen = []
    monkeypatch.setattr(client, "execute_kw",
                        lambda m, meth, a, k=None: seen.append((m, meth, a, k)) or True)

    client.call_action("sale.order", [3], "action_confirm")
    client.post_message("crm.lead", 8, "Note interne")
    client.send_email("crm.lead", 8, [12], "Bonjour", "<p>Corps</p>")

    assert seen[0] == ("sale.order", "action_confirm", [[3]], None)
    assert seen[1][:3] == ("crm.lead", "message_post", [[8]])
    assert seen[1][3]["body"] == "Note interne"
    assert seen[2][1] == "message_post"
    assert seen[2][3]["partner_ids"] == [12]
    assert seen[2][3]["subject"] == "Bonjour"
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_odoo_client.py::test_action_message_email_delegate -v`
Expected: FAIL — `AttributeError: 'OdooClient' object has no attribute 'call_action'`

- [ ] **Step 3: Ajouter les méthodes à `OdooClient`**

```python
    def call_action(self, model, ids, action):
        return self.execute_kw(model, action, [list(ids)])

    def post_message(self, model, record_id, body):
        return self.execute_kw(model, "message_post", [[record_id]], {
            "body": body,
            "message_type": "comment",
        })

    def send_email(self, model, record_id, partner_ids, subject, body):
        return self.execute_kw(model, "message_post", [[record_id]], {
            "subject": subject,
            "body": body,
            "partner_ids": list(partner_ids),
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
        })
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_odoo_client.py -v`
Expected: PASS (tous les tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/odoo_client.py tests/test_odoo_client.py
git commit -m "feat: Odoo client actions, internal chatter and outbound email"
```

---

### Task 10: `dedup.py` — détection de doublons

**Files:**
- Create: `odoo_mcp/dedup.py`
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_dedup.py
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
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_dedup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.dedup'`

- [ ] **Step 3: Écrire `odoo_mcp/dedup.py`**

```python
# Modèles pour lesquels l'anti-doublon s'applique, et les champs identifiants.
_DEDUP_MODELS = {
    "res.partner": ["email", "phone", "mobile"],
    "crm.lead": ["email_from", "phone", "partner_name"],
}


def find_duplicates(odoo_client, model, values):
    """Renvoie les records existants qui ressemblent à `values`. Liste vide si
    le modèle n'est pas concerné ou si aucun identifiant n'est fourni."""
    id_fields = _DEDUP_MODELS.get(model)
    if not id_fields:
        return []
    domain = []
    for field in id_fields:
        val = values.get(field)
        if val:
            if domain:
                domain = ["|"] + domain
            domain = domain + [[field, "=ilike", val]]
    if not domain:
        return []
    return odoo_client.search(model, domain=domain,
                              fields=["id", "name", "display_name"])
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_dedup.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/dedup.py tests/test_dedup.py
git commit -m "feat: duplicate detection for contacts and leads"
```

---

## Milestone 3 — Outils MCP & bibliothèque de savoir-faire

### Task 11: `skills.py` — chargement de la bibliothèque

**Files:**
- Create: `odoo_mcp/skills.py`
- Test: `tests/test_skills.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_skills.py
from odoo_mcp.skills import list_skills, get_skill


def _make_skill(dir_path, name, description, body):
    (dir_path / f"{name}.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}",
        encoding="utf-8",
    )


def test_list_skills_reads_frontmatter(tmp_path):
    _make_skill(tmp_path, "prospection", "Créer un lead", "Corps A")
    _make_skill(tmp_path, "devis", "Créer un devis", "Corps B")
    skills = list_skills(str(tmp_path))
    by_name = {s["name"]: s for s in skills}
    assert by_name["prospection"]["description"] == "Créer un lead"
    assert by_name["devis"]["description"] == "Créer un devis"


def test_get_skill_returns_full_content(tmp_path):
    _make_skill(tmp_path, "prospection", "Créer un lead", "Corps détaillé")
    content = get_skill(str(tmp_path), "prospection")
    assert "Corps détaillé" in content


def test_get_skill_unknown_raises(tmp_path):
    try:
        get_skill(str(tmp_path), "inexistant")
        assert False, "doit lever"
    except FileNotFoundError as exc:
        assert "inexistant" in str(exc)


def test_list_skills_missing_dir_returns_empty(tmp_path):
    assert list_skills(str(tmp_path / "absent")) == []
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_skills.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.skills'`

- [ ] **Step 3: Écrire `odoo_mcp/skills.py`**

```python
from pathlib import Path


def _parse_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
    return meta


def list_skills(skills_dir):
    directory = Path(skills_dir)
    if not directory.is_dir():
        return []
    out = []
    for path in sorted(directory.glob("*.md")):
        meta = _parse_frontmatter(path.read_text(encoding="utf-8"))
        out.append({
            "name": meta.get("name", path.stem),
            "description": meta.get("description", ""),
        })
    return out


def get_skill(skills_dir, name):
    path = Path(skills_dir) / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Skill '{name}' introuvable.")
    return path.read_text(encoding="utf-8")
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_skills.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/skills.py tests/test_skills.py
git commit -m "feat: skills library loader (frontmatter listing + content fetch)"
```

---

### Task 12: `runtime.py` + `tools/read.py` — outils de lecture

**Files:**
- Create: `odoo_mcp/runtime.py`
- Create: `odoo_mcp/tools/__init__.py`
- Create: `odoo_mcp/tools/read.py`
- Test: `tests/test_tools_read.py`

- [ ] **Step 1: Écrire `odoo_mcp/runtime.py`**

```python
from dataclasses import dataclass


@dataclass
class Deps:
    config: object
    odoo: object


# Rempli une seule fois au démarrage par server.py ; les outils le lisent.
deps = None


def get_deps():
    if deps is None:
        raise RuntimeError("runtime.deps non initialisé.")
    return deps
```

- [ ] **Step 2: Écrire `odoo_mcp/tools/__init__.py` (registre)**

```python
# Registre des outils MCP. Chaque module d'outils décore ses fonctions avec
# @mcp_tool ; server.py importe les modules puis enregistre tout via all_tools().
# Pas d'auto-import ici : les modules read/write/actions sont créés au fil des
# tâches 12-14 et importés explicitement par server.py.
_REGISTRY = []


def mcp_tool(fn):
    _REGISTRY.append(fn)
    return fn


def all_tools():
    return list(_REGISTRY)
```

- [ ] **Step 3: Écrire le test qui échoue**

```python
# tests/test_tools_read.py
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
```

- [ ] **Step 4: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_tools_read.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.tools.read'`

- [ ] **Step 5: Écrire `odoo_mcp/tools/read.py`**

```python
from odoo_mcp.runtime import get_deps
from odoo_mcp.tools import mcp_tool


@mcp_tool
def server_status() -> dict:
    """Renvoie l'état de la connexion Odoo et la liste des modèles autorisés."""
    cfg = get_deps().config
    return {"odoo_url": cfg.odoo_url, "allowed_models": cfg.allowed_models}


@mcp_tool
def list_models() -> list:
    """Liste les modèles Odoo accessibles via ce serveur."""
    return get_deps().config.allowed_models


@mcp_tool
def inspect_model(model: str) -> dict:
    """Décrit les champs d'un modèle Odoo (nom, type, obligatoire, relation,
    valeurs de sélection). À utiliser avant toute création pour connaître les
    champs exacts."""
    return get_deps().odoo.fields(model)


@mcp_tool
def search(model: str, domain: list = None, fields: list = None,
           limit: int = 50, offset: int = 0, order: str = None) -> list:
    """Cherche des records. `domain` est un domaine Odoo (ex.
    [["name", "ilike", "acme"]]). Renvoie au plus `limit` records."""
    return get_deps().odoo.search(model, domain=domain, fields=fields,
                                  limit=limit, offset=offset, order=order)


@mcp_tool
def read(model: str, ids: list, fields: list = None) -> list:
    """Lit le détail des records dont les identifiants sont donnés."""
    return get_deps().odoo.read(model, ids, fields=fields)


@mcp_tool
def count(model: str, domain: list = None) -> int:
    """Compte les records correspondant au domaine, sans les télécharger."""
    return get_deps().odoo.count(model, domain=domain)


@mcp_tool
def stats(model: str, fields: list, groupby: list, domain: list = None) -> list:
    """Statistiques agrégées (regroupement). Ex. fields=["expected_revenue:sum"],
    groupby=["stage_id"]."""
    return get_deps().odoo.read_group(model, domain or [], fields, groupby)
```

- [ ] **Step 6: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_tools_read.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add odoo_mcp/runtime.py odoo_mcp/tools/__init__.py odoo_mcp/tools/read.py tests/test_tools_read.py
git commit -m "feat: runtime container, tool registry and read tools"
```

---

### Task 13: `tools/write.py` — outils d'écriture (garde-fous + anti-doublons + audit)

**Files:**
- Create: `odoo_mcp/tools/write.py`
- Test: `tests/test_tools_write.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_tools_write.py
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
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_tools_write.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.tools.write'`

- [ ] **Step 3: Écrire `odoo_mcp/tools/write.py`**

```python
import json

from odoo_mcp import audit, dedup, guardrails
from odoo_mcp.runtime import get_deps
from odoo_mcp.tools import mcp_tool


def _as_list(values):
    return values if isinstance(values, list) else [values]


@mcp_tool
def create(model: str, values, force_duplicate: bool = False,
           confirmation_token: str = None) -> dict:
    """Crée un ou plusieurs records. `values` est un dictionnaire (un record)
    ou une liste de dictionnaires (création groupée). Avant création, les
    doublons de contacts/leads sont signalés sauf si force_duplicate=True.
    Une création groupée (>1) demande une confirmation."""
    deps = get_deps()
    records = _as_list(values)
    guardrails.enforce_cap(len(records), deps.config.mass_op_cap)

    if not force_duplicate:
        all_matches = []
        for rec in records:
            all_matches += dedup.find_duplicates(deps.odoo, model, rec)
        if all_matches:
            return {"status": "doublon_possible", "matches": all_matches,
                    "message": "Doublon(s) possible(s). Rappelez create avec "
                               "force_duplicate=true pour créer malgré tout."}

    if len(records) > 1:
        descriptor = f"create:{model}:{len(records)}"
        token = guardrails.needs_confirmation(descriptor, confirmation_token)
        if token is not None:
            return {"status": "confirmation_requise", "confirmation_token": token,
                    "message": f"Création groupée de {len(records)} records. "
                               f"Rappelez create avec confirmation_token."}

    ids = [deps.odoo.create(model, rec) for rec in records]
    audit.record(deps.config.audit_log_path, "create", model, ids,
                 f"{len(ids)} record(s) créé(s)", "success")
    return {"status": "created", "ids": ids}


@mcp_tool
def update(model: str, ids: list, values: dict) -> dict:
    """Modifie les records donnés en leur appliquant `values`."""
    deps = get_deps()
    deps.odoo.write(model, ids, values)
    audit.record(deps.config.audit_log_path, "update", model, ids,
                 f"champs modifiés : {', '.join(values)}", "success")
    return {"status": "updated", "ids": list(ids)}


@mcp_tool
def delete(model: str, ids: list, confirmation_token: str = None) -> dict:
    """Supprime les records donnés. Première invocation : renvoie un jeton de
    confirmation sans rien supprimer. Seconde invocation avec ce jeton :
    supprime réellement. Plafonné par mass_op_cap."""
    deps = get_deps()
    try:
        guardrails.enforce_cap(len(ids), deps.config.mass_op_cap)
    except guardrails.GuardrailError as exc:
        return {"status": "refuse", "message": str(exc)}

    descriptor = f"delete:{model}:{sorted(ids)}"
    token = guardrails.needs_confirmation(descriptor, confirmation_token)
    if token is not None:
        return {"status": "confirmation_requise", "confirmation_token": token,
                "records_concernes": list(ids),
                "message": f"{len(ids)} record(s) seraient supprimés. "
                           f"Rappelez delete avec confirmation_token pour confirmer."}

    deps.odoo.unlink(model, ids)
    audit.record(deps.config.audit_log_path, "delete", model, list(ids),
                 f"{len(ids)} record(s) supprimé(s)", "success")
    return {"status": "deleted", "ids": list(ids)}


@mcp_tool
def import_records(model: str, records: list, confirmation_token: str = None) -> dict:
    """Import groupé : crée plusieurs records d'un coup. Demande toujours une
    confirmation et est plafonné par mass_op_cap."""
    return create(model, records, force_duplicate=True,
                  confirmation_token=confirmation_token)
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_tools_write.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add odoo_mcp/tools/write.py tests/test_tools_write.py
git commit -m "feat: write tools with dedup, mass-op guardrails and audit"
```

---

### Task 14: `tools/actions.py` — actions Odoo, pièces jointes, email, skills, audit

**Files:**
- Create: `odoo_mcp/tools/actions.py`
- Test: `tests/test_tools_actions.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_tools_actions.py
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
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_tools_actions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.tools.actions'`

- [ ] **Step 3: Écrire `odoo_mcp/tools/actions.py`**

```python
import base64

from odoo_mcp import audit, guardrails, skills
from odoo_mcp.runtime import get_deps
from odoo_mcp.tools import mcp_tool


@mcp_tool
def run_action(model: str, ids: list, action: str,
               confirmation_token: str = None) -> dict:
    """Exécute une action de workflow Odoo (ex. action_confirm sur un devis).
    Seules les actions inscrites en liste blanche sont autorisées."""
    deps = get_deps()
    allowed = deps.config.allowed_actions.get(model, [])
    if action not in allowed:
        return {"status": "refuse",
                "message": f"Action '{action}' non autorisée sur {model}. "
                           f"Actions autorisées : {', '.join(allowed) or 'aucune'}."}
    deps.odoo.call_action(model, ids, action)
    audit.record(deps.config.audit_log_path, f"action:{action}", model, list(ids),
                 f"action {action} exécutée", "success")
    return {"status": "executed", "ids": list(ids), "action": action}


@mcp_tool
def post_message(model: str, record_id: int, body: str) -> dict:
    """Ajoute une note interne dans le fil de discussion (chatter) d'un record.
    N'envoie aucun email."""
    deps = get_deps()
    deps.odoo.post_message(model, record_id, body)
    audit.record(deps.config.audit_log_path, "post_message", model, [record_id],
                 "note interne ajoutée", "success")
    return {"status": "posted", "record_id": record_id}


@mcp_tool
def send_email(model: str, record_id: int, partner_ids: list, subject: str,
               body: str, confirmation_token: str = None) -> dict:
    """Envoie un véritable email aux contacts donnés depuis Odoo, tracé dans le
    chatter du record. Demande une confirmation explicite (email difficile à
    rétracter)."""
    deps = get_deps()
    descriptor = f"send_email:{model}:{record_id}:{sorted(partner_ids)}:{subject}"
    token = guardrails.needs_confirmation(descriptor, confirmation_token)
    if token is not None:
        return {"status": "confirmation_requise", "confirmation_token": token,
                "message": f"Email '{subject}' vers {len(partner_ids)} destinataire(s). "
                           f"Rappelez send_email avec confirmation_token pour envoyer."}
    deps.odoo.send_email(model, record_id, partner_ids, subject, body)
    audit.record(deps.config.audit_log_path, "send_email", model, [record_id],
                 f"email '{subject}' envoyé à {len(partner_ids)} destinataire(s)",
                 "success")
    return {"status": "sent", "record_id": record_id}


@mcp_tool
def attach_file(model: str, record_id: int, filename: str,
                content_base64: str) -> dict:
    """Joint un fichier (encodé en base64) à un record."""
    deps = get_deps()
    attachment_id = deps.odoo.create("ir.attachment", {
        "name": filename,
        "datas": content_base64,
        "res_model": model,
        "res_id": record_id,
    })
    audit.record(deps.config.audit_log_path, "attach_file", model, [record_id],
                 f"fichier '{filename}' joint", "success")
    return {"status": "attached", "attachment_id": attachment_id}


@mcp_tool
def get_attachments(model: str, record_id: int) -> list:
    """Liste les pièces jointes d'un record et renvoie leur contenu (base64).
    Permet de récupérer les PDF générés par Odoo (factures, etc.)."""
    deps = get_deps()
    return deps.odoo.search("ir.attachment",
                            domain=[["res_model", "=", model],
                                    ["res_id", "=", record_id]],
                            fields=["name", "mimetype", "datas"])


@mcp_tool
def audit_log(limit: int = 50) -> list:
    """Renvoie les dernières entrées du journal d'audit (quoi et quand)."""
    deps = get_deps()
    return audit.read_recent(deps.config.audit_log_path, limit=limit)


@mcp_tool
def list_skills_tool() -> list:
    """Liste les savoir-faire métier disponibles (nom + description)."""
    return skills.list_skills(get_deps().config.skills_dir)


@mcp_tool
def get_skill_tool(name: str) -> str:
    """Renvoie le contenu complet d'un savoir-faire métier par son nom."""
    return skills.get_skill(get_deps().config.skills_dir, name)
```

> Note : `base64` est importé pour cohérence avec d'éventuels usages futurs de
> validation ; Odoo accepte directement les chaînes base64 dans les champs
> binaires, donc `attach_file` transmet `content_base64` tel quel.

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_tools_actions.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Retirer l'import inutile**

Dans `odoo_mcp/tools/actions.py`, supprimer la ligne `import base64` (non utilisée) et la note correspondante. Vérifier : `python -m pytest tests/test_tools_actions.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add odoo_mcp/tools/actions.py tests/test_tools_actions.py
git commit -m "feat: action, attachment, email, audit and skills tools"
```

---

## Milestone 4 — Serveur MCP

### Task 15: `server.py` — assemblage FastMCP + middleware d'authentification

**Files:**
- Create: `odoo_mcp/server.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Écrire le test qui échoue (logique d'auth du middleware)**

```python
# tests/test_server.py
from odoo_mcp.server import is_authorized


def test_is_authorized_accepts_correct_bearer():
    assert is_authorized("Bearer good-secret", "good-secret") is True


def test_is_authorized_rejects_wrong_or_missing():
    assert is_authorized("Bearer wrong", "good-secret") is False
    assert is_authorized(None, "good-secret") is False
    assert is_authorized("Basic good-secret", "good-secret") is False
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'odoo_mcp.server'`

- [ ] **Step 3: Écrire `odoo_mcp/server.py`**

```python
import os

from odoo_mcp import runtime
from odoo_mcp.auth import extract_bearer, verify_secret
from odoo_mcp.config import Config
from odoo_mcp.odoo_client import OdooClient
from odoo_mcp.tools import all_tools
from odoo_mcp.tools import actions, read, write  # noqa: F401  (enregistre les outils)


def is_authorized(authorization_header, expected_secret):
    """Vrai si l'en-tête Authorization porte le bon secret partagé."""
    return verify_secret(extract_bearer(authorization_header), expected_secret)


def build_app():
    """Construit l'application ASGI : FastMCP (HTTP streamable) + middleware
    d'authentification par secret partagé. Le endpoint /health reste ouvert."""
    from fastmcp import FastMCP
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    cfg = Config.load(
        toml_path=os.environ.get("ODOO_MCP_CONFIG", "config.toml"),
        env_path=os.environ.get("ODOO_MCP_ENV", ".env"),
    )
    runtime.deps = runtime.Deps(
        config=cfg,
        odoo=OdooClient(cfg.odoo_url, cfg.odoo_db, cfg.odoo_username,
                        cfg.odoo_api_key, cfg.allowed_models),
    )

    mcp = FastMCP("Odoo MCP — magin")
    for fn in all_tools():
        mcp.tool(fn)

    # FastMCP 2.x : http_app() renvoie une application Starlette (transport
    # streamable-http). Voir https://gofastmcp.com si l'API évolue.
    app = mcp.http_app()

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path == "/health":
                return JSONResponse({"status": "ok"})
            if not is_authorized(request.headers.get("authorization"),
                                 cfg.access_secret):
                return JSONResponse({"error": "non autorisé"}, status_code=401)
            return await call_next(request)

    app.add_middleware(AuthMiddleware)
    return app


def main():
    import uvicorn
    app = build_app()
    uvicorn.run(app, host="127.0.0.1",
                port=int(os.environ.get("ODOO_MCP_PORT", "8000")))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_server.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Vérifier que la suite complète passe**

Run: `python -m pytest -v`
Expected: PASS — tous les tests non-intégration.

- [ ] **Step 6: Vérifier le démarrage du serveur localement**

Créer un `.env` et un `config.toml` réels (à partir des `.example`). Puis :

Run: `python -m odoo_mcp.server &` puis `curl -s localhost:8000/health`
Expected: `{"status":"ok"}`. Arrêter le serveur ensuite (`kill %1`).

- [ ] **Step 7: Commit**

```bash
git add odoo_mcp/server.py tests/test_server.py
git commit -m "feat: FastMCP server assembly with shared-secret auth middleware"
```

---

### Task 16: Test d'intégration contre la base de test Odoo

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Écrire le test d'intégration (marqueur `integration`)**

```python
# tests/test_integration.py
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
```

- [ ] **Step 2: Lancer le test d'intégration contre la BASE DE TEST**

⚠️ Pointer `.env` sur la base de test : `ODOO_URL=https://magin-support-20260519-qudg.odoo.com`.

Run: `python -m pytest tests/test_integration.py -m integration -v`
Expected: PASS (2 tests) — l'authentification réussit et le cycle créer/lire/supprimer fonctionne sur la base de test.

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration tests against the Odoo test database"
```

---

## Milestone 5 — Déploiement

### Task 17: Artefacts de déploiement (Caddy, systemd, guide)

**Files:**
- Create: `deploy/Caddyfile`, `deploy/odoo-mcp.service`, `DEPLOY.md`

- [ ] **Step 1: Créer `deploy/Caddyfile`**

```
# Remplacer mcp.exemple.com par le sous-domaine réel.
mcp.exemple.com {
    reverse_proxy 127.0.0.1:8000
}
```

- [ ] **Step 2: Créer `deploy/odoo-mcp.service`**

```ini
[Unit]
Description=Serveur MCP Odoo (magin)
After=network.target

[Service]
Type=simple
User=odoo-mcp
WorkingDirectory=/opt/odoo-mcp-server
Environment=ODOO_MCP_PORT=8000
ExecStart=/opt/odoo-mcp-server/.venv/bin/python -m odoo_mcp.server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Créer `DEPLOY.md`**

```markdown
# Déploiement — Serveur MCP Odoo

## Prérequis
- VPS Hostinger (KVM 1) sous Ubuntu, accès SSH par clé.
- Un sous-domaine pointant (enregistrement A) vers l'IP du VPS.
- Python 3.11+ installé.

## Étapes

1. **Durcir le VPS**
   - Pare-feu : n'ouvrir que 22 (SSH), 80 et 443.
     `ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable`
   - SSH par clé uniquement.

2. **Déposer le code**
   - `git clone <dépôt> /opt/odoo-mcp-server`
   - `cd /opt/odoo-mcp-server && python3 -m venv .venv`
   - `.venv/bin/pip install -r requirements.txt`

3. **Configurer**
   - `cp .env.example .env` puis remplir avec la clé API du compte Odoo
     partagé et un `MCP_ACCESS_SECRET` long et aléatoire
     (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`).
   - `cp config.example.toml config.toml` puis ajuster les listes blanches.
   - `chmod 600 .env config.toml`

4. **Service systemd**
   - Créer l'utilisateur : `useradd -r -s /usr/sbin/nologin odoo-mcp`
   - `chown -R odoo-mcp /opt/odoo-mcp-server`
   - `cp deploy/odoo-mcp.service /etc/systemd/system/`
   - `systemctl enable --now odoo-mcp`
   - Vérifier : `systemctl status odoo-mcp`

5. **HTTPS via Caddy**
   - Installer Caddy (voir caddyserver.com).
   - Adapter `deploy/Caddyfile` avec le vrai sous-domaine, le copier dans
     `/etc/caddy/Caddyfile`, puis `systemctl reload caddy`.
   - Caddy obtient et renouvelle le certificat TLS automatiquement.

6. **Vérifier**
   - `curl https://mcp.<domaine>.com/health` → `{"status":"ok"}`

## Connecter Claude (les 4 collègues)
- Dans l'app Claude : Réglages → Connecteurs → ajouter un connecteur
  personnalisé avec l'URL `https://mcp.<domaine>.com` et le secret partagé
  (`MCP_ACCESS_SECRET`) comme jeton d'authentification.
- Le mécanisme exact de saisie du secret côté connecteur dépend de la version
  de l'app Claude — voir la documentation Claude sur les connecteurs MCP
  personnalisés. Le serveur attend le secret en en-tête `Authorization: Bearer`.

## Bascule production
- Une fois validé sur la base de test, modifier `.env` :
  `ODOO_URL=https://magin.odoo.com` + la clé API de production.
- `systemctl restart odoo-mcp`.
```

- [ ] **Step 4: Commit**

```bash
git add deploy/Caddyfile deploy/odoo-mcp.service DEPLOY.md
git commit -m "docs: deployment artifacts (Caddy, systemd) and deploy guide"
```

---

## Auto-revue du plan

**1. Couverture de la spec**

| Exigence spec | Tâche(s) |
|---|---|
| Hébergement VPS + HTTPS Caddy + systemd | 17 |
| Transport MCP distant | 15 |
| Python + FastMCP | 15 |
| API Odoo XML-RPC | 6 |
| Parité lecture/écriture/suppression/import | 7, 8, 12, 13 |
| Exécution d'actions Odoo | 9, 14 |
| Envoi d'email | 9, 14 |
| Secret partagé / HTTPS / clé API confinée | 3, 15, 17 |
| Liste blanche de modèles | 6 ; d'actions | 14 |
| Durcissement VPS | 17 |
| Garde-fous opérations massives (essai à blanc + plafond) | 5, 13 |
| Anti-doublons | 10, 13 |
| Journal d'audit | 4, 13, 14 |
| Bibliothèque de savoir-faire | 11, 14 |
| Inspecter les champs, compter, stats agrégées | 7, 12 |
| Télécharger une pièce jointe | 14 |
| Gestion des erreurs lisibles | 6 (`_clean_fault`, `OdooError`) |
| Tests logique interne sans Odoo | 2-14 |
| Tests dialogue Odoo sur base de test | 16 |
| Génération PDF/rapport | **reportée Phase 3** (cf. en-tête) |

Aucune exigence du périmètre socle sans tâche.

**2. Placeholders** — aucun « TODO », aucune étape sans code. Task 14 introduisait un import `base64` inutilisé, retiré explicitement à l'étape 5.

**3. Cohérence des types** — `OdooClient` : `search/read/fields/count/read_group/create/write/unlink/call_action/post_message/send_email` définies en tâches 6-9, utilisées identiquement par `dedup` et `tools/*`. `runtime.Deps(config, odoo)` défini en tâche 12, utilisé tel quel partout. `guardrails.needs_confirmation/enforce_cap/GuardrailError` définis en tâche 5, signatures respectées en tâches 13-14. Le registre `mcp_tool` / `all_tools` défini en tâche 12, consommé en tâche 15.
