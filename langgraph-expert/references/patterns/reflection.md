# Reflection 模式

## 概述

Reflection（反思）模式让 Agent 能够自我评估和改进输出质量。通过引入一个专门的反思器节点来评估生成器的输出，并提供改进建议，Agent 可以迭代优化结果直到达到满意的质量标准。

## 何时使用

### 适用场景

1. **内容质量要求高**
   - 技术文档撰写
   - 代码生成和优化
   - 创意内容创作
   - 学术论文写作

2. **需要多轮优化**
   - 复杂问题求解
   - 设计方案迭代
   - 翻译质量提升
   - 数据分析报告

3. **自我纠错场景**
   - 逻辑错误检测
   - 格式规范检查
   - 一致性验证
   - 完整性审查

4. **持续改进需求**
   - 性能优化建议
   - 安全漏洞修复
   - 用户体验改进
   - 可读性提升

### 不适用场景

- 简单的数据转换任务
- 实时性要求极高的场景
- 质量标准模糊不清的任务
- 计算资源受限的环境

## 核心概念

### 1. 生成器（Generator）

生成器负责创建初始输出或根据反馈改进现有输出。

**职责：**
- 生成初始内容
- 根据反馈进行修改
- 保持输出格式一致

### 2. 反思器（Reflector）

反思器评估生成器的输出质量，识别问题并提供具体的改进建议。

**职责：**
- 评估输出质量
- 识别具体问题
- 提供改进建议
- 判断是否需要继续迭代

### 3. 循环控制

控制反思-改进循环的次数，避免无限循环或过早终止。

**策略：**
- 最大迭代次数限制
- 质量阈值判断
- 改进幅度检测
- 时间或成本限制

## 完整代码示例

### 基础示例：代码审查与改进

```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages

class ReflectionState(TypedDict):
    messages: Annotated[list, add_messages]
    code: str
    reflection: str
    iteration: int
    max_iterations: int
    quality_score: float

def generate_code(state: ReflectionState) -> ReflectionState:
    """生成或改进代码"""
    messages = state["messages"]
    iteration = state.get("iteration", 0)

    # 构建提示
    if iteration == 0:
        # 初始生成
        prompt = f"请根据以下需求生成代码：\n{messages[-1].content}"
    else:
        # 根据反思改进
        prompt = f"""
当前代码：
{state['code']}

反思意见：
{state['reflection']}

请根据反思意见改进代码。
"""

    # 调用 LLM 生成代码（这里简化为示例）
    # 实际应用中应调用真实的 LLM
    generated_code = f"""
def fibonacci(n: int) -> int:
    '''计算斐波那契数列第 n 项'''
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""

    return {
        "code": generated_code,
        "iteration": iteration + 1,
        "messages": [AIMessage(content=f"已生成代码（第 {iteration + 1} 次迭代）")]
    }

def reflect_on_code(state: ReflectionState) -> ReflectionState:
    """反思代码质量并提供改进建议"""
    code = state["code"]

    # 评估代码质量（实际应用中应使用 LLM）
    reflection = """
质量评估：
1. 功能正确性：✓ 实现了斐波那契数列计算
2. 性能问题：✗ 使用递归效率低，存在大量重复计算
3. 文档完整性：△ 有文档字符串，但缺少参数说明和示例
4. 错误处理：✗ 缺少输入验证，负数输入会导致无限递归

改进建议：
- 使用动态规划或记忆化优化性能
- 添加输入验证，处理边界情况
- 完善文档字符串，添加参数说明和使用示例
- 考虑添加类型提示和单元测试
"""

    # 计算质量分数（0-1）
    quality_score = 0.6  # 示例分数

    return {
        "reflection": reflection,
        "quality_score": quality_score,
        "messages": [AIMessage(content=f"已完成反思，质量分数：{quality_score}")]
    }

def should_continue(state: ReflectionState) -> Literal["generate", "end"]:
    """决定是否继续迭代"""
    iteration = state["iteration"]
    max_iterations = state.get("max_iterations", 3)
    quality_score = state.get("quality_score", 0)

    # 达到最大迭代次数
    if iteration >= max_iterations:
        return "end"

    # 质量达标
    if quality_score >= 0.9:
        return "end"

    # 继续改进
    return "generate"

# 构建图
workflow = StateGraph(ReflectionState)

# 添加节点
workflow.add_node("generate", generate_code)
workflow.add_node("reflect", reflect_on_code)

# 添加边
workflow.set_entry_point("generate")
workflow.add_edge("generate", "reflect")
workflow.add_conditional_edges(
    "reflect",
    should_continue,
    {
        "generate": "generate",  # 继续改进
        "end": END
    }
)

# 编译图
app = workflow.compile()

# 使用示例
initial_input = {
    "messages": [HumanMessage(content="实现一个计算斐波那契数列的函数")],
    "iteration": 0,
    "max_iterations": 3
}

# 运行工作流
for event in app.stream(initial_input):
    print(event)
    print("---")

# 获取最终结果
final_state = app.invoke(initial_input)
print(f"\n最终代码：\n{final_state['code']}")
print(f"\n迭代次数：{final_state['iteration']}")
print(f"最终质量分数：{final_state['quality_score']}")
```

