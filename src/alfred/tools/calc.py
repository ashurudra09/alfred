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
# Sizes count in 1024s, like disk_usage. A size is bytes^1: '230 MB + 2 GB' is a size, '2 GB / 230 MB' a plain ratio.
UNITS = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}
SPELLINGS = {"b": "B", "byte": "B", "bytes": "B", "kb": "KB", "mb": "MB", "gb": "GB", "tb": "TB"}
SAME_DIM = (ast.Add, ast.Sub, ast.Mod, ast.FloorDiv)  # both sides need the same dimension; the result keeps it
KEEP_DIM = {"round", "abs", "min", "max", "floor", "ceil"}  # functions that work on sizes


NUM = r"\d+(?:\.\d+)?"


def _normalise(expr: str) -> str:
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**").replace("−", "-").replace("·", "*")
    expr = re.sub(r"[₹$€£¥]|\b(?:rs|inr|usd|eur)\.?(?=\s*\d)", "", expr, flags=re.I)  # currency
    expr = re.sub(r"(?<=\d),(?=(?:\d{2,3},)*\d{3}(?!\d))", "", expr)  # 34,999 and 1,00,000 -> plain numbers
    expr = re.sub(rf"({NUM})\s*%\s*of\s*", r"(\1/100)*", expr, flags=re.I)  # 18% of 34999
    expr = re.sub(rf"({NUM})\s*%(?=\s*(?:$|[)+\-*/]))", r"(\1/100)", expr)  # 34999 * 18%   (10 % 3 stays modulo)
    expr = re.sub(rf"(?<=[\d)])\s*[xX]\s*(?=[\d(])", "*", expr)  # 3 x 4
    unit = r"\b(bytes?|[kmgt]?b)\b"
    expr = re.sub(rf"\)\s*(?={unit})", ")*", expr, flags=re.I)  # (43.6 + 7.8) GB
    expr = re.sub(rf"({NUM})\s*{unit[2:]}", lambda m: f"({m[1]}*_{SPELLINGS[m[2].lower()]})", expr, flags=re.I)  # 230 MB
    return re.sub(unit, lambda m: f"_{SPELLINGS[m[1].lower()]}", expr, flags=re.I)  # a bare unit: '5 GB / MB'


def fmt_size(n: float) -> str:
    """Bytes in the largest unit that keeps the number >= 1, to 2 decimals: '56.72 GB'."""
    unit = next((u for u in ("TB", "GB", "MB", "KB") if abs(n) >= UNITS[u]), "B")
    v = f"{n / UNITS[unit]:.2f}".rstrip("0").rstrip(".")
    return f"{v} {unit}" + (f" ({n:,.0f} bytes)" if unit != "B" else "")


def calculate(expression):
    """The `calculate` tool: the exact result as text, e.g. '6299.82', or a size: '56.72 GB (60,903,290,880 bytes)'."""
    from mcp.server.fastmcp.exceptions import ToolError
    try:
        v, dim = _evaluate(expression)
    except ValueError as e:
        raise ToolError(str(e)) from e
    if dim == 1:
        return fmt_size(v)
    if dim:
        raise ToolError(f"The result is in bytes^{dim}, not a size or a number: check where sizes are multiplied.")
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        v = int(v)
    return f"{v:.10g}" if isinstance(v, float) else str(v)


def evaluate(expression: str) -> int | float:
    """Raises ValueError for anything that isn't plain arithmetic. Sizes come back in bytes."""
    return _evaluate(expression)[0]


def _evaluate(expression: str) -> tuple[int | float, int]:
    """(value, dimension): 0 = a plain number, 1 = a size in bytes."""
    try:
        tree = ast.parse(_normalise(expression).strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"not an arithmetic expression: {expression!r}") from e

    def ev(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value, 0
        if isinstance(node, ast.Name) and node.id in CONSTS:
            return CONSTS[node.id], 0
        if isinstance(node, ast.Name) and node.id.startswith("_") and node.id[1:] in UNITS:
            return UNITS[node.id[1:]], 1
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            v, d = ev(node.operand)
            return OPS[type(node.op)](v), d
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            (left, ld), (right, rd) = ev(node.left), ev(node.right)
            if isinstance(node.op, SAME_DIM) and ld != rd:
                raise ValueError("can't mix a size and a plain number with + - % //: give both a unit (e.g. '5 GB + 3 MB')")
            if isinstance(node.op, ast.Pow) and (ld or rd):
                raise ValueError("sizes can't be raised to a power")
            if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
                raise ValueError("exponent too large")
            dim = ld + rd if isinstance(node.op, ast.Mult) else ld - rd if isinstance(node.op, ast.Div) else ld
            return OPS[type(node.op)](left, right), dim
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCS
                and not node.keywords):
            args = [ev(a) for a in node.args]
            dims = {d for _, d in args}
            if dims - {0} and (node.func.id not in KEEP_DIM or len(dims) > 1 and node.func.id in ("min", "max")):
                raise ValueError(f"{node.func.id}() doesn't work on sizes here")
            out = FUNCS[node.func.id](*(v for v, _ in args))
            return out, args[0][1] if node.func.id in KEEP_DIM and args else 0
        raise ValueError(f"not allowed in a calculation: {ast.dump(node)[:60]}")

    try:
        return ev(tree.body)
    except (ArithmeticError, TypeError) as e:
        raise ValueError(str(e)) from e
