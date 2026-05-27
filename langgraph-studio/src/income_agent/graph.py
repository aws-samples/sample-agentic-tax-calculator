"""Income Agent - retrieves revenue from profit-and-loss accounts."""

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, MessagesState
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode, tools_condition
from shared.llm import llm
from income_agent.tools import get_income

tools = [get_income]
llm_with_tools = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Income Agent for the agentic tax calculator.
Your job is to retrieve all revenue/income data for a business.

Use the get_income tool with the business_id to fetch CREDIT accounts.
Report each income account and the total revenue clearly.
Say FINISHED when done."""),
    ("placeholder", "{messages}"),
])

chain = prompt | llm_with_tools


def income_agent(state):
    return {"messages": [chain.invoke(state)]}


graph_builder = StateGraph(MessagesState, config_schema=RunnableConfig)
graph_builder.add_node("income_agent", income_agent)
graph_builder.add_node("tools", ToolNode(tools=tools))
graph_builder.add_conditional_edges("income_agent", tools_condition)
graph_builder.add_edge("tools", "income_agent")
graph_builder.add_edge(START, "income_agent")

graph = graph_builder.compile()
graph.name = "IncomeAgentGraph"
