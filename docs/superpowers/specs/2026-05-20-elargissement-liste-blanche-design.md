# Design — Élargissement de la liste blanche du serveur MCP (Phase 1bis)

- **Date** : 2026-05-20
- **Statut** : validé en brainstorming, à transformer en plan d'implémentation
- **Périmètre** : extension de la liste blanche de modèles et d'actions (Phase 1bis). Pas un nouveau pack métier.

## 1. Contexte & objectif

Le serveur MCP Odoo (socle, Phase 1) est en production sur `magin.odoo.com`. Sa liste blanche ne couvre aujourd'hui qu'**une quinzaine de modèles** : suffisant pour la prospection initiale, insuffisant pour les besoins quotidiens du commettant qui veut piloter via Claude une couverture beaucoup plus large d'Odoo.

**Objectif :** étendre la liste blanche (`config.toml`) pour couvrir les modèles métier de **14 modules Odoo** :

> *project, social marketing, WhatsApp, note de frais, point de vente, CRM (étendu), site web, rendez-vous, inventaire (étendu), calendrier, planning, email marketing (étendu), achats (étendu), spreadsheet/dashboard + Documents.*

Une fois un modèle ajouté à la liste, **tous les outils CRUD existants** (`create`, `update`, `delete`, `import_records`, `attach_file`, `post_message`, etc.) y deviennent immédiatement applicables. Les **actions de workflow** ajoutées au catalogue deviennent déclenchables via `run_action`.

**Pas un nouveau pack métier.** Ce travail livre de la *capacité brute*. Les phases 2-4 (packs prospection / cycle de vente / newsletter) ajouteront, plus tard, du *confort métier* par-dessus.

## 2. Périmètre

### Inclus

- Modèles métier courants des 14 modules.
- Actions de workflow principales (boutons « confirmer », « valider », « envoyer », « annuler »…) sur les modèles qui en ont.

### Exclus (volontairement)

- **Sécurité / utilisateurs** : `res.users`, `res.groups`.
- **Configuration interne d'Odoo** : `ir.*` (modèle, droits d'accès, automatisations, cron, paramètres système, vues, etc.).
- **Paiements** : `payment.*` (jetons, fournisseurs, transactions techniques).
- **Comptabilité technique** : `account.account`, `account.journal`, plans comptables (les écritures via `account.move` restent autorisées, c'est le cas aujourd'hui).
- **Modèles `whatsapp.account`** : configuration sensible de l'API WhatsApp Business.

### Hors périmètre (pas dans ce chantier)

- Pas de nouveaux outils MCP — on n'étend que la config.
- Le portail web d'administration reste en pause (brainstorm à reprendre séparément).
- Phases 2 à 4 (packs métier) restent à part.

## 3. Catalogue des modèles

`✓` = déjà autorisé en production ; `•` = à ajouter.

**CRM (étendu)** — ✓ `crm.lead`, ✓ `crm.stage`, ✓ `crm.team`, • `crm.tag`, • `crm.lost.reason`, • `utm.campaign`, • `utm.source`, • `utm.medium`

**Project** — • `project.project`, • `project.task`, • `project.task.type`, • `project.tag`, • `project.collaborator`, • `project.milestone`, • `project.update`

**Stock / Inventaire (étendu)** — ✓ `stock.picking`, • `stock.move`, • `stock.move.line`, • `stock.location`, • `stock.warehouse`, • `stock.quant`, • `stock.lot`, • `stock.scrap`, • `stock.picking.type`, • `stock.rule`, • `stock.route`

**Purchase / Achats (étendu)** — ✓ `purchase.order`, ✓ `purchase.order.line`, • `purchase.requisition`, • `purchase.requisition.line`

**POS / Point de vente** — • `pos.config`, • `pos.session`, • `pos.order`, • `pos.order.line`, • `pos.payment`, • `pos.payment.method`, • `pos.category`

**HR / Note de frais** — • `hr.expense`, • `hr.expense.sheet`, • `hr.department`, • `hr.employee`

**Calendar / Calendrier** — • `calendar.event`, • `calendar.attendee`, • `calendar.alarm`, • `calendar.recurrence`

**Appointment / Rendez-vous** — • `appointment.type`, • `appointment.resource`, • `appointment.invite`, • `appointment.answer`, • `appointment.question`

**Planning** — • `planning.slot`, • `planning.role`, • `planning.recurrency`, • `planning.shift.template`

**Email Marketing (étendu)** — ✓ `mailing.mailing`, • `mailing.contact`, • `mailing.list`, • `mailing.trace`

**Social Marketing** — • `social.account`, • `social.media`, • `social.post`, • `social.stream`, • `social.stream.post`, • `social.live.post`

**WhatsApp** — • `whatsapp.message`, • `whatsapp.template` *(exclu : `whatsapp.account`)*

**Website / Site web** — • `website`, • `website.page`, • `website.menu`, • `blog.blog`, • `blog.post`, • `blog.tag`

**Spreadsheet / Dashboard & Documents** — • `spreadsheet.dashboard`, • `spreadsheet.dashboard.group`, • `spreadsheet.template`, • `documents.document`, • `documents.folder`, • `documents.tag`

