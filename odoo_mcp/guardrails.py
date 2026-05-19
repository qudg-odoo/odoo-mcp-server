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
