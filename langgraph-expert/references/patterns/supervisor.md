# Supervisor 模式

## 概述

Supervisor 模式使用一个中心协调者(Supervisor)来管理和调度多个工作 Agent(Workers)。Supervisor 负责理解任务、分配工作、收集结果,而 Workers 专注于执行具体任务。

## 何时使用

### 适用场景

- **中心协调**: 需要统一的任务分配和结果汇总
- **动态调度**: 根据任务类型动态选择合适的 Worker
- **资源管理**: 需要控制 Worker 的并发执行
- **复杂工作流**: 任务需要多个步骤,每步由不同 Worker 完成
- **质量控制**: Supervisor 可以验证 Worker 的输出

### 不适用场景

- Agent 之间需要直接通信和协作
- 没有明确的任务分配逻辑
- 所有 Agent 地位平等,无需中心控制
- 需要层级化的多级管理

## 核心概念

### 1. Supervisor 节点

Supervisor 是系统的大脑:
- **任务理解**: 分析用户请求,确定需要哪些 Worker
- **任务分配**: 决定下一个执行的 Worker
- **结果汇总**: 收集 Worker 的输出,生成最终结果
- **流程控制**: 决定何时结束工作流

### 2. Worker 节点

Workers 是专门的执行者:
- **专注执行**: 只负责特定类型的任务
- **无需协调**: 不需要知道其他 Worker 的存在
- **返回 Supervisor**: 完成任务后总是返回 Supervisor

### 3. 任务分配

Supervisor 使用以下策略分配任务:
- **基于规则**: 根据预定义规则选择 Worker
- **基于 LLM**: 让 LLM 决定下一个 Worker
- **基于状态**: 根据当前状态选择 Worker

## 完整代码示例

### 场景: 客户服务系统

创建一个包含 Supervisor 和多个专门 Worker 的客户服务系统。

```python
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

# 1. 定义状态
class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    next_worker: str
    task_history: list[str]

# 2. 定义 Supervisor 的输出格式
class SupervisorDecision(BaseModel):
    """Supervisor 的决策"""
    next_worker: Literal["order_agent", "refund_agent", "support_agent", "FINISH"]
    reasoning: str

# 3. 初始化模型
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# 4. 创建 Supervisor
def create_supervisor():
    """创建 Supervisor 节点"""

    system_prompt = """你是客户服务团队的 Supervisor。
    你管理以下 Workers:

    1. order_agent: 处理订单查询、订单状态、配送信息
    2. refund_agent: 处理退款、退货、换货请求
    3. support_agent: 处理技术支持、产品咨询、一般问题

    你的职责:
    1. 分析客户的请求
    2. 选择最合适的 Worker 处理
    3. 如果任务完成,选择 FINISH
    4. 解释你的决策理由

    规则:
    - 每次只选择一个 Worker
    - 如果需要多个 Worker,按顺序调用
    - 当所有必要的信息都已收集,选择 FINISH
    """

    def supervisor_node(state: SupervisorState) -> SupervisorState:
        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"]
        ]

        # 使用结构化输出
        response = model.with_structured_output(SupervisorDecision).invoke(messages)

        # 记录决策
        task_history = state.get("task_history", [])
        task_history.append(f"Supervisor -> {response.next_worker}: {response.reasoning}")

        return {
            "next_worker": response.next_worker,
            "task_history": task_history,
            "messages": [HumanMessage(content=f"[Supervisor] 分配给: {response.next_worker}")]
        }

    return supervisor_node

# 5. 创建 Worker Agents
def create_order_agent():
    """处理订单相关问题"""

    system_prompt = """你是订单处理专员。
    你负责:
    - 查询订单状态
    - 提供配送信息
    - 更新订单详情

    完成任务后,简洁地报告结果。"""

    def order_agent(state: SupervisorState) -> SupervisorState:
        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"]
        ]

        response = model.invoke(messages)

        return {
            "messages": [response]
        }

    return order_agent

def create_refund_agent():
    """处理退款相关问题"""

    system_prompt = """你是退款处理专员。
    你负责:
    - 处理退款请求
    - 处理退货流程
    - 处理换货请求

    完成任务后,简洁地报告结果。"""

    def refund_agent(state: SupervisorState) -> SupervisorState:
        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"]
        ]

        response = model.invoke(messages)

        return {
            "messages": [response]
        }

    return refund_agent

def create_support_agent():
    """处理技术支持问题"""

    system_prompt = """你是技术支持专员。
    你负责:
    - 解答产品使用问题
    - 提供技术支持
    - 回答一般咨询

    完成任务后,简洁地报告结果。"""

    def support_agent(state: SupervisorState) -> SupervisorState:
        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"]
        ]

        response = model.invoke(messages)

        return {
            "messages": [response]
        }

    return support_agent

# 6. 定义路由函数
def route_worker(state: SupervisorState) -> Literal["order_agent", "refund_agent", "support_agent", "supervisor", "__end__"]:
    """路由到下一个节点"""
    next_worker = state.get("next_worker", "FINISH")

    if next_worker == "FINISH":
        return END

    return next_worker

# 7. 构建图
def create_supervisor_graph():
    workflow = StateGraph(SupervisorState)

    # 添加节点
    workflow.add_node("supervisor", create_supervisor())
    workflow.add_node("order_agent", create_order_agent())
    workflow.add_node("refund_agent", create_refund_agent())
    workflow.add_node("support_agent", create_support_agent())

    # 添加边
    # 从 START 到 Supervisor
    workflow.add_edge(START, "supervisor")

    # 从 Supervisor 到 Workers 或 END
    workflow.add_conditional_edges(
        "supervisor",
        route_worker,
        {
            "order_agent": "order_agent",
            "refund_agent": "refund_agent",
            "support_agent": "support_agent",
            END: END
        }
    )

    # 所有 Workers 完成后返回 Supervisor
    workflow.add_edge("order_agent", "supervisor")
    workflow.add_edge("refund_agent", "supervisor")
    workflow.add_edge("support_agent", "supervisor")

    return workflow.compile()

# 8. 使用示例
if __name__ == "__main__":
    app = create_supervisor_graph()

    # 测试案例 1: 订单查询
    print("=== 测试案例 1: 订单查询 ===")
    result = app.invoke({
        "messages": [HumanMessage(content="我想查询订单 #12345 的配送状态")],
        "next_worker": "",
        "task_history": []
    })

    print("\n任务历史:")
    for task in result["task_history"]:
        print(f"  {task}")

    print("\n最终消息:")
    print(result["messages"][-1].content)

    # 测试案例 2: 复杂请求(需要多个 Worker)
    print("\n=== 测试案例 2: 复杂请求 ===")
    result = app.invoke({
        "messages": [HumanMessage(content="我的订单 #12345 有问题,想要退款")],
        "next_worker": "",
        "task_history": []
    })

    print("\n任务历史:")
    for task in result["task_history"]:
        print(f"  {task}")
```

