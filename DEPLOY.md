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
