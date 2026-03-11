# ReAct 模式

## 概述

ReAct（Reasoning and Acting）模式是 LangGraph 中最基础和最常用的架构模式。它将推理（Reasoning）和行动（Acting）结合在一个循环中，让 LLM 能够：

1. **推理**：分析当前状态，决定下一步行动
2. **行动**：调用工具执行具体操作
3. **观察**：获取工具执行结果
4. **循环**：基于观察结果继续推理

这种模式特别适合需要多步骤推理和工具调用的任务。

## 何时使用

ReAct 模式适用于以下场景：

- **需要多步骤推理**：任务无法一次性完成，需要根据中间结果调整策略
- **需要工具调用**：需要访问外部 API、数据库、搜索引擎等
- **需要动态决策**：下一步行动取决于前一步的结果
- **需要错误恢复**：工具调用可能失败，需要重试或调整策略

典型应用场景：
- 问答系统（需要搜索和推理）
- 数据分析助手（需要查询数据库和分析）
- 自动化任务执行（需要调用多个 API）
- 代码生成和调试（需要执行代码和分析结果）

## 核心概念

### 1. 状态设计

ReAct 模式的状态通常包含：

```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """ReAct Agent 的状态定义"""
    # 消息历史（使用 add_messages reducer 自动合并）
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # 可选：当前步骤计数（用于循环控制）
    step_count: int
```

**关键点**：
- `messages` 使用 `add_messages` reducer，新消息会自动追加到历史中
- `step_count` 用于防止无限循环
- 状态应该是不可变的（immutable），每次更新返回新的状态副本

### 2. 节点定义

ReAct 模式通常包含两个核心节点：

#### Agent 节点（推理节点）

```python
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

def agent_node(state: AgentState) -> AgentState:
    """Agent 推理节点：决定下一步行动"""
    # 初始化 LLM（绑定工具）
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    # 调用 LLM 进行推理
    response = llm_with_tools.invoke(state["messages"])

    # 返回新状态（不修改原状态）
    return {
        "messages": [response],
        "step_count": state.get("step_count", 0) + 1
    }
```

#### Tool 节点（行动节点）

```python
from langgraph.prebuilt import ToolNode

# 使用 LangGraph 内置的 ToolNode
tool_node = ToolNode(tools)

# 或者自定义工具节点
def custom_tool_node(state: AgentState) -> AgentState:
    """自定义工具执行节点"""
    last_message = state["messages"][-1]

    # 执行工具调用
    tool_results = []
    for tool_call in last_message.tool_calls:
        tool = tool_map[tool_call["name"]]
        result = tool.invoke(tool_call["args"])
        tool_results.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))

    return {"messages": tool_results}
```

### 3. 边和条件路由

ReAct 模式的核心是条件路由：根据 LLM 的输出决定下一步。

```python
def should_continue(state: AgentState) -> str:
    """条件路由函数：决定是继续还是结束"""
    last_message = state["messages"][-1]

    # 检查是否有工具调用
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"  # 继续执行工具

    # 检查是否超过最大步骤
    if state.get("step_count", 0) >= 10:
        return END  # 强制结束，防止无限循环

    return END  # 正常结束
```

## 完整代码示例

以下是一个完整的可运行示例，实现了一个能够搜索和计算的 ReAct Agent：

