"""Print the server's tool list (name, parameters, description) as Markdown.

Usage: uv run python -m zero_bed_by_midnight.list_tools
"""

from __future__ import annotations

import asyncio

from fastmcp import Client

from .server import create_server


async def _render() -> str:
    lines = []
    async with Client(create_server()) as client:
        for tool in await client.list_tools():
            props = tool.input_schema.get("properties", {})
            required = set(tool.input_schema.get("required", []))
            params = ", ".join(f"{name}{'' if name in required else '?'}" for name in props)
            lines.append(f"- **`{tool.name}({params})`**: {tool.description}")
    return "\n".join(lines)


def main() -> None:
    print(asyncio.run(_render()))


if __name__ == "__main__":
    main()
