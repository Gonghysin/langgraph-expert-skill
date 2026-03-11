# Human-in-the-Loop 模式

## 概述

Human-in-the-Loop（人机协作）模式允许在 Agent 执行过程中暂停工作流，等待人工输入、审批或决策。这种模式在需要人工监督、敏感操作或复杂决策的场景中至关重要。

## 何时使用

### 适用场景

1. **敏感操作审批**
   - 金融交易确认
   - 数据删除操作
   - 权限变更
   - 系统配置修改

2. **复杂决策支持**
   - 多个可行方案需要人工选择
   - 风险评估需要专家判断
   - 创意内容需要人工审核

3. **质量控制**
   - 生成内容的人工审核
   - 关键步骤的验证
   - 错误处理的人工介入

4. **合规要求**
   - 法律文件审批
   - 医疗决策确认
   - 隐私数据处理授权

### 不适用场景

- 完全自动化的批处理任务
- 实时性要求极高的场景
- 简单的数据转换操作
- 低风险的常规任务

## 核心概念

### 1. 中断点（Interrupt）

中断点是工作流中预定义的暂停位置，Agent 在到达中断点时会停止执行并等待人工输入。

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

# 在特定节点前设置中断
graph = StateGraph(State)
graph.add_node("analyze", analyze_node)
graph.add_node("execute", execute_node)  # 在此节点前中断

# 编译时指定中断点
app = graph.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["execute"]  # 在 execute 节点前暂停
)
```

### 2. 检查点（Checkpoint）

检查点机制保存工作流的状态，使得中断后可以从相同位置恢复执行。

**关键特性：**
- 自动保存状态
- 支持状态恢复
- 持久化存储
- 版本管理

### 3. 人工输入（Human Input）

人工可以在中断点：
- 审批或拒绝操作
- 修改状态数据
- 提供额外信息
- 选择执行路径

## 完整代码示例

### 基础示例：审批工作流

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

class ApprovalState(TypedDict):
    messages: Annotated[list, add_messages]
    action: str
    approved: bool
    reason: str

def analyze_request(state: ApprovalState) -> ApprovalState:
    """分析用户请求"""
    action = state["messages"][-1].content

    # 分析请求的风险等级
    risk_level = "high" if "delete" in action.lower() else "low"

    return {
        "action": action,
        "messages": [{"role": "assistant", "content": f"检测到操作: {action}, 风险等级: {risk_level}"}]
    }

def execute_action(state: ApprovalState) -> ApprovalState:
    """执行已批准的操作"""
    if not state.get("approved", False):
        return {
            "messages": [{"role": "assistant", "content": "操作未获批准，已取消"}]
        }

    # 执行实际操作
    result = f"已执行操作: {state['action']}"

    return {
        "messages": [{"role": "assistant", "content": result}]
    }

def should_continue(state: ApprovalState) -> str:
    """决定是否需要人工审批"""
    # 高风险操作需要审批
    if "delete" in state["action"].lower() or "modify" in state["action"].lower():
        return "require_approval"
    return "execute"

# 构建图
workflow = StateGraph(ApprovalState)

# 添加节点
workflow.add_node("analyze", analyze_request)
workflow.add_node("execute", execute_action)

# 添加边
workflow.set_entry_point("analyze")
workflow.add_conditional_edges(
    "analyze",
    should_continue,
    {
        "require_approval": "execute",  # 需要审批时也指向 execute，但会在此前中断
        "execute": "execute"
    }
)
workflow.add_edge("execute", END)

# 编译图，设置中断点
checkpointer = MemorySaver()
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["execute"]  # 在执行前中断，等待人工审批
)

# 使用示例
from langchain_core.messages import HumanMessage

# 配置线程 ID
config = {"configurable": {"thread_id": "approval-001"}}

# 第一步：提交请求
initial_input = {
    "messages": [HumanMessage(content="删除用户数据库中的所有测试账户")]
}

# 运行到中断点
for event in app.stream(initial_input, config):
    print(event)

# 此时工作流已暂停，等待人工审批

# 第二步：人工审批（在另一个会话中）
# 获取当前状态
current_state = app.get_state(config)
print(f"当前状态: {current_state.values}")
print(f"下一步: {current_state.next}")  # 应该显示 ('execute',)

# 人工审批：更新状态
app.update_state(
    config,
    {
        "approved": True,
        "reason": "已验证，这是合法的测试数据清理操作"
    }
)

# 第三步：恢复执行
for event in app.stream(None, config):  # 传入 None 表示从当前状态继续
    print(event)
```