### 高级示例：多维度反思

```python
from typing import List
from pydantic import BaseModel, Field

class QualityDimension(BaseModel):
    """质量维度评估"""
    name: str = Field(description="维度名称")
    score: float = Field(description="分数 0-1", ge=0, le=1)
    issues: List[str] = Field(description="发现的问题")
    suggestions: List[str] = Field(description="改进建议")

class MultiDimensionState(TypedDict):
    messages: Annotated[list, add_messages]
    content: str
    dimensions: List[QualityDimension]
    iteration: int
    max_iterations: int
    overall_score: float

def generate_content(state: MultiDimensionState) -> MultiDimensionState:
    """生成或改进内容"""
    iteration = state.get("iteration", 0)

    if iteration == 0:
        # 初始生成
        request = state["messages"][-1].content
        content = f"根据需求生成的初始内容：{request}"
    else:
        # 根据多维度反馈改进
        content = state["content"]
        for dim in state["dimensions"]:
            if dim.score < 0.8:
                # 针对每个维度的问题进行改进
                content += f"\n[改进 {dim.name}]"

    return {
        "content": content,
        "iteration": iteration + 1
    }

def reflect_multi_dimension(state: MultiDimensionState) -> MultiDimensionState:
    """多维度反思"""
    content = state["content"]

    # 定义评估维度
    dimensions = [
        QualityDimension(
            name="准确性",
            score=0.85,
            issues=["部分信息需要验证"],
            suggestions=["添加数据来源", "核实关键数字"]
        ),
        QualityDimension(
            name="完整性",
            score=0.75,
            issues=["缺少边界情况说明", "示例不够充分"],
            suggestions=["补充边界情况", "添加更多示例"]
        ),
        QualityDimension(
            name="可读性",
            score=0.90,
            issues=["部分段落过长"],
            suggestions=["拆分长段落", "添加小标题"]
        ),
        QualityDimension(
            name="一致性",
            score=0.80,
            issues=["术语使用不统一"],
            suggestions=["统一术语表达", "检查格式一致性"]
        )
    ]

    # 计算总体分数（加权平均）
    weights = {"准确性": 0.4, "完整性": 0.3, "可读性": 0.2, "一致性": 0.1}
    overall_score = sum(
        dim.score * weights.get(dim.name, 0.25)
        for dim in dimensions
    )

    return {
        "dimensions": dimensions,
        "overall_score": overall_score,
        "messages": [AIMessage(content=f"多维度评估完成，总分：{overall_score:.2f}")]
    }

def should_continue_multi(state: MultiDimensionState) -> Literal["generate", "end"]:
    """基于多维度评估决定是否继续"""
    iteration = state["iteration"]
    max_iterations = state.get("max_iterations", 5)
    overall_score = state.get("overall_score", 0)

    if iteration >= max_iterations:
        return "end"

    # 所有维度都达到 0.85 以上才结束
    if overall_score >= 0.88:
        all_good = all(dim.score >= 0.85 for dim in state.get("dimensions", []))
        if all_good:
            return "end"

    return "generate"

# 构建工作流
workflow = StateGraph(MultiDimensionState)

workflow.add_node("generate", generate_content)
workflow.add_node("reflect", reflect_multi_dimension)

workflow.set_entry_point("generate")
workflow.add_edge("generate", "reflect")
workflow.add_conditional_edges(
    "reflect",
    should_continue_multi,
    {
        "generate": "generate",
        "end": END
    }
)

app = workflow.compile()
```

