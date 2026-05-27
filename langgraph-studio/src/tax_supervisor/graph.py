"""Tax Supervisor - orchestrates the 3-phase tax calculation workflow.

Phase 1: Business Tool (metadata + validation)
Phase 2: Income, Expense, Asset Tools (PARALLEL data gathering)
Phase 3: Tax Tool (aggregation + computation)

This mirrors the production architecture:
- Tools simulate the MCP server (GraphQL API)
- Orchestrator routes between tools based on workflow state
- Phase 2 tools run in parallel (fan-out / fan-in)
- In production, tools would call the real MCP server
"""

from typing import TypedDict, Annotated
import functools

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from business_agent.graph import graph as business_graph
from income_agent.graph import graph as income_graph
from expense_agent.graph import graph as expense_graph
from asset_agent.graph import graph as asset_graph
from tax_agent.graph import graph as tax_graph


class State(TypedDict):
    messages: Annotated[list, add_messages]
    next: str | None


def tool_node(state, agent, name):
    result = agent.invoke(state)
    last_msg = result["messages"][-1]
    content = last_msg.content
    if isinstance(content, list) and len(content) > 0:
        content = content[0].get("text", str(content))
    return {
        "messages": [HumanMessage(content=str(content), name=name)]
    }


def route_after_business(state: State) -> list[str]:
    """After business tool completes, fan out to 3 data tools in parallel."""
    return ["income_tool", "expense_tool", "asset_tool"]


# Build the workflow graph - 3 phases with parallel Phase 2
workflow = StateGraph(State, config_schema=RunnableConfig)

# Phase 1: Business Tool
workflow.add_node(
    "business_tool",
    functools.partial(tool_node, agent=business_graph, name="business_tool"),
)

# Phase 2: Data gathering tools (run in parallel)
workflow.add_node(
    "income_tool",
    functools.partial(tool_node, agent=income_graph, name="income_tool"),
)
workflow.add_node(
    "expense_tool",
    functools.partial(tool_node, agent=expense_graph, name="expense_tool"),
)
workflow.add_node(
    "asset_tool",
    functools.partial(tool_node, agent=asset_graph, name="asset_tool"),
)

# Phase 3: Tax Tool
workflow.add_node(
    "tax_tool",
    functools.partial(tool_node, agent=tax_graph, name="tax_tool"),
)

# Edges - Phase 1 -> Phase 2 (parallel fan-out) -> Phase 3 -> END
workflow.add_edge(START, "business_tool")

# Fan-out: business_tool -> [income, expense, asset] in parallel
workflow.add_conditional_edges(
    "business_tool",
    route_after_business,
    ["income_tool", "expense_tool", "asset_tool"],
)

# Fan-in: all three Phase 2 tools -> tax_tool
workflow.add_edge("income_tool", "tax_tool")
workflow.add_edge("expense_tool", "tax_tool")
workflow.add_edge("asset_tool", "tax_tool")

# Phase 3 -> END
workflow.add_edge("tax_tool", END)

graph = workflow.compile()
graph.name = "AgenticTaxCalculator"