### 高级示例: 带工具的 Supervisor

```python
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# 1. 定义工具
@tool
def query_order(order_id: str) -> dict:
    """查询订单信息"""
    # 实际实现会查询数据库
    return {
        "order_id": order_id,
        "status": "已发货",
        "tracking": "SF1234567890"
    }

@tool
def process_refund(order_id: str, reason: str) -> dict:
    """处理退款"""
    # 实际实现会调用支付系统
    return {
        "refund_id": "RF" + order_id,
        "status": "处理中",
        "estimated_days": 3
    }

@tool
def search_knowledge_base(query: str) -> str:
    """搜索知识库"""
    # 实际实现会查询知识库
    return f"关于 '{query}' 的帮助文档..."

# 2. 为每个 Worker 分配工具
order_tools = [query_order]
refund_tools = [process_refund]
support_tools = [search_knowledge_base]

# 3. 创建基于工具的 Workers
def create_tool_based_workers(model):
    order_agent = create_react_agent(
        model,
        order_tools,
        state_modifier="你是订单处理专员,使用工具查询和处理订单"
    )

    refund_agent = create_react_agent(
        model,
        refund_tools,
        state_modifier="你是退款处理专员,使用工具处理退款请求"
    )

    support_agent = create_react_agent(
        model,
        support_tools,
        state_modifier="你是技术支持专员,使用知识库回答问题"
    )

    return order_agent, refund_agent, support_agent
```

### 并行 Workers 示例

