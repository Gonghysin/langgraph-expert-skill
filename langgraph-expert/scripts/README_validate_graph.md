# validate_graph.py - LangGraph 图验证工具

## 功能

自动验证 LangGraph 图定义的正确性,包括:

1. **循环依赖检测** - 检测图中的循环和自循环
2. **状态类型验证** - 验证是否使用了 TypedDict 定义状态
3. **死节点检测** - 检查无法从入口点到达的节点
4. **条件边完整性** - 验证条件边是否定义了足够的路径
5. **入口点验证** - 确保图有明确的入口点

## 使用方法

### 命令行使用

```bash
python validate_graph.py <graph_file.py>
```

### Python API 使用

```python
from validate_graph import validate_graph

result = validate_graph("my_graph.py")

if result["valid"]:
    print("图验证通过!")
else:
    print("发现错误:")
    for error in result["errors"]:
        print(f"  - {error}")
```

## 示例

### 示例 1: 检测循环依赖

```python
# bad_graph.py
from langgraph.graph import StateGraph

graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge("a", "b")
graph.add_edge("b", "a")  # 循环!
```

运行验证:
```bash
$ python validate_graph.py bad_graph.py

============================================================
验证结果: ✗ 失败
============================================================

错误:
  ✗ 检测到循环依赖: b -> a -> b
```

### 示例 2: 检测死节点

```python
# orphan_node.py
from langgraph.graph import StateGraph, END

graph = StateGraph(State)
graph.add_node("start", start_node)
graph.add_node("process", process_node)
graph.add_node("orphan", orphan_node)  # 死节点

graph.set_entry_point("start")
graph.add_edge("start", "process")
graph.add_edge("process", END)
```

运行验证:
```bash
$ python validate_graph.py orphan_node.py

============================================================
验证结果: ✗ 失败
============================================================

错误:
  ✗ 节点 'orphan' 无法从入口点到达
```

### 示例 3: 有效的图

```python
# good_graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, END

class State(TypedDict):
    messages: list
    count: int

graph = StateGraph(State)
graph.add_node("start", start_node)
graph.add_node("process", process_node)
graph.set_entry_point("start")
graph.add_edge("start", "process")
graph.add_edge("process", END)
```

运行验证:
```bash
$ python validate_graph.py good_graph.py

============================================================
验证结果: ✓ 通过
============================================================

节点数: 2
边数: 1
入口点: start
状态类型: State
```

## 返回值结构

`validate_graph()` 函数返回一个字典:

```python
{
    "valid": bool,              # 是否通过验证
    "errors": List[str],        # 错误列表
    "warnings": List[str],      # 警告列表
    "nodes": List[str],         # 节点列表
    "edges": List[tuple],       # 边列表
    "entry_point": str,         # 入口点
    "state_types": List[str]    # 状态类型列表
}
```

## 集成到工作流

### 在 CI/CD 中使用

```yaml
# .github/workflows/validate.yml
name: Validate LangGraph

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate graphs
        run: |
          python scripts/validate_graph.py src/my_graph.py
```

### 在 pre-commit hook 中使用

```bash
# .git/hooks/pre-commit
#!/bin/bash

for file in $(git diff --cached --name-only | grep '\.py$'); do
    if grep -q "StateGraph" "$file"; then
        python scripts/validate_graph.py "$file" || exit 1
    fi
done
```

## 测试

运行测试套件:

```bash
pytest test_validate_graph.py -v
```

## 限制

- 仅支持静态分析,无法检测运行时动态创建的节点和边
- 条件边的完整性检查是启发式的,可能产生误报
- 不验证节点函数的实现逻辑
- **循环检测**: 工具会检测所有循环,包括有终止条件的合法循环(如 ReAct 模式)。在这种情况下,请确保:
  - 条件边中有明确的终止路径(如 `END`)
  - 状态中有循环计数器和最大迭代次数限制
  - 节点函数中有适当的终止逻辑

## 最佳实践

1. 在开发过程中频繁运行验证
2. 将验证集成到 CI/CD 流程
3. 结合单元测试和集成测试使用
4. 定期审查警告信息,即使图通过了验证
