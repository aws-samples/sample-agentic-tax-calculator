"""Expense Agent - retrieves expenses from profit-and-loss accounts."""

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, MessagesState
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode, tools_condition
from shared.llm import llm
from expense_agent.tools import get_expenses

tools = [get_expenses]
llm_with_tools = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the Expense Agent for the agentic tax calculator.
Your job is to retrieve all expense data for a business.

Use the get_expenses tool with the business_id to fetch DEBIT accounts.
Report each expense account and the total expenses clearly.
Say FINISHED when done."""),
    ("placeholder", "{messages}"),
])

chain = prompt | llm_with_tools


def expense_agent(state):
    return {"messages": [chain.invoke(state)]}


graph_builder = StateGraph(MessagesState, config_schema=RunnableConfig)
graph_builder.add_node("expense_agent", expense_agent)
graph_builder.add_node("tools", ToolNode(tools=tools))
graph_builder.add_conditional_edges("expense_agent", tools_condition)
graph_builder.add_edge("tools", "expense_agent")
graph_builder.add_edge(START, "expense_agent")

graph = graph_builder.compile()
graph.name = "ExpenseAgentGraph"
