# Portail web d'administration — brainstorm EN COURS (à reprendre)

- **Date de mise en pause** : 2026-05-19
- **Statut** : brainstorming interrompu volontairement, à reprendre.

## Où on en est

Le socle du serveur MCP Odoo est **déployé et en production** :
- VPS Hostinger Ubuntu 24.04, IP `193.203.191.143`.
- Serveur sur `https://mcp.magincorp.be` (Caddy HTTPS), service systemd `odoo-mcp`.
- Code dans `/opt/odoo-mcp-server`, dépôt GitHub privé `qudg-odoo/odoo-mcp-server`.
- Connecteur Claude branché et vérifié — URL `https://mcp.magincorp.be/mcp?secret=…`.
- **Bascule production faite** : pointe sur `magin.odoo.com` (base `magin`), vérifié (992 contacts).
- Base de test : `magin-support-20260519-qudg.odoo.com`.

Aujourd'hui, basculer test ↔ prod = éditer `.env` sur le VPS en SSH + `systemctl restart odoo-mcp`.

## Le sujet à reprendre : un portail web d'administration

Le commettant veut un portail web pour piloter le serveur sans passer par le terminal SSH.

### Fonctions candidates (à garder — décision de périmètre non encore prise)

1. **Basculer test ↔ prod** — un bouton pour changer la base Odoo cible. *(Le besoin explicitement exprimé.)*
2. **Voir le journal d'audit** — consulter les opérations récentes depuis une page web.
3. **État du serveur** — serveur en marche ?, base connectée (test/prod) ?, dernière erreur.
4. **Gérer listes blanches & clés** — éditer modèles/actions autorisés et clés API Odoo depuis le web.

## Prochaine étape du brainstorming

1. Obtenir la décision de **périmètre** (quelles fonctions parmi les 4 ci-dessus).
2. Puis questions de clarification restantes : qui utilise le portail (admin seul ?), authentification, hébergement (même VPS ?).
3. Proposer 2-3 approches, présenter le design, écrire la spéc, puis plan d'implémentation.

## Roadmap d'ensemble du projet (rappel)

- Phase 1 — Le socle ✅ déployé.
- Phase 2 — Pack prospection (outils métier CRM).
- Phase 3 — Pack cycle de vente (devis → commande → livraison → facture, génération PDF).
- Phase 4 — Pack newsletter.
- + Portail web d'administration (ce document).
