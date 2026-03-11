# Hierarchical 模式

## 概述

Hierarchical（层级化）模式构建多层次的 Agent 系统，上层 Agent 将复杂任务分解并委派给下层 Agent，下层 Agent 可以进一步分解任务给更下层的 Agent。这种模式类似于企业的组织架构，通过层级化管理实现大规模复杂任务的协调。

## 何时使用

### 适用场景

1. **大规模复杂任务**
   - 需要多个团队协作
   - 任务可以自然地分解为子任务
   - 不同层级有不同的抽象级别
   - 需要清晰的责任划分

2. **组织化工作流**
   - 模拟企业组织结构
   - 需要多级审批流程
   - 不同层级有不同的权限
   - 需要向上汇报机制

3. **可扩展系统**
   - 需要动态添加新的团队或 Agent
   - 不同子系统相对独立
   - 需要灵活的资源分配
   - 支持水平和垂直扩展

4. **专业化分工**
   - 不同层级需要不同的专业知识
   - 高层负责战略，底层负责执行
   - 需要专家团队处理特定领域
   - 任务复杂度跨越多个层次

### 不适用场景

- 简单的线性任务流程
- 所有 Agent 地位平等的场景
- 需要频繁跨层级通信
- 任务无法清晰分解为层级结构

## 核心概念

### 1. 层级结构

**顶层管理者（Top-Level Manager）**
- 接收用户请求
- 制定整体策略
- 分配任务给中层管理者
- 汇总最终结果

**中层管理者（Mid-Level Managers）**
- 接收上级任务
- 分解为具体子任务
- 管理执行团队
- 向上汇报进度

**执行层（Workers）**
- 执行具体任务
- 使用工具完成工作
- 向直接上级汇报结果

### 2. 任务委派

**向下委派**
- 上级将任务分解为子任务
- 为每个子任务选择合适的下级
- 传递必要的上下文和资源
- 设置期望和截止时间

**向上汇报**
- 下级完成任务后向上级汇报
- 包含执行结果和遇到的问题
- 上级汇总结果并继续向上汇报
- 最终结果返回给用户

### 3. 子图（Subgraphs）

每个管理者可以管理一个子图：
- 子图是独立的工作流
- 有自己的状态和节点
- 可以嵌套多层子图
- 对外表现为单个节点

## 完整代码示例

### 基础示例：软件开发团队

创建一个三层架构：CTO -> 团队负责人 -> 工程师