### 高级示例：多步骤审批

```python
from typing import Literal

class MultiStepState(TypedDict):
    messages: Annotated[list, add_messages]
    plan: list[str]
    current_step: int
    approvals: dict[int, bool]
    results: list[str]

def create_plan(state: MultiStepState) -> MultiStepState:
    """创建执行计划"""
    request = state["messages"][-1].content

    # 生成多步骤计划
    plan = [
        "步骤1: 备份现有数据",
        "步骤2: 验证备份完整性",
        "步骤3: 执行数据迁移",
        "步骤4: 验证迁移结果",
        "步骤5: 清理临时文件"
    ]

    return {
        "plan": plan,
        "current_step": 0,
        "approvals": {},
        "results": [],
        "messages": [{"role": "assistant", "content": f"已创建执行计划，共 {len(plan)} 步"}]
    }

def execute_step(state: MultiStepState) -> MultiStepState:
    """执行当前步骤"""
    step_idx = state["current_step"]

    # 检查是否已批准
    if not state["approvals"].get(step_idx, False):
        return {
            "messages": [{"role": "assistant", "content": f"步骤 {step_idx + 1} 未获批准"}]
        }

    # 执行步骤
    step_desc = state["plan"][step_idx]
    result = f"✓ 已完成: {step_desc}"

    new_results = state["results"] + [result]
    next_step = step_idx + 1

    return {
        "results": new_results,
        "current_step": next_step,
        "messages": [{"role": "assistant", "content": result}]
    }

def check_completion(state: MultiStepState) -> Literal["continue", "end"]:
    """检查是否完成所有步骤"""
    if state["current_step"] >= len(state["plan"]):
        return "end"
    return "continue"

# 构建工作流
workflow = StateGraph(MultiStepState)

workflow.add_node("plan", create_plan)
workflow.add_node("execute_step", execute_step)

workflow.set_entry_point("plan")
workflow.add_edge("plan", "execute_step")
workflow.add_conditional_edges(
    "execute_step",
    check_completion,
    {
        "continue": "execute_step",  # 继续下一步
        "end": END
    }
)

# 编译，每步执行前都需要审批
app = workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["execute_step"]
)

# 使用示例
config = {"configurable": {"thread_id": "multi-step-001"}}

# 创建计划
initial_input = {
    "messages": [HumanMessage(content="执行数据库迁移")]
}

for event in app.stream(initial_input, config):
    print(event)

# 逐步审批和执行
for step_idx in range(5):
    # 获取当前状态
    state = app.get_state(config)
    current_step = state.values["current_step"]
    plan = state.values["plan"]

    print(f"\n等待审批: {plan[current_step]}")

    # 模拟人工审批
    approval = input(f"是否批准步骤 {current_step + 1}? (y/n): ")

    # 更新审批状态
    approvals = state.values["approvals"].copy()
    approvals[current_step] = (approval.lower() == 'y')

    app.update_state(config, {"approvals": approvals})

    # 继续执行
    for event in app.stream(None, config):
        print(event)

    # 如果未批准，终止流程
    if approval.lower() != 'y':
        print("流程已终止")
        break
```

## 最佳实践

### 1. 中断点设计

**合理设置中断位置：**
```python
# ✓ 好的做法：在关键决策点设置中断
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["execute_transaction", "delete_data", "send_email"]
)

# ✗ 避免：过多的中断点影响效率
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["step1", "step2", "step3", "step4", "step5"]  # 太多了
)
```

**提供清晰的上下文：**
```python
def prepare_approval(state: State) -> State:
    """在中断前准备审批所需的所有信息"""
    return {
        "approval_context": {
            "action": state["action"],
            "risk_level": state["risk_level"],
            "affected_resources": state["resources"],
            "estimated_impact": state["impact"],
            "rollback_plan": state["rollback"]
        }
    }
```

### 2. 状态持久化

**使用合适的 Checkpointer：**
```python
# 开发环境：内存存储
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()

# 生产环境：持久化存储
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# 分布式环境：Redis 或数据库
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string("postgresql://...")
```

**管理检查点生命周期：**
```python
# 清理过期的检查点
def cleanup_old_checkpoints(checkpointer, days=7):
    """清理超过指定天数的检查点"""
    cutoff_time = datetime.now() - timedelta(days=days)
    # 实现清理逻辑
    pass
```

### 3. 用户体验优化

