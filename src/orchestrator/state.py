"""Shared state schema for the LangGraph tax calculation workflow.

This TypedDict defines the data contract between all agents in the
workflow.  LangGraph passes this state through each node, and agents
read/write fields as needed.  The DynamoDB checkpointer persists
snapshots between steps.

Requirements: 6.4, 6.6
"""

from __future__ import annotations

from typing import Optional, TypedDict


class SharedState(TypedDict, total=False):
    """DynamoDB-backed shared state passed between agents via LangGraph.

    Fields are grouped by the agent that writes them:

    Workflow metadata - set by the orchestrator:
        workflow_id, session_id, status, error

    Business metadata - written by BusinessAgent:
        business_id, business_name, accounting_method, jurisdiction,
        fiscal_year_end, business_type, tax_year, business_metadata

    Financial data - written by Income/Expense/Asset agents:
        revenue, expenses, asset_data

    Tax result - written by TaxAgent:
        tax_result
    """

    # -- Workflow metadata ---------------------------------------------------
    workflow_id: str
    session_id: str
    status: str  # "pending" | "running" | "completed" | "failed"
    error: Optional[str]

    # -- Business metadata (Business Agent) ----------------------------------
    business_id: str
    business_name: str
    accounting_method: str  # "cash" | "accrual"
    jurisdiction: str  # Province/territory code: "ON", "BC", etc.
    fiscal_year_end: str
    business_type: str
    tax_year: int
    business_metadata: dict  # full raw response from get_business_info

    # -- Financial data (Income / Expense / Asset Agents) --------------------
    revenue: float
    expenses: float
    asset_data: dict  # HST/GST account data

    # -- Tax result (Tax Agent) ----------------------------------------------
    tax_result: dict  # Full TaxBreakdown serialized
