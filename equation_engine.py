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
    # --- v2 presets (prefix before ":" selects the mode in the GUI) ---
    ("Sliders: y = a*x^2 + b*x + c (drag a, b, c)", "sliders: y = a*x^2 + b*x + c"),
    ("Multi: y = x^2 and y = sin(x)", "multi: y = x^2 ; y = sin(x)"),
    ("3D surface: z = x^2 + y^2", "3d: z = x^2 + y^2"),
    ("3D surface: z = sin(x)*cos(y)", "3d: z = sin(x)*cos(y)"),
    ("System: x + y = 5, x - y = 1", "system: x + y = 5 ; x - y = 1"),
    ("Complex roots: x^2 + 1 = 0", "x^2 + 1 = 0"),
    ("Implicit circle: x^2 + y^2 = 25", "implicit: x^2 + y^2 = 25"),
    ("Implicit ellipse: x^2/9 + y^2/4 = 1", "implicit: x^2/9 + y^2/4 = 1"),
    ("Parametric circle: x = cos(t), y = sin(t)", "parametric: x = cos(t) ; y = sin(t)"),
    ("Parametric Lissajous: x = sin(3t), y = sin(2t)", "parametric: x = sin(3*t) ; y = sin(2*t)"),
    ("Polar rose: r = 2*sin(3*theta)", "polar: r = 2*sin(3*theta)"),
    # --- v2 breadth presets: basic -> advanced ladder ---
    ("Arithmetic: 1/2 + 1/3", "calc: 1/2 + 1/3"),
    ("Arithmetic: (2+3)*4 - 10/2", "calc: (2+3)*4 - 10/2"),
    ("Fractions: 3/4 * 2/5", "calc: 3/4 * 2/5"),
    ("Trigonometry: sin(pi/3)", "calc: sin(pi/3)"),
    ("Trigonometry: tan(pi/4)", "calc: tan(pi/4)"),
    ("Limit: sin(x)/x as x -> 0", "limit: sin(x)/x at 0"),
    ("Limit: (x^2-1)/(x-1) as x -> 1", "limit: (x^2-1)/(x-1) at 1"),
    ("ODE: dy/dx = y", "ode: dy/dx = y"),
    ("ODE: dy/dx = -2*y", "ode: dy/dx = -2*y"),
    ("Matrix: [[1,2],[3,4]] det/inverse/eigen", "matrix: [[1,2],[3,4]]"),
    ("Matrix: [[2,0],[0,3]] eigenvalues", "matrix: [[2,0],[0,3]]"),
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
            steps.append("Complex roots (from the quadratic formula):")
            for r in complex_roots(expr):
                steps.append(f"Root (complex): x = {r}")
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
    if deg == 3:
        a, b, c, d = [float(v) for v in coeffs]
        steps.append(f"This is cubic with a = {a:g}, b = {b:g}, c = {c:g}, d = {d:g}")
        steps.append("A cubic always has at least one real root; sympy solves it exactly:")
        for r in complex_roots(expr):
            if abs(r.imag) < 1e-9:
                steps.append(f"Root: x = {r.real:g}")
            else:
                steps.append(f"Root (complex): x = {r}")
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


# =====================================================================
# v2 — more powerful modes. All numbers come from sympy, as in v1.
# Preset text uses a prefix (e.g. "3d:", "system:") to select the mode;
# the GUI dispatches on it via render_input(). Nothing here invents
# results: every value is computed, and bad input raises ValueError.
# =====================================================================

A = sp.Symbol("a")
B = sp.Symbol("b")
C = sp.Symbol("c")
T = sp.Symbol("t")
THETA = sp.Symbol("theta")


def _parse_with(text, allowed, local):
    expr = parse_expr(
        _clean(text), local_dict=local, transformations=TRANSFORMATIONS
    )
    unknown = sorted(str(s) for s in expr.free_symbols - allowed)
    if unknown:
        raise ValueError(
            f"Unknown variable or name: {', '.join(unknown)}."
        )
    return expr


