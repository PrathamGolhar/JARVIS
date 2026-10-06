import ast
import math
import operator
from typing import Any

# Allowed operators and functions for safe mathematical evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}


def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.Name):
        if node.id in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id]
        raise ValueError(f"Unknown variable: {node.id}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return SAFE_OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _eval_node(node.operand)
        return SAFE_OPERATORS[op_type](operand)

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in SAFE_FUNCTIONS:
                args = [_eval_node(arg) for arg in node.args]
                return SAFE_FUNCTIONS[func_name](*args)
        raise ValueError("Unsupported function call")

    raise ValueError(f"Unsupported syntax expression: {type(node).__name__}")


def evaluate_expression(expression: str) -> dict[str, Any]:
    """
    Safely evaluate a mathematical expression without eval() or arbitrary code execution.
    """
    cleaned = expression.strip().replace("^", "**")
    if not cleaned:
        return {"ok": False, "error": "Expression cannot be empty."}

    try:
        parsed = ast.parse(cleaned, mode="eval")
        result = _eval_node(parsed.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return {
            "ok": True,
            "expression": expression,
            "result": result,
            "formatted": f"{result:,}" if isinstance(result, (int, float)) and abs(result) >= 10000 else str(result),
        }
    except Exception as exc:
        return {"ok": False, "expression": expression, "error": str(exc)}