```python
from langgraph.graph import Send

# 1. 定义支持并行的状态
class ParallelSupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    workers_to_call: list[str]
    worker_results: dict[str, str]

# 2. Supervisor 决定并行调用哪些 Workers
class ParallelSupervisorDecision(BaseModel):
    workers: list[Literal["order_agent", "refund_agent", "support_agent"]]
    reasoning: str
    is_finished: bool

def parallel_supervisor(state: ParallelSupervisorState):
    """Supervisor 可以并行调用多个 Workers"""
    system_prompt = """分析请求,决定需要调用哪些 Workers。
    你可以同时调用多个 Workers 来并行处理。"""

    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"]
    ]

    decision = model.with_structured_output(ParallelSupervisorDecision).invoke(messages)

    if decision.is_finished:
        return {"workers_to_call": []}

    # 返回需要并行调用的 Workers
    return [Send(worker, state) for worker in decision.workers]

# 3. 构建支持并行的图
def create_parallel_supervisor_graph():
    workflow = StateGraph(ParallelSupervisorState)

    workflow.add_node("supervisor", parallel_supervisor)
    workflow.add_node("order_agent", create_order_agent())
    workflow.add_node("refund_agent", create_refund_agent())
    workflow.add_node("support_agent", create_support_agent())

    # Supervisor 可以并行发送到多个 Workers
    workflow.add_conditional_edges(START, parallel_supervisor)

    # Workers 完成后返回 Supervisor
    workflow.add_edge("order_agent", "supervisor")
    workflow.add_edge("refund_agent", "supervisor")
    workflow.add_edge("support_agent", "supervisor")

    return workflow.compile()
```

## 最佳实践

### 1. 清晰的 Worker 定义

```python
# 好的做法: 明确的 Worker 职责和能力
WORKERS = {
    "order_agent": {
        "description": "处理订单查询、状态更新、配送跟踪",
        "tools": [query_order, update_order],
        "capabilities": ["查询", "更新", "跟踪"]
    },
    "refund_agent": {
        "description": "处理退款、退货、换货",
        "tools": [process_refund, create_return],
        "capabilities": ["退款", "退货", "换货"]
    }
}

# 在 Supervisor 提示词中包含这些信息
supervisor_prompt = f"""你管理以下 Workers:
{format_workers(WORKERS)}
"""
```

### 2. 结构化的决策输出

```python
# 好的做法: 使用 Pydantic 模型
class SupervisorDecision(BaseModel):
    next_worker: str
    reasoning: str
    confidence: float
    estimated_time: int

# 不好的做法: 解析文本输出
# response = "我认为应该调用 order_agent..."  # 容易出错
```

### 3. 任务历史跟踪

```python
class TaskRecord(BaseModel):
    worker: str
    action: str
    timestamp: str
    result: str

class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    task_history: list[TaskRecord]

def supervisor_with_history(state):
    # 在提示词中包含历史
    history_summary = "\n".join([
        f"- {r.worker}: {r.action} -> {r.result}"
        for r in state.get("task_history", [])
    ])

    prompt = f"""已完成的任务:
{history_summary}

当前请求: {state['messages'][-1].content}
"""
    # ...
```

### 4. Worker 超时和重试

```python
import time
from functools import wraps

def with_timeout(timeout_seconds: int):
    def decorator(func):
        @wraps(func)
        def wrapper(state):
            start_time = time.time()

            try:
                result = func(state)

                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    return {
                        "messages": [HumanMessage(
                            content=f"[Worker 超时] 执行时间: {elapsed:.2f}s"
                        )]
                    }

                return result

            except Exception as e:
                return {
                    "messages": [HumanMessage(
                        content=f"[Worker 错误] {str(e)}"
                    )]
                }

        return wrapper
    return decorator

# 使用
@with_timeout(30)
def order_agent(state):
    # Worker 逻辑
    pass
```

### 5. 动态 Worker 注册

```python
class WorkerRegistry:
    def __init__(self):
        self.workers = {}

    def register(self, name: str, agent_func, description: str):
        self.workers[name] = {
            "func": agent_func,
            "description": description
        }

    def get_worker_descriptions(self) -> str:
        return "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.workers.items()
        ])

    def get_worker(self, name: str):
        return self.workers[name]["func"]

# 使用
registry = WorkerRegistry()
registry.register("order_agent", create_order_agent(), "处理订单")
registry.register("refund_agent", create_refund_agent(), "处理退款")

# 在 Supervisor 中使用
supervisor_prompt = f"""你管理以下 Workers:
{registry.get_worker_descriptions()}
"""
```

## 常见陷阱

### 1. Supervisor 过载

**问题**: Supervisor 承担了太多逻辑,变得复杂难维护