```python
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

# 1. 定义状态
class TeamState(TypedDict):
    messages: Annotated[list, add_messages]
    task: str
    assigned_to: str
    results: dict[str, str]

# 2. 定义决策模型
class ManagerDecision(BaseModel):
    assigned_team: Literal["frontend_team", "backend_team", "FINISH"]
    reasoning: str

class TeamLeadDecision(BaseModel):
    assigned_engineer: Literal["engineer_1", "engineer_2", "FINISH"]
    reasoning: str

# 3. 初始化模型
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# 4. 顶层：CTO
def cto_node(state: TeamState) -> TeamState:
    """CTO 分配任务给团队负责人"""
    system_prompt = """你是 CTO，管理前端和后端团队。

    团队：
    - frontend_team: 处理 UI、用户体验、前端功能
    - backend_team: 处理 API、数据库、服务器逻辑

    分析任务并分配给合适的团队。如果所有团队都完成了，选择 FINISH。
    """

    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"]
    ]

    decision = model.with_structured_output(ManagerDecision).invoke(messages)

    return {
        "assigned_to": decision.assigned_team,
        "messages": [HumanMessage(content=f"[CTO] 分配给: {decision.assigned_team}")]
    }

# 5. 中层：团队负责人
def create_team_lead(team_name: str):
    """创建团队负责人节点"""

    def team_lead_node(state: TeamState) -> TeamState:
        system_prompt = f"""你是 {team_name} 的负责人，管理两名工程师。

        工程师：
        - engineer_1: 资深工程师，处理复杂任务
        - engineer_2: 初级工程师，处理简单任务

        分析任务并分配给合适的工程师。如果任务完成，选择 FINISH。
        """

        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"]
        ]

        decision = model.with_structured_output(TeamLeadDecision).invoke(messages)

        return {
            "assigned_to": decision.assigned_engineer,
            "messages": [HumanMessage(content=f"[{team_name} Lead] 分配给: {decision.assigned_engineer}")]
        }

    return team_lead_node

# 6. 执行层：工程师
def create_engineer(engineer_name: str, specialty: str):
    """创建工程师节点"""

    def engineer_node(state: TeamState) -> TeamState:
        system_prompt = f"""你是 {engineer_name}，专长：{specialty}。

        执行分配给你的任务，完成后简洁汇报结果。
        """

        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"]
        ]

        response = model.invoke(messages)

        # 记录结果
        results = state.get("results", {})
        results[engineer_name] = response.content

        return {
            "results": results,
            "messages": [response]
        }

    return engineer_node

# 7. 构建层级图
def create_hierarchical_team():
    workflow = StateGraph(TeamState)

    # 添加顶层节点
    workflow.add_node("cto", cto_node)

    # 添加中层节点
    workflow.add_node("frontend_lead", create_team_lead("Frontend"))
    workflow.add_node("backend_lead", create_team_lead("Backend"))

    # 添加执行层节点
    workflow.add_node("frontend_engineer_1", create_engineer("Frontend Engineer 1", "React, TypeScript"))
    workflow.add_node("frontend_engineer_2", create_engineer("Frontend Engineer 2", "CSS, HTML"))
    workflow.add_node("backend_engineer_1", create_engineer("Backend Engineer 1", "Python, PostgreSQL"))
    workflow.add_node("backend_engineer_2", create_engineer("Backend Engineer 2", "API Design"))

    # 设置入口
    workflow.add_edge(START, "cto")

    # CTO 到团队负责人
    def route_from_cto(state: TeamState) -> str:
        assigned = state.get("assigned_to", "")
        if assigned == "FINISH":
            return END
        elif assigned == "frontend_team":
            return "frontend_lead"
        elif assigned == "backend_team":
            return "backend_lead"
        return END

    workflow.add_conditional_edges(
        "cto",
        route_from_cto,
        {
            "frontend_lead": "frontend_lead",
            "backend_lead": "backend_lead",
            END: END
        }
    )

    # 团队负责人到工程师
    def route_from_frontend_lead(state: TeamState) -> str:
        assigned = state.get("assigned_to", "")
        if assigned == "FINISH":
            return "cto"  # 返回上级
        elif assigned == "engineer_1":
            return "frontend_engineer_1"
        elif assigned == "engineer_2":
            return "frontend_engineer_2"
        return "cto"

    def route_from_backend_lead(state: TeamState) -> str:
        assigned = state.get("assigned_to", "")
        if assigned == "FINISH":
            return "cto"
        elif assigned == "engineer_1":
            return "backend_engineer_1"
        elif assigned == "engineer_2":
            return "backend_engineer_2"
        return "cto"

    workflow.add_conditional_edges(
        "frontend_lead",
        route_from_frontend_lead,
        {
            "frontend_engineer_1": "frontend_engineer_1",
            "frontend_engineer_2": "frontend_engineer_2",
            "cto": "cto"
        }
    )

    workflow.add_conditional_edges(
        "backend_lead",
        route_from_backend_lead,
        {
            "backend_engineer_1": "backend_engineer_1",
            "backend_engineer_2": "backend_engineer_2",
            "cto": "cto"
        }
    )

    # 工程师完成后返回团队负责人
    workflow.add_edge("frontend_engineer_1", "frontend_lead")
    workflow.add_edge("frontend_engineer_2", "frontend_lead")
    workflow.add_edge("backend_engineer_1", "backend_lead")
    workflow.add_edge("backend_engineer_2", "backend_lead")

    return workflow.compile()

# 8. 使用示例
if __name__ == "__main__":
    app = create_hierarchical_team()

    result = app.invoke({
        "messages": [HumanMessage(content="开发一个用户登录功能，包括前端表单和后端 API")],
        "task": "",
        "assigned_to": "",
        "results": {}
    })

    print("\n执行结果：")
    for engineer, result in result["results"].items():
        print(f"\n{engineer}:")
        print(result)
```

### 高级示例：使用子图

