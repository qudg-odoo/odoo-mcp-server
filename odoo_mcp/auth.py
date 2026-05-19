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
