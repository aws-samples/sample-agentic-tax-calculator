"""Tool group routing for consolidated vs separate MCP deployment.

In consolidated mode (default), all 6 tools are registered on a single
FastMCP server instance. In separate mode, each tool group would be
deployed as its own MCP server - this module provides the mapping so
the gateway knows which server handles which tool.
"""

from src.config.settings import AppSettings, MCPDeploymentMode

# Canonical mapping of tool names to their module paths.
# Used by the consolidated server to register all tools, and by
# separate-mode deployment to route requests to the correct server.
TOOL_REGISTRY: dict[str, str] = {
    "get_business_info": "src.mcp.tools.business_info",
    "get_income": "src.mcp.tools.income",
    "get_expenses": "src.mcp.tools.expenses",
    "get_assets": "src.mcp.tools.assets",
    "calculate_tax": "src.mcp.tools.calculate_tax",
    "get_tax_rules": "src.mcp.tools.tax_rules",
}

# Agent-to-tool authorization (mirrors guardrails/access_control.py)
AGENT_TOOL_MAP: dict[str, list[str]] = {
    "business_agent": ["get_business_info"],
    "income_agent": ["get_income"],
    "expense_agent": ["get_expenses"],
    "asset_agent": ["get_assets"],
    "tax_agent": ["calculate_tax", "get_tax_rules"],
}


def get_tools_for_mode(settings: AppSettings | None = None) -> list[str]:
    """Return the list of tool names to register based on deployment mode.

    In consolidated mode, returns all tools.
    In separate mode, returns all tools (each would be filtered per-server
    at deployment time via TOOL_REGISTRY).
    """
    if settings is None:
        settings = AppSettings()

    if settings.mcp_deployment_mode == MCPDeploymentMode.CONSOLIDATED:
        return list(TOOL_REGISTRY.keys())
    else:
        # In separate mode, the caller filters by server identity.
        # Return all for now - deployment config handles the split.
        return list(TOOL_REGISTRY.keys())


def get_tools_for_agent(agent_id: str) -> list[str]:
    """Return the authorized tool names for a given agent."""
    return AGENT_TOOL_MAP.get(agent_id, [])
