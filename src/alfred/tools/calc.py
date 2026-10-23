"""Safe arithmetic for the `calculate` tool (and the scorer's `number` rule). Walks the AST; never calls eval()."""

import ast
import math
import operator
import re

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
       ast.USub: operator.neg, ast.UAdd: operator.pos}
FUNCS = {"sqrt": math.sqrt, "round": round, "abs": abs, "min": min, "max": max, "floor": math.floor,
         "ceil": math.ceil, "log": math.log, "log10": math.log10, "exp": math.exp}
CONSTS = {"pi": math.pi, "e": math.e}


NUM = r"\d+(?:\.\d+)?"


def _normalise(expr: str) -> str:
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**").replace("−", "-").replace("·", "*")
    expr = re.sub(r"[₹$€£¥]|\b(?:rs|inr|usd|eur)\.?(?=\s*\d)", "", expr, flags=re.I)  # currency
    expr = re.sub(r"(?<=\d),(?=(?:\d{2,3},)*\d{3}(?!\d))", "", expr)  # 34,999 and 1,00,000 -> plain numbers
    expr = re.sub(rf"({NUM})\s*%\s*of\s*", r"(\1/100)*", expr, flags=re.I)  # 18% of 34999
    expr = re.sub(rf"({NUM})\s*%(?=\s*(?:$|[)+\-*/]))", r"(\1/100)", expr)  # 34999 * 18%   (10 % 3 stays modulo)
    return re.sub(rf"(?<=[\d)])\s*[xX]\s*(?=[\d(])", "*", expr)  # 3 x 4


def calculate(expression):
    """The `calculate` tool: the exact result as text, e.g. '6299.82'."""
    from mcp.server.fastmcp.exceptions import ToolError
    try:
        v = evaluate(expression)
    except ValueError as e:
        raise ToolError(str(e)) from e
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        v = int(v)
    return f"{v:.10g}" if isinstance(v, float) else str(v)


def evaluate(expression: str) -> int | float:
    """Raises ValueError for anything that isn't plain arithmetic."""
    try:
        tree = ast.parse(_normalise(expression).strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"not an arithmetic expression: {expression!r}") from e

    def ev(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.Name) and node.id in CONSTS:
            return CONSTS[node.id]
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
                raise ValueError("exponent too large")
            return OPS[type(node.op)](left, right)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCS
                and not node.keywords):
            return FUNCS[node.func.id](*map(ev, node.args))
        raise ValueError(f"not allowed in a calculation: {ast.dump(node)[:60]}")

    try:
        return ev(tree.body)
    except (ArithmeticError, TypeError) as e:
        raise ValueError(str(e)) from e
