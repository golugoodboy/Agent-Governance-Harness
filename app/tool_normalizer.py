from app.tool_registry import ALIASES

def normalize_toolname(action : str) ->str:

    return ALIASES.get(action.lower().strip(), action)

    