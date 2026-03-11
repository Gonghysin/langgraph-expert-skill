# LangGraph 测试指南

## 概述

本指南提供 LangGraph 应用的测试策略和最佳实践，涵盖单元测试、集成测试、Mock 技巧和调试方法。

## 测试策略

### 测试金字塔

```
        /\
       /E2E\        少量端到端测试
      /------\
     /集成测试 \     中等数量集成测试
    /----------\
   /  单元测试   \   大量单元测试
  /--------------\
```

**推荐比例：** 单元测试 70% | 集成测试 20% | E2E 测试 10%

### 测试覆盖目标

- **节点函数：** 100% 覆盖（纯函数易测试）
- **图逻辑：** 80%+ 覆盖（关键路径必测）
- **边缘情况：** 错误处理、超时、重试
- **性能测试：** 响应时间、内存使用

## 单元测试

### 测试节点函数

节点函数通常是纯函数，接收状态返回更新，易于测试。

**示例：测试分析节点**

```python
import pytest
from my_graph.nodes import analyze_query
from my_graph.state import GraphState

def test_analyze_query_simple():
    """测试简单查询分析"""
    state = GraphState(
        query="What is the weather?",
        analysis=None
    )

    result = analyze_query(state)

    assert result["analysis"] is not None
    assert "weather" in result["analysis"].lower()
    assert result["query"] == "What is the weather?"

def test_analyze_query_empty():
    """测试空查询处理"""
    state = GraphState(query="", analysis=None)

    with pytest.raises(ValueError, match="Query cannot be empty"):
        analyze_query(state)

def test_analyze_query_complex():
    """测试复杂查询"""
    state = GraphState(
        query="Compare Python and JavaScript for web development",
        analysis=None
    )

    result = analyze_query(state)

    assert "python" in result["analysis"].lower()
    assert "javascript" in result["analysis"].lower()
    assert "comparison" in result["analysis"].lower() or "compare" in result["analysis"].lower()
```

### 测试条件边函数

```python
from my_graph.edges import should_continue

def test_should_continue_max_iterations():
    """测试达到最大迭代次数"""
    state = GraphState(
        iteration=5,
        max_iterations=5,
        is_complete=False
    )

    result = should_continue(state)
    assert result == "end"

def test_should_continue_task_complete():
    """测试任务完成"""
    state = GraphState(
        iteration=2,
        max_iterations=5,
        is_complete=True
    )

    result = should_continue(state)
    assert result == "end"

def test_should_continue_normal():
    """测试正常继续"""
    state = GraphState(
        iteration=2,
        max_iterations=5,
        is_complete=False
    )

    result = should_continue(state)
    assert result == "continue"
```

### 测试工具函数

```python
from unittest.mock import patch, MagicMock
from my_graph.tools import search_web

@patch('my_graph.tools.requests.get')
def test_search_web_success(mock_get):
    """测试成功的网络搜索"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [{"title": "Result 1", "url": "http://example.com"}]
    }
    mock_get.return_value = mock_response

    result = search_web("test query")

    assert len(result) == 1
    assert result[0]["title"] == "Result 1"
    mock_get.assert_called_once()

@patch('my_graph.tools.requests.get')
def test_search_web_timeout(mock_get):
    """测试搜索超时"""
    mock_get.side_effect = TimeoutError("Request timeout")

    with pytest.raises(TimeoutError):
        search_web("test query")
```

## 集成测试

### 测试完整图执行

```python
import pytest
from langgraph.graph import StateGraph
from my_graph.graph import create_graph
from my_graph.state import GraphState

@pytest.fixture
def graph():
    """创建测试图实例"""
    return create_graph()

def test_graph_simple_flow(graph):
    """测试简单流程"""
    initial_state = GraphState(
        query="What is LangGraph?",
        messages=[],
        iteration=0
    )

    result = graph.invoke(initial_state)

    assert result["query"] == "What is LangGraph?"
    assert len(result["messages"]) > 0
    assert result["iteration"] > 0
    assert "langgraph" in str(result["messages"]).lower()

def test_graph_max_iterations(graph):
    """测试最大迭代限制"""
    initial_state = GraphState(
        query="Complex recursive query",
        messages=[],
        iteration=0,
        max_iterations=3
    )

    result = graph.invoke(initial_state)

    assert result["iteration"] <= 3

def test_graph_error_handling(graph):
    """测试错误处理"""
    initial_state = GraphState(
        query="",  # 空查询应触发错误
        messages=[]
    )

    result = graph.invoke(initial_state)

    assert "error" in result or len(result["messages"]) == 0
```

### 测试流式输出

```python
def test_graph_streaming(graph):
    """测试流式输出"""
    initial_state = GraphState(query="Test streaming")

    chunks = []
    for chunk in graph.stream(initial_state):
        chunks.append(chunk)

    assert len(chunks) > 0
    # 验证每个 chunk 包含预期字段
    for chunk in chunks:
        assert isinstance(chunk, dict)
```

## Mock LLM 调用

### 使用 FakeListLLM

