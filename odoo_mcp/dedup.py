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
