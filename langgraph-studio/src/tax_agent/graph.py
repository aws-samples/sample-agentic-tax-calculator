"""Tax Agent - computes tax liability using the deterministic engine."""

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, MessagesState
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode, tools_condition
from shared.llm import llm
from tax_agent.tools import calculate_tax, get_supported_jurisdictions

tools = [calculate_tax, get_supported_jurisdictions]
llm_with_tools = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Tax Agent for the agentic tax calculator.
Your job is to compute the final tax liability.

Given revenue, expenses, jurisdiction, and accounting method:
1. Use calculate_tax to compute the full breakdown
2. Present results clearly: profit, federal tax, provincial tax, CPP, EI, total
3. Show the effective tax rate
4. If asked, explain the bracket details

You use a deterministic rules engine with 2024 CRA rates, not estimates.
Say FINISHED when done."""),
    ("placeholder", "{messages}"),
])

chain = prompt | llm_with_tools


def tax_calc_agent(state):
    return {"messages": [chain.invoke(state)]}


graph_builder = StateGraph(MessagesState, config_schema=RunnableConfig)
graph_builder.add_node("tax_agent", tax_calc_agent)
graph_builder.add_node("tools", ToolNode(tools=tools))
graph_builder.add_conditional_edges("tax_agent", tools_condition)
graph_builder.add_edge("tools", "tax_agent")
graph_builder.add_edge(START, "tax_agent")

graph = graph_builder.compile()
graph.name = "TaxAgentGraph"
