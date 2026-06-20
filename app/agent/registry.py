import inspect
import importlib
import pkgutil
from typing import get_type_hints, Optional

_TOOL_REGISTRY: dict[str, dict] = {}

PYTHON_TYPE_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _extract_params(func) -> tuple[dict, list]:
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name == "ctx":
            continue

        json_type = "string"
        is_optional = False

        hint = hints.get(name)
        if hint:
            origin = getattr(hint, "__origin__", None)
            if origin is Optional or (origin is type(None)):
                is_optional = True
                args = getattr(hint, "__args__", ())
                hint = args[0] if args else str
            json_type = PYTHON_TYPE_TO_JSON.get(hint, "string")

        prop = {"type": json_type}

        if param.default is not inspect.Parameter.empty and param.default is not None:
            prop["default"] = param.default
            is_optional = True

        properties[name] = prop

        if not is_optional and param.default is inspect.Parameter.empty:
            required.append(name)

    return properties, required


def tool(description: str, name: str = None):
    def decorator(func):
        tool_name = name or func.__name__
        properties, required = _extract_params(func)

        _TOOL_REGISTRY[tool_name] = {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
            "func": func,
        }
        return func
    return decorator


def get_all_tools() -> dict[str, dict]:
    return _TOOL_REGISTRY


def get_tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in _TOOL_REGISTRY.values()
    ]


async def execute_tool(tool_name: str, arguments: dict, ctx) -> dict:
    entry = _TOOL_REGISTRY.get(tool_name)
    if not entry:
        return {"error": f"Unknown tool: {tool_name}"}

    func = entry["func"]
    try:
        result = await func(ctx=ctx, **arguments)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def discover_tools():
    from app.agent import tools as tools_package
    package_path = tools_package.__path__
    for importer, module_name, _ in pkgutil.iter_modules(package_path):
        importlib.import_module(f"app.agent.tools.{module_name}")
