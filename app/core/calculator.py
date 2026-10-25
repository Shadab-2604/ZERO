"""
Deterministic, secure local calculation engine for Zero AI.
Evaluates mathematical expressions, percentages, and numerical problems
without using unsafe eval().
"""

import ast
import math
import operator
import re
from typing import Any, NamedTuple


class CalculationResult(NamedTuple):
    is_calculation: bool
    expression: str
    result: float | int | None
    formatted_result: str
    explanation: str


# Safe AST operators mapping
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

# Safe math functions mapping
SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": math.pow,
    "min": min,
    "max": max,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


class SafeEvaluator(ast.NodeVisitor):
    """Safely evaluates an AST expression containing arithmetic and allowed math functions."""

    def visit(self, node: ast.AST) -> Any:
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported syntax: {node.__class__.__name__}")

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    def visit_Name(self, node: ast.Name) -> Any:
        name_lower = node.id.lower()
        if name_lower in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[name_lower]
        if name_lower in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[name_lower]
        raise ValueError(f"Undefined variable or identifier: {node.id}")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        # Prevent massive exponents causing denial of service
        if op_type == ast.Pow:
            if right > 1000 or (isinstance(left, (int, float)) and abs(left) > 1e6 and right > 10):
                raise ValueError("Exponent too large for safe calculation")

        op_func = SAFE_OPERATORS[op_type]
        return op_func(left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = self.visit(node.operand)
        return SAFE_OPERATORS[op_type](operand)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct math function calls are permitted")
        func_name = node.func.id.lower()
        if func_name not in SAFE_FUNCTIONS:
            raise ValueError(f"Function '{func_name}' is not in allowed math functions")
        args = [self.visit(arg) for arg in node.args]
        return SAFE_FUNCTIONS[func_name](*args)


class LocalCalculator:
    """Engine that identifies and deterministically solves arithmetic and percentage queries."""

    # Patterns for natural language math
    PERCENT_OF_PATTERN = re.compile(
        r"(?i)\b(?:what\s+is\s+|calculate\s+|compute\s+|how\s+much\s+is\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:of)\s*(\d+(?:\.\d+)?)"
    )
    PERCENT_INCREASE_PATTERN = re.compile(
        r"(?i)\b(?:increase|add)\s+(\d+(?:\.\d+)?)\s+by\s+(\d+(?:\.\d+)?)\s*%"
    )
    PERCENT_DECREASE_PATTERN = re.compile(
        r"(?i)\b(?:decrease|discount|reduce)\s+(\d+(?:\.\d+)?)\s+by\s+(\d+(?:\.\d+)?)\s*%"
    )
    DIRECT_CALC_PREFIX = re.compile(
        r"(?i)^(?:zero\s+)?(?:calculate|compute|solve|eval|evaluate|what\s+is|what\'s)\s*[:\s]\s*(.+)$"
    )

    @classmethod
    def evaluate_expression(cls, expr_str: str) -> float | int:
        """Parse and safely evaluate mathematical string expression."""
        # Clean expression
        clean_expr = expr_str.strip()
        # Replace common math tokens
        clean_expr = clean_expr.replace("^", "**").replace("×", "*").replace("÷", "/")
        clean_expr = clean_expr.replace("x", "*").replace("X", "*")
        
        tree = ast.parse(clean_expr, mode="eval")
        evaluator = SafeEvaluator()
        result = evaluator.visit(tree)
        if isinstance(result, float) and result.is_integer():
            return int(result)
        if isinstance(result, float):
            return round(result, 6)
        return result

    @classmethod
    def try_calculate(cls, text: str) -> CalculationResult:
        """
        Check if query is an arithmetic or percentage calculation and compute answer.
        Returns CalculationResult with is_calculation=True if solved.
        """
        stripped = text.strip()

        # 1. Check percentage of: "18% of 450" or "what is 18% of 450"
        pct_match = cls.PERCENT_OF_PATTERN.search(stripped)
        if pct_match:
            pct_val = float(pct_match.group(1))
            total_val = float(pct_match.group(2))
            res = (pct_val / 100.0) * total_val
            if res.is_integer():
                res = int(res)
            else:
                res = round(res, 4)
            formatted = str(res)
            expr = f"{total_val} * {pct_val}%"
            explanation = (
                f"Calculation: {pct_val}% of {total_val} = ({pct_val} / 100) × {total_val} = **{formatted}**."
            )
            return CalculationResult(
                is_calculation=True,
                expression=expr,
                result=res,
                formatted_result=formatted,
                explanation=explanation,
            )

        # 2. Check percentage increase: "increase 100 by 15%"
        inc_match = cls.PERCENT_INCREASE_PATTERN.search(stripped)
        if inc_match:
            base_val = float(inc_match.group(1))
            pct_val = float(inc_match.group(2))
            res = base_val * (1.0 + pct_val / 100.0)
            res = int(res) if res.is_integer() else round(res, 4)
            formatted = str(res)
            return CalculationResult(
                is_calculation=True,
                expression=f"{base_val} + {pct_val}%",
                result=res,
                formatted_result=formatted,
                explanation=f"{base_val} increased by {pct_val}% = **{formatted}**.",
            )

        # 3. Check percentage decrease: "discount 200 by 20%"
        dec_match = cls.PERCENT_DECREASE_PATTERN.search(stripped)
        if dec_match:
            base_val = float(dec_match.group(1))
            pct_val = float(dec_match.group(2))
            res = base_val * (1.0 - pct_val / 100.0)
            res = int(res) if res.is_integer() else round(res, 4)
            formatted = str(res)
            return CalculationResult(
                is_calculation=True,
                expression=f"{base_val} - {pct_val}%",
                result=res,
                formatted_result=formatted,
                explanation=f"{base_val} reduced by {pct_val}% = **{formatted}**.",
            )

        # 4. Check explicit calculation queries: "calculate: 128 * 45", "what is 500 / 4"
        candidate_expr = None
        prefix_match = cls.DIRECT_CALC_PREFIX.match(stripped)
        if prefix_match:
            candidate_expr = prefix_match.group(1).rstrip("?").strip()
        elif re.match(r"^[\d\s\+\-\*\/\(\)\.\,\^\%\=\×\÷\b(sqrt|pi|abs|round|sin|cos|log)\b]+$", stripped):
            candidate_expr = stripped.rstrip("=").strip()

        if candidate_expr:
            try:
                # Check that expression contains at least one operator or function
                if any(op in candidate_expr for op in ["+", "-", "*", "/", "%", "^", "sqrt", "abs", "round", "×", "÷"]):
                    result = cls.evaluate_expression(candidate_expr)
                    formatted = str(result)
                    explanation = f"Result: `{candidate_expr}` = **{formatted}**"
                    return CalculationResult(
                        is_calculation=True,
                        expression=candidate_expr,
                        result=result,
                        formatted_result=formatted,
                        explanation=explanation,
                    )
            except Exception:
                pass

        return CalculationResult(
            is_calculation=False,
            expression="",
            result=None,
            formatted_result="",
            explanation="",
        )
