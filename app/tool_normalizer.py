from app.tool_registry import ALIASES

def normalize_toolname(action: str) -> str:
    return ALIASES.get(action.lower().strip(), action)


class ToolNormalizer:
    def normalize(self, action: str) -> str:
        return normalize_toolname(action)