### 实战示例：集成真实 LLM

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

class RealReflectionState(TypedDict):
    messages: Annotated[list, add_messages]
    draft: str
    critique: str
    iteration: int
    max_iterations: int

# 初始化 LLM
llm = ChatOpenAI(model="gpt-4", temperature=0.7)

def generate_draft(state: RealReflectionState) -> RealReflectionState:
    """使用 LLM 生成草稿"""
    iteration = state.get("iteration", 0)

    if iteration == 0:
        # 初始生成
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的技术写作助手。"),
            ("human", "{request}")
        ])
        request = state["messages"][-1].content
    else:
        # 根据批评改进
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的技术写作助手。请根据批评意见改进内容。"),
            ("human", """
当前草稿：
{draft}

批评意见：
{critique}

请改进草稿，解决提出的问题。
""")
        ])
        request = None

    # 调用 LLM
    if iteration == 0:
        chain = prompt | llm
        response = chain.invoke({"request": request})
    else:
        chain = prompt | llm
        response = chain.invoke({
            "draft": state["draft"],
            "critique": state["critique"]
        })

    draft = response.content

    return {
        "draft": draft,
        "iteration": iteration + 1,
        "messages": [AIMessage(content=f"已生成草稿（迭代 {iteration + 1}）")]
    }

def critique_draft(state: RealReflectionState) -> RealReflectionState:
    """使用 LLM 批评草稿"""
    draft = state["draft"]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个严格的技术审稿人。请从以下维度评估内容：
1. 技术准确性
2. 逻辑清晰度
3. 完整性
4. 可读性
5. 示例质量

请指出具体问题并提供改进建议。如果质量已经很好，请说明"质量优秀，无需改进"。
"""),
        ("human", "请评估以下内容：\n\n{draft}")
    ])

    chain = prompt | llm
    response = chain.invoke({"draft": draft})

    critique = response.content

    return {
        "critique": critique,
        "messages": [AIMessage(content="已完成批评")]
    }

def should_continue_real(state: RealReflectionState) -> Literal["generate", "end"]:
    """决定是否继续迭代"""
    iteration = state["iteration"]
    max_iterations = state.get("max_iterations", 3)
    critique = state.get("critique", "")

    # 达到最大迭代次数
    if iteration >= max_iterations:
        return "end"

    # 批评中包含"质量优秀"或"无需改进"
    if "质量优秀" in critique or "无需改进" in critique:
        return "end"

    return "generate"

# 构建工作流
workflow = StateGraph(RealReflectionState)

workflow.add_node("generate", generate_draft)
workflow.add_node("critique", critique_draft)

workflow.set_entry_point("generate")
workflow.add_edge("generate", "critique")
workflow.add_conditional_edges(
    "critique",
    should_continue_real,
    {
        "generate": "generate",
        "end": END
    }
)

app = workflow.compile()

# 使用示例
result = app.invoke({
    "messages": [HumanMessage(content="写一篇关于 Python 装饰器的技术文章")],
    "iteration": 0,
    "max_iterations": 3
})

print(f"最终草稿：\n{result['draft']}")
print(f"\n迭代次数：{result['iteration']}")
```

## 最佳实践

### 1. 设计有效的反思提示

**明确评估标准：**
```python
reflection_prompt = """
请从以下维度评估代码质量（每项 0-10 分）：

