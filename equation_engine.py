"""Math engine for Equation Visualizer.

Pure sympy / matplotlib logic, no GUI code here, so it can be tested
headlessly. Every number shown to the user comes from sympy; nothing is
hardcoded or invented.

Input forms accepted (x is the variable):
    y = x^2          f(x) = sin(x)      x^2          (bare expression)
    2x + 3 = 7       x^2 - 5x + 6 = 0   (equations to solve)

"^" is treated as power, and implicit multiplication like "2x" works.
"""

import os
import re
import sys

import matplotlib

# Headless Linux (no display) gets the Agg backend so tests and plot
# exports work without a window. On Windows/macOS, or Linux with a
# display, the backend is left alone so the Tk GUI can use TkAgg.
if sys.platform not in ("win32", "darwin") and not os.environ.get("DISPLAY"):
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

X = sp.Symbol("x")
Y = sp.Symbol("y")

TRANSFORMATIONS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)

# Presets shown in the GUI: (label, input text)
PRESETS = [
    ("Linear: y = 2x + 3", "y = 2x + 3"),
    ("Quadratic: y = x^2 - 5x + 6", "y = x^2 - 5x + 6"),
    ("Cubic: y = x^3 - 3x", "y = x^3 - 3x"),
    ("Sine: y = sin(x)", "y = sin(x)"),
    ("Cosine: y = cos(x)", "y = cos(x)"),
    ("Exponential: y = e^x", "y = e^x"),
    ("Logarithm: y = ln(x)", "y = ln(x)"),
    ("Absolute value: y = |x|", "y = |x|"),
    ("Linear equation: 2x + 3 = 7", "2x + 3 = 7"),
    ("Quadratic equation: x^2 - 5x + 6 = 0", "x^2 - 5x + 6 = 0"),
]


def _clean(text):
    """Normalise user text before parsing."""
    t = text.strip().lower()
    t = t.replace("ln(", "log(")          # ln -> sympy log (natural log)
    t = t.replace("|x|", "Abs(x)")        # absolute value
    t = t.replace("e^x", "exp(x)")
    t = t.replace("e**x", "exp(x)")
    return t


def _parse_expr(text):
    """Parse one side of an equation into a sympy expression in x.

    Rejects anything that is not a number, x, or a known function:
    without this, stray words like "hello" would silently parse as
    unknown symbols instead of raising an error.
    """
    expr = parse_expr(
        _clean(text),
        local_dict={"x": X, "e": sp.E, "pi": sp.pi},
        transformations=TRANSFORMATIONS,
    )
    unknown = sorted(str(s) for s in expr.free_symbols - {X})
    if unknown:
        raise ValueError(
            f"Unknown variable or name: {', '.join(unknown)}. "
            "Use x as the variable, e.g. y = x^2."
        )
    return expr


def parse_input(text):
    """Parse user input.

    Returns (kind, expr) where kind is "function" or "equation" and expr
    is a sympy expression in x:
      - function: expr is f(x) itself (from y = f(x) or a bare expression)
      - equation: expr is lhs - rhs, so solving expr = 0 solves the input
    Raises ValueError with a plain-language message on bad input.
    """
    if not text or not text.strip():
        raise ValueError("Please type an equation first, e.g. y = x^2.")
    t = _clean(text.strip())
    # f(x) = ...  -> function
    m = re.match(r"^f\(x\)\s*=\s*(.+)$", t)
    if m:
        return "function", _parse_expr(m.group(1))
    # y = ... -> function
    m = re.match(r"^y\s*=\s*(.+)$", t)
    if m:
        return "function", _parse_expr(m.group(1))
    # lhs = rhs -> equation (anything else with "=")
    if "=" in t:
        lhs, rhs = t.split("=", 1)
        if not lhs.strip() or not rhs.strip():
            raise ValueError("An equation needs something on both sides of '='.")
        return "equation", sp.expand(_parse_expr(lhs) - _parse_expr(rhs))
    # bare expression -> function
    return "function", _parse_expr(t)


def real_roots(expr):
    """Real roots of expr = 0, as floats, sorted. Empty list if none."""
    roots = []
    try:
        for r in sp.solve(expr, X):
            if r.is_real:
                roots.append(float(r))
    except Exception:
        pass
    # Deduplicate near-identical roots (e.g. double roots).
    out = []
    for r in sorted(roots):
        if not out or abs(r - out[-1]) > 1e-6:
            out.append(r)
    return out


