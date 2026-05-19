from dataclasses import dataclass


@dataclass
class Deps:
    config: object
    odoo: object


# Rempli une seule fois au démarrage par server.py ; les outils le lisent.
deps = None


def get_deps():
    if deps is None:
        raise RuntimeError("runtime.deps non initialisé.")
    return deps
