"""Zero Bed by Midnight: tools for the Lisbon check-in incident (16 November 2026)."""


def main() -> None:
    """Run the FastMCP server over stdio."""
    from .server import main as run_server

    run_server()
