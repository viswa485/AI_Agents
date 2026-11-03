from pathlib import Path

from hybrid_rag.mcp_server import create_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_mcp_server_builds_tool_schemas_for_local_corpus() -> None:
    server = create_server(PROJECT_ROOT / "data" / "sample_corpus")
    assert server is not None
