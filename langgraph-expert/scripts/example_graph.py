"""
示例: 一个简单的 ReAct Agent 图定义

这个示例展示了如何定义一个基本的 LangGraph 图。
"""

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Agent 状态定义"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    iteration_count: int


def agent_node(state: AgentState) -> dict:
    """Agent 推理节点"""
    return {
        "iteration_count": state.get("iteration_count", 0) + 1
    }


def tool_node(state: AgentState) -> dict:
    """工具执行节点"""
    return {}


def should_continue(state: AgentState) -> str:
    """决定是否继续"""
    if state.get("iteration_count", 0) >= 5:
        return "end"
    return "continue"


# 构建图
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

# 设置入口点
graph.set_entry_point("agent")

# 添加条件边
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END
    }
)

# 添加普通边
graph.add_edge("tools", "agent")

# 编译图
app = graph.compile()
