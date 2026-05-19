# Registre des outils MCP. Chaque module d'outils décore ses fonctions avec
# @mcp_tool ; server.py importe les modules puis enregistre tout via all_tools().
# Pas d'auto-import ici : les modules read/write/actions sont créés au fil des
# tâches 12-14 et importés explicitement par server.py.
_REGISTRY = []


def mcp_tool(fn):
    _REGISTRY.append(fn)
    return fn


def all_tools():
    return list(_REGISTRY)
