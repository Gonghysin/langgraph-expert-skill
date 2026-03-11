# Multi-Agent 模式

## 概述

Multi-Agent 模式允许多个专门的 Agent 平等协作完成复杂任务。每个 Agent 都有自己的专长领域,通过消息传递和状态共享进行协作,无需中心控制者。

## 何时使用

### 适用场景

- **并行任务处理**: 多个独立任务可以同时执行
- **专业化分工**: 不同 Agent 负责不同领域(如研究、编码、测试)
- **平等协作**: 没有明确的层级关系,Agent 之间地位平等
- **灵活路由**: 根据任务类型动态选择合适的 Agent
- **分布式决策**: 每个 Agent 可以独立做决策

### 不适用场景

- 需要中心协调者统一调度
- 任务之间有严格的依赖顺序
- 需要层级化的权限控制
- Agent 之间需要复杂的冲突解决机制

## 核心概念

### 1. Agent 定义

每个 Agent 是一个独立的节点,具有:
- **专门的工具集**: 只能访问特定领域的工具
- **独立的提示词**: 定义 Agent 的角色和行为
- **状态访问**: 可以读写共享状态

### 2. 消息传递

Agent 之间通过消息进行通信:
- **直接消息**: Agent 可以直接向其他 Agent 发送消息
- **广播消息**: 消息可以被所有 Agent 接收
- **状态更新**: 通过更新共享状态间接通信

### 3. 协作机制

- **路由逻辑**: 根据当前状态决定下一个执行的 Agent
- **状态共享**: 所有 Agent 共享同一个状态对象
- **工作流控制**: 通过条件边控制 Agent 之间的转换

## 完整代码示例

### 场景: 研究助手系统

创建一个包含研究员、编码员和审查员的多 Agent 系统。

```python
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# 1. 定义共享状态
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: str
    research_data: str
    code: str
    review_result: str

# 2. 初始化模型
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# 3. 定义研究员 Agent
def researcher_agent(state: AgentState) -> AgentState:
    """负责收集和分析信息"""
    system_prompt = """你是一个专业的研究员。
    你的任务是:
    1. 分析用户的问题
    2. 收集相关信息
    3. 总结研究发现

    将研究结果传递给编码员或审查员。"""

    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"]
    ]

    response = model.invoke(messages)

    # 决定下一个 Agent
    if "代码" in response.content or "实现" in response.content:
        next_agent = "coder"
    else:
        next_agent = "reviewer"

    return {
        "messages": [response],
        "research_data": response.content,
        "next_agent": next_agent
    }

# 4. 定义编码员 Agent
def coder_agent(state: AgentState) -> AgentState:
    """负责编写代码"""
    system_prompt = """你是一个专业的程序员。
    你的任务是:
    1. 根据研究结果编写代码
    2. 确保代码质量和可读性
    3. 添加必要的注释

    完成后将代码传递给审查员。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"研究结果: {state.get('research_data', '')}"),
        *state["messages"]
    ]

    response = model.invoke(messages)

    return {
        "messages": [response],
        "code": response.content,
        "next_agent": "reviewer"
    }

# 5. 定义审查员 Agent
def reviewer_agent(state: AgentState) -> AgentState:
    """负责审查和验证"""
    system_prompt = """你是一个专业的审查员。
    你的任务是:
    1. 审查研究结果或代码
    2. 指出问题和改进建议
    3. 决定是否需要重新处理

    如果需要改进,指定返回哪个 Agent。"""

    context = []
    if state.get("research_data"):
        context.append(f"研究结果: {state['research_data']}")
    if state.get("code"):
        context.append(f"代码: {state['code']}")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="\n".join(context)),
        *state["messages"]
    ]

    response = model.invoke(messages)

    # 决定是否需要重新处理
    content_lower = response.content.lower()
    if "需要改进" in content_lower or "重新" in content_lower:
        if "研究" in content_lower:
            next_agent = "researcher"
        elif "代码" in content_lower:
            next_agent = "coder"
        else:
            next_agent = "end"
    else:
        next_agent = "end"

    return {
        "messages": [response],
        "review_result": response.content,
        "next_agent": next_agent
    }

# 6. 定义路由函数
def route_agent(state: AgentState) -> Literal["researcher", "coder", "reviewer", "end"]:
    """根据状态决定下一个 Agent"""
    next_agent = state.get("next_agent", "end")

    if next_agent == "end":
        return END

    return next_agent

# 7. 构建图
def create_multi_agent_graph():
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("coder", coder_agent)
    workflow.add_node("reviewer", reviewer_agent)

    # 添加边
    workflow.add_edge(START, "researcher")

    # 添加条件边 - 从每个 Agent 到路由函数
    workflow.add_conditional_edges(
        "researcher",
        route_agent,
        {
            "coder": "coder",
            "reviewer": "reviewer",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "coder",
        route_agent,
        {
            "reviewer": "reviewer",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "reviewer",
        route_agent,
        {
            "researcher": "researcher",
            "coder": "coder",
            END: END
        }
    )

    return workflow.compile()

# 8. 使用示例
if __name__ == "__main__":
    app = create_multi_agent_graph()

    # 测试案例 1: 需要研究和编码
    initial_state = {
        "messages": [HumanMessage(content="创建一个计算斐波那契数列的函数")],
        "next_agent": "researcher",
        "research_data": "",
        "code": "",
        "review_result": ""
    }

    result = app.invoke(initial_state)

    print("=== 最终结果 ===")
    print(f"研究数据: {result['research_data'][:100]}...")
    print(f"代码: {result['code'][:100]}...")
    print(f"审查结果: {result['review_result'][:100]}...")
```