```python
# 错误示例: Supervisor 做了太多事情
def supervisor(state):
    # 解析请求
    parsed = parse_request(state["messages"][-1])

    # 验证数据
    if not validate(parsed):
        return error_response()

    # 查询数据库
    data = query_database(parsed)

    # 处理业务逻辑
    result = process_business_logic(data)

    # 选择 Worker
    worker = select_worker(result)

    return {"next_worker": worker}
```

**解决方案**: Supervisor 只负责协调,具体逻辑交给 Workers

```python
# 正确做法: Supervisor 只做决策
def supervisor(state):
    # 简单的决策逻辑
    decision = model.with_structured_output(SupervisorDecision).invoke(state["messages"])
    return {"next_worker": decision.next_worker}

# 复杂逻辑在 Workers 中
def order_agent(state):
    # 这里处理所有订单相关的复杂逻辑
    parsed = parse_order_request(state["messages"][-1])
    data = query_order_database(parsed)
    result = process_order(data)
    return {"messages": [result]}
```

### 2. Worker 之间的依赖

**问题**: Workers 需要其他 Workers 的输出

```python
# 错误示例: Worker B 依赖 Worker A 的输出
def worker_b(state):
    # 需要 worker_a 的结果,但可能还没执行
    worker_a_result = state.get("worker_a_result")
    if not worker_a_result:
        # 怎么办?
        pass
```

**解决方案**: 通过 Supervisor 管理依赖

```python
class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    completed_workers: set[str]
    worker_outputs: dict[str, str]

def supervisor(state):
    completed = state.get("completed_workers", set())

    # 检查依赖
    if "worker_a" not in completed:
        return {"next_worker": "worker_a"}

    # worker_a 完成后才调用 worker_b
    if "worker_b" not in completed:
        return {"next_worker": "worker_b"}

    return {"next_worker": "FINISH"}

def worker_b(state):
    # 现在可以安全地访问 worker_a 的输出
    worker_a_output = state["worker_outputs"]["worker_a"]
    # 处理逻辑
    pass
```

### 3. 无限循环

**问题**: Supervisor 不断调用同一个 Worker

```python
# 错误示例: 没有终止条件
def supervisor(state):
    # 总是返回同一个 Worker
    return {"next_worker": "order_agent"}
```

**解决方案**: 添加循环检测和最大迭代次数

```python
class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    iteration_count: int
    max_iterations: int
    worker_call_count: dict[str, int]

def supervisor(state):
    # 检查总迭代次数
    if state.get("iteration_count", 0) >= state.get("max_iterations", 10):
        return {"next_worker": "FINISH"}

    # 检查单个 Worker 的调用次数
    worker_calls = state.get("worker_call_count", {})
    next_worker = decide_next_worker(state)

    if worker_calls.get(next_worker, 0) >= 3:
        # 同一个 Worker 被调用太多次,可能有问题
        return {"next_worker": "FINISH"}

    # 更新计数
    worker_calls[next_worker] = worker_calls.get(next_worker, 0) + 1

    return {
        "next_worker": next_worker,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "worker_call_count": worker_calls
    }
```

### 4. 状态膨胀

**问题**: 状态对象变得越来越大

```python
# 错误示例: 不断添加数据到状态
def worker(state):
    # 每次都添加大量数据
    return {
        "messages": [...],
        "large_data_1": "...",  # 几 MB 的数据
        "large_data_2": "...",  # 更多数据
        # 状态越来越大
    }
```

**解决方案**: 只保留必要的数据,使用引用

```python
# 正确做法: 使用外部存储
class DataStore:
    def __init__(self):
        self.data = {}

    def store(self, key: str, value: any) -> str:
        data_id = generate_id()
        self.data[data_id] = value
        return data_id

    def retrieve(self, data_id: str) -> any:
        return self.data.get(data_id)

store = DataStore()

def worker(state):
    # 处理大量数据
    large_result = process_large_data()

    # 存储到外部,只在状态中保留引用
    data_id = store.store("worker_result", large_result)

    return {
        "messages": [...],
        "worker_result_id": data_id  # 只保留 ID
    }

def next_worker(state):
    # 需要时再取回数据
    data_id = state["worker_result_id"]
    data = store.retrieve(data_id)
    # 使用数据
    pass
```

### 5. 错误处理不当

**问题**: Worker 失败导致整个流程中断

```python
# 错误示例: 没有错误处理
def worker(state):
    result = risky_operation()  # 可能抛出异常
    return {"messages": [result]}
```