def parse_function_with_params(text):
    """Parse a one-variable function that may use parameters a, b, c.

    Returns a sympy expression in x (and a/b/c). Used by the sliders.
    """
    t = _clean(text.strip())
    m = re.match(r"^f\(x\)\s*=\s*(.+)$", t) or re.match(r"^y\s*=\s*(.+)$", t)
    body = m.group(1) if m else t
    if "=" in body:
        raise ValueError("Slider mode takes a function (y = ...), not an equation.")
    return _parse_with(body, {X, A, B, C},
                       {"x": X, "a": A, "b": B, "c": C, "e": sp.E, "pi": sp.pi})


def substitute_params(expr, params):
    """Replace a/b/c with numbers, e.g. {'a': 1, 'b': -5, 'c': 6}."""
    subs = {}
    for name, sym in (("a", A), ("b", B), ("c", C)):
        if name in params:
            subs[sym] = params[name]
    return sp.expand(expr.subs(subs))


def complex_roots(expr):
    """All roots of expr = 0 (real and complex), as complex floats, sorted."""
    out = []
    try:
        for r in sp.solve(expr, X):
            try:
                z = complex(r.evalf())
            except Exception:
                continue
            if not any(abs(z - o) < 1e-6 for o in out):
                out.append(z)
    except Exception:
        pass
    return sorted(out, key=lambda z: (z.real, z.imag))


def _parse_xy(text):
    """Parse one side of a two-variable expression in x and y."""
    return _parse_with(text, {X, Y},
                       {"x": X, "y": Y, "e": sp.E, "pi": sp.pi})


def _split_equation(text):
    """'lhs = rhs' -> lhs - rhs expression, or bare expression -> itself."""
    if "=" in text:
        lhs, rhs = text.split("=", 1)
        if not lhs.strip() or not rhs.strip():
            raise ValueError("An equation needs something on both sides of '='.")
        return lhs.strip(), rhs.strip()
    return text.strip(), "0"


def parse_two_var_function(text):
    """Parse 'z = f(x, y)' or a bare f(x, y) into an expression in x, y."""
    t = _clean(text.strip())
    m = re.match(r"^z\s*=\s*(.+)$", t)
    body = m.group(1) if m else t
    if "=" in body:
        raise ValueError("A 3D surface takes z = f(x, y), not an equation.")
    return _parse_xy(body)


