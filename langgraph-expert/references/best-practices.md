# LangGraph 最佳实践指南

本文档提供 LangGraph 开发的最佳实践，涵盖架构设计、性能优化和测试调试三个方面。

## 目录

1. [架构设计原则](#架构设计原则)
2. [性能优化](#性能优化)
3. [测试和调试](#测试和调试)

---

## 架构设计原则

### 1. 状态设计

#### 1.1 最小化状态

**原则：** 只在状态中保存必要的信息，避免冗余数据。

**反例：**
```python
class BadState(TypedDict):
    messages: List[BaseMessage]
    message_count: int  # 冗余：可以从 messages 计算
    last_message: str   # 冗余：可以从 messages 获取
    has_messages: bool  # 冗余：可以从 messages 判断
```

**正例：**
```python
class GoodState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# 需要时通过计算获取
def get_message_count(state: GoodState) -> int:
    return len(state["messages"])
```

#### 1.2 类型安全

**原则：** 使用 TypedDict 和类型注解确保状态类型安全。

**正例：**
```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph import add_messages

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    current_step: Literal["research", "write", "review"]
    iteration_count: int
    final_output: str | None
```

#### 1.3 不可变性

**原则：** 节点函数应返回新的状态更新，而不是修改现有状态。

**反例：**
```python
def bad_node(state: AgentState) -> AgentState:
    state["iteration_count"] += 1  # 直接修改状态
    return state
```

**正例：**
```python
def good_node(state: AgentState) -> dict:
    return {
        "iteration_count": state["iteration_count"] + 1
    }
```

#### 1.4 使用 Reducer 函数

**原则：** 对于复杂的状态更新逻辑，使用自定义 reducer 函数。

```python
from typing import Annotated

def merge_metadata(existing: dict, new: dict) -> dict:
    """合并元数据，新值覆盖旧值"""
    return {**existing, **new}

class State(TypedDict):
    metadata: Annotated[dict, merge_metadata]
    messages: Annotated[List[BaseMessage], add_messages]
```

### 2. 图结构设计

#### 2.1 节点粒度

**原则：** 每个节点应该有单一职责，但不要过度拆分。

**过度拆分（反例）：**
```python
def validate_input(state): ...
def parse_input(state): ...
def normalize_input(state): ...
# 三个节点做的事情太相似，应该合并
```

**合理粒度（正例）：**
```python
def process_input(state: State) -> dict:
    """验证、解析和规范化输入"""
    validated = validate(state["input"])
    parsed = parse(validated)
    normalized = normalize(parsed)
    return {"processed_input": normalized}

def generate_response(state: State) -> dict:
    """生成响应"""
    ...

def format_output(state: State) -> dict:
    """格式化输出"""
    ...
```

#### 2.2 边的条件设计

**原则：** 条件函数应该简单、可测试，避免复杂逻辑。

**反例：**
```python
def complex_router(state: State) -> str:
    if state["count"] > 5 and state["quality"] < 0.8:
        if state["has_fallback"]:
            return "fallback"
        else:
            return "retry"
    elif state["count"] <= 5:
        return "continue"
    else:
        return "end"
```

**正例：**
```python
def should_retry(state: State) -> bool:
    return state["count"] <= 5 and state["quality"] < 0.8

def has_fallback(state: State) -> bool:
    return state["has_fallback"]

def route_next_step(state: State) -> str:
    if should_retry(state):
        return "retry"
    elif has_fallback(state):
        return "fallback"
    else:
        return "end"
```

#### 2.3 循环检测和防护

**原则：** 在可能产生循环的图中，添加循环检测机制。

```python
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    iteration_count: int
    max_iterations: int

def check_should_continue(state: State) -> str:
    """防止无限循环"""
    if state["iteration_count"] >= state["max_iterations"]:
        return "max_iterations_reached"

    # 检查是否满足结束条件
    if is_task_complete(state):
        return "end"

    return "continue"

# 在图中使用
graph.add_conditional_edges(
    "agent",
    check_should_continue,
    {
        "continue": "agent",
        "end": END,
        "max_iterations_reached": "fallback_handler"
    }
)
```

#### 2.4 错误处理节点

**原则：** 为关键节点添加错误处理路径。

```python
def risky_operation(state: State) -> dict:
    try:
        result = perform_operation(state)
        return {"result": result, "error": None}
    except Exception as e:
        return {"result": None, "error": str(e)}

def error_handler(state: State) -> dict:
    """处理错误情况"""
    error_msg = state.get("error")
    return {
        "messages": [SystemMessage(content=f"Error occurred: {error_msg}")]
    }

# 在图中使用
def route_after_operation(state: State) -> str:
    return "error_handler" if state.get("error") else "next_step"

graph.add_conditional_edges(
    "risky_operation",
    route_after_operation,
    {
        "next_step": "continue_processing",
        "error_handler": "error_handler"
    }
)
```

### 3. 模式选择

#### 3.1 何时使用不同模式

**Agent Executor（代理执行器）：**
- 需要动态工具调用
- 任务需要多步推理
- 工具选择依赖上下文

```python
# 适用场景：客户支持、数据分析、研究助手
graph.add_node("agent", call_model)
graph.add_node("tools", tool_executor)
graph.add_conditional_edges("agent", should_continue)
```

**Multi-Agent（多代理）：**
- 需要专业化分工
- 不同角色有不同能力
- 需要协作完成复杂任务

```python
# 适用场景：内容创作（研究员+作家+编辑）、软件开发（架构师+开发者+测试员）
graph.add_node("researcher", researcher_agent)
graph.add_node("writer", writer_agent)
graph.add_node("editor", editor_agent)
```

**Plan-and-Execute（计划执行）：**
- 任务可以分解为子任务
- 需要先规划再执行
- 执行结果可能影响计划

```python
# 适用场景：项目管理、复杂问题求解、长期目标
graph.add_node("planner", create_plan)
graph.add_node("executor", execute_step)
graph.add_node("replanner", update_plan)
```

**Reflection（反思）：**
- 需要自我评估和改进
- 输出质量要求高
- 可以通过迭代提升

```python
# 适用场景：内容生成、代码生成、创意写作
graph.add_node("generator", generate_content)
graph.add_node("critic", critique_content)
graph.add_conditional_edges("critic", should_regenerate)
```

#### 3.2 模式组合

**原则：** 可以组合多个模式以满足复杂需求。

**示例：Plan-and-Execute + Reflection**
```python
class State(TypedDict):
    plan: List[str]
    current_step: int
    step_results: List[str]
    critique: str | None
    messages: Annotated[List[BaseMessage], add_messages]

def planner(state: State) -> dict:
    """创建执行计划"""
    ...

def executor(state: State) -> dict:
    """执行当前步骤"""
    ...

def critic(state: State) -> dict:
    """评估执行结果"""
    ...

def should_revise(state: State) -> str:
    """决定是否需要修订"""
    if state["critique"] and "needs_revision" in state["critique"]:
        return "revise"
    return "continue"

# 构建组合图
graph.add_node("planner", planner)
graph.add_node("executor", executor)
graph.add_node("critic", critic)
graph.add_conditional_edges("critic", should_revise, {
    "revise": "executor",
    "continue": "next_step"
})
```

---

## 性能优化

### 1. Checkpointing

#### 1.1 何时使用 Checkpointing

**使用场景：**
- 长时间运行的工作流
- 需要人工审核的流程
- 可能失败需要重试的操作
- 需要保存中间状态的应用

**不需要使用的场景：**
- 简单的单次调用
- 无状态的转换
- 不需要恢复的短流程

#### 1.2 存储选择

**MemorySaver（内存存储）：**
```python
from langgraph.checkpoint.memory import MemorySaver

# 适用于：开发测试、短期会话、单机应用
memory = MemorySaver()
graph = graph.compile(checkpointer=memory)
```

**SqliteSaver（SQLite 存储）：**
```python
from langgraph.checkpoint.sqlite import SqliteSaver

# 适用于：持久化需求、中小规模应用、本地部署
with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    graph = graph.compile(checkpointer=checkpointer)
```

**PostgresSaver（PostgreSQL 存储）：**
```python
from langgraph.checkpoint.postgres import PostgresSaver

# 适用于：生产环境、高并发、分布式系统
checkpointer = PostgresSaver.from_conn_string("postgresql://...")
graph = graph.compile(checkpointer=checkpointer)
```

#### 1.3 Checkpoint 配置优化

```python
# 配置 checkpoint 保存策略
config = {
    "configurable": {
        "thread_id": "user-123",
        "checkpoint_ns": "my-app",  # 命名空间隔离
    }
}

# 只在关键节点保存 checkpoint
graph = StateGraph(State)
graph.add_node("critical_step", critical_operation, checkpoint=True)
graph.add_node("fast_step", fast_operation, checkpoint=False)
```

### 2. 异步处理

#### 2.1 并发节点执行

**原则：** 对于独立的操作，使用并发执行提升性能。

```python
from langgraph.graph import StateGraph, START

# 定义可以并发执行的节点
def fetch_data_a(state: State) -> dict:
    # 独立的数据获取操作
    data = fetch_from_source_a()
    return {"data_a": data}

def fetch_data_b(state: State) -> dict:
    # 独立的数据获取操作
    data = fetch_from_source_b()
    return {"data_b": data}

def combine_results(state: State) -> dict:
    # 合并并发结果
    combined = merge(state["data_a"], state["data_b"])
    return {"result": combined}

# 构建并发图
graph = StateGraph(State)
graph.add_node("fetch_a", fetch_data_a)
graph.add_node("fetch_b", fetch_data_b)
graph.add_node("combine", combine_results)

# 并发执行 fetch_a 和 fetch_b
graph.add_edge(START, "fetch_a")
graph.add_edge(START, "fetch_b")

# 等待两者完成后执行 combine
graph.add_edge("fetch_a", "combine")
graph.add_edge("fetch_b", "combine")
```

#### 2.2 流式输出

**原则：** 对于长时间运行的操作，使用流式输出提升用户体验。

```python
# 流式执行图
async def stream_graph_execution():
    config = {"configurable": {"thread_id": "1"}}

    async for event in graph.astream_events(
        {"messages": [HumanMessage(content="Hello")]},
        config,
        version="v2"
    ):
        kind = event["event"]

        # 流式输出 LLM tokens
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                print(content, end="", flush=True)

        # 节点开始/结束事件
        elif kind == "on_chain_start":
            print(f"\n[Starting {event['name']}]")
        elif kind == "on_chain_end":
            print(f"\n[Finished {event['name']}]")
```

#### 2.3 异步节点函数

```python
import asyncio
from typing import Any

async def async_node(state: State) -> dict:
    """异步节点函数"""
    # 并发执行多个异步操作
    results = await asyncio.gather(
        fetch_data_async(state["query"]),
        process_data_async(state["data"]),
        validate_async(state["input"])
    )

    return {
        "fetched": results[0],
        "processed": results[1],
        "validated": results[2]
    }

# 使用异步执行
async def run_async_graph():
    result = await graph.ainvoke(initial_state, config)
    return result
```

### 3. Token 优化

#### 3.1 上下文管理

**原则：** 控制传递给 LLM 的上下文大小，避免不必要的 token 消耗。

```python
def trim_messages(messages: List[BaseMessage], max_tokens: int = 4000) -> List[BaseMessage]:
    """保留最近的消息，控制 token 数量"""
    # 始终保留系统消息
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    other_messages = [m for m in messages if not isinstance(m, SystemMessage)]

    # 从最新消息开始累积
    trimmed = []
    token_count = 0

    for msg in reversed(other_messages):
        msg_tokens = estimate_tokens(msg.content)
        if token_count + msg_tokens > max_tokens:
            break
        trimmed.insert(0, msg)
        token_count += msg_tokens

    return system_messages + trimmed

def agent_node(state: State) -> dict:
    """使用修剪后的消息"""
    trimmed = trim_messages(state["messages"])
    response = model.invoke(trimmed)
    return {"messages": [response]}
```

#### 3.2 提示词优化

**原则：** 使用简洁、明确的提示词，避免冗余信息。

**反例：**
```python
prompt = """
You are a helpful AI assistant. You should always be polite and professional.
When answering questions, make sure to provide detailed and accurate information.
If you don't know something, admit it. Always format your responses clearly.
Now, please help me with the following task: {task}
Remember to follow all the guidelines mentioned above.
"""
```

**正例：**
```python
prompt = """You are a helpful assistant. Answer accurately and concisely.

Task: {task}"""
```

#### 3.3 缓存策略

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_system_prompt(role: str) -> str:
    """缓存系统提示词"""
    return load_prompt_template(role)

def create_messages(state: State) -> List[BaseMessage]:
    """复用缓存的系统提示词"""
    system_prompt = get_system_prompt(state["role"])
    return [
        SystemMessage(content=system_prompt),
        *state["messages"]
    ]
```

---

## 测试和调试

### 1. 单元测试

#### 1.1 测试节点函数

**原则：** 节点函数应该是纯函数，易于测试。

```python
import pytest
from your_graph import process_input, State

def test_process_input_valid():
    """测试有效输入"""
    state: State = {
        "input": "valid input",
        "processed": None
    }

    result = process_input(state)

    assert result["processed"] is not None
    assert "error" not in result

def test_process_input_invalid():
    """测试无效输入"""
    state: State = {
        "input": "",
        "processed": None
    }

    result = process_input(state)

    assert "error" in result
    assert result["error"] == "Input cannot be empty"

def test_process_input_immutability():
    """测试不可变性"""
    state: State = {
        "input": "test",
        "processed": None
    }

    original_state = state.copy()
    result = process_input(state)

    # 确保原始状态未被修改
    assert state == original_state
```

#### 1.2 测试条件函数

```python
from your_graph import should_continue, route_next_step

def test_should_continue_max_iterations():
    """测试最大迭代次数"""
    state: State = {
        "iteration_count": 10,
        "max_iterations": 10
    }

    result = should_continue(state)

    assert result == "max_iterations_reached"

def test_route_next_step_retry():
    """测试重试路由"""
    state: State = {
        "count": 3,
        "quality": 0.5,
        "has_fallback": False
    }

    result = route_next_step(state)

    assert result == "retry"

@pytest.mark.parametrize("count,quality,expected", [
    (3, 0.5, "retry"),
    (6, 0.5, "fallback"),
    (6, 0.9, "end"),
])
def test_route_next_step_parametrized(count, quality, expected):
    """参数化测试路由逻辑"""
    state: State = {
        "count": count,
        "quality": quality,
        "has_fallback": True
    }

    result = route_next_step(state)

    assert result == expected
```

### 2. 集成测试

#### 2.1 测试完整图

```python
import pytest
from your_graph import create_graph, State

@pytest.fixture
def graph():
    """创建测试图实例"""
    return create_graph()

def test_graph_execution_success(graph):
    """测试成功执行路径"""
    initial_state: State = {
        "messages": [HumanMessage(content="Hello")],
        "iteration_count": 0,
        "max_iterations": 5
    }

    config = {"configurable": {"thread_id": "test-1"}}
    result = graph.invoke(initial_state, config)

    assert result["iteration_count"] > 0
    assert len(result["messages"]) > 1
    assert result["iteration_count"] <= result["max_iterations"]

def test_graph_execution_max_iterations(graph):
    """测试达到最大迭代次数"""
    initial_state: State = {
        "messages": [HumanMessage(content="Complex task")],
        "iteration_count": 0,
        "max_iterations": 2
    }

    config = {"configurable": {"thread_id": "test-2"}}
    result = graph.invoke(initial_state, config)

    assert result["iteration_count"] == result["max_iterations"]

async def test_graph_streaming(graph):
    """测试流式执行"""
    initial_state: State = {
        "messages": [HumanMessage(content="Hello")]
    }

    config = {"configurable": {"thread_id": "test-3"}}
    events = []

    async for event in graph.astream(initial_state, config):
        events.append(event)

    assert len(events) > 0
    assert any("messages" in event for event in events)
```

#### 2.2 Mock LLM 调用

```python
from unittest.mock import Mock, patch
from langchain_core.messages import AIMessage

def test_agent_with_mock_llm(graph):
    """使用 Mock LLM 测试代理"""
    mock_response = AIMessage(content="Mocked response")

    with patch("your_graph.model.invoke", return_value=mock_response):
        initial_state: State = {
            "messages": [HumanMessage(content="Test")]
        }

        result = graph.invoke(initial_state)

        assert len(result["messages"]) == 2
        assert result["messages"][-1].content == "Mocked response"

@pytest.fixture
def mock_llm():
    """创建可配置的 Mock LLM"""
    mock = Mock()
    mock.invoke.return_value = AIMessage(content="Test response")
    return mock

def test_agent_with_fixture(mock_llm):
    """使用 fixture 测试"""
    graph = create_graph(model=mock_llm)

    result = graph.invoke({"messages": [HumanMessage(content="Test")]})

    assert mock_llm.invoke.called
    assert len(result["messages"]) == 2
```

#### 2.3 测试 Checkpointing

```python
from langgraph.checkpoint.memory import MemorySaver

def test_checkpoint_resume():
    """测试从 checkpoint 恢复"""
    checkpointer = MemorySaver()
    graph = create_graph().compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "test-checkpoint"}}

    # 第一次执行
    initial_state: State = {
        "messages": [HumanMessage(content="Start")],
        "step": 1
    }
    result1 = graph.invoke(initial_state, config)

    # 从 checkpoint 恢复并继续
    result2 = graph.invoke(
        {"messages": [HumanMessage(content="Continue")]},
        config
    )

    # 验证状态延续
    assert len(result2["messages"]) > len(result1["messages"])
    assert result2["step"] > result1["step"]
```

### 3. 调试技巧

#### 3.1 日志记录

**原则：** 在关键节点添加结构化日志。

```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def agent_node(state: State) -> dict:
    """带日志的代理节点"""
    logger.info(
        "Agent node started",
        extra={
            "timestamp": datetime.now().isoformat(),
            "iteration": state["iteration_count"],
            "message_count": len(state["messages"])
        }
    )

    try:
        response = model.invoke(state["messages"])

        logger.info(
            "Agent node completed",
            extra={
                "response_length": len(response.content),
                "iteration": state["iteration_count"]
            }
        )

        return {"messages": [response]}

    except Exception as e:
        logger.error(
            "Agent node failed",
            extra={
                "error": str(e),
                "iteration": state["iteration_count"]
            },
            exc_info=True
        )
        raise

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

#### 3.2 状态追踪

**原则：** 记录状态变化历史，便于调试。

```python
from typing import List, Dict, Any
from datetime import datetime

class StateTracker:
    """状态追踪器"""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def record(self, node_name: str, state: State):
        """记录状态快照"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "node": node_name,
            "state": {
                "iteration_count": state.get("iteration_count"),
                "message_count": len(state.get("messages", [])),
                "current_step": state.get("current_step")
            }
        })

    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return self.history

    def print_summary(self):
        """打印摘要"""
        print("\n=== State History ===")
        for entry in self.history:
            print(f"{entry['timestamp']} - {entry['node']}")
            print(f"  State: {entry['state']}")

# 在节点中使用
tracker = StateTracker()

def tracked_node(state: State) -> dict:
    """带追踪的节点"""
    tracker.record("tracked_node", state)
    result = process(state)
    return result
```

#### 3.3 可视化调试

**原则：** 使用可视化工具理解图结构和执行流程。

```python
from IPython.display import Image, display

def visualize_graph(graph):
    """可视化图结构"""
    try:
        display(Image(graph.get_graph().draw_mermaid_png()))
    except Exception:
        print(graph.get_graph().draw_ascii())

def trace_execution(graph, initial_state: State, config: dict):
    """追踪执行路径"""
    print("\n=== Execution Trace ===")

    for i, step in enumerate(graph.stream(initial_state, config)):
        print(f"\nStep {i + 1}:")
        for node_name, node_state in step.items():
            print(f"  Node: {node_name}")
            print(f"  State keys: {list(node_state.keys())}")

            # 打印关键状态信息
            if "messages" in node_state:
                print(f"  Messages: {len(node_state['messages'])}")
            if "iteration_count" in node_state:
                print(f"  Iteration: {node_state['iteration_count']}")

# 使用示例
graph = create_graph()
visualize_graph(graph)

initial_state = {"messages": [HumanMessage(content="Debug this")]}
config = {"configurable": {"thread_id": "debug-1"}}

trace_execution(graph, initial_state, config)
```

#### 3.4 断点调试

**原则：** 在复杂逻辑中使用断点和交互式调试。

```python
def debug_node(state: State) -> dict:
    """可调试的节点"""
    # 在关键位置设置断点
    import pdb; pdb.set_trace()

    # 或使用条件断点
    if state["iteration_count"] > 5:
        import pdb; pdb.set_trace()

    result = complex_operation(state)
    return result

# 使用 IPython 的调试器（更友好）
def debug_node_ipython(state: State) -> dict:
    """使用 IPython 调试器"""
    from IPython import embed

    # 在此处进入交互式 shell
    if state.get("debug_mode"):
        embed()

    result = complex_operation(state)
    return result
```

#### 3.5 性能分析

```python
import time
from functools import wraps

def profile_node(func):
    """节点性能分析装饰器"""
    @wraps(func)
    def wrapper(state: State) -> dict:
        start_time = time.time()

        result = func(state)

        elapsed = time.time() - start_time
        logger.info(
            f"Node {func.__name__} took {elapsed:.2f}s",
            extra={"node": func.__name__, "duration": elapsed}
        )

        return result

    return wrapper

@profile_node
def slow_node(state: State) -> dict:
    """被分析的节点"""
    # 执行操作
    result = expensive_operation(state)
    return result

# 完整图性能分析
def profile_graph_execution(graph, initial_state: State, config: dict):
    """分析图执行性能"""
    node_times = {}

    start_time = time.time()

    for step in graph.stream(initial_state, config):
        for node_name in step.keys():
            if node_name not in node_times:
                node_times[node_name] = []

            node_start = time.time()
            # 节点已执行，记录时间
            node_times[node_name].append(time.time() - node_start)

    total_time = time.time() - start_time

    print("\n=== Performance Profile ===")
    print(f"Total time: {total_time:.2f}s")
    print("\nNode times:")
    for node, times in node_times.items():
        avg_time = sum(times) / len(times)
        print(f"  {node}: {avg_time:.2f}s (called {len(times)} times)")
```

---

## 总结

本文档涵盖了 LangGraph 开发的核心最佳实践：

**架构设计：**
- 保持状态最小化和类型安全
- 合理设计节点粒度和边的条件
- 根据场景选择合适的模式
- 可以组合多个模式解决复杂问题

**性能优化：**
- 根据需求选择合适的 checkpointing 策略
- 使用并发和异步提升性能
- 优化上下文和提示词减少 token 消耗

**测试调试：**
- 编写全面的单元测试和集成测试
- 使用 Mock 隔离外部依赖
- 通过日志、追踪和可视化辅助调试
- 使用性能分析工具优化瓶颈

遵循这些最佳实践，可以构建高质量、高性能、易维护的 LangGraph 应用。
