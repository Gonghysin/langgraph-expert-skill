# Plan-and-Execute 模式

## 概述

Plan-and-Execute（规划-执行）模式是 LangGraph 中用于处理复杂任务的高级架构模式。它将任务分解为两个独立的阶段：

1. **规划（Plan）**：分析任务，制定详细的执行计划
2. **执行（Execute）**：按照计划逐步执行，收集结果并反馈

这种模式的核心思想是"先思考，再行动"，通过前期的充分规划来提高执行效率和成功率。

## 何时使用

Plan-and-Execute 模式适用于以下场景：

- **复杂的多步骤任务**：任务需要多个步骤，且步骤之间有依赖关系
- **需要全局视角**：需要在开始执行前了解整体任务结构
- **资源受限**：需要优化执行顺序以节省时间或成本
- **需要可预测性**：用户需要提前知道系统将执行哪些操作

典型应用场景：
- 数据分析流程（数据收集 → 清洗 → 分析 → 可视化）
- 软件开发任务（需求分析 → 设计 → 实现 → 测试）
- 研究报告生成（主题研究 → 资料收集 → 内容撰写 → 审核）
- 复杂的 API 编排（需要按特定顺序调用多个 API）

## 与 ReAct 模式的对比

| 特性 | ReAct 模式 | Plan-and-Execute 模式 |
|------|-----------|---------------------|
| 决策时机 | 每步动态决策 | 前期一次性规划 |
| 适用场景 | 不确定性高的任务 | 结构化的复杂任务 |
| 灵活性 | 高（可随时调整） | 中（需重新规划） |
| 可预测性 | 低 | 高 |
| Token 消耗 | 每步都需要推理 | 规划阶段消耗较多 |
| 执行效率 | 可能有冗余步骤 | 优化的执行路径 |

## 核心概念

### 1. 状态设计

Plan-and-Execute 模式的状态需要同时管理计划和执行进度：

```python
from typing import TypedDict, Annotated, Sequence, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class PlanExecuteState(TypedDict):
    """Plan-and-Execute 模式的状态定义"""
    # 用户输入
    input: str
    # 执行计划（步骤列表）
    plan: List[str]
    # 当前执行到的步骤索引
    current_step: int
    # 每个步骤的执行结果
    step_results: List[str]
    # 消息历史（用于与 LLM 交互）
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # 最终输出
    output: str
```

**关键点**：
- `plan` 存储完整的执行计划，每个元素是一个步骤描述
- `current_step` 跟踪执行进度
- `step_results` 记录每个步骤的执行结果，用于后续步骤参考
- 状态保持不可变性，每次更新返回新的状态副本

### 2. 节点定义

Plan-and-Execute 模式通常包含三个核心节点：

#### 规划节点（Planner）

```python
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

def planner_node(state: PlanExecuteState) -> PlanExecuteState:
    """规划节点：分析任务并制定执行计划"""
    # 构建规划提示
    system_prompt = """你是一个任务规划专家。
    给定一个任务，你需要将其分解为清晰的执行步骤。

    要求：
    1. 每个步骤应该是具体的、可执行的
    2. 步骤之间应该有逻辑顺序
    3. 每个步骤只做一件事
    4. 使用简洁的语言描述

    输出格式：
    1. 第一步描述
    2. 第二步描述
    3. 第三步描述
    ..."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"任务: {state['input']}")
    ]

    # 调用 LLM 生成计划
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    response = llm.invoke(messages)

    # 解析计划（假设 LLM 返回编号列表）
    plan_text = response.content
    plan_steps = []
    for line in plan_text.split('\n'):
        line = line.strip()
        if line and line[0].isdigit():
            # 移除编号，只保留步骤描述
            step = line.split('.', 1)[1].strip() if '.' in line else line
            plan_steps.append(step)

    print(f"📋 生成计划: {len(plan_steps)} 个步骤")
    for i, step in enumerate(plan_steps, 1):
        print(f"  {i}. {step}")

    return {
        "plan": plan_steps,
        "current_step": 0,
        "step_results": [],
        "messages": [response]
    }
```