```python
from langgraph.graph import StateGraph
from typing import Any

# 1. 定义子图状态
class SubteamState(TypedDict):
    messages: Annotated[list, add_messages]
    task: str
    subtask_results: list[str]

# 2. 创建前端团队子图
def create_frontend_subgraph():
    """前端团队的完整工作流"""
    subgraph = StateGraph(SubteamState)

    def frontend_lead(state: SubteamState):
        # 团队负责人分解任务
        return {
            "messages": [HumanMessage(content="[Frontend Lead] 分解任务为：UI 设计 + 组件开发")]
        }

    def ui_designer(state: SubteamState):
        # UI 设计师
        results = state.get("subtask_results", [])
        results.append("UI 设计完成")
        return {"subtask_results": results}

    def component_developer(state: SubteamState):
        # 组件开发者
        results = state.get("subtask_results", [])
        results.append("组件开发完成")
        return {"subtask_results": results}

    subgraph.add_node("lead", frontend_lead)
    subgraph.add_node("ui_designer", ui_designer)
    subgraph.add_node("developer", component_developer)

    subgraph.add_edge(START, "lead")
    subgraph.add_edge("lead", "ui_designer")
    subgraph.add_edge("ui_designer", "developer")
    subgraph.add_edge("developer", END)

    return subgraph.compile()

# 3. 创建后端团队子图
def create_backend_subgraph():
    """后端团队的完整工作流"""
    subgraph = StateGraph(SubteamState)

    def backend_lead(state: SubteamState):
        return {
            "messages": [HumanMessage(content="[Backend Lead] 分解任务为：API 设计 + 数据库设计")]
        }

    def api_designer(state: SubteamState):
        results = state.get("subtask_results", [])
        results.append("API 设计完成")
        return {"subtask_results": results}

    def db_designer(state: SubteamState):
        results = state.get("subtask_results", [])
        results.append("数据库设计完成")
        return {"subtask_results": results}

    subgraph.add_node("lead", backend_lead)
    subgraph.add_node("api_designer", api_designer)
    subgraph.add_node("db_designer", db_designer)

    subgraph.add_edge(START, "lead")
    subgraph.add_edge("lead", "api_designer")
    subgraph.add_edge("api_designer", "db_designer")
    subgraph.add_edge("db_designer", END)

    return subgraph.compile()

# 4. 主图使用子图
def create_hierarchical_with_subgraphs():
    main_graph = StateGraph(TeamState)

    # CTO 节点
    def cto(state: TeamState):
        return {
            "messages": [HumanMessage(content="[CTO] 协调前端和后端团队")]
        }

    main_graph.add_node("cto", cto)

    # 将子图作为节点添加
    main_graph.add_node("frontend_team", create_frontend_subgraph())
    main_graph.add_node("backend_team", create_backend_subgraph())

    # 定义流程
    main_graph.add_edge(START, "cto")
    main_graph.add_edge("cto", "frontend_team")
    main_graph.add_edge("cto", "backend_team")
    main_graph.add_edge("frontend_team", END)
    main_graph.add_edge("backend_team", END)

    return main_graph.compile()
```

## 最佳实践

### 1. 清晰的层级定义

```python
# 定义组织结构
HIERARCHY = {
    "cto": {
        "level": 0,
        "manages": ["frontend_lead", "backend_lead"],
        "reports_to": None
    },
    "frontend_lead": {
        "level": 1,
        "manages": ["frontend_engineer_1", "frontend_engineer_2"],
        "reports_to": "cto"
    },
    "backend_lead": {
        "level": 1,
        "manages": ["backend_engineer_1", "backend_engineer_2"],
        "reports_to": "cto"
    }
}

def get_manager(agent_name: str) -> str:
    """获取上级管理者"""
    return HIERARCHY[agent_name]["reports_to"]

def get_subordinates(agent_name: str) -> list[str]:
    """获取下属"""
    return HIERARCHY[agent_name]["manages"]
```

### 2. 任务分解策略

```python
class Task(BaseModel):
    id: str
    description: str
    level: int  # 任务层级
    assigned_to: str
    subtasks: list[str]  # 子任务 ID
    parent_task: str | None  # 父任务 ID

def decompose_task(task: Task, manager: str) -> list[Task]:
    """管理者分解任务"""
    subordinates = get_subordinates(manager)

    # 根据下属能力分解任务
    subtasks = []
    for i, subordinate in enumerate(subordinates):
        subtask = Task(
            id=f"{task.id}.{i+1}",
            description=f"子任务 {i+1}",
            level=task.level + 1,
            assigned_to=subordinate,
            subtasks=[],
            parent_task=task.id
        )
        subtasks.append(subtask)

    return subtasks
```

### 3. 结果汇总机制

```python
class TaskResult(BaseModel):
    task_id: str
    status: Literal["completed", "failed", "in_progress"]
    output: str
    issues: list[str]

def aggregate_results(subtask_results: list[TaskResult]) -> TaskResult:
    """汇总子任务结果"""
    # 检查所有子任务状态
    all_completed = all(r.status == "completed" for r in subtask_results)

    if all_completed:
        # 合并输出
        combined_output = "\n".join([r.output for r in subtask_results])
        return TaskResult(
            task_id="parent",
            status="completed",
            output=combined_output,
            issues=[]
        )
    else:
        # 收集问题
        all_issues = []
        for r in subtask_results:
            all_issues.extend(r.issues)

        return TaskResult(
            task_id="parent",
            status="failed",
            output="",
            issues=all_issues
        )
```

### 4. 跨层级通信

