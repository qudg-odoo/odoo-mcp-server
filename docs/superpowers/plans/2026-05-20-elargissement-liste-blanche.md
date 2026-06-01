# Plan d'implémentation — Élargissement de la liste blanche (Phase 1bis)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Étendre la liste blanche du serveur MCP (`config.toml`) pour couvrir ~80 modèles métier supplémentaires et leurs actions de workflow sur 14 modules Odoo, sans modifier le code Python.

**Architecture:** Modification purement déclarative — on étend `config.example.toml` (gabarit canonique du repo) et on ajoute un petit script bash de déploiement (`deploy/apply-config.sh`) qui copie le gabarit en config active, fixe les permissions et redémarre le service systemd. Pas de nouvelle dépendance, pas de modification de code Python.

**Tech Stack:** TOML (config), Python 3.11+ (tests existants), bash (script de déploiement), systemd.

**Référence :** spéc `docs/superpowers/specs/2026-05-20-elargissement-liste-blanche-design.md`.

---

## Structure des fichiers

- **Modifier** : `config.example.toml` — étendre la liste blanche.
- **Créer** : `deploy/apply-config.sh` — script idempotent de mise à jour de la config active.
- **Modifier** : `DEPLOY.md` — documenter le nouveau cycle de maintenance.
- **Modifier** : `tests/test_config.py` — ajouter un test qui charge `config.example.toml` et vérifie que les entrées attendues y sont.

Aucun fichier sous `odoo_mcp/` n'est touché.

---

## Task 1: Étendre config.example.toml