> *Note* : en Odoo 19 les dashboards reposent sur le moteur Spreadsheet et leur contenu réel est stocké dans `documents.document`. Inclure les modèles `documents.*` donne donc accès aux dashboards/spreadsheets, **mais aussi à l'ensemble du contenu de l'app Documents** (PDF, images, autres fichiers stockés). Choix assumé : couverture complète plutôt que partielle.

**Transverses (utilitaires)** — • `mail.activity`, • `mail.activity.type`, • `mail.template`, • `product.category`, • `uom.uom`, • `res.partner.category`

**Total : ~80 nouveaux modèles autorisés** (~95 au total avec ceux déjà en place).

Un modèle listé dont le **module Odoo n'est pas activé** reste simplement inutilisable au runtime (la liste blanche elle-même ne vérifie pas l'existence). Sans incidence.

## 4. Catalogue des actions de workflow

`✓` = déjà autorisé ; `•` = à ajouter.

| Modèle | Actions |
|---|---|
| `crm.lead` | • `action_set_won`, • `action_set_lost`, • `action_schedule_meeting` |
| `sale.order` | ✓ `action_confirm`, ✓ `action_quotation_send`, • `action_cancel`, • `action_draft` |
| `purchase.order` | ✓ `button_confirm`, • `button_cancel`, • `button_draft`, • `button_done` |
| `account.move` | ✓ `action_post`, • `button_cancel` |
| `stock.picking` | ✓ `button_validate`, • `action_confirm`, • `action_assign`, • `action_cancel` |
| `hr.expense.sheet` | • `action_submit_sheet`, • `approve_expense_sheets`, • `refuse_sheet` |
| `pos.session` | • `action_pos_session_open`, • `action_pos_session_close` |
| `pos.order` | • `action_pos_order_invoice` |
| `mailing.mailing` | • `action_send_mail`, • `action_test`, • `action_schedule`, • `action_cancel` |
| `social.post` | • `action_post`, • `action_schedule` |
| `whatsapp.message` | • `action_send` |
| `planning.slot` | • `action_send` |

Les autres modèles (project.task, calendar.event, appointment.*, website.page, blog.post, spreadsheet/documents…) **n'ont pas d'action de workflow exposée** : leurs transitions se font via des écritures normales (`update` sur `stage_id`, `state`, `is_published`…).

**Honnêteté technique :** les noms de méthodes sont stables d'une version Odoo majeure à l'autre, mais des variantes existent. Si une action ne « prend » pas au premier usage, on l'ajustera dans `config.toml` — `run_action` renvoie une erreur claire (« action non autorisée » ou « méthode inconnue »), pas un crash.

## 5. Déploiement

1. Mettre à jour **`config.example.toml`** dans le repo (gabarit canonique) avec le catalogue ci-dessus. Commit + push.
2. Sur le VPS : `git pull`, puis `cp config.example.toml config.toml` (le fichier actif n'est qu'une copie du gabarit ; il ne contient aucun secret — ceux-ci sont dans `.env`).
3. `systemctl restart odoo-mcp`. Le redémarrage prend ~2-3 s, sans interruption visible pour les collègues actifs.
4. Vérifier : `systemctl is-active odoo-mcp` → `active` ; `curl localhost:8000/health` → `{"status":"ok"}`.

Aucune modification de code applicatif Python n'est requise. Aucune dépendance nouvelle.

## 6. Validation post-déploiement (smoke tests)

À exécuter dans une conversation Claude, connecteur Odoo Magin actif :

1. **Lecture nouveau modèle** : *« Combien de tâches dans `project.task` ? »* → un entier.
2. **Découverte de champs** : *« Quels sont les champs de `hr.expense` ? »* → liste de champs et types.
3. **Action sur record de test** *(optionnel)* : *« Marque le lead [id] comme gagné »* → `run_action` avec `action_set_won` réussit.

En cas d'échec d'une action (« méthode inconnue »), on note le nom Odoo réel et on l'ajuste dans `config.toml`.

## 7. Maintenance future

- **Ajouter/retirer un modèle** : éditer `config.example.toml` (repo), commit, push, `git pull` + `cp` + `systemctl restart` sur le VPS.
- **Quand le portail web sera construit** : cette même opération deviendra un clic via interface.
- Le gabarit `config.example.toml` reste le **document source de vérité** sur la couverture autorisée — toute la communication d'équipe sur « que peut faire Claude ? » s'y réfère.

## 8. Risques résiduels

- **Noms d'actions Odoo** : éventuels écarts à corriger au premier usage. Pas de risque structurel — juste un ajustement de config.
- **Modules non activés** : modèles listés mais inutilisables si le module Odoo n'est pas installé. Sans incidence.
- **Surface d'attaque** : ~80 modèles supplémentaires écrivables. Les garde-fous existants (plafond `mass_op_cap`, jeton de confirmation pour suppression et création groupée, anti-doublons sur contacts/leads, journal d'audit) restent en place et s'appliquent automatiquement.

## 9. Points ouverts (à trancher au plan)

- Devra-t-on **commiter `config.toml`** (la version active du VPS) en plus du `config.example.toml`, ou laisser le VPS gérer son fichier local par copie du gabarit ? *(Décision pressentie : laisser via copie, c'est ce qui est en place.)*
- Faut-il **un script** au déploiement (`apply-config.sh` qui fait `cp` + `chown` + `chmod 600` + `restart`) pour automatiser les futures mises à jour ? *(Décision pressentie : oui, petit ajout utile.)*
