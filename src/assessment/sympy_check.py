"""
sympy_check.py  --  The third check for numerical questions.

The pipeline for a NUMERIC question has three independent checks:

  1. Groq writes the question and its answer.
  2. Gemini solves it independently and agrees.
  3. SymPy COMPUTES the answer from the underlying maths.   <-- this file

A numeric answer key is trusted only when all three agree. SymPy is the
strongest check because it does not guess -- it calculates.

How the maths is supplied: for a numeric question, the generator also returns
the expression to evaluate (and any values to substitute), e.g.

    { "expr": "diff(3*x**2, x)", "subs": {"x": 2} }   ->  12

--- Run it ---
    python sympy_check.py
"""

import ast
import math
import re

import sympy

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9]{0,31}")
_FUNCTIONS = {"sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
              "exp": sympy.exp, "log": sympy.log, "sqrt": sympy.sqrt,
              "abs": sympy.Abs, "Abs": sympy.Abs}
_CONSTANTS = {"pi": sympy.pi, "E": sympy.E}


def _math_node(node):
    """Construct SymPy objects from a restricted AST; never evaluate Python code."""
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        if not math.isfinite(node.value) or abs(node.value) > 1e100:
            raise ValueError("numeric literal is too large or not finite")
        return sympy.Integer(node.value) if isinstance(node.value, int) else sympy.Float(node.value)
    if isinstance(node, ast.Name) and _NAME.fullmatch(node.id):
        return _CONSTANTS.get(node.id, sympy.Symbol(node.id))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _math_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left, right = _math_node(node.left), _math_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            if not right.is_number or right.is_real is not True or abs(right) > 100:
                raise ValueError("power must be a real numeric value between -100 and 100")
            if left.is_Rational and right.is_Integer:
                # Integer bases are rationals too. Negative powers swap the
                # numerator and denominator; both must be bounded before SymPy
                # constructs them, including powers of earlier reciprocals.
                bits = max(abs(int(left.p)).bit_length(), int(left.q).bit_length())
                if bits * abs(int(right)) > 4096:
                    raise ValueError("rational power exceeds calculation size limit")
            return left ** right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        name = node.func.id
        if name == "symbols" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and _NAME.fullmatch(arg.value):
                return sympy.Symbol(arg.value)
        if name in _FUNCTIONS and len(node.args) == 1:
            return _FUNCTIONS[name](_math_node(node.args[0]))
        if name == "diff" and len(node.args) in (2, 3):
            expr, variable = (_math_node(n) for n in node.args[:2])
            order = _math_node(node.args[2]) if len(node.args) == 3 else sympy.Integer(1)
            if not isinstance(variable, sympy.Symbol) or not isinstance(order, sympy.Integer) or not 0 <= order <= 5:
                raise ValueError("diff requires a symbol and an integer order between 0 and 5")
            return sympy.diff(expr, variable, int(order))
    raise ValueError("unsupported math syntax; use explicit arithmetic and approved functions")


def evaluate(expression, subs=None):
    """Evaluate bounded arithmetic/differentiation, using explicit '*' multiplication.

    Model output is untrusted. Python attributes, indexing, imports, arbitrary
    function calls and string substitutions are never evaluated.
    """
    text = str(expression).strip()
    if not text or len(text) > 512:
        raise ValueError("math expression must contain 1 to 512 characters")
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, RecursionError) as error:
        raise ValueError("invalid math expression") from error
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise ValueError("math expression is too complex")
    try:
        expr = _math_node(tree.body)
    except (TypeError, OverflowError, RecursionError) as error:
        raise ValueError("invalid math expression") from error
    if subs:
        values = {}
        for name, value in subs.items():
            if not isinstance(name, str) or not _NAME.fullmatch(name):
                raise ValueError("invalid substitution name")
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError("substitutions must be finite numbers") from error
            if not math.isfinite(number):
                raise ValueError("substitutions must be finite numbers")
            values[sympy.Symbol(name)] = sympy.Float(number)
        expr = expr.subs(values)
    try:
        result = float(sympy.N(expr))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("expression must evaluate to a finite real number") from error
    if not math.isfinite(result):
        raise ValueError("expression must evaluate to a finite real number")
    return result


def check_numeric(expression, subs, claimed_answer, tol=1e-6):
    """Return (ok, computed_value, claimed_value). ok=True means they match."""
    computed = evaluate(expression, subs)
    try:
        claimed = float(str(claimed_answer).strip())
    except (TypeError, ValueError):
        return False, computed, None
    return math.isfinite(claimed) and abs(computed - claimed) <= tol, computed, claimed


# demo: the numeric questions from the mock bank, paired with their maths
DEMO = [
    ("q2", "If f(x) = 3x^2, what is f'(2)?",
     {"expr": "diff(3*x**2, x)", "subs": {"x": 2}}, "12"),
    ("q4", "If y = (2x + 1)^3, what is dy/dx at x = 0?",
     {"expr": "diff((2*x+1)**3, x)", "subs": {"x": 0}}, "6"),
    ("q8", "With learning rate 0.1 and gradient 5, what is the update step size?",
     {"expr": "0.1*5", "subs": {}}, "0.5"),
]


def main():
    print("=" * 60)
    print("SYMPY CHECK  --  computing numeric answers independently")
    print("=" * 60)
    for qid, stem, spec, claimed in DEMO:
        ok, computed, _ = check_numeric(spec["expr"], spec.get("subs"), claimed)
        print(f"[{'MATCH' if ok else 'MISMATCH'}] {qid}: {stem}")
        print(f"          expression : {spec['expr']}   subs={spec.get('subs')}")
        print(f"          SymPy says : {computed}    answer key: {claimed}")
    print("-" * 60)
    print("Catching a wrong answer key on purpose:")
    ok, computed, _ = check_numeric("diff(3*x**2, x)", {"x": 2}, "15")
    print(f"  diff(3*x**2, x) at x=2 -> SymPy={computed}, key=15 -> "
          f"{'MATCH' if ok else 'MISMATCH (rejected)'}")
    print("-" * 60)
    print("Done. A numeric question is kept only if Groq, Gemini AND SymPy agree.")


if __name__ == "__main__":
    main()