1. 功能正确性：代码是否正确实现了需求？
2. 性能效率：是否存在性能瓶颈？时间/空间复杂度如何？
3. 代码可读性：命名是否清晰？结构是否合理？
4. 错误处理：是否处理了异常情况？
5. 文档完整性：是否有充分的注释和文档？
6. 测试覆盖：是否易于测试？是否需要单元测试？

对于每个维度，请：
- 给出具体分数
- 指出存在的问题
- 提供改进建议
"""
```

**提供具体反馈：**
```python
# ✓ 好的反馈：具体、可操作
"第 15 行的循环可以用列表推导式替代，提高可读性和性能"

# ✗ 差的反馈：模糊、不可操作
"代码需要改进"
```

### 2. 控制迭代次数

**设置合理的上限：**
```python
def should_continue(state: ReflectionState) -> str:
    iteration = state["iteration"]
    max_iterations = state.get("max_iterations", 3)  # 默认最多 3 次

    # 硬性上限
    if iteration >= max_iterations:
        return "end"

    # 质量阈值
    if state.get("quality_score", 0) >= 0.9:
        return "end"

    # 改进幅度检测
    if iteration > 1:
        improvement = state["quality_score"] - state.get("previous_score", 0)
        if improvement < 0.05:  # 改进不明显
            return "end"

    return "generate"
```

**监控成本：**
```python
class CostAwareState(TypedDict):
    iteration: int
    total_tokens: int
    max_tokens: int
    estimated_cost: float
    max_cost: float

def should_continue_cost_aware(state: CostAwareState) -> str:
    # 检查 token 使用量
    if state["total_tokens"] >= state["max_tokens"]:
        return "end"

    # 检查成本
    if state["estimated_cost"] >= state["max_cost"]:
        return "end"

    return "generate"
```

### 3. 避免循环陷阱

**检测振荡：**
```python
def detect_oscillation(state: ReflectionState) -> bool:
    """检测是否在两个状态之间振荡"""
    history = state.get("content_history", [])

    if len(history) < 4:
        return False

    # 检查最近的内容是否重复
    recent = history[-4:]
    if recent[0] == recent[2] and recent[1] == recent[3]:
        return True  # 检测到 A-B-A-B 模式

    return False

def should_continue_safe(state: ReflectionState) -> str:
    if detect_oscillation(state):
        return "end"  # 终止振荡

    # 其他判断逻辑...
    return "generate"
```

**记录改进历史：**
```python
def track_improvements(state: ReflectionState) -> ReflectionState:
    """跟踪每次迭代的改进"""
    history = state.get("improvement_history", [])

    current_record = {
        "iteration": state["iteration"],
        "quality_score": state["quality_score"],
        "issues_fixed": state.get("issues_fixed", []),
        "new_issues": state.get("new_issues", [])
    }

    history.append(current_record)

    return {"improvement_history": history}
```

### 4. 优化性能

**并行评估多个维度：**
```python
import asyncio
from langchain_core.runnables import RunnableParallel

async def parallel_reflection(state: ReflectionState):
    """并行评估多个维度"""
    content = state["content"]

    # 定义多个评估任务
    tasks = {
        "accuracy": evaluate_accuracy(content),
        "completeness": evaluate_completeness(content),
        "readability": evaluate_readability(content),
        "consistency": evaluate_consistency(content)
    }

    # 并行执行
    results = await asyncio.gather(*tasks.values())

    return dict(zip(tasks.keys(), results))
```

**缓存中间结果：**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def evaluate_code_quality(code_hash: str) -> float:
    """缓存代码质量评估结果"""
    # 评估逻辑...
    pass

def reflect_with_cache(state: ReflectionState) -> ReflectionState:
    code = state["code"]
    code_hash = hash(code)

    # 使用缓存
    quality_score = evaluate_code_quality(code_hash)

    return {"quality_score": quality_score}
```

## 常见陷阱

### 1. 无限循环

**问题：**
```python
# ✗ 没有明确的终止条件
def should_continue(state):
    if state["quality_score"] < 1.0:  # 永远无法达到完美
        return "generate"
    return "end"
```

**解决方案：**
```python
# ✓ 多重终止条件
def should_continue(state):
    # 条件 1：最大迭代次数
    if state["iteration"] >= 5:
        return "end"

    # 条件 2：质量阈值（现实的目标）
    if state["quality_score"] >= 0.85:
        return "end"

    # 条件 3：改进停滞
    if state["iteration"] > 1:
        improvement = state["quality_score"] - state["previous_score"]
        if improvement < 0.02:
            return "end"

    return "generate"
```

### 2. 反馈质量差

**问题：**
```python
# ✗ 反馈过于笼统
reflection = "代码有问题，需要改进"
```

**解决方案：**
```python
# ✓ 具体、可操作的反馈
reflection = """
具体问题：
1. 第 10 行：变量名 'x' 不够描述性，建议改为 'user_count'
2. 第 15-20 行：嵌套过深（4 层），建议提取为独立函数
3. 第 25 行：缺少空值检查，可能导致 NullPointerException

