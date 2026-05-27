"""Asset Agent - retrieves HST/GST tax account data.

Calls get_assets and stores asset data in SharedState.
Zero-data case stores empty dict + warning.

Requirements: 10.1, 10.2, 10.3
"""

from __future__ import annotations

import logging

from src.agents.base import BaseAgent
from src.mcp.tools.assets import get_assets
from src.orchestrator.state import SharedState

logger = logging.getLogger(__name__)


class AssetAgent(BaseAgent):
    agent_name = "Asset Workflow"
    allowed_tools = ["get_assets"]

    def execute(self, state: SharedState) -> SharedState:
        """Call get_assets, store asset data in state."""
        self.validate_tool_access("get_assets")

        business_id = state.get("business_id", "")
        tax_year = state.get("tax_year", 2024)

        try:
            result = get_assets(business_id, tax_year)
        except Exception as exc:
            logger.error("AssetAgent failed: %s", exc)
            return {
                "status": "failed",
                "error": f"AssetAgent: {exc}",
            }

        # Check for empty / zero data
        has_data = (
            result.get("hst_collected", 0.0) != 0.0
            or result.get("hst_paid", 0.0) != 0.0
        )

        if not has_data:
            logger.warning(
                "AssetAgent: no asset data returned for %s/%s - "
                "storing empty asset_data",
                business_id,
                tax_year,
            )

        logger.info(
            "AssetAgent: net_hst=%.2f province=%s",
            result.get("net_hst", 0.0),
            result.get("province", ""),
        )
        return {"asset_data": result}


def asset_node(state: SharedState) -> SharedState:
    """LangGraph node function for the Asset Agent."""
    return AssetAgent().execute(state)
