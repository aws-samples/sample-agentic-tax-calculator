"""LangGraph orchestrator - 3-phase tax calculation workflow.

Phase 1: Business Tool (metadata + validation)
Phase 2: Income, Expense, Asset Tools (parallel data gathering)
Phase 3: Tax Tool (aggregation + computation)

The graph is compiled with a checkpointer for DynamoDB persistence.
Tool failures are caught, recorded in SharedState, and halt the
workflow.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from langgraph.graph import END, StateGraph

from src.orchestrator.state import SharedState
from src.orchestrator.checkpointer import create_checkpointer
from src.agents.business import business_node
from src.agents.income import income_node
from src.agents.expense import expense_node
from src.agents.asset import asset_node
from src.agents.tax import tax_node

logger = logging.getLogger(__name__)


def _halt_node(state: SharedState) -> SharedState:
    """Terminal node that records workflow failure."""
    error = state.get("error", "Unknown error")
    logger.error("Workflow halted: %s", error)
    return {"status": "failed"}


def build_tax_workflow(
    use_memory_checkpointer: bool = True,
    checkpointer=None,
):
    """Build and compile the 3-phase tax calculation StateGraph.

    Args:
        use_memory_checkpointer: Use in-memory checkpointer (default
            for local dev).  Set False + provide checkpointer for
            DynamoDB in production.
        checkpointer: Pre-built checkpointer instance.  If None, one
            is created based on use_memory_checkpointer.

    Returns:
        A compiled LangGraph runnable.
    """
    if checkpointer is None:
        checkpointer = create_checkpointer(use_memory=use_memory_checkpointer)

    graph = StateGraph(SharedState)

    # -- Add nodes -----------------------------------------------------------
    graph.add_node("business_tool", business_node)
    graph.add_node("income_tool", income_node)
    graph.add_node("expense_tool", expense_node)
    graph.add_node("asset_tool", asset_node)
    graph.add_node("tax_tool", tax_node)
    graph.add_node("halt", _halt_node)

    # -- Entry point ---------------------------------------------------------
    graph.set_entry_point("business_tool")

    # -- Phase 1 → Phase 2 (fan-out from business to 3 data tools) ----------
    # LangGraph fan-out: return a list of node names to run in parallel.
    def _route_after_business(state: SharedState) -> list[str]:
        if state.get("status") == "failed":
            return ["halt"]
        return ["income_tool", "expense_tool", "asset_tool"]

    graph.add_conditional_edges(
        "business_tool",
        _route_after_business,
        ["income_tool", "expense_tool", "asset_tool", "halt"],
    )

    # -- Phase 2 → Tax (all three data tools must complete) -----------------
    graph.add_edge("income_tool", "tax_tool")
    graph.add_edge("expense_tool", "tax_tool")
    graph.add_edge("asset_tool", "tax_tool")

    # -- Phase 3 → END -------------------------------------------------------
    graph.add_edge("tax_tool", END)
    graph.add_edge("halt", END)

    return graph.compile(checkpointer=checkpointer)


def run_tax_workflow(
    business_id: str,
    tax_year: int,
    session_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    **kwargs,
) -> SharedState:
    """Convenience function to run the full tax workflow.

    Args:
        business_id: Business identifier.
        tax_year: Tax year to calculate.
        session_id: Optional session ID for checkpointing.
        workflow_id: Optional workflow ID for traceability.
        **kwargs: Passed to build_tax_workflow.

    Returns:
        Final SharedState with tax_result or error.
    """
    workflow_id = workflow_id or str(uuid.uuid4())
    session_id = session_id or str(uuid.uuid4())

    initial_state: SharedState = {
        "workflow_id": workflow_id,
        "session_id": session_id,
        "status": "pending",
        "business_id": business_id,
        "tax_year": tax_year,
    }

    app = build_tax_workflow(**kwargs)

    config = {"configurable": {"thread_id": session_id}}
    result = app.invoke(initial_state, config=config)

    return result
