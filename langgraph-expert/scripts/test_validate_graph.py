"""
测试 validate_graph.py 工具

测试覆盖：
1. 循环依赖检测
2. 状态类型验证
3. 死节点检测
4. 条件边完整性验证
"""

import pytest
from pathlib import Path


# 测试辅助函数：创建临时 Python 文件
def create_temp_graph_file(tmp_path: Path, code: str) -> Path:
    """创建临时图定义文件"""
    file_path = tmp_path / "test_graph.py"
    file_path.write_text(code)
    return file_path


# ============ 测试循环依赖检测 ============

def test_detect_simple_cycle(tmp_path):
    """测试检测简单循环依赖"""
    code = '''
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge("a", "b")
graph.add_edge("b", "a")  # 循环
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert not result["valid"]
    assert "cycle" in result["errors"][0].lower()


def test_detect_self_loop(tmp_path):
    """测试检测自循环"""
    code = '''
from langgraph.graph import StateGraph

graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_edge("a", "a")  # 自循环
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert not result["valid"]
    assert "cycle" in result["errors"][0].lower() or "self" in result["errors"][0].lower()


def test_no_cycle_with_end(tmp_path):
    """测试正常的线性图（无循环）"""
    code = '''
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge("a", "b")
graph.add_edge("b", END)
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert result["valid"]
    assert len(result["errors"]) == 0


# ============ 测试状态类型验证 ============

def test_valid_state_type(tmp_path):
    """测试有效的状态类型定义"""
    code = '''
from typing import TypedDict
from langgraph.graph import StateGraph

class State(TypedDict):
    messages: list
    count: int

graph = StateGraph(State)
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert result["valid"]
    assert "State" in result["state_types"]


def test_missing_state_type(tmp_path):
    """测试缺少状态类型定义"""
    code = '''
from langgraph.graph import StateGraph

# 没有定义 State 类型
graph = StateGraph(dict)
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert len(result["warnings"]) > 0


# ============ 测试死节点检测 ============

def test_detect_unreachable_node(tmp_path):
    """测试检测无法到达的节点"""
    code = '''
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("start", start_node)
graph.add_node("process", process_node)
graph.add_node("orphan", orphan_node)  # 死节点

graph.set_entry_point("start")
graph.add_edge("start", "process")
graph.add_edge("process", END)
# orphan 没有任何边连接
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert not result["valid"]
    assert any("unreachable" in err.lower() or "orphan" in err.lower() for err in result["errors"])


def test_all_nodes_reachable(tmp_path):
    """测试所有节点都可达"""
    code = '''
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("start", start_node)
graph.add_node("process", process_node)
graph.add_node("end", end_node)

graph.set_entry_point("start")
graph.add_edge("start", "process")
graph.add_edge("process", "end")
graph.add_edge("end", END)
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert result["valid"]


# ============ 测试条件边完整性 ============

def test_conditional_edge_missing_path(tmp_path):
    """测试条件边缺少路径"""
    code = '''
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("router", router_node)
graph.add_node("path_a", path_a_node)

graph.set_entry_point("router")
graph.add_conditional_edges(
    "router",
    route_function,
    {
        "a": "path_a",
        # 缺少 "b" 路径
    }
)
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert len(result["warnings"]) > 0


def test_conditional_edge_complete(tmp_path):
    """测试完整的条件边"""
    code = '''
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("router", router_node)
graph.add_node("path_a", path_a_node)
graph.add_node("path_b", path_b_node)

graph.set_entry_point("router")
graph.add_conditional_edges(
    "router",
    route_function,
    {
        "a": "path_a",
        "b": "path_b",
        "end": END
    }
)
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert result["valid"]


# ============ 测试入口点验证 ============

def test_missing_entry_point(tmp_path):
    """测试缺少入口点"""
    code = '''
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_edge("a", END)
# 没有设置入口点
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert not result["valid"]
    assert any("entry" in err.lower() for err in result["errors"])


def test_valid_entry_point(tmp_path):
    """测试有效的入口点"""
    code = '''
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("start", start_node)
graph.set_entry_point("start")
graph.add_edge("start", END)
'''
    file_path = create_temp_graph_file(tmp_path, code)

    from validate_graph import validate_graph

    result = validate_graph(str(file_path))

    assert result["valid"]
