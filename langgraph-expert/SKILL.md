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