**提供进度反馈：**
```python
def get_workflow_status(app, config):
    """获取工作流当前状态和进度"""
    state = app.get_state(config)

    return {
        "status": "waiting_approval" if state.next else "completed",
        "current_step": state.values.get("current_step"),
        "total_steps": len(state.values.get("plan", [])),
        "next_action": state.next[0] if state.next else None,
        "context": state.values.get("approval_context")
    }
```

**支持批量审批：**
```python
def batch_approve(app, config, step_range, approved=True):
    """批量审批多个步骤"""
    state = app.get_state(config)
    approvals = state.values.get("approvals", {}).copy()

    for step_idx in step_range:
        approvals[step_idx] = approved

    app.update_state(config, {"approvals": approvals})
```

### 4. 错误处理

**处理超时：**
```python
from datetime import datetime, timedelta

class TimeoutState(TypedDict):
    created_at: str
    timeout_minutes: int

def check_timeout(state: TimeoutState) -> bool:
    """检查是否超时"""
    created = datetime.fromisoformat(state["created_at"])
    timeout = timedelta(minutes=state["timeout_minutes"])
    return datetime.now() - created > timeout

# 在恢复执行前检查
state = app.get_state(config)
if check_timeout(state.values):
    # 处理超时情况
    app.update_state(config, {"status": "timeout", "approved": False})
```

**支持撤销和重试：**
```python
def rollback_to_step(app, config, step_idx):
    """回滚到指定步骤"""
    state = app.get_state(config)

    # 重置状态到指定步骤
    app.update_state(config, {
        "current_step": step_idx,
        "results": state.values["results"][:step_idx],
        "approvals": {k: v for k, v in state.values["approvals"].items() if k < step_idx}
    })
```

## 常见陷阱

### 1. 过度中断

**问题：**
```python
# ✗ 每个小步骤都中断
app = workflow.compile(
    interrupt_before=["validate", "transform", "format", "save"]
)
```

**解决方案：**
```python
# ✓ 只在关键决策点中断
app = workflow.compile(
    interrupt_before=["save"]  # 只在最终保存前确认
)
```

### 2. 缺少上下文

**问题：**
```python
# ✗ 审批时缺少必要信息
def execute(state):
    # 人工不知道要审批什么
    pass
```

**解决方案：**
```python
# ✓ 提供完整的审批上下文
def prepare_for_approval(state):
    return {
        "approval_request": {
            "summary": "删除 100 个测试账户",
            "details": state["affected_accounts"],
            "risk": "中等",
            "reversible": True
        }
    }
```

### 3. 状态丢失

**问题：**
```python
# ✗ 使用内存存储，重启后状态丢失
checkpointer = MemorySaver()  # 生产环境不应使用
```

**解决方案：**
```python
# ✓ 使用持久化存储
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
```

### 4. 并发冲突

**问题：**
```python
# ✗ 多个用户同时修改同一个工作流状态
app.update_state(config, {"approved": True})  # 可能覆盖其他更新
```

**解决方案：**
```python
# ✓ 使用版本控制或锁机制
state = app.get_state(config)
checkpoint_id = state.config["configurable"]["checkpoint_id"]

# 基于特定检查点更新
app.update_state(
    {**config, "configurable": {**config["configurable"], "checkpoint_id": checkpoint_id}},
    {"approved": True}
)
```

## 与其他模式的结合

### Human-in-the-Loop + ReAct

```python
# 在 ReAct 循环中添加人工审批
def should_interrupt(state):
    # 高风险工具需要审批
    if state["next_tool"] in ["delete_file", "execute_code"]:
        return "approve_tool"
    return "execute_tool"

workflow.add_conditional_edges(
    "agent",
    should_interrupt,
    {
        "approve_tool": "execute_tool",  # 会在此前中断
        "execute_tool": "execute_tool"
    }
)

app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["execute_tool"]
)
```

### Human-in-the-Loop + Plan-and-Execute

```python
# 在计划执行前审批整个计划
workflow.add_edge("planner", "executor")

app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["executor"]  # 审批计划后再执行
)
```

## 总结

Human-in-the-Loop 模式的关键要素：

1. **中断点设计**：在关键决策点设置中断，避免过度中断
2. **状态持久化**：使用合适的 checkpointer 确保状态不丢失
3. **上下文提供**：为人工决策提供充分的信息
4. **用户体验**：提供清晰的进度反馈和操作界面
5. **错误处理**：处理超时、撤销、重试等异常情况

通过合理使用 Human-in-the-Loop 模式，可以在保持自动化效率的同时，确保关键操作的安全性和准确性。
