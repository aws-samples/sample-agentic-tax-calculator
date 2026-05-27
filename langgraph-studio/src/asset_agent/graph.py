"""Asset Agent - retrieves HST/GST tax account data."""

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, MessagesState
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode, tools_condition
from shared.llm import llm
from asset_agent.tools import get_assets

tools = [get_assets]
llm_with_tools = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Asset Agent for the agentic tax calculator.
Your job is to retrieve HST/GST tax account data for a business.

Use the get_assets tool with the business_id.
Report: HST collected, HST paid, net HST owing, province, and rate.
Say FINISHED when done."""),
    ("placeholder", "{messages}"),
])

chain = prompt | llm_with_tools


def asset_agent(state):
    return {"messages": [chain.invoke(state)]}


graph_builder = StateGraph(MessagesState, config_schema=RunnableConfig)
graph_builder.add_node("asset_agent", asset_agent)
graph_builder.add_node("tools", ToolNode(tools=tools))
graph_builder.add_conditional_edges("asset_agent", tools_condition)
graph_builder.add_edge("tools", "asset_agent")
graph_builder.add_edge(START, "asset_agent")

graph = graph_builder.compile()
graph.name = "AssetAgentGraph"