```python
from langchain_core.language_models.fake import FakeListLLM
from my_graph.nodes import llm_node

def test_llm_node_with_fake_llm():
    """使用假 LLM 测试节点"""
    fake_llm = FakeListLLM(responses=[
        "This is a test response",
        "This is another response"
    ])

    state = GraphState(
        query="Test query",
        llm=fake_llm  # 注入假 LLM
    )

    result = llm_node(state)

    assert "test response" in result["messages"][-1].content.lower()
```

### 使用 Mock 对象

```python
from unittest.mock import Mock, patch
from langchain_core.messages import AIMessage

@patch('my_graph.nodes.ChatOpenAI')
def test_llm_node_with_mock(mock_chat):
    """使用 Mock 测试 LLM 节点"""
    mock_instance = Mock()
    mock_instance.invoke.return_value = AIMessage(content="Mocked response")
    mock_chat.return_value = mock_instance

    state = GraphState(query="Test")
    result = llm_node(state)

    assert result["messages"][-1].content == "Mocked response"
```

### 使用环境变量控制

```python
import os
import pytest

@pytest.fixture
def mock_api_key(monkeypatch):
    """Mock API 密钥"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    yield
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

def test_with_mock_api_key(mock_api_key):
    """测试使用 Mock API 密钥"""
    assert os.getenv("OPENAI_API_KEY") == "test-key-123"
```

## 调试技巧

### 1. 启用详细日志

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 在节点中添加日志
def my_node(state: GraphState):
    logging.debug(f"Node input state: {state}")
    # ... 处理逻辑
    logging.debug(f"Node output: {result}")
    return result
```

### 2. 状态追踪

```python
def test_graph_with_state_tracking(graph):
    """追踪状态变化"""
    initial_state = GraphState(query="Test")

    states = []
    for step in graph.stream(initial_state):
        states.append(step)
        print(f"Step {len(states)}: {step.keys()}")

    # 验证状态演变
    assert len(states) > 0
    assert states[0] != states[-1]
```

### 3. 可视化图结构

```python
from IPython.display import Image, display

def visualize_graph(graph):
    """可视化图结构（Jupyter Notebook）"""
    try:
        display(Image(graph.get_graph().draw_mermaid_png()))
    except Exception as e:
        print(f"Visualization failed: {e}")
        # 打印文本表示
        print(graph.get_graph().to_json())

# 在测试中使用
def test_graph_structure(graph):
    """验证图结构"""
    graph_dict = graph.get_graph().to_json()

    # 验证节点存在
    assert "analyze" in str(graph_dict)
    assert "process" in str(graph_dict)

    # 可选：可视化
    visualize_graph(graph)
```

### 4. 断点调试

```python
def test_with_breakpoint(graph):
    """使用断点调试"""
    initial_state = GraphState(query="Debug test")

    # 设置断点
    import pdb; pdb.set_trace()

    result = graph.invoke(initial_state)
    assert result is not None
```

### 5. 性能分析

```python
import time
import pytest

def test_graph_performance(graph):
    """测试图执行性能"""
    initial_state = GraphState(query="Performance test")

    start_time = time.time()
    result = graph.invoke(initial_state)
    end_time = time.time()

    execution_time = end_time - start_time

    # 验证性能要求
    assert execution_time < 5.0, f"Execution took {execution_time}s, expected < 5s"
    assert result is not None

@pytest.mark.benchmark
def test_graph_benchmark(benchmark, graph):
    """使用 pytest-benchmark 进行基准测试"""
    initial_state = GraphState(query="Benchmark test")

    result = benchmark(graph.invoke, initial_state)
    assert result is not None
```

## 测试组织

### 目录结构

```
tests/
├── unit/
│   ├── test_nodes.py
│   ├── test_edges.py
│   └── test_tools.py
├── integration/
│   ├── test_graph_flow.py
│   └── test_streaming.py
├── e2e/
│   └── test_complete_scenarios.py
├── fixtures/
│   ├── sample_data.py
│   └── mock_responses.py
└── conftest.py
```

### conftest.py 示例

```python
import pytest
from my_graph.graph import create_graph
from my_graph.state import GraphState

@pytest.fixture
def graph():
    """提供测试图实例"""
    return create_graph()

@pytest.fixture
def sample_state():
    """提供示例状态"""
    return GraphState(
        query="Sample query",
        messages=[],
        iteration=0
    )

@pytest.fixture(scope="session")
def test_config():
    """提供测试配置"""
    return {
        "max_iterations": 5,
        "timeout": 30,
        "model": "gpt-4"
    }
```

## 持续集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=my_graph --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 最佳实践总结

1. **隔离测试：** 每个测试独立，不依赖其他测试
2. **快速反馈：** 单元测试应在秒级完成
3. **Mock 外部依赖：** LLM、API、数据库等
4. **测试边缘情况：** 空输入、超时、错误
5. **保持测试简单：** 一个测试验证一个行为
6. **使用 Fixtures：** 复用测试数据和配置
7. **持续运行：** CI/CD 自动化测试
8. **监控覆盖率：** 目标 80%+ 覆盖

## 参考资源

- [Pytest 文档](https://docs.pytest.org/)
- [LangChain 测试指南](https://python.langchain.com/docs/contributing/testing)
- [Mock 对象库](https://docs.python.org/3/library/unittest.mock.html)
