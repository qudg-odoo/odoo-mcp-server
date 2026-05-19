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

    def create(self, model, values):
        return self.execute_kw(model, "create", [values])

    def write(self, model, ids, values):
        return self.execute_kw(model, "write", [list(ids), values])

    def unlink(self, model, ids):
        return self.execute_kw(model, "unlink", [list(ids)])