```python
"""
ReAct 模式完整示例
功能：能够搜索信息和执行数学计算的智能助手
"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# ============================================================================
# 1. 定义工具
# ============================================================================

@tool
def search(query: str) -> str:
    """搜索信息（模拟）"""
    # 实际应用中，这里会调用真实的搜索 API
    mock_results = {
        "python": "Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年创建。",
        "langgraph": "LangGraph 是一个用于构建有状态、多参与者应用的框架。",
    }
    for key, value in mock_results.items():
        if key in query.lower():
            return value
    return f"未找到关于 '{query}' 的信息"

@tool
def calculator(expression: str) -> str:
    """执行数学计算"""
    try:
        # 注意：实际应用中应该使用更安全的计算方式
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

# 工具列表
tools = [search, calculator]

# ============================================================================
# 2. 定义状态
# ============================================================================

class AgentState(TypedDict):
    """Agent 状态"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    step_count: int

# ============================================================================
# 3. 定义节点
# ============================================================================

def agent_node(state: AgentState) -> AgentState:
    """Agent 推理节点"""
    # 初始化 LLM
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    # 调用 LLM
    response = llm_with_tools.invoke(state["messages"])

    # 返回新状态
    return {
        "messages": [response],
        "step_count": state.get("step_count", 0) + 1
    }

# 使用内置的 ToolNode
tool_node = ToolNode(tools)

# ============================================================================
# 4. 定义条件路由
# ============================================================================

def should_continue(state: AgentState) -> str:
    """决定是继续还是结束"""
    last_message = state["messages"][-1]

    # 检查步骤限制
    if state.get("step_count", 0) >= 10:
        print("⚠️ 达到最大步骤限制，强制结束")
        return END

    # 检查是否有工具调用
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return END

# ============================================================================
# 5. 构建图
# ============================================================================

def create_react_agent() -> StateGraph:
    """创建 ReAct Agent 图"""
    # 初始化图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # 设置入口点
    workflow.set_entry_point("agent")

    # 添加条件边
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",  # 如果需要调用工具，跳转到 tools 节点
            END: END           # 否则结束
        }
    )

    # 工具执行后返回 agent
    workflow.add_edge("tools", "agent")

    return workflow.compile()

# ============================================================================
# 6. 运行示例
# ============================================================================

if __name__ == "__main__":
    # 创建 agent
    app = create_react_agent()

    # 测试用例 1：需要搜索
    print("=" * 60)
    print("测试 1: 搜索信息")
    print("=" * 60)

    initial_state = {
        "messages": [HumanMessage(content="什么是 LangGraph？")],
        "step_count": 0
    }

    for step, state in enumerate(app.stream(initial_state), 1):
        print(f"\n--- Step {step} ---")
        print(state)

    # 测试用例 2：需要计算
    print("\n" + "=" * 60)
    print("测试 2: 数学计算")
    print("=" * 60)

    initial_state = {
        "messages": [HumanMessage(content="计算 (123 + 456) * 2")],
        "step_count": 0
    }

    for step, state in enumerate(app.stream(initial_state), 1):
        print(f"\n--- Step {step} ---")
        print(state)

    # 测试用例 3：多步骤推理
    print("\n" + "=" * 60)
    print("测试 3: 多步骤推理")
    print("=" * 60)

    initial_state = {
        "messages": [HumanMessage(
            content="先搜索 Python 的信息，然后计算 100 * 50"
        )],
        "step_count": 0
    }

    for step, state in enumerate(app.stream(initial_state), 1):
        print(f"\n--- Step {step} ---")
        print(state)
```

## 最佳实践

### 1. 状态设计

**✅ 推荐做法**：

```python
# 使用 TypedDict 明确定义状态结构
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    step_count: int
    metadata: dict  # 可选的元数据

# 使用 reducer 自动合并状态
from langgraph.graph.message import add_messages
```

**❌ 避免做法**：

```python
# 不要使用普通 dict，缺乏类型检查
state = {"messages": [], "count": 0}

# 不要在节点中直接修改状态
def bad_node(state):
    state["messages"].append(msg)  # ❌ 直接修改
    return state
```

### 2. 工具设计

**✅ 推荐做法**：

```python
@tool
def well_designed_tool(param: str) -> str:
    """
    清晰的工具描述，帮助 LLM 理解何时使用

    Args:
        param: 参数说明

    Returns:
        返回值说明
    """
    try:
        # 实现逻辑
        result = do_something(param)
        return f"成功: {result}"
    except Exception as e:
        # 返回清晰的错误信息
        return f"错误: {str(e)}"
```

**❌ 避免做法**：

```python
@tool
def bad_tool(x):  # ❌ 缺乏类型注解和文档
    return do_something(x)  # ❌ 没有错误处理
```

### 3. 循环控制

**✅ 推荐做法**：

