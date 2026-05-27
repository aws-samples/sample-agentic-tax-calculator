"""AgentCore MCP server entry point.

This is the file referenced by agentcore.json as the runtime entryPoint.
It imports the FastMCP app from the src package and starts it with
streamable-http transport for AgentCore Runtime hosting.

Architecture (default - no Gateway):
    Web UI → AgentCore Runtime → MCP Server → GraphQL (auth + data)

    Token is passed through from the incoming request to GraphQL.
    GraphQL handles all authentication and authorization.
    No Gateway or AgentCore Identity in the default flow.

    To enable Gateway (future - multi-MCP or Cedar policies):
        Set TAX_CALC_GATEWAY_ENABLED=true
        Set TAX_CALC_GATEWAY_URL=<gateway-endpoint>

Usage (local dev):
    python mcp_server.py

Usage (AgentCore - deployed via CLI):
    agentcore deploy

Usage (container / K8s):
    opentelemetry-instrument python mcp_server.py
"""

import sys
import os

# Ensure the project root is on sys.path so `src.*` imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp.server import mcp  # noqa: E402


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
