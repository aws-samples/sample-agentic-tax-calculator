"""Business Agent - retrieves and validates business metadata."""

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, MessagesState
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode, tools_condition
from shared.llm import llm
from business_agent.tools import get_business_info, list_businesses

tools = [get_business_info, list_businesses]
llm_with_tools = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Business Agent for the agentic tax calculator.
Your job is to retrieve and validate business metadata.

When a user asks about a business or wants to calculate taxes:
1. If they provide a business ID, use get_business_info to retrieve it
2. If they don't specify, use list_businesses to show available options
3. Validate that accounting_method and jurisdiction are present
4. Report the business details clearly

Always confirm: business name, accounting method, jurisdiction, and business type.
Say FINISHED when done."""),
    ("placeholder", "{messages}"),
])

chain = prompt | llm_with_tools


def business_agent(state):
    return {"messages": [chain.invoke(state)]}


graph_builder = StateGraph(MessagesState, config_schema=RunnableConfig)
graph_builder.add_node("business_agent", business_agent)
graph_builder.add_node("tools", ToolNode(tools=tools))
graph_builder.add_conditional_edges("business_agent", tools_condition)
graph_builder.add_edge("tools", "business_agent")
graph_builder.add_edge(START, "business_agent")

graph = graph_builder.compile()
graph.name = "BusinessAgentGraph"