```python
def should_continue(state: AgentState) -> str:
    # 多重安全检查
    if state.get("step_count", 0) >= MAX_STEPS:
        return END

    if state.get("error_count", 0) >= MAX_ERRORS:
        return END

    last_message = state["messages"][-1]
    if has_tool_calls(last_message):
        return "tools"

    return END
```

**❌ 避免做法**：

```python
def bad_should_continue(state):
    # ❌ 没有步骤限制，可能无限循环
    if has_tool_calls(state["messages"][-1]):
        return "tools"
    return END
```

### 4. 可观测性

**✅ 推荐做法**：

```python
def agent_node(state: AgentState) -> AgentState:
    # 添加日志
    print(f"Step {state['step_count']}: Agent 推理中...")

    response = llm_with_tools.invoke(state["messages"])

    # 记录关键信息
    if hasattr(response, "tool_calls"):
        print(f"  → 计划调用 {len(response.tool_calls)} 个工具")

    return {"messages": [response], "step_count": state["step_count"] + 1}
```

## 常见陷阱

### 1. 无限循环

**问题**：Agent 陷入无限循环，不断调用相同的工具。

**原因**：
- 没有设置最大步骤限制
- 工具返回的信息不足，LLM 无法做出决策
- 条件路由逻辑错误

**解决方案**：

```python
def should_continue(state: AgentState) -> str:
    # 1. 添加步骤限制
    if state.get("step_count", 0) >= 10:
        return END

    # 2. 检测循环模式
    recent_actions = get_recent_tool_calls(state["messages"], n=3)
    if len(set(recent_actions)) == 1:  # 连续调用同一工具
        print("⚠️ 检测到循环，强制结束")
        return END

    # 3. 正常路由
    last_message = state["messages"][-1]
    if has_tool_calls(last_message):
        return "tools"

    return END
```

### 2. 工具调用失败

**问题**：工具调用失败导致 Agent 无法继续。

**原因**：
- 工具实现有 bug
- 参数验证不足
- 没有错误处理

**解决方案**：

```python
@tool
def robust_tool(param: str) -> str:
    """健壮的工具实现"""
    # 1. 参数验证
    if not param or not isinstance(param, str):
        return "错误: 参数必须是非空字符串"

    try:
        # 2. 执行操作
        result = do_something(param)
        return f"成功: {result}"
    except ValueError as e:
        # 3. 具体错误处理
        return f"参数错误: {str(e)}"
    except Exception as e:
        # 4. 通用错误处理
        return f"执行失败: {str(e)}"
```

### 3. 状态过大

**问题**：消息历史不断增长，导致上下文窗口溢出。

**原因**：
- 所有消息都保留在状态中
- 工具返回大量数据

**解决方案**：

```python
def agent_node(state: AgentState) -> AgentState:
    messages = state["messages"]

    # 1. 保留最近的 N 条消息
    MAX_MESSAGES = 20
    if len(messages) > MAX_MESSAGES:
        # 保留系统消息和最近的消息
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        recent_msgs = messages[-(MAX_MESSAGES - len(system_msgs)):]
        messages = system_msgs + recent_msgs

    # 2. 压缩工具输出
    compressed_messages = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and len(msg.content) > 1000:
            # 截断过长的工具输出
            compressed_msg = ToolMessage(
                content=msg.content[:1000] + "... (已截断)",
                tool_call_id=msg.tool_call_id
            )
            compressed_messages.append(compressed_msg)
        else:
            compressed_messages.append(msg)

    response = llm_with_tools.invoke(compressed_messages)
    return {"messages": [response], "step_count": state["step_count"] + 1}
```

## 扩展阅读

- [LangGraph 官方文档 - ReAct Agent](https://langchain-ai.github.io/langgraph/tutorials/introduction/)
- [ReAct 论文](https://arxiv.org/abs/2210.03629)
- [LangGraph 示例库](https://github.com/langchain-ai/langgraph/tree/main/examples)
- [工具调用最佳实践](https://python.langchain.com/docs/modules/agents/tools/)


