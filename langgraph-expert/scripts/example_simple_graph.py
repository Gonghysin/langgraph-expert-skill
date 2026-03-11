"""
示例: 一个简单的线性工作流

这个图没有循环,适合演示验证通过的情况。
"""

from typing import TypedDict
from langgraph.graph import StateGraph, END


class WorkflowState(TypedDict):
    """工作流状态"""
    input_data: str
    processed_data: str
    result: str


def input_node(state: WorkflowState) -> dict:
    """输入处理节点"""
    return {"processed_data": state["input_data"].upper()}


def process_node(state: WorkflowState) -> dict:
    """处理节点"""
    return {"result": f"Processed: {state['processed_data']}"}


# 构建图
graph = StateGraph(WorkflowState)

# 添加节点
graph.add_node("input", input_node)
graph.add_node("process", process_node)

# 设置入口点
graph.set_entry_point("input")

# 添加边
graph.add_edge("input", "process")
graph.add_edge("process", END)

# 编译图
app = graph.compile()
