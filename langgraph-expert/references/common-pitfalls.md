# LangGraph 常见陷阱与最佳实践

本文档总结了在使用 LangGraph 开发过程中常见的错误模式及其解决方案。

## 目录

- [状态管理错误](#状态管理错误)
- [图结构错误](#图结构错误)
- [性能问题](#性能问题)
- [LLM 调用错误](#llm-调用错误)

---

## 状态管理错误

### 1. 状态突变（State Mutation）

#### ❌ 错误示例

```python
from typing import TypedDict

class State(TypedDict):
    messages: list[str]
    count: int

def bad_node(state: State) -> State:
    # 直接修改原始状态对象
    state["messages"].append("new message")
    state["count"] += 1
    return state
```

**问题：** 直接修改状态对象会导致：
- 破坏状态的不可变性原则
- Checkpointing 无法正确追踪变化
- 时间旅行调试失效
- 并发执行时出现竞态条件

#### ✅ 正确做法

```python
def good_node(state: State) -> State:
    # 返回新的状态更新
    return {
        "messages": state["messages"] + ["new message"],
        "count": state["count"] + 1
    }
```

**原因：** LangGraph 依赖不可变状态来实现可靠的 Checkpointing 和状态回溯。

---

### 2. 状态类型不一致

#### ❌ 错误示例

```python
from typing import TypedDict

class State(TypedDict):
    user_id: int
    metadata: dict

def bad_node(state: State) -> State:
    return {
        "user_id": "123",  # 应该是 int，却返回 str
        "metadata": None   # 应该是 dict，却返回 None
    }
```

**问题：**
- 类型不匹配导致运行时错误
- 下游节点假设类型错误
- 难以调试和维护

#### ✅ 正确做法

```python
from typing import TypedDict, Optional

class State(TypedDict):
    user_id: int
    metadata: dict

def good_node(state: State) -> State:
    return {
        "user_id": int(state.get("user_id", 0)),
        "metadata": state.get("metadata", {})
    }

# 或使用 Optional 类型
class BetterState(TypedDict):
    user_id: int
    metadata: Optional[dict]  # 明确允许 None
```

**原因：** 严格的类型一致性确保状态在整个图中的可预测性。

---

### 3. 缺少 Reducer 导致状态覆盖

#### ❌ 错误示例

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph

class State(TypedDict):
    messages: list[str]  # 没有 Reducer

def node1(state: State) -> State:
    return {"messages": ["msg1"]}

def node2(state: State) -> State:
    return {"messages": ["msg2"]}  # 覆盖了 node1 的消息

graph = StateGraph(State)
graph.add_node("node1", node1)
graph.add_node("node2", node2)
graph.add_edge("node1", "node2")
```

**问题：** `node2` 的消息会完全覆盖 `node1` 的消息，而不是追加。

#### ✅ 正确做法

```python
from typing import Annotated
from operator import add

class State(TypedDict):
    messages: Annotated[list[str], add]  # 使用 add reducer

def node1(state: State) -> State:
    return {"messages": ["msg1"]}

def node2(state: State) -> State:
    return {"messages": ["msg2"]}  # 追加到现有消息

# 最终状态: {"messages": ["msg1", "msg2"]}
```

**原因：** Reducer 定义了如何合并多个状态更新，避免意外覆盖。

---

## 图结构错误

### 1. 无限循环

#### ❌ 错误示例

```python
from langgraph.graph import StateGraph, END

def always_continue(state: State) -> str:
    return "continue"

graph = StateGraph(State)
graph.add_node("process", process_node)
graph.add_conditional_edges(
    "process",
    always_continue,
    {
        "continue": "process",  # 总是返回自己
        "end": END
    }
)
```

**问题：**
- 条件函数永远不返回 "end"
- 图会无限循环直到超时
- 消耗大量资源

#### ✅ 正确做法

```python
def safe_continue(state: State) -> str:
    # 添加终止条件
    if state.get("iteration_count", 0) >= 10:
        return "end"
    if state.get("goal_achieved", False):
        return "end"
    return "continue"

graph = StateGraph(State)
graph.add_node("process", process_node)
graph.add_conditional_edges(
    "process",
    safe_continue,
    {
        "continue": "process",
        "end": END
    }
)
```

**原因：** 始终提供明确的终止条件，防止无限循环。

---

### 2. 死节点（Unreachable Nodes）

#### ❌ 错误示例

```python
graph = StateGraph(State)
graph.add_node("start", start_node)
graph.add_node("process", process_node)
graph.add_node("orphan", orphan_node)  # 没有边指向它

graph.set_entry_point("start")
graph.add_edge("start", "process")
graph.add_edge("process", END)
# orphan 节点永远不会被执行
```

**问题：**
- `orphan` 节点无法到达
- 浪费代码和维护成本
- 可能是逻辑错误的信号

#### ✅ 正确做法

```python
# 方案1: 连接所有节点
graph = StateGraph(State)
graph.add_node("start", start_node)
graph.add_node("process", process_node)
graph.add_node("finalize", finalize_node)

graph.set_entry_point("start")
graph.add_edge("start", "process")
graph.add_edge("process", "finalize")
graph.add_edge("finalize", END)

# 方案2: 移除未使用的节点
# 如果节点不需要，直接删除
```

**原因：** 确保所有节点都有明确的执行路径，或移除不需要的节点。

---

### 3. 缺少入口点

#### ❌ 错误示例

```python
graph = StateGraph(State)
graph.add_node("node1", node1)
graph.add_node("node2", node2)
graph.add_edge("node1", "node2")
# 忘记设置入口点

app = graph.compile()  # 运行时错误
```

**问题：** 图不知道从哪里开始执行。

#### ✅ 正确做法

```python
graph = StateGraph(State)
graph.add_node("node1", node1)
graph.add_node("node2", node2)
graph.set_entry_point("node1")  # 明确设置入口点
graph.add_edge("node1", "node2")
graph.add_edge("node2", END)

app = graph.compile()
```

**原因：** 入口点定义了图的执行起点，是必需的。

---

## 性能问题

### 1. 过度 Checkpointing

#### ❌ 错误示例

```python
from langgraph.checkpoint.memory import MemorySaver

# 为每个小操作都保存 checkpoint
def process_items(state: State) -> State:
    results = []
    for item in state["items"]:
        # 每次迭代都触发 checkpoint
        results.append(process_single_item(item))
    return {"results": results}

memory = MemorySaver()
app = graph.compile(checkpointer=memory)

# 处理1000个项目 = 1000次 checkpoint
```

**问题：**
- 大量 I/O 操作降低性能
- 存储空间快速增长
- 序列化/反序列化开销大

#### ✅ 正确做法

```python
# 批量处理，减少 checkpoint 频率
def process_items_batch(state: State) -> State:
    batch_size = 100
    results = []

    for i in range(0, len(state["items"]), batch_size):
        batch = state["items"][i:i + batch_size]
        batch_results = [process_single_item(item) for item in batch]
        results.extend(batch_results)

    # 只在批次完成后返回状态
    return {"results": results}

# 或者只在关键节点使用 checkpointing
app = graph.compile(
    checkpointer=memory,
    # 只在特定节点保存
)
```

**原因：** 合理控制 checkpoint 频率，平衡可恢复性和性能。

---

### 2. 上下文过长

#### ❌ 错误示例

```python
def accumulate_messages(state: State) -> State:
    # 无限累积消息
    return {
        "messages": state["messages"] + [new_message]
    }

# 经过100次迭代后，messages 包含所有历史
# 导致 LLM 调用超出 token 限制
```

**问题：**
- 超出 LLM 上下文窗口
- API 调用失败或被截断
- 成本线性增长

#### ✅ 正确做法

```python
def accumulate_messages_with_limit(state: State) -> State:
    messages = state["messages"] + [new_message]

    # 方案1: 保留最近 N 条消息
    max_messages = 20
    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    # 方案2: 使用滑动窗口
    # 方案3: 定期总结历史消息

    return {"messages": messages}

def summarize_history(state: State) -> State:
    if len(state["messages"]) > 50:
        summary = llm.invoke("Summarize: " + str(state["messages"][:-10]))
        return {
            "messages": [summary] + state["messages"][-10:]
        }
    return {}
```

**原因：** 主动管理上下文长度，避免超出限制和成本失控。

---

### 3. 同步阻塞调用

#### ❌ 错误示例

```python
def sequential_llm_calls(state: State) -> State:
    # 串行调用多个 LLM
    result1 = llm.invoke(prompt1)  # 等待2秒
    result2 = llm.invoke(prompt2)  # 等待2秒
    result3 = llm.invoke(prompt3)  # 等待2秒
    # 总耗时: 6秒

    return {
        "results": [result1, result2, result3]
    }
```

**问题：** 串行调用浪费时间，用户体验差。

#### ✅ 正确做法

```python
import asyncio

async def parallel_llm_calls(state: State) -> State:
    # 并行调用多个 LLM
    results = await asyncio.gather(
        llm.ainvoke(prompt1),
        llm.ainvoke(prompt2),
        llm.ainvoke(prompt3)
    )
    # 总耗时: ~2秒（最慢的那个）

    return {"results": results}

# 使用异步图
app = graph.compile()
await app.ainvoke(initial_state)
```

**原因：** 并行化独立的 I/O 操作，显著提升性能。

---

## LLM 调用错误

### 1. 未处理 API 错误

#### ❌ 错误示例

```python
def call_llm(state: State) -> State:
    # 直接调用，不处理错误
    response = llm.invoke(state["prompt"])
    return {"response": response}

# 当 API 限流、超时或失败时，整个图崩溃
```

**问题：**
- 网络错误导致图执行失败
- 限流错误未重试
- 用户看到原始错误信息

#### ✅ 正确做法

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def call_llm_with_retry(prompt: str) -> str:
    try:
        return llm.invoke(prompt)
    except Exception as e:
        logging.error(f"LLM call failed: {e}")
        raise

def safe_call_llm(state: State) -> State:
    try:
        response = call_llm_with_retry(state["prompt"])
        return {"response": response, "error": None}
    except Exception as e:
        return {
            "response": None,
            "error": f"LLM 调用失败: {str(e)}"
        }
```

**原因：** 优雅处理 API 错误，提供重试机制和降级方案。

---

### 2. 忽略流式输出

#### ❌ 错误示例

```python
def generate_long_content(state: State) -> State:
    # 等待完整响应，用户长时间无反馈
    response = llm.invoke(long_prompt)
    return {"content": response}

# 用户等待30秒才看到结果
```

**问题：**
- 用户体验差，感觉应用卡死
- 无法提前取消
- 浪费已生成的部分内容

#### ✅ 正确做法

```python
def generate_long_content_streaming(state: State) -> State:
    chunks = []

    # 使用流式输出
    for chunk in llm.stream(long_prompt):
        chunks.append(chunk)
        # 实时发送给用户
        yield {"partial_content": "".join(chunks)}

    return {"content": "".join(chunks)}

# 或使用 astream_events
async def generate_with_events(state: State):
    async for event in app.astream_events(state):
        if event["event"] == "on_llm_stream":
            print(event["data"]["chunk"])
```

**原因：** 流式输出提供实时反馈，改善用户体验。

---

### 3. 硬编码 Prompt

#### ❌ 错误示例

```python
def analyze_text(state: State) -> State:
    # Prompt 硬编码在代码中
    prompt = f"Analyze this text: {state['text']}"
    response = llm.invoke(prompt)
    return {"analysis": response}

# 修改 prompt 需要改代码、重新部署
```

**问题：**
- Prompt 工程需要频繁修改代码
- 难以 A/B 测试不同 prompt
- 无法动态调整

#### ✅ 正确做法

```python
from langchain.prompts import PromptTemplate

# 使用 PromptTemplate
ANALYSIS_PROMPT = PromptTemplate.from_template(
    """分析以下文本：

文本: {text}

请提供：
1. 主题
2. 情感
3. 关键点
"""
)

def analyze_text(state: State) -> State:
    prompt = ANALYSIS_PROMPT.format(text=state["text"])
    response = llm.invoke(prompt)
    return {"analysis": response}

# 或从配置文件加载
import json

with open("prompts.json") as f:
    prompts = json.load(f)

def analyze_text_configurable(state: State) -> State:
    prompt_template = prompts["analysis"]
    prompt = prompt_template.format(text=state["text"])
    response = llm.invoke(prompt)
    return {"analysis": response}
```

**原因：** 分离 prompt 和代码，便于迭代和管理。

---

### 4. 未验证 LLM 输出格式

#### ❌ 错误示例

```python
def extract_json(state: State) -> State:
    prompt = "Extract JSON: " + state["text"]
    response = llm.invoke(prompt)

    # 假设 LLM 总是返回有效 JSON
    data = json.loads(response)
    return {"data": data}

# LLM 返回 "```json\n{...}\n```" 时崩溃
```

**问题：**
- LLM 输出格式不可预测
- 解析失败导致图崩溃
- 难以调试

#### ✅ 正确做法

```python
import json
import re

def extract_json_safe(state: State) -> State:
    prompt = "Extract JSON: " + state["text"]
    response = llm.invoke(prompt)

    try:
        # 尝试直接解析
        data = json.loads(response)
    except json.JSONDecodeError:
        # 尝试提取 JSON 代码块
        match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
            # 使用结构化输出
            from langchain.output_parsers import PydanticOutputParser
            parser = PydanticOutputParser(pydantic_object=MyModel)
            data = parser.parse(response)

    return {"data": data}

# 更好的方案：使用 structured output
from langchain_core.pydantic_v1 import BaseModel

class ExtractedData(BaseModel):
    name: str
    age: int

def extract_structured(state: State) -> State:
    llm_with_structure = llm.with_structured_output(ExtractedData)
    data = llm_with_structure.invoke(state["text"])
    return {"data": data.dict()}
```

**原因：** 验证和规范化 LLM 输出，确保下游节点正常工作。

---

## 总结

避免这些常见陷阱的关键原则：

1. **不可变性**: 永远不要修改状态对象
2. **类型安全**: 严格遵守状态类型定义
3. **终止条件**: 所有循环都要有明确的退出条件
4. **错误处理**: 优雅处理所有外部调用
5. **性能意识**: 合理使用 checkpointing 和并行化
6. **可观测性**: 添加日志和监控

遵循这些最佳实践，可以构建健壮、高效的 LangGraph 应用。