#### 执行节点（Executor）

```python
from langchain_core.tools import tool

def executor_node(state: PlanExecuteState) -> PlanExecuteState:
    """执行节点：执行当前步骤"""
    current_step_idx = state["current_step"]
    current_step_desc = state["plan"][current_step_idx]

    print(f"⚙️ 执行步骤 {current_step_idx + 1}/{len(state['plan'])}: {current_step_desc}")

    # 构建执行上下文（包含之前的结果）
    context = f"任务: {state['input']}\n\n"
    context += f"完整计划:\n"
    for i, step in enumerate(state['plan'], 1):
        context += f"{i}. {step}\n"

    if state["step_results"]:
        context += f"\n已完成的步骤结果:\n"
        for i, result in enumerate(state["step_results"], 1):
            context += f"步骤 {i}: {result}\n"

    context += f"\n当前需要执行: {current_step_desc}"

    # 初始化 LLM（绑定工具）
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    # 执行当前步骤
    messages = [HumanMessage(content=context)]
    response = llm_with_tools.invoke(messages)

    # 如果需要调用工具，执行工具调用
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_results = []
        for tool_call in response.tool_calls:
            tool = tool_map[tool_call["name"]]
            result = tool.invoke(tool_call["args"])
            tool_results.append(str(result))

        # 合并工具结果作为步骤结果
        step_result = "; ".join(tool_results)
    else:
        # 没有工具调用，使用 LLM 的响应
        step_result = response.content

    print(f"  ✓ 结果: {step_result[:100]}...")

    # 更新状态
    new_step_results = state["step_results"] + [step_result]

    return {
        "current_step": current_step_idx + 1,
        "step_results": new_step_results,
        "messages": [response]
    }
```

#### 总结节点（Summarizer）

```python
def summarizer_node(state: PlanExecuteState) -> PlanExecuteState:
    """总结节点：汇总所有步骤的结果"""
    print("📊 汇总结果...")

    # 构建总结提示
    summary_prompt = f"""任务: {state['input']}

执行计划和结果:
"""

    for i, (step, result) in enumerate(zip(state['plan'], state['step_results']), 1):
        summary_prompt += f"\n步骤 {i}: {step}\n结果: {result}\n"

    summary_prompt += "\n请基于以上执行结果，生成一个完整、连贯的最终答案。"

    # 调用 LLM 生成总结
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    response = llm.invoke([HumanMessage(content=summary_prompt)])

    final_output = response.content
    print(f"✅ 最终输出: {final_output[:100]}...")

    return {
        "output": final_output,
        "messages": [response]
    }
```

### 3. 边和条件路由

Plan-and-Execute 模式的路由逻辑相对简单：按顺序执行计划中的步骤。

```python
def should_continue(state: PlanExecuteState) -> str:
    """条件路由：决定是继续执行还是进入总结"""
    current_step = state["current_step"]
    total_steps = len(state["plan"])

    if current_step < total_steps:
        return "executor"  # 继续执行下一步
    else:
        return "summarizer"  # 所有步骤完成，进入总结
```

## 完整代码示例

以下是一个完整的可运行示例，实现了一个能够规划和执行研究任务的 Agent：