def solve_steps(expr):
    """Step-by-step solution for linear / quadratic equations.

    Returns a list of human-readable step strings built from real sympy
    values (coefficients, discriminant, roots). For anything else it
    falls back to sympy's solve result without inventing steps.
    """
    poly = sp.Poly(expr, X)
    if poly is None:
        return ["Could not form a polynomial from this equation."]
    deg = poly.degree()
    coeffs = poly.all_coeffs()
    steps = [f"Original equation, moved to one side: {sp.simplify(expr)} = 0"]
    if deg == 1:
        a, b = [float(c) for c in coeffs]
        lhs = f"{a:g}x - {-b:g}" if b < 0 else f"{a:g}x + {b:g}"
        move = f"Add {-b:g} to both sides" if b < 0 else f"Subtract {b:g} from both sides"
        steps.append(f"This is linear: {lhs} = 0")
        steps.append(f"{move}: {a:g}x = {-b:g}")
        steps.append(f"Divide by {a:g}: x = {-b / a:g}")
        return steps
    if deg == 2:
        a, b, c = [float(c) for c in coeffs]
        disc = b * b - 4 * a * c
        steps.append(f"This is quadratic with a = {a:g}, b = {b:g}, c = {c:g}")
        steps.append(f"Discriminant: b^2 - 4ac = {b:g}^2 - 4({a:g})({c:g}) = {disc:g}")
        if disc < 0:
            steps.append("Discriminant is negative, so there are no real roots.")
            return steps
        steps.append("Quadratic formula: x = (-b ± sqrt(discriminant)) / (2a)")
        steps.append(
            f"x = ({-b:g} ± sqrt({disc:g})) / (2 x {a:g})"
        )
        for r in real_roots(expr):
            steps.append(f"Root: x = {r:g}")
        factored = sp.factor(expr)
        if factored != expr:
            steps.append(f"Factored form: {factored} = 0")
        return steps
    roots = real_roots(expr)
    if roots:
        steps.append(f"Degree {deg} equation — sympy solves it as:")
        for r in roots:
            steps.append(f"Root: x = {r:g}")
    else:
        steps.append("No real roots found for this equation.")
    return steps


def evaluate(expr, x_values):
    """Evaluate expr at numpy x values, returning floats (nan off-domain)."""
    f = sp.lambdify(X, expr, modules=["numpy"])
    with np.errstate(all="ignore"):
        vals = np.asarray(f(np.asarray(x_values, dtype=float)), dtype=float)
    return vals


def make_plot(expr, kind, mode="plot", x_min=-10.0, x_max=10.0,
              tangent_x=1.0, int_a=-2.0, int_b=2.0):
    """Build a matplotlib figure for expr, plus an info dict.

    mode: "plot" (curve + roots), "derivative" (f, f', tangent at tangent_x),
          "integral" (shaded area between int_a and int_b).
    """
    xs = np.linspace(x_min, x_max, 800)
    ys = evaluate(expr, xs)
    # Keep the y-axis sane when the function blows up off-domain.
    finite = ys[np.isfinite(ys)]
    y_lo, y_hi = (-10.0, 10.0)
    if finite.size:
        y_lo = min(-10.0, float(np.min(finite)))
        y_hi = max(10.0, float(np.max(finite)))

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(xs, ys, label=f"y = {sp.simplify(expr)}", linewidth=2)
    ax.set_title(f"y = {sp.simplify(expr)}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_lo, y_hi)

    info = {"expression": str(sp.simplify(expr))}
    roots = real_roots(expr)
    if kind == "equation":
        info["roots"] = roots
        for r in roots:
            if x_min <= r <= x_max:
                ax.plot(r, 0, "ro", markersize=8)
                ax.annotate(f"x = {r:g}", (r, 0), textcoords="offset points",
                            xytext=(4, 8), color="red")
    elif roots:
        info["roots"] = roots
        for r in roots:
            if x_min <= r <= x_max:
                ax.plot(r, 0, "ro", markersize=8)
                ax.annotate(f"x = {r:g}", (r, 0), textcoords="offset points",
                            xytext=(4, 8), color="red")
    else:
        info["roots"] = []

    if mode == "derivative":
        deriv = sp.diff(expr, X)
        ax.plot(xs, evaluate(deriv, xs), "--",
                label=f"f'(x) = {sp.simplify(deriv)}", linewidth=1.6)
        f0 = float(expr.subs(X, tangent_x))
        d0 = float(deriv.subs(X, tangent_x))
        tangent = f0 + d0 * (xs - tangent_x)
        ax.plot(xs, tangent, ":", label=f"tangent at x = {tangent_x:g}",
                linewidth=1.6)
        ax.plot(tangent_x, f0, "go", markersize=8)
        ax.annotate(f"({tangent_x:g}, {f0:g})", (tangent_x, f0),
                    textcoords="offset points", xytext=(4, 8), color="green")
        info["derivative"] = str(sp.simplify(deriv))
        info["tangent_point"] = (tangent_x, f0)
        info["tangent_slope"] = d0
    elif mode == "integral":
        lo, hi = (int_a, int_b) if int_a <= int_b else (int_b, int_a)
        mask = (xs >= lo) & (xs <= hi)
        ax.fill_between(xs[mask], ys[mask], 0, alpha=0.3,
                        label=f"area from {lo:g} to {hi:g}")
        area = float(sp.integrate(expr, (X, lo, hi)))
        info["integral_bounds"] = (lo, hi)
        info["integral_value"] = area

    ax.legend(loc="best")
    fig.tight_layout()
    return fig, info
