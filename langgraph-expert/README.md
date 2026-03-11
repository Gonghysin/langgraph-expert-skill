# LangGraph Expert Skill

LangGraph 专家技能包，为 Claude Code 提供 LangGraph 开发的全面支持。

## 📋 概述

这个 skill 提供了 LangGraph 开发的最佳实践、常见模式、测试指南和实用工具，帮助开发者快速构建高质量的 LangGraph 应用。

## 🎯 功能特性

### 1. 设计模式库
- **ReAct 模式** - 推理与行动循环
- **Plan-and-Execute 模式** - 规划与执行分离
- **Reflection 模式** - 自我反思与改进
- **Human-in-the-Loop 模式** - 人机协作
- **Multi-Agent 模式** - 多智能体协作
- **Supervisor 模式** - 监督者协调
- **Hierarchical 模式** - 层次化任务分解

### 2. 开发指南
- **最佳实践** - 状态管理、错误处理、性能优化
- **测试指南** - 单元测试、集成测试、端到端测试
- **常见陷阱** - 避免常见错误和反模式

### 3. 实用工具
- **图验证工具** (`validate_graph.py`) - 验证图结构的完整性和正确性
- **示例代码** - 可运行的示例图
- **测试套件** - 完整的测试覆盖

## 🚀 快速开始

### 安装依赖

```bash
pip install langgraph langchain-core
```

### 使用 Skill

在 Claude Code 中调用：

```
/langgraph-expert [你的问题或需求]
```

### 运行示例

```bash
cd langgraph-expert/scripts
python example_simple_graph.py
```

### 验证图结构

```bash
cd langgraph-expert/scripts
python validate_graph.py path/to/your/graph.py
```

## 📚 文档结构

```
langgraph-expert/
├── README.md                          # 本文件
├── SKILL.md                           # Skill 定义
├── references/                        # 参考文档
│   ├── best-practices.md             # 最佳实践
│   ├── testing-guide.md              # 测试指南
│   ├── common-pitfalls.md            # 常见陷阱
│   └── patterns/                     # 设计模式
│       ├── react.md
│       ├── plan-and-execute.md
│       ├── reflection.md
│       ├── human-in-the-loop.md
│       ├── multi-agent.md
│       ├── supervisor.md
│       └── hierarchical.md
└── scripts/                          # 工具和示例
    ├── validate_graph.py             # 图验证工具
    ├── test_validate_graph.py        # 测试文件
    ├── example_simple_graph.py       # 简单示例
    ├── example_graph.py              # 复杂示例
    ├── demo.sh                       # 演示脚本
    ├── README_validate_graph.md      # 工具文档
    └── IMPLEMENTATION_REPORT.md      # 实现报告
```

## 🔧 工具说明

### validate_graph.py

图验证工具，检查：
- 节点定义完整性
- 边连接有效性
- 入口点和结束点配置
- 条件边逻辑
- 状态类型一致性

**使用方法：**

```bash
python validate_graph.py <graph_file.py>
```

**示例输出：**

```
✓ 节点定义检查通过
✓ 边连接检查通过
✓ 入口点检查通过
✓ 结束点检查通过
✓ 条件边检查通过
✓ 状态类型检查通过

图验证通过！
```

## 📖 使用场景

### 1. 学习 LangGraph
- 查看设计模式文档了解不同的架构方式
- 运行示例代码理解实际应用
- 阅读最佳实践避免常见错误

### 2. 开发新应用
- 选择合适的设计模式
- 使用验证工具确保图结构正确
- 参考测试指南编写测试

### 3. 调试和优化
- 查看常见陷阱文档排查问题
- 使用验证工具检查图配置
- 参考最佳实践优化性能

## 🧪 测试

运行所有测试：

```bash
cd langgraph-expert/scripts
python -m pytest test_validate_graph.py -v
```

## 📝 版本历史

### v1.0.0 (2026-03-11)
- ✅ 7 个核心设计模式
- ✅ 完整的最佳实践指南
- ✅ 测试指南和常见陷阱文档
- ✅ 图验证工具
- ✅ 示例代码和测试套件

## 🤝 贡献

欢迎提交问题和改进建议！

## 📄 许可

MIT License

## 🔗 相关资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 文档](https://python.langchain.com/)
- [Claude Code 文档](https://docs.anthropic.com/claude/docs)

---

**Made with ❤️ for Claude Code users**