```python
"""
Plan-and-Execute 模式完整示例
功能：能够规划和执行复杂研究任务的智能助手
"""

from typing import TypedDict, Annotated, Sequence, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# ============================================================================
# 1. 定义工具
# ============================================================================

@tool
def search_web(query: str) -> str:
    """搜索网络信息（模拟）"""
    mock_results = {
        "python": "Python 是一种高级编程语言，广泛用于数据科学、Web 开发等领域。",
        "langgraph": "LangGraph 是用于构建有状态 AI 应用的框架，支持复杂的工作流编排。",
        "ai": "人工智能（AI）是计算机科学的一个分支，致力于创建能够执行智能任务的系统。",
    }
    for key, value in mock_results.items():
        if key in query.lower():
            return value
    return f"关于 '{query}' 的搜索结果：这是一个模拟的搜索结果。"

@tool
def analyze_data(data: str) -> str:
    """分析数据（模拟）"""
    return f"数据分析结果：对 '{data[:50]}...' 的分析显示其包含 {len(data)} 个字符，主要讨论技术主题。"

@tool
def generate_summary(content: str) -> str:
    """生成摘要（模拟）"""
    return f"摘要：{content[:100]}...（共 {len(content)} 字符）"

# 工具映射
tools = [search_web, analyze_data, generate_summary]
tool_map = {tool.name: tool for tool in tools}

# ============================================================================
# 2. 定义状态
# ============================================================================

class PlanExecuteState(TypedDict):
    """Plan-and-Execute 状态"""
    input: str
    plan: List[str]
    current_step: int
    step_results: List[str]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    output: str

# ============================================================================
# 3. 定义节点
# ============================================================================

def planner_node(state: PlanExecuteState) -> PlanExecuteState:
    """规划节点"""
    system_prompt = """你是一个任务规划专家。
给定一个任务，你需要将其分解为清晰的执行步骤。

要求：
1. 每个步骤应该是具体的、可执行的
2. 步骤之间应该有逻辑顺序
3. 每个步骤只做一件事
4. 使用简洁的语言描述

输出格式（每行一个步骤，以数字开头）：
1. 第一步描述
2. 第二步描述
3. 第三步描述"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"任务: {state['input']}")
    ]

    llm = ChatOpenAI(model="gpt-4", temperature=0)
    response = llm.invoke(messages)

    # 解析计划
    plan_steps = []
    for line in response.content.split('\n'):
        line = line.strip()
        if line and line[0].isdigit():
            step = line.split('.', 1)[1].strip() if '.' in line else line
            plan_steps.append(step)

    print(f"\n📋 生成计划: {len(plan_steps)} 个步骤")
    for i, step in enumerate(plan_steps, 1):
        print(f"  {i}. {step}")

    return {
        "plan": plan_steps,
        "current_step": 0,
        "step_results": [],
        "messages": [response]
    }

def executor_node(state: PlanExecuteState) -> PlanExecuteState:
    """执行节点"""
    current_step_idx = state["current_step"]
    current_step_desc = state["plan"][current_step_idx]

    print(f"\n⚙️ 执行步骤 {current_step_idx + 1}/{len(state['plan'])}: {current_step_desc}")

    # 构建执行上下文
    context = f"任务: {state['input']}\n\n"
    context += f"当前步骤: {current_step_desc}\n\n"

    if state["step_results"]:
        context += "之前步骤的结果:\n"
        for i, result in enumerate(state["step_results"], 1):
            context += f"步骤 {i}: {result}\n"

    context += f"\n请执行当前步骤。可用工具: search_web, analyze_data, generate_summary"

    # 执行步骤（简化版：直接调用工具）
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    messages = [HumanMessage(content=context)]
    response = llm_with_tools.invoke(messages)

    # 处理工具调用
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_results = []
        for tool_call in response.tool_calls:
            tool = tool_map[tool_call["name"]]
            result = tool.invoke(tool_call["args"])
            tool_results.append(str(result))
        step_result = "; ".join(tool_results)
    else:
        step_result = response.content

    print(f"  ✓ 结果: {step_result[:80]}...")

    new_step_results = state["step_results"] + [step_result]

    return {
        "current_step": current_step_idx + 1,
        "step_results": new_step_results,
        "messages": [response]
    }

def summarizer_node(state: PlanExecuteState) -> PlanExecuteState:
    """总结节点"""
    print("\n📊 汇总结果...")

    summary_prompt = f"""任务: {state['input']}

执行计划和结果:
"""
    for i, (step, result) in enumerate(zip(state['plan'], state['step_results']), 1):
        summary_prompt += f"\n步骤 {i}: {step}\n结果: {result}\n"

    summary_prompt += "\n请基于以上执行结果，生成一个完整、连贯的最终答案。"

    llm = ChatOpenAI(model="gpt-4", temperature=0)
    response = llm.invoke([HumanMessage(content=summary_prompt)])

    final_output = response.content
    print(f"\n✅ 最终输出:\n{final_output}\n")

    return {
        "output": final_output,
        "messages": [response]
    }

# ============================================================================
# 4. 定义条件路由
# ============================================================================

def should_continue(state: PlanExecuteState) -> str:
    """决定是继续执行还是总结"""
    current_step = state["current_step"]
    total_steps = len(state["plan"])

    if current_step < total_steps:
        return "executor"
    else:
        return "summarizer"

# ============================================================================
# 5. 构建图
# ============================================================================

def create_plan_execute_agent() -> StateGraph:
    """创建 Plan-and-Execute Agent 图"""
    workflow = StateGraph(PlanExecuteState)

    # 添加节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("summarizer", summarizer_node)

    # 设置入口点
    workflow.set_entry_point("planner")

    # 添加边
    workflow.add_edge("planner", "executor")  # 规划后开始执行

    # 添加条件边：执行完一步后决定继续还是总结
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",      # 继续执行下一步
            "summarizer": "summarizer"   # 所有步骤完成，进入总结
        }
    )

    # 总结后结束
    workflow.add_edge("summarizer", END)

    return workflow.compile()

# ============================================================================
# 6. 运行示例
# ============================================================================

if __name__ == "__main__":
    app = create_plan_execute_agent()

    # 测试用例：复杂的研究任务
    print("=" * 70)
    print("测试: 复杂研究任务")
    print("=" * 70)

    initial_state = {
        "input": "研究 LangGraph 框架，分析其核心特性，并生成一份摘要报告",
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "messages": [],
        "output": ""
    }

    final_state = app.invoke(initial_state)

    print("\n" + "=" * 70)
    print("执行完成")
    print("=" * 70)
    print(f"最终输出: {final_state['output']}")
```

