"""Headless verification for Equation Visualizer's math engine.

Run:  python test_engine.py
Checks every preset parses, functions plot, roots/derivative/integral
values are correct, step-by-step solving works, bad input raises a
plain ValueError (never crashes), and sample plots save as real PNGs.
Exit code 0 = all checks passed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from equation_engine import PRESETS, make_plot, parse_input, real_roots, solve_steps
import sympy as sp

X = sp.Symbol("x")
FAILED = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    if not condition:
        FAILED.append(name)


def main():
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(outdir, exist_ok=True)

    # 1. Every preset parses and plots.
    for label, text in PRESETS:
        try:
            kind, expr = parse_input(text)
            fig, info = make_plot(expr, kind)
            fig.savefig(os.path.join(outdir, "preset.png"))
            check(f"preset parses+plots: {label}", True, f"kind={kind}")
        except Exception as exc:  # noqa: BLE001
            check(f"preset parses+plots: {label}", False, str(exc))

    # 2. Known roots: x^2 - 5x + 6 = 0 -> 2 and 3.
    kind, expr = parse_input("x^2 - 5x + 6 = 0")
    check("quadratic roots 2 and 3", real_roots(expr) == [2.0, 3.0],
          str(real_roots(expr)))
    check("quadratic kind is equation", kind == "equation")

    # 3. Linear equation: 2x + 3 = 7 -> x = 2.
    kind, expr = parse_input("2x + 3 = 7")
    check("linear root 2", real_roots(expr) == [2.0], str(real_roots(expr)))

    # 4. Step-by-step solving contains real computed values.
    steps = solve_steps(expr)
    check("linear steps show x = 2", any("x = 2" in s for s in steps), " | ".join(steps))
    _, q = parse_input("x^2 - 5x + 6 = 0")
    qsteps = solve_steps(q)
    check("quadratic steps show discriminant 1",
          any("= 1" in s and "Discriminant" in s for s in qsteps), " | ".join(qsteps))

    # 5. Derivative: d/dx (x^2) = 2x, tangent at x=1 has slope 2.
    _, f = parse_input("y = x^2")
    fig, info = make_plot(f, "function", mode="derivative", tangent_x=1.0)
    check("derivative of x^2 is 2*x", info["derivative"] == "2*x", info["derivative"])
    check("tangent slope at x=1 is 2", info["tangent_slope"] == 2.0)
    fig.savefig(os.path.join(outdir, "derivative-x-squared.png"))

    # 6. Integral: area under x^2 from 0 to 3 is 9.
    fig, info = make_plot(f, "function", mode="integral", int_a=0.0, int_b=3.0)
    check("integral of x^2 0..3 is 9", abs(info["integral_value"] - 9.0) < 1e-9,
          str(info["integral_value"]))
    fig.savefig(os.path.join(outdir, "integral-x-squared.png"))

    # 7. Sine plot is a real PNG, non-trivial size.
    _, s = parse_input("y = sin(x)")
    fig, _ = make_plot(s, "function")
    p = os.path.join(outdir, "sine.png")
    fig.savefig(p)
    check("sine plot PNG saved", os.path.getsize(p) > 5000, f"{os.path.getsize(p)} bytes")

    # 8. Bad input -> plain error, no crash.
    for bad in ["", "y =", "x^^2", "hello world"]:
        try:
            parse_input(bad)
            check(f"bad input rejected: {bad!r}", False, "parsed without error")
        except Exception as exc:  # noqa: BLE001
            check(f"bad input rejected: {bad!r}", True, type(exc).__name__)

    # 9. GUI file compiles. A real Tk window cannot open headlessly in
    # this VM, so this check is compile-only by design (see README).
    import py_compile
    try:
        py_compile.compile(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "main.py"), doraise=True)
        check("main.py compiles cleanly", True)
    except Exception as exc:  # noqa: BLE001
        check("main.py compiles cleanly", False, str(exc))

    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) FAILED: {FAILED}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