### 高级示例: 带工具的 Multi-Agent

```python
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# 1. 定义专门的工具
@tool
def search_web(query: str) -> str:
    """搜索网络信息"""
    # 实际实现会调用搜索 API
    return f"搜索结果: {query}"

@tool
def execute_code(code: str) -> str:
    """执行 Python 代码"""
    # 实际实现会在沙箱中执行
    return f"执行结果: {code}"

@tool
def validate_code(code: str) -> str:
    """验证代码质量"""
    # 实际实现会进行静态分析
    return f"验证结果: 代码质量良好"

# 2. 为每个 Agent 创建专门的工具集
researcher_tools = [search_web]
coder_tools = [execute_code]
reviewer_tools = [validate_code]

# 3. 使用 create_react_agent 创建 Agent
researcher_agent = create_react_agent(
    model,
    researcher_tools,
    state_modifier="你是研究员,负责收集信息"
)

coder_agent = create_react_agent(
    model,
    coder_tools,
    state_modifier="你是编码员,负责编写和测试代码"
)

reviewer_agent = create_react_agent(
    model,
    reviewer_tools,
    state_modifier="你是审查员,负责验证代码质量"
)

# 4. 构建多 Agent 图
def create_tool_based_multi_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("coder", coder_agent)
    workflow.add_node("reviewer", reviewer_agent)

    # 添加路由逻辑
    workflow.add_edge(START, "researcher")
    workflow.add_conditional_edges("researcher", route_agent)
    workflow.add_conditional_edges("coder", route_agent)
    workflow.add_conditional_edges("reviewer", route_agent)

    return workflow.compile()
```

## 最佳实践

### 1. Agent 职责清晰

```python
# 好的做法: 明确的职责划分
researcher_prompt = "你只负责研究和信息收集,不要编写代码"
coder_prompt = "你只负责编写代码,不要做研究"

# 不好的做法: 职责重叠
agent_prompt = "你可以做研究,也可以编写代码"  # 容易混乱
```

### 2. 状态管理

```python
# 好的做法: 结构化的状态
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_agent: str
    agent_outputs: dict[str, str]  # 每个 Agent 的输出
    metadata: dict  # 元数据

# 不好的做法: 扁平化的状态
class AgentState(TypedDict):
    messages: list
    data1: str
    data2: str
    data3: str  # 难以维护
```

### 3. 路由逻辑

```python
# 好的做法: 基于状态的路由
def route_agent(state: AgentState) -> str:
    # 使用状态中的明确字段
    return state.get("next_agent", END)

# 不好的做法: 基于消息内容的路由
def route_agent(state: AgentState) -> str:
    # 解析最后一条消息,容易出错
    last_message = state["messages"][-1].content
    if "代码" in last_message:
        return "coder"
    # ...
```

### 4. 错误处理

```python
def safe_agent(state: AgentState) -> AgentState:
    try:
        # Agent 逻辑
        result = process(state)
        return result
    except Exception as e:
        # 记录错误并返回安全状态
        return {
            "messages": [HumanMessage(content=f"错误: {str(e)}")],
            "next_agent": "error_handler"
        }
```

### 5. Agent 通信协议

```python
# 定义标准的消息格式
class AgentMessage(TypedDict):
    from_agent: str
    to_agent: str
    content: str
    metadata: dict

def send_message(state: AgentState, msg: AgentMessage) -> AgentState:
    """标准化的消息发送"""
    return {
        "messages": [HumanMessage(content=msg["content"])],
        "next_agent": msg["to_agent"]
    }
```

## 常见陷阱

### 1. 无限循环

**问题**: Agent 之间互相调用,形成死循环

```python
# 错误示例
def agent_a(state):
    return {"next_agent": "agent_b"}

def agent_b(state):
    return {"next_agent": "agent_a"}  # 无限循环!
```

**解决方案**: 添加循环检测和最大迭代次数

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: str
    iteration_count: int
    max_iterations: int

def route_agent(state: AgentState) -> str:
    # 检查迭代次数
    if state.get("iteration_count", 0) >= state.get("max_iterations", 10):
        return END

    return state.get("next_agent", END)

def agent_wrapper(agent_func):
    """包装 Agent 函数以增加迭代计数"""
    def wrapper(state: AgentState) -> AgentState:
        result = agent_func(state)
        result["iteration_count"] = state.get("iteration_count", 0) + 1
        return result
    return wrapper