## 最佳实践

### 1. 规划质量

**✅ 推荐做法**：

```python
# 提供清晰的规划指导
system_prompt = """你是任务规划专家。

规划原则：
1. SMART 原则：具体、可衡量、可实现、相关、有时限
2. 单一职责：每个步骤只做一件事
3. 逻辑顺序：考虑步骤之间的依赖关系
4. 适度粒度：不要太粗（难以执行）也不要太细（效率低）

示例：
任务：研究某个技术
好的计划：
1. 搜索技术的官方文档
2. 分析核心特性和优势
3. 查找实际应用案例
4. 总结关键要点

差的计划：
1. 了解技术（太粗）
2. 打开浏览器（太细）
3. 写报告（缺少中间步骤）
"""
```

**❌ 避免做法**：

```python
# 规划提示过于简单
system_prompt = "把任务分成几个步骤"  # ❌ 缺乏指导
```

### 2. 执行反馈

**✅ 推荐做法**：

```python
def executor_node(state: PlanExecuteState) -> PlanExecuteState:
    """执行节点（带反馈）"""
    current_step_idx = state["current_step"]
    current_step_desc = state["plan"][current_step_idx]

    # 构建丰富的上下文
    context = f"""
任务: {state['input']}

完整计划:
{format_plan(state['plan'])}

已完成步骤:
{format_results(state['step_results'])}

当前步骤: {current_step_desc}

请执行当前步骤，并确保结果能够支持后续步骤的执行。
"""

    # 执行并验证结果
    result = execute_step(context)

    # 检查结果质量
    if not result or len(result) < 10:
        print("⚠️ 步骤结果不充分，可能影响后续执行")

    return {
        "current_step": current_step_idx + 1,
        "step_results": state["step_results"] + [result]
    }
```

