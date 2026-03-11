#!/usr/bin/env python3
"""
LangGraph 图结构验证工具

功能:
1. 检测循环依赖
2. 验证状态类型
3. 检查死节点(无法到达的节点)
4. 验证条件边的完整性
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict, deque


class GraphValidator:
    """LangGraph 图验证器"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.nodes: Set[str] = set()
        self.edges: List[tuple] = []
        self.conditional_edges: Dict[str, Dict] = {}
        self.entry_point: str = None
        self.state_types: List[str] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_file(self) -> ast.Module:
        """解析 Python 文件为 AST"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return ast.parse(content)

    def extract_graph_info(self, tree: ast.Module):
        """从 AST 中提取图信息"""
        for node in ast.walk(tree):
            # 提取状态类型定义
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'TypedDict':
                        self.state_types.append(node.name)

            # 提取图操作
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr

                    # add_node
                    if method_name == 'add_node' and len(node.args) >= 1:
                        node_name = self._extract_string_value(node.args[0])
                        if node_name:
                            self.nodes.add(node_name)

                    # add_edge
                    elif method_name == 'add_edge' and len(node.args) >= 2:
                        from_node = self._extract_string_value(node.args[0])
                        to_node = self._extract_string_value(node.args[1])
                        if from_node and to_node:
                            self.edges.append((from_node, to_node))

                    # add_conditional_edges
                    elif method_name == 'add_conditional_edges' and len(node.args) >= 3:
                        from_node = self._extract_string_value(node.args[0])
                        # 第三个参数是路径字典
                        if from_node and len(node.args) >= 3:
                            paths = self._extract_dict_keys(node.args[2])
                            self.conditional_edges[from_node] = paths

                    # set_entry_point
                    elif method_name == 'set_entry_point' and len(node.args) >= 1:
                        entry = self._extract_string_value(node.args[0])
                        if entry:
                            self.entry_point = entry

    def _extract_string_value(self, node: ast.AST) -> str:
        """从 AST 节点提取字符串值"""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _extract_dict_keys(self, node: ast.AST) -> Dict:
        """从字典 AST 节点提取键"""
        if isinstance(node, ast.Dict):
            keys = {}
            for key, value in zip(node.keys, node.values):
                key_str = self._extract_string_value(key)
                value_str = self._extract_string_value(value)
                if key_str:
                    keys[key_str] = value_str
            return keys
        return {}

    def check_cycles(self) -> List[str]:
        """检测循环依赖"""
        errors = []

        # 构建邻接表
        graph = defaultdict(list)
        for from_node, to_node in self.edges:
            if to_node != "END":  # END 不是真实节点
                graph[from_node].append(to_node)

        # 添加条件边
        for from_node, paths in self.conditional_edges.items():
            for path_name, to_node in paths.items():
                if to_node and to_node != "END":
                    graph[from_node].append(to_node)

        # 检测自循环
        for node in self.nodes:
            if node in graph[node]:
                errors.append(f"检测到自循环: 节点 '{node}' 指向自己")

        # 使用 DFS 检测循环
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    errors.append(f"检测到循环依赖: {' -> '.join(cycle)}")
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                dfs(node, [])

        return errors

    def check_unreachable_nodes(self) -> List[str]:
        """检查无法到达的节点"""
        if not self.entry_point:
            return []

        errors = []

        # 构建邻接表
        graph = defaultdict(list)
        for from_node, to_node in self.edges:
            if to_node != "END":
                graph[from_node].append(to_node)

        for from_node, paths in self.conditional_edges.items():
            for path_name, to_node in paths.items():
                if to_node and to_node != "END":
                    graph[from_node].append(to_node)

        # BFS 从入口点开始
        reachable = set()
        queue = deque([self.entry_point])
        reachable.add(self.entry_point)

        while queue:
            node = queue.popleft()
            for neighbor in graph.get(node, []):
                if neighbor not in reachable:
                    reachable.add(neighbor)
                    queue.append(neighbor)

        # 检查不可达节点
        unreachable = self.nodes - reachable
        for node in unreachable:
            errors.append(f"节点 '{node}' 无法从入口点到达")

        return errors

    def check_entry_point(self) -> List[str]:
        """检查入口点"""
        errors = []
        if not self.entry_point and len(self.nodes) > 0:
            errors.append("图缺少入口点,请使用 set_entry_point() 设置")
        return errors

    def check_state_types(self) -> List[str]:
        """检查状态类型定义"""
        warnings = []
        if len(self.state_types) == 0:
            warnings.append("未找到 TypedDict 状态类型定义,建议使用类型安全的状态")
        return warnings

    def check_conditional_edges(self) -> List[str]:
        """检查条件边的完整性"""
        warnings = []
        for from_node, paths in self.conditional_edges.items():
            if len(paths) < 2:
                warnings.append(
                    f"节点 '{from_node}' 的条件边只有 {len(paths)} 个路径,可能不完整"
                )
        return warnings

    def validate(self) -> Dict[str, Any]:
        """执行所有验证"""
        try:
            tree = self.parse_file()
            self.extract_graph_info(tree)

            # 执行各项检查
            self.errors.extend(self.check_entry_point())
            self.errors.extend(self.check_cycles())
            self.errors.extend(self.check_unreachable_nodes())
            self.warnings.extend(self.check_state_types())
            self.warnings.extend(self.check_conditional_edges())

            return {
                "valid": len(self.errors) == 0,
                "errors": self.errors,
                "warnings": self.warnings,
                "nodes": list(self.nodes),
                "edges": self.edges,
                "entry_point": self.entry_point,
                "state_types": self.state_types,
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"解析文件失败: {str(e)}"],
                "warnings": [],
                "nodes": [],
                "edges": [],
                "entry_point": None,
                "state_types": [],
            }


def validate_graph(file_path: str) -> Dict[str, Any]:
    """验证 LangGraph 图定义文件

    Args:
        file_path: Python 文件路径

    Returns:
        验证结果字典,包含:
        - valid: 是否有效
        - errors: 错误列表
        - warnings: 警告列表
        - nodes: 节点列表
        - edges: 边列表
        - entry_point: 入口点
        - state_types: 状态类型列表
    """
    validator = GraphValidator(file_path)
    return validator.validate()


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python validate_graph.py <graph_file.py>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"错误: 文件不存在: {file_path}")
        sys.exit(1)

    result = validate_graph(file_path)

    print(f"\n{'='*60}")
    print(f"验证结果: {'✓ 通过' if result['valid'] else '✗ 失败'}")
    print(f"{'='*60}\n")

    if result["errors"]:
        print("错误:")
        for error in result["errors"]:
            print(f"  ✗ {error}")
        print()

    if result["warnings"]:
        print("警告:")
        for warning in result["warnings"]:
            print(f"  ⚠ {warning}")
        print()

    print(f"节点数: {len(result['nodes'])}")
    print(f"边数: {len(result['edges'])}")
    print(f"入口点: {result['entry_point']}")
    print(f"状态类型: {', '.join(result['state_types']) if result['state_types'] else '无'}")

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()