```

### 2. 状态污染

**问题**: Agent 修改了不该修改的状态字段

```python
# 错误示例
def researcher_agent(state):
    # 不小心覆盖了其他 Agent 的数据
    return {
        "messages": [...],
        "code": "",  # 清空了编码员的工作!
    }
```

**解决方案**: 使用命名空间隔离

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    researcher_data: dict
    coder_data: dict
    reviewer_data: dict

def researcher_agent(state):
    # 只修改自己的命名空间
    return {
        "messages": [...],
        "researcher_data": {"findings": "..."}
    }
```

### 3. 工具访问混乱

**问题**: Agent 使用了不该使用的工具

```python
# 错误示例: 所有 Agent 共享所有工具
all_tools = [search_web, execute_code, validate_code]
agent = create_react_agent(model, all_tools)  # 太宽泛
```

**解决方案**: 严格限制每个 Agent 的工具集

```python
# 正确做法: 每个 Agent 只能访问特定工具
researcher = create_react_agent(model, [search_web])
coder = create_react_agent(model, [execute_code])
reviewer = create_react_agent(model, [validate_code])
```

### 4. 缺乏协调机制

**问题**: Agent 之间没有协调,产生冲突

```python
# 错误示例: 两个 Agent 同时修改同一数据
def agent_a(state):
    return {"shared_data": "A's version"}

def agent_b(state):
    return {"shared_data": "B's version"}  # 覆盖了 A 的数据
```

**解决方案**: 使用锁或版本控制

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    shared_data: dict
    data_version: int
    lock_holder: str

def agent_with_lock(agent_name: str, agent_func):
    def wrapper(state: AgentState):
        # 检查锁
        if state.get("lock_holder") and state["lock_holder"] != agent_name:
            return state  # 等待锁释放

        # 获取锁
        result = agent_func(state)
        result["lock_holder"] = None  # 释放锁
        result["data_version"] = state.get("data_version", 0) + 1
        return result

    return wrapper
```

### 5. 性能问题

**问题**: 所有 Agent 串行执行,效率低下

```python
# 错误示例: 严格的串行执行
workflow.add_edge("agent_a", "agent_b")
workflow.add_edge("agent_b", "agent_c")
workflow.add_edge("agent_c", "agent_d")
```

**解决方案**: 使用并行执行

```python
from langgraph.graph import Send

def fan_out(state: AgentState):
    """并行执行多个 Agent"""
    return [
        Send("agent_a", state),
        Send("agent_b", state),
        Send("agent_c", state)
    ]

workflow.add_conditional_edges(START, fan_out)
```

## 调试技巧

### 1. 添加日志

```python
import logging

logger = logging.getLogger(__name__)

def logged_agent(agent_name: str, agent_func):
    def wrapper(state: AgentState):
        logger.info(f"[{agent_name}] 开始执行")
        logger.debug(f"[{agent_name}] 状态: {state}")

        result = agent_func(state)

        logger.info(f"[{agent_name}] 完成执行")
        logger.debug(f"[{agent_name}] 结果: {result}")

        return result
    return wrapper
```

### 2. 可视化执行流程

```python
def visualize_execution(app, initial_state):
    """可视化 Agent 执行流程"""
    execution_path = []

    for step in app.stream(initial_state):
        agent_name = list(step.keys())[0]
        execution_path.append(agent_name)
        print(f"执行: {agent_name}")

    print(f"\n执行路径: {' -> '.join(execution_path)}")
```

### 3. 状态快照

```python
def agent_with_snapshot(agent_func):
    snapshots = []

    def wrapper(state: AgentState):
        # 保存执行前的状态
        snapshots.append(("before", state.copy()))

        result = agent_func(state)

        # 保存执行后的状态
        snapshots.append(("after", result.copy()))

        return result

    wrapper.snapshots = snapshots
    return wrapper
```

## 与其他模式的对比

| 特性 | Multi-Agent | Supervisor | Hierarchical |
|------|-------------|------------|--------------|
| 控制方式 | 分布式 | 中心化 | 层级化 |
| Agent 地位 | 平等 | Worker 服从 Supervisor | 上下级关系 |
| 路由逻辑 | 每个 Agent 自主决定 | Supervisor 决定 | 上级委派给下级 |
| 适用规模 | 小到中型 | 中到大型 | 大型复杂系统 |
| 复杂度 | 中等 | 较低 | 较高 |

## 总结

Multi-Agent 模式适合需要多个专门 Agent 平等协作的场景。关键要点:

1. **明确职责**: 每个 Agent 有清晰的专长领域
2. **状态管理**: 使用结构化的共享状态
3. **路由逻辑**: 基于状态而非消息内容
4. **避免循环**: 添加迭代限制和终止条件
5. **工具隔离**: 每个 Agent 只能访问特定工具
6. **错误处理**: 优雅地处理 Agent 失败
7. **性能优化**: 在可能的情况下并行执行

通过遵循这些最佳实践,你可以构建健壮、可维护的多 Agent 系统。