**❌ 避免做法**：

```python
def bad_executor(state):
    # ❌ 没有提供上下文，执行器不知道之前发生了什么
    result = execute_current_step(state["plan"][state["current_step"]])
    return {"current_step": state["current_step"] + 1}
```

### 3. 动态调整

**✅ 推荐做法**：

```python
def adaptive_executor_node(state: PlanExecuteState) -> PlanExecuteState:
    """自适应执行节点：根据执行情况调整计划"""
    current_step_idx = state["current_step"]
    current_step_desc = state["plan"][current_step_idx]

    # 执行当前步骤
    result = execute_step(current_step_desc, state)

    # 检查是否需要调整计划
    if is_step_failed(result):
        print("⚠️ 步骤执行失败，重新规划...")
        # 重新规划剩余步骤
        remaining_plan = replan(
            original_task=state["input"],
            completed_steps=state["step_results"],
            failed_step=current_step_desc,
            remaining_steps=state["plan"][current_step_idx + 1:]
        )
        new_plan = state["plan"][:current_step_idx + 1] + remaining_plan
        return {
            "plan": new_plan,
            "current_step": current_step_idx + 1,
            "step_results": state["step_results"] + [result]
        }

    return {
        "current_step": current_step_idx + 1,
        "step_results": state["step_results"] + [result]
    }
```

### 4. 计划可视化

**✅ 推荐做法**：

```python
def visualize_plan(state: PlanExecuteState) -> None:
    """可视化执行计划和进度"""
    print("\n" + "=" * 60)
    print("执行计划")
    print("=" * 60)

    for i, step in enumerate(state["plan"], 1):
        if i <= state["current_step"]:
            status = "✅"
        elif i == state["current_step"] + 1:
            status = "⏳"
        else:
            status = "⏸️"

        print(f"{status} 步骤 {i}: {step}")

        if i <= len(state["step_results"]):
            result = state["step_results"][i - 1]
            print(f"   结果: {result[:60]}...")

    print("=" * 60 + "\n")

# 在执行过程中调用
def executor_with_visualization(state: PlanExecuteState) -> PlanExecuteState:
    visualize_plan(state)
    return executor_node(state)
```

## 常见陷阱

### 1. 规划过于详细

**问题**：计划包含过多细节，导致执行效率低下。

**示例**：

```python
# ❌ 过于详细的计划
plan = [
    "打开浏览器",
    "输入搜索关键词",
    "点击搜索按钮",
    "查看第一个结果",
    "点击链接",
    "阅读内容",
    "复制相关信息",
    "关闭浏览器"
]

# ✅ 适度粒度的计划
plan = [
    "搜索相关信息",
    "分析搜索结果",
    "提取关键信息"
]
```

**解决方案**：

```python
def validate_plan_granularity(plan: List[str]) -> bool:
    """验证计划粒度是否合适"""
    # 检查步骤数量
    if len(plan) > 10:
        print("⚠️ 计划步骤过多，建议合并相关步骤")
        return False

    # 检查步骤描述长度
    for step in plan:
        if len(step) < 10:
            print(f"⚠️ 步骤描述过短: '{step}'")
            return False

    return True
```

### 2. 执行偏离计划

**问题**：执行过程中偏离原计划，导致结果不符合预期。

**原因**：
- 执行器没有严格遵循计划
- 计划描述不够清晰
- 缺少执行验证

**解决方案**：

