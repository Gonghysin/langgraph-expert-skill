---
name: langgraph-expert
description: "Build production-grade AI agents with LangGraph. TRIGGER when: user mentions building agents, state graphs, workflow orchestration, agentic systems, multi-step AI workflows, or imports langgraph. Also trigger for: ReAct patterns, plan-and-execute, human-in-the-loop, agent architecture design, state management for AI agents. DO NOT TRIGGER when: simple LLM calls without state, basic LangChain usage without graphs, or general Python programming unrelated to agents."
---

# LangGraph Expert

为 LangGraph 开发者提供架构模式选择、最佳实践指导和调试支持的专家 skill。

## 概述

本 skill 帮助你：
- 选择合适的 LangGraph 架构模式
- 实现高质量的 Agent 代码
- 调试和优化 LangGraph 应用
- 遵循最佳实践进行开发

## 工作流程

根据用户请求类型，本 skill 采用不同的工作流：

### 新功能或复杂任务

1. **理解需求** - 询问澄清性问题，了解具体需求
2. **推荐模式** - 基于决策树推荐合适的架构模式
3. **生成计划** - 调用 @superpowers:writing-plans 生成详细实施计划
4. **TDD 开发** - 调用 @superpowers:test-driven-development 进行测试驱动开发
5. **提供指导** - 从 references/ 读取相关模式文档和最佳实践
6. **验证优化** - 使用 scripts/validate_graph.py 验证图结构

### 调试或优化任务

1. **识别问题** - 分析用户提供的代码和错误信息
2. **查找陷阱** - 读取 references/common-pitfalls.md 找到相关错误模式
3. **提供方案** - 展示正确做法，解释原因，提供代码示例
4. **验证修复** - 运行 validate_graph.py，建议相关测试

## 语言检测

在开始之前，检查项目环境以确认使用 Python：

1. **查找 Python 项目文件**：
   - requirements.txt
   - pyproject.toml
   - setup.py
   - *.py 文件

2. **如果检测到 package.json 但没有 Python 文件**：
   提示用户 LangGraph 主要支持 Python，建议使用 Python 实现

3. **如果环境不明确**：
   询问用户使用的编程语言

## 模式选择决策树

根据用户需求选择合适的 LangGraph 架构模式：

```
用户需求是什么？

1. 需要工具调用和推理循环
   └─> ReAct 模式
   读取: references/patterns/react.md

2. 需要先规划再执行
   └─> Plan-and-Execute 模式
   读取: references/patterns/plan-and-execute.md

3. 需要人工审批或输入
   └─> Human-in-the-Loop 模式
   读取: references/patterns/human-in-the-loop.md

4. 需要自我反思和改进
   └─> Reflection 模式
   读取: references/patterns/reflection.md

5. 需要多个专门的 Agent 协作
   ├─> 平等协作 → Multi-Agent 模式
   │   读取: references/patterns/multi-agent.md
   ├─> 有中心协调者 → Supervisor 模式
   │   读取: references/patterns/supervisor.md
   └─> 有层级关系 → Hierarchical 模式
       读取: references/patterns/hierarchical.md
```

### 如何使用决策树

1. **询问用户需求** - 了解用户想要实现什么功能
2. **匹配模式** - 根据上述决策树找到最合适的模式
3. **读取文档** - 从 references/patterns/ 读取对应的模式文档
4. **提供指导** - 基于模式文档提供架构设计和实现建议

## 阅读指南

### 架构模式文档

**核心模式**（按使用频率排序）：

1. **references/patterns/react.md**
   - 最常用的模式
   - 工具调用 + 推理循环
   - 适合大多数 Agent 场景

2. **references/patterns/plan-and-execute.md**
   - 先规划后执行
   - 适合复杂多步骤任务

3. **references/patterns/human-in-the-loop.md**
   - 人工审批和输入
   - 适合需要人工监督的场景

4. **references/patterns/reflection.md**
   - 自我反思和改进
   - 适合需要质量保证的场景

**扩展模式**（多 Agent 协作）：

5. **references/patterns/multi-agent.md**
   - 多个平等 Agent 协作
   - 适合分布式任务处理

6. **references/patterns/supervisor.md**
   - 中心协调者模式
   - 适合需要任务分配的场景

7. **references/patterns/hierarchical.md**
   - 层级化 Agent 架构
   - 适合大型复杂系统

### 最佳实践和指导

**必读文档**：

- **references/best-practices.md**
  - 状态管理最佳实践
  - 错误处理策略
  - 性能优化建议
  - 测试策略

- **references/common-pitfalls.md**
  - 常见错误和陷阱
  - 调试技巧
  - 问题排查指南

- **references/testing-guide.md**
  - 单元测试策略
  - 集成测试方法
  - Mock 和 Stub 技巧

### 工具脚本

- **scripts/validate_graph.py**
  - 验证图结构完整性
  - 检查节点和边的定义
  - 发现潜在的死循环

- **scripts/visualize_graph.py**
  - 生成图的可视化
  - 帮助理解复杂的状态流转

## 使用示例

### 示例 1：构建新的 Agent

**用户请求**：
> "我想构建一个能够搜索网络、分析内容并生成报告的 Agent"

**Skill 工作流**：

1. **理解需求**
   ```
   询问：
   - 是否需要多次工具调用？
   - 是否需要人工审批？
   - 报告质量要求如何？
   ```

2. **推荐模式**
   ```
   基于需求，推荐：
   - 主模式：ReAct（工具调用 + 推理）
   - 可选：Reflection（提升报告质量）
   ```

3. **生成计划**
   ```
   调用 @superpowers:writing-plans
   生成详细的实施计划
   ```

4. **提供指导**
   ```
   读取 references/patterns/react.md
   展示代码结构和关键实现
   ```

5. **TDD 开发**
   ```
   调用 @superpowers:test-driven-development
   先写测试，再实现功能
   ```

### 示例 2：调试循环问题

**用户请求**：
> "我的 Agent 陷入了无限循环，怎么办？"

**Skill 工作流**：

1. **识别问题**
   ```
   请求用户提供：
   - 图定义代码
   - 错误日志
   - 预期行为
   ```

2. **查找陷阱**
   ```
   读取 references/common-pitfalls.md
   查找"无限循环"相关章节
   ```

3. **提供方案**
   ```
   展示：
   - 循环检测机制
   - 最大迭代次数设置
   - 条件边的正确使用
   ```

4. **验证修复**
   ```
   运行 scripts/validate_graph.py
   建议添加循环检测测试
   ```

## 重要提示

### 开发原则

1. **DRY（Don't Repeat Yourself）**
   - 复用模式文档中的代码结构
   - 避免重复实现相同的逻辑

2. **YAGNI（You Aren't Gonna Need It）**
   - 从最简单的模式开始
   - 只在需要时添加复杂性

3. **TDD（Test-Driven Development）**
   - 始终先写测试
   - 使用 @superpowers:test-driven-development

### 质量保证

- **代码审查**：完成后调用 @superpowers:code-review
- **图验证**：使用 scripts/validate_graph.py
- **测试覆盖率**：确保 ≥80% 覆盖率

### 性能考虑

- **状态大小**：保持状态对象精简
- **工具调用**：避免不必要的 LLM 调用
- **并行执行**：利用 LangGraph 的并行能力

### 安全注意事项

- **输入验证**：验证所有外部输入
- **错误处理**：优雅处理所有异常
- **敏感数据**：不在状态中存储敏感信息