```python
class HierarchicalState(TypedDict):
    messages: Annotated[list, add_messages]
    escalations: list[dict]  # 向上升级的问题
    broadcasts: list[dict]  # 向下广播的通知

def escalate_issue(state: HierarchicalState, issue: str, from_agent: str):
    """向上级升级问题"""
    manager = get_manager(from_agent)

    escalations = state.get("escalations", [])
    escalations.append({
        "from": from_agent,
        "to": manager,
        "issue": issue,
        "timestamp": "2024-01-01T00:00:00"
    })

    return {"escalations": escalations}

def broadcast_message(state: HierarchicalState, message: str, from_agent: str):
    """向下属广播消息"""
    subordinates = get_subordinates(from_agent)

    broadcasts = state.get("broadcasts", [])
    for subordinate in subordinates:
        broadcasts.append({
            "from": from_agent,
            "to": subordinate,
            "message": message
        })

    return {"broadcasts": broadcasts}
```

## 常见陷阱

### 1. 层级过深

**问题**：层级太多导致通信开销大，响应慢

```python
# 错误示例：5 层层级
CEO -> VP -> Director -> Manager -> Team Lead -> Engineer
```

**解决方案**：控制在 3-4 层

```python
# 正确做法：3 层层级
CTO -> Team Lead -> Engineer

# 如果任务复杂，使用子图而不是增加层级
```

### 2. 职责不清

**问题**：不同层级的职责重叠或模糊

```python
# 错误示例：管理者也执行具体任务
def team_lead(state):
    # 既分配任务
    assign_task_to_engineer()
    # 又自己执行任务（不应该）
    execute_task()
```

**解决方案**：明确职责边界

```python
# 正确做法：管理者只管理
def team_lead(state):
    # 只负责分配和协调
    subtasks = decompose_task(state["task"])
    assign_to_engineers(subtasks)

# 执行者只执行
def engineer(state):
    # 只负责执行
    result = execute_task(state["task"])
    return result
```

### 3. 缺少向上汇报

**问题**：下级完成任务后没有通知上级

```python
# 错误示例：工程师完成后直接结束
workflow.add_edge("engineer", END)  # 错误！
```

**解决方案**：始终返回上级

```python
# 正确做法：返回直接上级
workflow.add_edge("engineer", "team_lead")  # 汇报给上级
workflow.add_edge("team_lead", "cto")  # 继续向上汇报
```

### 4. 状态膨胀

**问题**：每层都在状态中添加数据，导致状态过大

```python
# 错误示例：每层都添加大量数据
class State(TypedDict):
    cto_data: dict  # 大量数据
    frontend_lead_data: dict  # 更多数据
    backend_lead_data: dict  # 更多数据
    engineer_1_data: dict  # 更多数据
    # ... 状态越来越大
```

**解决方案**：使用层级化的状态或外部存储

```python
# 正确做法：每层有自己的状态
class CTOState(TypedDict):
    messages: Annotated[list, add_messages]
    team_assignments: dict

class TeamLeadState(TypedDict):
    messages: Annotated[list, add_messages]
    engineer_assignments: dict

# 或使用外部存储
class State(TypedDict):
    messages: Annotated[list, add_messages]
    result_ids: list[str]  # 只存储引用

# 实际数据存储在外部
result_store = {}
```

### 5. 忽略并行机会

**问题**：串行执行可以并行的任务

```python
# 错误示例：串行执行独立任务
workflow.add_edge("frontend_team", "backend_team")  # 串行
```

**解决方案**：识别并行机会

```python
# 正确做法：并行执行独立任务
from langgraph.graph import Send

def cto(state):
    # 并行分配给两个团队
    return [
        Send("frontend_team", state),
        Send("backend_team", state)
    ]

workflow.add_conditional_edges(START, cto)
```

## 与其他模式的对比

| 特性 | Hierarchical | Supervisor | Multi-Agent |
|------|--------------|------------|-------------|
| 层级数量 | 多层（3+） | 单层 | 无层级 |
| 管理者数量 | 多个 | 一个 | 无 |
| 任务分解 | 递归分解 | 一次分解 | 协商分解 |
| 适用规模 | 大型 | 中型 | 小型 |
| 通信模式 | 层级化 | 星型 | 网状 |
| 扩展性 | 高 | 中 | 低 |

## 总结

Hierarchical 模式适合大规模复杂任务的层级化管理。关键要点：

1. **清晰的层级结构**：定义明确的组织架构和汇报关系
2. **任务分解**：上级将任务分解为子任务并委派
3. **结果汇总**：下级完成后向上汇报，逐层汇总
4. **职责分离**：管理者负责协调，执行者负责实施
5. **使用子图**：每个团队可以是独立的子图
6. **控制层级深度**：避免过深的层级结构
7. **识别并行机会**：同级任务可以并行执行

通过合理使用 Hierarchical 模式，可以构建可扩展的大规模 Agent 系统，有效管理复杂的多层次任务。
