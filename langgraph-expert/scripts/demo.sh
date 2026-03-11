#!/bin/bash
# 演示 validate_graph.py 工具的功能

echo "=========================================="
echo "validate_graph.py 工具演示"
echo "=========================================="
echo ""

echo "1. 验证简单的有效图:"
echo "---"
python3 validate_graph.py example_simple_graph.py
echo ""

echo "=========================================="
echo ""
echo "2. 检测循环依赖 (ReAct 模式):"
echo "---"
python3 validate_graph.py example_graph.py
echo ""

echo "=========================================="
echo "演示完成!"
