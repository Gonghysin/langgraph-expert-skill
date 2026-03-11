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