**Files:**
- Modify: `tests/test_config.py` (ajout d'un test)
- Modify: `config.example.toml` (réécriture complète)

- [ ] **Step 1: Ajouter le test qui échoue**

À la fin de `tests/test_config.py`, ajouter :

```python
def test_load_example_config_has_extended_whitelist(monkeypatch, tmp_path):
    """Vérifie que config.example.toml du repo contient bien la liste blanche
    étendue : un échantillon de modèles et d'actions de chaque module clé."""
    for k, v in {
        "ODOO_URL": "https://example.odoo.com",
        "ODOO_DB": "db",
        "ODOO_USERNAME": "u",
        "ODOO_API_KEY": "k",
        "MCP_ACCESS_SECRET": "s",
    }.items():
        monkeypatch.setenv(k, v)
    # Charge le vrai config.example.toml du repo, env_path inexistant.
    cfg = Config.load(
        toml_path="config.example.toml",
        env_path=str(tmp_path / "missing.env"),
    )
    # Échantillon couvrant chaque module ajouté
    expected_models = {
        "project.task",          # project
        "social.post",           # social marketing
        "whatsapp.message",      # whatsapp
        "hr.expense",            # note de frais
        "pos.order",             # point de vente
        "crm.tag",               # crm étendu
        "website.page",          # site web
        "appointment.type",      # rendez-vous
        "stock.move",            # inventaire étendu
        "calendar.event",        # calendrier
        "planning.slot",         # planning
        "mailing.contact",       # email marketing étendu
        "purchase.requisition",  # achats étendu
        "documents.document",    # documents
        "spreadsheet.dashboard", # dashboards
        "mail.activity",         # transverse
        "uom.uom",               # transverse
    }
    assert expected_models.issubset(set(cfg.allowed_models)), (
        "Modèles manquants : " + ", ".join(expected_models - set(cfg.allowed_models))
    )
    # Échantillon d'actions ajoutées
    assert "action_set_won" in cfg.allowed_actions.get("crm.lead", [])
    assert "button_cancel" in cfg.allowed_actions.get("purchase.order", [])
    assert "action_send_mail" in cfg.allowed_actions.get("mailing.mailing", [])
    assert "action_pos_session_open" in cfg.allowed_actions.get("pos.session", [])
    assert "action_send" in cfg.allowed_actions.get("whatsapp.message", [])
    # Plafond et chemin d'audit inchangés
    assert cfg.mass_op_cap == 50
    assert cfg.audit_log_path == "audit.log"
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `python3 -m pytest tests/test_config.py::test_load_example_config_has_extended_whitelist -v`
Expected: FAIL — `AssertionError: Modèles manquants : project.task, social.post, ...`

- [ ] **Step 3: Réécrire `config.example.toml`**

Remplacer **intégralement** le contenu de `config.example.toml` par :

```toml
# Listes blanches et plafonds — copier en config.toml.

[models]
allowed = [
  # CRM (étendu)
  "crm.lead", "crm.stage", "crm.team",
  "crm.tag", "crm.lost.reason",
  "utm.campaign", "utm.source", "utm.medium",
  # Sales / Ventes
  "sale.order", "sale.order.line",
  # Project (Projets)
  "project.project", "project.task", "project.task.type", "project.tag",
  "project.collaborator", "project.milestone", "project.update",
  # Stock / Inventaire (étendu)
  "stock.picking", "stock.move", "stock.move.line",
  "stock.location", "stock.warehouse", "stock.quant", "stock.lot",
  "stock.scrap", "stock.picking.type", "stock.rule", "stock.route",
  # Purchase / Achats (étendu)
  "purchase.order", "purchase.order.line",
  "purchase.requisition", "purchase.requisition.line",
  # POS / Point de vente
  "pos.config", "pos.session", "pos.order", "pos.order.line",
  "pos.payment", "pos.payment.method", "pos.category",
  # HR / Note de frais
  "hr.expense", "hr.expense.sheet", "hr.department", "hr.employee",
  # Calendar / Calendrier
  "calendar.event", "calendar.attendee", "calendar.alarm", "calendar.recurrence",
  # Appointment / Rendez-vous
  "appointment.type", "appointment.resource", "appointment.invite",
  "appointment.answer", "appointment.question",
  # Planning
  "planning.slot", "planning.role", "planning.recurrency", "planning.shift.template",
  # Email Marketing (étendu)
  "mailing.mailing", "mailing.contact", "mailing.list", "mailing.trace",
  # Social Marketing
  "social.account", "social.media", "social.post",
  "social.stream", "social.stream.post", "social.live.post",
  # WhatsApp
  "whatsapp.message", "whatsapp.template",
  # Website / Site web
  "website", "website.page", "website.menu",
  "blog.blog", "blog.post", "blog.tag",
  # Spreadsheet / Dashboard & Documents
  "spreadsheet.dashboard", "spreadsheet.dashboard.group", "spreadsheet.template",
  "documents.document", "documents.folder", "documents.tag",
  # Comptabilité (écritures)
  "account.move", "account.move.line",
  # Produits
  "product.product", "product.template",
  # Partenaires
  "res.partner",
  # Pièces jointes
  "ir.attachment",
  # Transverses utilitaires
  "mail.activity", "mail.activity.type", "mail.template",
  "product.category", "uom.uom", "res.partner.category",
]

[actions]
"crm.lead"          = ["action_set_won", "action_set_lost", "action_schedule_meeting"]
"sale.order"        = ["action_confirm", "action_quotation_send", "action_cancel", "action_draft"]
"purchase.order"    = ["button_confirm", "button_cancel", "button_draft", "button_done"]
"account.move"      = ["action_post", "button_cancel"]
"stock.picking"     = ["button_validate", "action_confirm", "action_assign", "action_cancel"]
"hr.expense.sheet"  = ["action_submit_sheet", "approve_expense_sheets", "refuse_sheet"]
"pos.session"       = ["action_pos_session_open", "action_pos_session_close"]
"pos.order"         = ["action_pos_order_invoice"]
"mailing.mailing"   = ["action_send_mail", "action_test", "action_schedule", "action_cancel"]
"social.post"       = ["action_post", "action_schedule"]
"whatsapp.message"  = ["action_send"]
"planning.slot"     = ["action_send"]

[guardrails]
mass_op_cap = 50
audit_log_path = "audit.log"

[skills]
dir = "skills_library"
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il passe**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: PASS (3 tests existants + 1 nouveau test = 4 PASSED).

- [ ] **Step 5: Lancer la suite complète pour confirmer aucune régression**

Run: `python3 -m pytest -v`
Expected: 39 passed, 2 deselected.

- [ ] **Step 6: Commit**

```bash
git add config.example.toml tests/test_config.py
git commit -m "feat(config): expand whitelist to cover 14 Odoo modules (~80 new models, ~40 action entries)"
```

---

## Task 2: Ajouter `deploy/apply-config.sh`

**Files:**
- Create: `deploy/apply-config.sh`

- [ ] **Step 1: Créer le script**

Créer `deploy/apply-config.sh` avec exactement ce contenu :

```bash
#!/usr/bin/env bash
# apply-config.sh — applique config.example.toml en config.toml actif,
# règle les permissions et redémarre le service MCP.
#
# À exécuter sur le VPS en root, depuis n'importe quel répertoire.
# Idempotent : peut être relancé sans dommage.

set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/odoo-mcp-server}"
SERVICE="${SERVICE:-odoo-mcp}"
OWNER="${OWNER:-odoo-mcp:odoo-mcp}"

if [[ ! -d "$REPO_DIR" ]]; then
    echo "ERREUR : $REPO_DIR introuvable." >&2
    exit 1
fi

cd "$REPO_DIR"

if [[ ! -f config.example.toml ]]; then
    echo "ERREUR : config.example.toml manquant dans $REPO_DIR (faire git pull ?)." >&2
    exit 1
fi

cp config.example.toml config.toml
chown "$OWNER" config.toml
chmod 600 config.toml
echo "✓ config.toml mis à jour à partir du gabarit."

systemctl restart "$SERVICE"
sleep 2

if ! systemctl is-active --quiet "$SERVICE"; then
    echo "✗ Le service $SERVICE n'est pas actif après redémarrage. Voir : journalctl -u $SERVICE -n 30" >&2
    exit 1
fi
echo "✓ Service $SERVICE actif."

if ! curl -fsS --max-time 5 http://127.0.0.1:8000/health > /dev/null; then
    echo "✗ /health ne répond pas correctement." >&2
    exit 1
fi
echo "✓ /health répond {\"status\":\"ok\"}."
echo
echo "Déploiement de la configuration : OK."
```

- [ ] **Step 2: Rendre le script exécutable**

Run: `chmod +x deploy/apply-config.sh`

- [ ] **Step 3: Vérifier la syntaxe bash**

Run: `bash -n deploy/apply-config.sh`
Expected: aucun affichage (pas d'erreur de syntaxe).

- [ ] **Step 4: Vérifier que le script échoue proprement si REPO_DIR n'existe pas**

Run: `REPO_DIR=/tmp/__missing__ bash deploy/apply-config.sh 2>&1 || true`
Expected: la commande affiche `ERREUR : /tmp/__missing__ introuvable.` et retourne un code de sortie non nul.

- [ ] **Step 5: Commit**

```bash
git add deploy/apply-config.sh
git commit -m "feat(deploy): add idempotent apply-config.sh helper (copy + chown + chmod + restart + healthcheck)"
```

---

## Task 3: Mettre à jour `DEPLOY.md`

**Files:**
- Modify: `DEPLOY.md` (ajouter une section, section existante intacte)

- [ ] **Step 1: Ajouter la section « Mise à jour de la liste blanche »**

Ajouter à la fin de `DEPLOY.md`, après la section existante « Bascule production », le bloc suivant :

```markdown

## Mise à jour de la liste blanche (modèles ou actions)

Le gabarit canonique est `config.example.toml` dans le repo — il est la **source de vérité** sur les modèles et actions accessibles via le MCP. La maintenance se fait en deux temps :

1. **Sur le poste de développement** : éditer `config.example.toml`, vérifier que `python3 -m pytest` passe encore, commit, `git push`.
2. **Sur le VPS** (terminal navigateur Hostinger ou SSH) :
   ```
   cd /opt/odoo-mcp-server
   git pull
   ./deploy/apply-config.sh
   ```

Le script `apply-config.sh` :
- copie `config.example.toml` en `config.toml` actif ;
- remet les bonnes permissions (`chown odoo-mcp:odoo-mcp`, `chmod 600`) ;
- redémarre le service `odoo-mcp` ;
- vérifie que le service est actif et que `/health` répond.

Le script est **idempotent** — relançable sans dommage. Aucun secret n'est dans `config.toml` (les secrets sont dans `.env`).
```

- [ ] **Step 2: Vérifier que `DEPLOY.md` reste cohérent**

Run: `cat DEPLOY.md | tail -25`
Expected: la nouvelle section apparaît à la fin, bien formée.

- [ ] **Step 3: Commit**

```bash
git add DEPLOY.md
git commit -m "docs: document whitelist-update workflow via apply-config.sh"
```

---

## Task 4: Déploiement et validation sur le VPS

> Cette tâche est opérationnelle (commandes à exécuter sur le VPS et dans Claude), pas du code à écrire. Elle conclut le chantier.

**Files:** aucun.

**Pré-requis :** Tasks 1-3 commitées, droits SSH sur le VPS (terminal navigateur Hostinger ou client SSH).

- [ ] **Step 1: Pousser les commits sur GitHub**

Sur le poste de développement :

Run: `git push`
Expected: les commits des Tasks 1-3 sont sur `origin/master`.

- [ ] **Step 2: Sur le VPS — récupérer le code et appliquer la config**

Dans le terminal du VPS (en root) :

```
cd /opt/odoo-mcp-server
git pull
./deploy/apply-config.sh
```

Expected : la sortie se termine par :
```
✓ config.toml mis à jour à partir du gabarit.
✓ Service odoo-mcp actif.
✓ /health répond {"status":"ok"}.

Déploiement de la configuration : OK.
```

Si la sortie diffère, lire la dernière ligne d'erreur, puis `journalctl -u odoo-mcp -n 30 --no-pager` pour diagnostiquer.

- [ ] **Step 3: Smoke test — lecture d'un nouveau modèle**

Dans une conversation Claude (connecteur Odoo Magin activé), demander :

> *« Combien de tâches dans `project.task` ? »*

Expected : Claude appelle l'outil `count` sur `project.task` et renvoie un entier (≥ 0). Si Claude répond « modèle non autorisé », la config n'a pas été rechargée — relancer `apply-config.sh`.

- [ ] **Step 4: Smoke test — inspection des champs d'un nouveau modèle**

Dans la même conversation :

> *« Quels sont les champs de `hr.expense` ? »*

Expected : Claude appelle `inspect_model` et renvoie la liste des champs (au moins `name`, `total_amount`, `employee_id`).

- [ ] **Step 5: Smoke test — action de workflow**

⚠️ À faire **sur un record de test** (créer un lead jetable d'abord, ou choisir un lead que l'on accepte de marquer « gagné »). Demander à Claude :

> *« Crée un lead nommé "Smoke test 1bis" puis marque-le comme gagné. »*

Expected : Claude crée un lead via `create` puis appelle `run_action` avec `action_set_won`. Le statut du lead passe à « gagné ». En cas d'erreur de méthode (« action non autorisée » ou « méthode inconnue »), noter le nom de méthode réel et ajuster `config.example.toml` dans une itération suivante.

- [ ] **Step 6: Nettoyer le lead de test**

Dans la même conversation :

> *« Supprime le lead "Smoke test 1bis". »*

Expected : Claude appelle `delete` (avec confirmation_token au 2e appel) et le lead est supprimé.

- [ ] **Step 7: (Optionnel) Lister précisément les modules absents sur l'instance SaaS**

Pour chaque modèle suspect non disponible (ex. `whatsapp.*` ou `social.*` si non souscrits), tenter dans Claude :

> *« Compte les `whatsapp.message`. »*

Expected : soit un entier (module présent), soit une erreur Odoo claire (« Object whatsapp.message doesn't exist ») — confirmant que le module n'est pas activé. Documenter mentalement les modules non disponibles ; aucune action requise sur la config (les entrées surnuméraires sont inoffensives).

---

## Auto-revue du plan

**1. Couverture de la spec**

| Section spec | Tâche(s) du plan |
|---|---|
| §1 Contexte & objectif | Implicite (objectif du plan = élargir la liste blanche) |
| §2 Inclus / Exclus | Task 1 (le contenu du gabarit reflète les inclusions, les exclus n'apparaissent simplement pas) |
| §3 Catalogue des modèles | Task 1 (réécriture complète de `config.example.toml`) |
| §4 Catalogue des actions | Task 1 (section `[actions]`) |
| §5 Déploiement | Tasks 2, 3, 4 (script + doc + exécution) |
| §6 Validation post-déploiement | Task 4 (smoke tests) |
| §7 Maintenance future | Task 3 (section ajoutée à DEPLOY.md) |
| §8 Risques résiduels | Task 4 step 5 (mention « ajuster si méthode inconnue ») et step 7 (modules absents) |
| §9 Point ouvert : commiter `config.toml` | Décision tranchée : **non**, on garde le gabarit comme source de vérité (cf. Task 2 le script copie depuis le gabarit) |
| §9 Point ouvert : `apply-config.sh` | Décision tranchée : **oui**, créé en Task 2 |

Aucune exigence du périmètre sans tâche.

**2. Placeholders** — aucun « TODO »/« TBD », chaque étape contient les commandes ou le code exacts.

**3. Cohérence des types** — pas d'API publique nouvelle. Le test ajouté en Task 1 utilise la signature actuelle de `Config.load(toml_path, env_path)`, identique à ce qui existe dans `odoo_mcp/config.py`. Les attributs `cfg.allowed_models`, `cfg.allowed_actions`, `cfg.mass_op_cap`, `cfg.audit_log_path` testés sont tous présents sur la dataclass `Config`. Le script bash en Task 2 utilise `WorkingDirectory=/opt/odoo-mcp-server` cohérent avec `deploy/odoo-mcp.service` existant, l'utilisateur `odoo-mcp` cohérent avec celui créé en Task 4 de la Phase 1.
