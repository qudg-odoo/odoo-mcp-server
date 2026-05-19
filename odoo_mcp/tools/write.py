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