```python
def strict_executor_node(state: PlanExecuteState) -> PlanExecuteState:
    """严格执行节点：确保执行符合计划"""
    current_step_idx = state["current_step"]
    current_step_desc = state["plan"][current_step_idx]

    # 明确的执行指令
    execution_prompt = f"""
你必须严格执行以下步骤，不要做其他事情：

步骤: {current_step_desc}

上下文:
- 任务目标: {state['input']}
- 已完成: {len(state['step_results'])} 个步骤
- 剩余: {len(state['plan']) - current_step_idx - 1} 个步骤

要求:
1. 只执行当前步骤，不要提前执行后续步骤
2. 确保输出能够支持后续步骤
3. 如果步骤无法执行，明确说明原因
"""

    result = execute_with_validation(execution_prompt)

    # 验证结果是否符合步骤要求
    if not is_result_relevant(result, current_step_desc):
        print(f"⚠️ 执行结果与步骤不符: {current_step_desc}")

    return {
        "current_step": current_step_idx + 1,
        "step_results": state["step_results"] + [result]
    }
```

### 3. 缺少反馈循环

**问题**：执行过程中没有反馈机制，无法根据实际情况调整。

**原因**：
- 计划是静态的，不能适应变化
- 没有检查执行结果的质量
- 缺少重新规划的机制

**解决方案**：

```python
def should_continue_with_feedback(state: PlanExecuteState) -> str:
    """带反馈的条件路由"""
    current_step = state["current_step"]
    total_steps = len(state["plan"])

    # 检查是否需要重新规划
    if current_step > 0:
        last_result = state["step_results"][-1]

        # 检查结果质量
        if is_result_insufficient(last_result):
            print("⚠️ 上一步结果不充分，需要重新规划")
            return "replanner"

        # 检查是否偏离目标
        if is_off_track(state):
            print("⚠️ 执行偏离目标，需要重新规划")
            return "replanner"

    # 正常流程
    if current_step < total_steps:
        return "executor"
    else:
        return "summarizer"

# 添加重新规划节点
def replanner_node(state: PlanExecuteState) -> PlanExecuteState:
    """重新规划节点"""
    print("🔄 重新规划中...")

    replan_prompt = f"""
原始任务: {state['input']}

已完成的步骤:
{format_completed_steps(state)}

问题: 最后一步的结果不理想

请重新规划剩余步骤，确保能够完成任务。
"""

    llm = ChatOpenAI(model="gpt-4", temperature=0)
    response = llm.invoke([HumanMessage(content=replan_prompt)])

    # 解析新计划
    new_steps = parse_plan(response.content)

    # 保留已完成的步骤，替换剩余步骤
    updated_plan = state["plan"][:state["current_step"]] + new_steps

    print(f"📋 更新计划: 新增 {len(new_steps)} 个步骤")

    return {
        "plan": updated_plan
    }
```

### 4. 忽略步骤依赖

**问题**：步骤之间有依赖关系，但执行时没有考虑。

**解决方案**：

```python
class PlanStep(TypedDict):
    """增强的计划步骤"""
    description: str
    dependencies: List[int]  # 依赖的步骤索引
    required_info: List[str]  # 需要的信息

def validate_dependencies(state: PlanExecuteState) -> bool:
    """验证依赖关系是否满足"""
    current_step_idx = state["current_step"]
    current_step = state["plan"][current_step_idx]

    # 检查依赖的步骤是否已完成
    if hasattr(current_step, "dependencies"):
        for dep_idx in current_step.dependencies:
            if dep_idx >= current_step_idx:
                print(f"⚠️ 依赖错误: 步骤 {current_step_idx} 依赖未完成的步骤 {dep_idx}")
                return False

            # 检查依赖步骤的结果是否可用
            if dep_idx >= len(state["step_results"]):
                print(f"⚠️ 依赖步骤 {dep_idx} 的结果不可用")
                return False

    return True
```

## 扩展阅读

- [LangGraph 官方文档 - Plan-and-Execute](https://langchain-ai.github.io/langgraph/)
- [LangChain Plan-and-Execute Agent](https://python.langchain.com/docs/use_cases/more/agents/plan_and_execute)
- [任务规划与分解最佳实践](https://www.anthropic.com/index/planning-for-agents)
- [ReAct vs Plan-and-Execute 对比分析](https://blog.langchain.dev/planning-agents/)