改进建议：
- 重命名变量以提高可读性
- 将复杂逻辑提取为 process_user_data() 函数
- 添加 if user is not None 检查
"""
```

### 3. 过度优化

**问题：**
```python
# ✗ 追求完美，永不满足
def should_continue(state):
    # 即使质量已经很好，仍然继续迭代
    if state["quality_score"] < 0.99:
        return "generate"
    return "end"
```

**解决方案：**
```python
# ✓ 设置合理的质量目标
def should_continue(state):
    # 80/20 原则：80% 的质量通常已经足够
    if state["quality_score"] >= 0.80:
        return "end"

    # 或者基于具体需求
    if state["critical_issues"] == 0 and state["quality_score"] >= 0.75:
        return "end"

    return "generate"
```

### 4. 忽略上下文

**问题：**
```python
# ✗ 每次反思都忽略之前的反馈
def reflect(state):
    # 只看当前内容，不考虑历史反馈
    return evaluate_current_content(state["content"])
```

**解决方案：**
```python
# ✓ 考虑历史反馈和改进轨迹
def reflect(state):
    current_content = state["content"]
    previous_feedback = state.get("feedback_history", [])

    # 检查之前提出的问题是否已解决
    resolved_issues = check_resolved_issues(current_content, previous_feedback)

    # 识别新问题
    new_issues = identify_new_issues(current_content)

    # 评估改进方向是否正确
    improvement_direction = evaluate_improvement_direction(
        previous_feedback,
        resolved_issues,
        new_issues
    )

    return {
        "resolved_issues": resolved_issues,
        "new_issues": new_issues,
        "improvement_direction": improvement_direction
    }
```

## 与其他模式的结合

### Reflection + Human-in-the-Loop

```python
# 在反思循环中加入人工审核
workflow.add_conditional_edges(
    "reflect",
    lambda state: "human_review" if state["iteration"] == 2 else should_continue(state),
    {
        "human_review": "human_review",
        "generate": "generate",
        "end": END
    }
)

app = workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["human_review"]
)
```

### Reflection + ReAct

```python
# Agent 在执行工具后反思结果
def agent_with_reflection(state):
    # 执行工具
    result = execute_tool(state)

    # 反思结果质量
    reflection = reflect_on_result(result)

    # 决定是否重试
    if reflection["quality"] < 0.7:
        return {"action": "retry", "reflection": reflection}

    return {"result": result}
```

## 总结

Reflection 模式的关键要素：

1. **清晰的评估标准**：定义明确的质量维度和评分标准
2. **具体的反馈**：提供可操作的改进建议，而非笼统评价
3. **合理的终止条件**：避免无限循环和过度优化
4. **上下文感知**：考虑历史反馈和改进轨迹
5. **成本控制**：监控迭代次数、token 使用和计算成本

通过合理使用 Reflection 模式，Agent 可以自主提升输出质量，减少人工干预，在内容生成、代码优化、问题求解等场景中发挥重要作用。