**解决方案**: 添加错误处理和恢复机制

```python
class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    failed_workers: list[str]
    retry_count: dict[str, int]

def safe_worker(worker_name: str, worker_func):
    def wrapper(state):
        try:
            return worker_func(state)
        except Exception as e:
            # 记录失败
            failed = state.get("failed_workers", [])
            failed.append(worker_name)

            return {
                "messages": [HumanMessage(
                    content=f"[{worker_name} 失败] {str(e)}"
                )],
                "failed_workers": failed
            }
    return wrapper

def supervisor(state):
    failed = state.get("failed_workers", [])
    retry_count = state.get("retry_count", {})

    next_worker = decide_next_worker(state)

    # 检查是否失败过
    if next_worker in failed:
        # 检查重试次数
        if retry_count.get(next_worker, 0) >= 2:
            # 超过重试次数,跳过这个 Worker
            return {"next_worker": "FINISH"}

        # 重试
        retry_count[next_worker] = retry_count.get(next_worker, 0) + 1
        return {
            "next_worker": next_worker,
            "retry_count": retry_count
        }

    return {"next_worker": next_worker}
```

## 调试技巧

### 1. 可视化 Supervisor 决策

```python
def visualize_supervisor_decisions(app, initial_state):
    """可视化 Supervisor 的决策过程"""
    decisions = []

    for step in app.stream(initial_state):
        if "supervisor" in step:
            state = step["supervisor"]
            decisions.append({
                "worker": state.get("next_worker"),
                "reasoning": state.get("reasoning", "")
            })

    print("Supervisor 决策链:")
    for i, decision in enumerate(decisions, 1):
        print(f"{i}. {decision['worker']}: {decision['reasoning']}")
```

### 2. Worker 性能监控

```python
import time

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}

    def track_worker(self, worker_name: str, worker_func):
        def wrapper(state):
            start_time = time.time()
            result = worker_func(state)
            elapsed = time.time() - start_time

            if worker_name not in self.metrics:
                self.metrics[worker_name] = []

            self.metrics[worker_name].append(elapsed)

            return result
        return wrapper

    def report(self):
        print("Worker 性能报告:")
        for worker, times in self.metrics.items():
            avg_time = sum(times) / len(times)
            print(f"  {worker}: 平均 {avg_time:.2f}s, 调用 {len(times)} 次")

monitor = PerformanceMonitor()

# 包装 Workers
order_agent = monitor.track_worker("order_agent", create_order_agent())
```

### 3. 交互式调试

```python
def interactive_supervisor(state):
    """允许人工干预 Supervisor 决策"""
    # 让 LLM 做决策
    decision = model.with_structured_output(SupervisorDecision).invoke(state["messages"])

    print(f"\nSupervisor 建议: {decision.next_worker}")
    print(f"理由: {decision.reasoning}")

    # 询问用户
    user_input = input("接受建议? (y/n/自定义 Worker 名称): ")

    if user_input.lower() == 'y':
        return {"next_worker": decision.next_worker}
    elif user_input.lower() == 'n':
        return {"next_worker": "FINISH"}
    else:
        return {"next_worker": user_input}
```

## 与其他模式的对比

| 特性 | Supervisor | Multi-Agent | Hierarchical |
|------|------------|-------------|--------------|
| 控制结构 | 单层中心化 | 分布式 | 多层层级化 |
| 决策者 | Supervisor | 每个 Agent | 每层的管理者 |
| Worker 通信 | 通过 Supervisor | 直接通信 | 通过上级 |
| 适用规模 | 中到大型 | 小到中型 | 大型复杂系统 |
| 实现复杂度 | 较低 | 中等 | 较高 |
| 并行能力 | 容易实现 | 需要协调 | 天然支持 |

## 总结

Supervisor 模式适合需要中心协调的多 Agent 系统。关键要点:

1. **清晰的角色**: Supervisor 负责协调,Workers 负责执行
2. **结构化决策**: 使用 Pydantic 模型定义决策输出
3. **任务跟踪**: 记录任务历史和 Worker 状态
4. **错误处理**: 优雅地处理 Worker 失败和重试
5. **避免过载**: Supervisor 只做决策,不做具体业务逻辑
6. **依赖管理**: 通过 Supervisor 管理 Workers 之间的依赖
7. **性能监控**: 跟踪 Worker 性能和调用次数

通过遵循这些最佳实践,你可以构建高效、可维护的 Supervisor 系统。