def make_3d_plot(expr_xy, lo=-5.0, hi=5.0):
    """3D surface plot of z = expr_xy(x, y). Returns (fig, info)."""
    xs = np.linspace(lo, hi, 60)
    ys = np.linspace(lo, hi, 60)
    xx, yy = np.meshgrid(xs, ys)
    f = sp.lambdify((X, Y), expr_xy, modules=["numpy"])
    with np.errstate(all="ignore"):
        zz = np.asarray(f(xx, yy), dtype=float)
    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(xx, yy, zz, cmap="viridis", alpha=0.9)
    ax.set_title(f"z = {sp.simplify(expr_xy)}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    fig.tight_layout()
    sample = float(expr_xy.subs({X: 1, Y: 2}))
    info = {"expression": str(sp.simplify(expr_xy)),
            "sample_at_1_2": sample}
    return fig, info


def parse_system(text):
    """Parse 'eq1 ; eq2' into two expressions in x, y (each = 0 form)."""
    parts = [p.strip() for p in text.split(";")]
    if len(parts) != 2 or not all(parts):
        raise ValueError("A system needs exactly two equations separated by ';'.")
    exprs = []
    for part in parts:
        lhs, rhs = _split_equation(_clean(part))
        exprs.append(sp.expand(_parse_xy(lhs) - _parse_xy(rhs)))
    return exprs


def solve_system(exprs):
    """Solve a 2-equation system. Returns a list of (x, y) complex pairs."""
    sols = []
    try:
        raw = sp.solve(exprs, (X, Y), dict=True)
    except Exception:
        raw = []
    for sol in raw:
        try:
            sols.append((complex(sol[X].evalf()), complex(sol[Y].evalf())))
        except Exception:
            continue
    return sols


def system_steps(exprs):
    """Step-by-step solution for a 2-equation system, from sympy."""
    steps = [f"Equation 1: {sp.simplify(exprs[0])} = 0",
             f"Equation 2: {sp.simplify(exprs[1])} = 0",
             "Solving both equations together (sympy):"]
    sols = solve_system(exprs)
    if not sols:
        steps.append("No solution found for this system.")
    for sx, sy in sols:
        def fmt(z):
            return f"{z.real:g}" if abs(z.imag) < 1e-9 else str(z)
        steps.append(f"Solution: x = {fmt(sx)}, y = {fmt(sy)}")
    return steps


def make_system_plot(exprs, lo=-10.0, hi=10.0):
    """Contour plot of both equations' zero curves, solutions marked."""
    xs = np.linspace(lo, hi, 400)
    ys = np.linspace(lo, hi, 400)
    xx, yy = np.meshgrid(xs, ys)
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = ["blue", "orange"]
    for i, expr in enumerate(exprs):
        f = sp.lambdify((X, Y), expr, modules=["numpy"])
        with np.errstate(all="ignore"):
            zz = np.asarray(f(xx, yy), dtype=float)
        ax.contour(xx, yy, zz, levels=[0], colors=colors[i], linewidths=2)
        ax.plot([], [], color=colors[i],
                label=f"eq{i + 1}: {sp.simplify(expr)} = 0")
    sols = solve_system(exprs)
    for sx, sy in sols:
        if abs(sx.imag) < 1e-9 and abs(sy.imag) < 1e-9:
            rx, ry = sx.real, sy.real
            if lo <= rx <= hi and lo <= ry <= hi:
                ax.plot(rx, ry, "ro", markersize=9)
                ax.annotate(f"({rx:g}, {ry:g})", (rx, ry),
                            textcoords="offset points", xytext=(4, 8),
                            color="red")
    ax.set_title("System of equations — intersection = solution")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig, {"solutions": sols}


def make_implicit_plot(expr_xy, lo=-10.0, hi=10.0):
    """Plot the curve expr_xy(x, y) = 0 (circle, ellipse, ...)."""
    xs = np.linspace(lo, hi, 400)
    ys = np.linspace(lo, hi, 400)
    xx, yy = np.meshgrid(xs, ys)
    f = sp.lambdify((X, Y), expr_xy, modules=["numpy"])
    with np.errstate(all="ignore"):
        zz = np.asarray(f(xx, yy), dtype=float)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.contour(xx, yy, zz, levels=[0], colors="blue", linewidths=2)
    ax.set_title(f"{sp.simplify(expr_xy)} = 0")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    fig.tight_layout()
    return fig, {"expression": str(sp.simplify(expr_xy))}


def parse_parametric(text):
    """Parse 'x = f(t) ; y = g(t)' into (x(t), y(t)) expressions."""
    parts = [p.strip() for p in text.split(";")]
    if len(parts) != 2 or not all(parts):
        raise ValueError("A parametric curve needs 'x = ... ; y = ...'.")
    out = {}
    for part in parts:
        m = re.match(r"^([xy])\s*=\s*(.+)$", _clean(part))
        if not m:
            raise ValueError("A parametric curve needs 'x = ... ; y = ...'.")
        out[m.group(1)] = _parse_with(
            m.group(2), {T}, {"t": T, "e": sp.E, "pi": sp.pi})
    return out["x"], out["y"]


def make_parametric_plot(xt, yt, t_min=0.0, t_max=2 * float(sp.pi)):
    """Plot a parametric curve x(t), y(t)."""
    ts = np.linspace(t_min, t_max, 800)
    fx = sp.lambdify(T, xt, modules=["numpy"])
    fy = sp.lambdify(T, yt, modules=["numpy"])
    with np.errstate(all="ignore"):
        xs = np.asarray(fx(ts), dtype=float)
        ys = np.asarray(fy(ts), dtype=float)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(xs, ys, linewidth=2)
    ax.plot(xs[0], ys[0], "go", markersize=8)
    ax.annotate(f"start ({xs[0]:g}, {ys[0]:g})", (xs[0], ys[0]),
                textcoords="offset points", xytext=(4, 8), color="green")
    ax.set_title(f"x(t) = {sp.simplify(xt)},  y(t) = {sp.simplify(yt)}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return fig, {"start_point": (float(xs[0]), float(ys[0]))}


def parse_polar(text):
    """Parse 'r = f(theta)' into an expression in theta."""
    t = _clean(text.strip())
    m = re.match(r"^r\s*=\s*(.+)$", t)
    body = m.group(1) if m else t
    if "=" in body:
        raise ValueError("A polar plot takes r = f(theta).")
    return _parse_with(body, {THETA},
                       {"theta": THETA, "e": sp.E, "pi": sp.pi})


def make_polar_plot(r_expr):
    """Polar plot of r(theta)."""
    th = np.linspace(0, 2 * np.pi, 800)
    f = sp.lambdify(THETA, r_expr, modules=["numpy"])
    with np.errstate(all="ignore"):
        rr = np.asarray(f(th), dtype=float)
    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection="polar")
    ax.plot(th, rr, linewidth=2)
    ax.set_title(f"r = {sp.simplify(r_expr)}")
    fig.tight_layout()
    sample = float(r_expr.subs(THETA, sp.pi / 6))
    return fig, {"expression": str(sp.simplify(r_expr)),
                 "r_at_pi_over_6": sample}


def make_multi_plot(exprs, x_min=-10.0, x_max=10.0):
    """Plot several one-variable functions together, one color each."""
    xs = np.linspace(x_min, x_max, 800)
    fig, ax = plt.subplots(figsize=(7, 5))
    for expr in exprs:
        ax.plot(xs, evaluate(expr, xs), linewidth=2,
                label=f"y = {sp.simplify(expr)}")
    ax.set_title("Multiple functions")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlim(x_min, x_max)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig, {"functions": [str(sp.simplify(e)) for e in exprs]}


def parse_multi(text):
    """Parse 'f1 ; f2 ; ...' (each 'y = ...' or a bare expression)."""
    parts = [p.strip() for p in text.split(";")]
    if len(parts) < 2 or not all(parts):
        raise ValueError("Multi-plot needs at least two functions separated by ';'.")
    exprs = []
    for part in parts:
        kind, expr = parse_input(part)
        if kind != "function":
            raise ValueError("Multi-plot takes functions (y = ...), not equations.")
        exprs.append(expr)
    return exprs


def render_input(text, params=None):
    """Dispatch a full input line (including v2 prefixes) to a plot.

    Returns (fig, info, mode_label). Raises ValueError on bad input.
    """
    t = text.strip()
    low = t.lower()
    if low.startswith("sliders:"):
        expr = parse_function_with_params(t.split(":", 1)[1])
        expr = substitute_params(expr, params or {})
        fig, info = make_plot(expr, "function")
        return fig, info, "sliders"
    if low.startswith("multi:"):
        exprs = parse_multi(t.split(":", 1)[1])
        fig, info = make_multi_plot(exprs)
        return fig, info, "multi"
    if low.startswith("3d:"):
        expr = parse_two_var_function(t.split(":", 1)[1])
        fig, info = make_3d_plot(expr)
        return fig, info, "3d"
    if low.startswith("system:"):
        exprs = parse_system(t.split(":", 1)[1])
        fig, info = make_system_plot(exprs)
        return fig, info, "system"
    if low.startswith("implicit:"):
        lhs, rhs = _split_equation(_clean(t.split(":", 1)[1]))
        expr = sp.expand(_parse_xy(lhs) - _parse_xy(rhs))
        fig, info = make_implicit_plot(expr)
        return fig, info, "implicit"
    if low.startswith("parametric:"):
        xt, yt = parse_parametric(t.split(":", 1)[1])
        fig, info = make_parametric_plot(xt, yt)
        return fig, info, "parametric"
    if low.startswith("polar:"):
        expr = parse_polar(t.split(":", 1)[1])
        fig, info = make_polar_plot(expr)
        return fig, info, "polar"
    kind, expr = parse_input(t)
    fig, info = make_plot(expr, kind)
    return fig, info, "plot"


# =====================================================================
# v2 breadth — basic-to-advanced ladder. Same rule: every value is
# computed by sympy; anything sympy cannot do raises a plain error
# instead of an invented answer.
# =====================================================================

import ast as _ast

YFUNC = sp.Function("y")


def _text_fig(lines):
    """A figure that just shows computed text (for calc/limit/matrix)."""
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.axis("off")
    ax.text(0.05, 0.95, "\n".join(lines), transform=ax.transAxes,
            fontsize=12, verticalalignment="top", family="monospace")
    fig.tight_layout()
    return fig


def compute_arithmetic(text):
    """Exact arithmetic: fractions stay fractions, e.g. 1/2 + 1/3 = 5/6.

    Returns (exact_str, decimal_float). Raises ValueError on bad input
    or on division by zero (sympy zoo/nan).
    """
    t = _clean(text.strip())
    if not t:
        raise ValueError("Nothing to calculate.")
    expr = parse_expr(t, local_dict={"e": sp.E, "pi": sp.pi},
                      transformations=TRANSFORMATIONS)
    if expr.free_symbols:
        raise ValueError("Arithmetic takes numbers only, no variables "
                         "(use a plot mode for expressions in x).")
    val = sp.simplify(expr)
    if val in (sp.zoo, sp.nan) or val is sp.oo or val is -sp.oo:
        raise ValueError("That calculation is undefined (e.g. division by zero).")
    return str(val), float(val.evalf())


def compute_limit(text):
    """Limit of a one-variable expression: 'expr at point'.

    Point may be a number, 'oo' (infinity) or '-oo'. Returns the exact
    sympy limit value as a string (1, 2, oo, ...).
    """
    t = _clean(text.strip())
    if " at " not in t:
        raise ValueError("A limit needs the form: expression at point, "
                         "e.g. sin(x)/x at 0.")
    body, point = t.rsplit(" at ", 1)
    body = body.strip()
    point = point.strip()
    expr = _parse_expr(body)
    if point in ("oo", "inf", "infinity"):
        pt = sp.oo
    elif point in ("-oo", "-inf", "-infinity"):
        pt = -sp.oo
    else:
        try:
            pt = sp.sympify(point, rational=True)
        except Exception:
            raise ValueError(f"Could not read the limit point: {point!r}.")
    val = sp.limit(expr, X, pt)
    return str(val)


def _parse_matrix_literal(s):
    """Parse '[[1,2],[3,4]]' (ints, decimals, fractions like 1/2 allowed)."""
    s = s.strip().replace("^", "**")
    try:
        expr = parse_expr(s, transformations=TRANSFORMATIONS)
    except Exception:
        raise ValueError(f"Could not read matrix: {s!r}.")
    try:
        return sp.Matrix(expr)
    except Exception:
        raise ValueError(f"Could not read matrix: {s!r}.")


def compute_matrix(text):
    """Matrix properties, or a binary operation between two matrices.

    Single matrix -> determinant, trace, inverse (if it exists),
    eigenvalues. 'A * B' / 'A + B' / 'A - B' -> the result matrix.
    Returns a list of human-readable lines.
    """
    t = text.strip()
    m = re.match(r"^(\[\[.*?\]\])\s*([\+\-\*])\s*(\[\[.*?\]\])$", t, re.DOTALL)
    if m:
        ma, op, mb = _parse_matrix_literal(m.group(1)), m.group(2), \
            _parse_matrix_literal(m.group(3))
        if op == "+":
            res = ma + mb
        elif op == "-":
            res = ma - mb
        else:
            if ma.cols != mb.rows:
                raise ValueError(
                    f"Cannot multiply: left has {ma.cols} columns but right "
                    f"has {mb.rows} rows.")
            res = ma * mb
        return [f"Result of {ma.tolist()} {op} {mb.tolist()}:",
                str(res.tolist())]
    mat = _parse_matrix_literal(t)
    lines = [f"Matrix: {mat.tolist()}",
             f"Size: {mat.rows} x {mat.cols}",
             f"Determinant: {mat.det()}",
             f"Trace: {mat.trace()}"]
    if mat.rows == mat.cols:
        try:
            lines.append(f"Inverse: {mat.inv().tolist()}")
        except Exception:
            lines.append("Inverse: does not exist (matrix is singular).")
        eig = mat.eigenvals()
        eig_str = ", ".join(f"{k} (x{int(v)})" for k, v in eig.items())
        lines.append(f"Eigenvalues: {eig_str}")
    else:
        lines.append("Inverse/eigenvalues need a square matrix.")
    return lines


def parse_ode(text):
    """Parse 'dy/dx = <rhs in x and y>' into the rhs expression.

    y is treated as the unknown function y(x), so sympy can solve it.
    """
    t = _clean(text.strip())
    m = re.match(r"^dy/dx\s*=\s*(.+)$", t)
    if not m:
        raise ValueError("An ODE needs the form: dy/dx = <expression in x and y>.")
    rhs = parse_expr(m.group(1), local_dict={"x": X, "y": YFUNC(X),
                                             "e": sp.E, "pi": sp.pi},
                     transformations=TRANSFORMATIONS)
    if rhs.free_symbols - {X}:
        raise ValueError("An ODE's right-hand side may only use x and y.")
    return rhs


def solve_ode_general(rhs):
    """General solution of dy/dx = rhs, as a sympy Eq. Raises on failure."""
    eq = sp.Eq(sp.Derivative(YFUNC(X), X), rhs)
    try:
        sol = sp.dsolve(eq, YFUNC(X))
    except Exception as exc:
        raise ValueError(f"Could not solve this ODE: {exc}")
    if not isinstance(sol, sp.Equality):
        raise ValueError("Could not solve this ODE with sympy.")
    return sol


def make_ode_plot(rhs, x_min=-5.0, x_max=5.0):
    """Plot particular solution curves of dy/dx = rhs for C = -2..2.

    Returns (fig, info) with the general solution string and, for the
    C = 1 curve, its value at x = 0 (checked in tests for dy/dx = y).
    """
    sol = solve_ode_general(rhs)
    sol_rhs = sol.rhs
    consts = sorted((s for s in sol_rhs.free_symbols if s != X),
                    key=str)
    xs = np.linspace(x_min, x_max, 400)
    fig, ax = plt.subplots(figsize=(7, 5))
    cval_at_0 = None
    for cval in (-2.0, -1.0, 1.0, 2.0):
        subs = {c: cval for c in consts}
        f = sp.lambdify(X, sol_rhs.subs(subs), modules=["numpy"])
        with np.errstate(all="ignore"):
            ys = np.asarray(f(xs), dtype=float)
        ax.plot(xs, ys, linewidth=1.8, label=f"C = {cval:g}")
        if cval == 1.0:
            try:
                cval_at_0 = float(sol_rhs.subs(subs).subs(X, 0))
            except Exception:
                pass
    ax.set_title(f"dy/dx = {sp.simplify(rhs)}  —  solution curves")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlim(x_min, x_max)
    ax.legend(loc="best")
    fig.tight_layout()
    info = {"general_solution": str(sol),
            "value_at_0_for_C_1": cval_at_0}
    return fig, info


def compute_text(text):
    """Text answers for the compute modes. Returns a list of lines."""
    t = text.strip()
    low = t.lower()
    if low.startswith("calc:"):
        exact, dec = compute_arithmetic(t.split(":", 1)[1])
        return [f"Calculation: {t.split(':', 1)[1].strip()}",
                f"Exact answer: {exact}",
                f"Decimal: {dec:g}"]
    if low.startswith("limit:"):
        val = compute_limit(t.split(":", 1)[1])
        return [f"Limit: {t.split(':', 1)[1].strip()}",
                f"Answer: {val}"]
    if low.startswith("matrix:"):
        return compute_matrix(t.split(":", 1)[1])
    if low.startswith("ode:"):
        rhs = parse_ode(t.split(":", 1)[1])
        sol = solve_ode_general(rhs)
        return [f"ODE: dy/dx = {sp.simplify(rhs)}",
                f"General solution: {sol}"]
    raise ValueError("Compute handles calc:, limit:, matrix: and ode: inputs.")


# --- extend render_input dispatch for the breadth modes ---------------
_orig_render_input = render_input


def render_input(text, params=None):  # noqa: F811 - intentional override
    """Dispatch a full input line, including breadth modes, to a plot.

    calc:/limit:/matrix: return a figure showing the computed text;
    ode: returns the solution-curve plot. All other inputs behave as
    before (see the v2 render_input above).
    """
    t = text.strip()
    low = t.lower()
    if low.startswith("ode:"):
        rhs = parse_ode(t.split(":", 1)[1])
        fig, info = make_ode_plot(rhs)
        return fig, info, "ode"
    if low.startswith(("calc:", "limit:", "matrix:")):
        lines = compute_text(t)
        return _text_fig(lines), {"expression": " | ".join(lines)}, \
            low.split(":", 1)[0]
    return _orig_render_input(text, params=params)
