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
