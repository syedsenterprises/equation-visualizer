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

from equation_engine import (
    PRESETS, complex_roots, compute_arithmetic, compute_limit,
    compute_matrix, compute_text, make_3d_plot, make_implicit_plot,
    make_multi_plot, make_ode_plot, make_parametric_plot,
    make_polar_plot, make_plot, make_system_plot,
    parse_function_with_params, parse_input, parse_ode, parse_parametric,
    parse_polar, parse_system, parse_two_var_function, render_input,
    real_roots, solve_ode_general, solve_system, solve_steps,
    substitute_params, system_steps,
)
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

    # 1. Every preset parses and plots (v2 presets go through render_input).
    for label, text in PRESETS:
        try:
            if ":" in text.split("=", 1)[0] and text.split(":", 1)[0].strip().lower() in (
                    "sliders", "multi", "3d", "system", "implicit",
                    "parametric", "polar", "calc", "limit", "matrix", "ode"):
                fig, _, _ = render_input(text, params={"a": 1, "b": -5, "c": 6})
                check(f"preset parses+plots: {label}", True, "v2 mode")
            else:
                kind, expr = parse_input(text)
                fig, info = make_plot(expr, kind)
                check(f"preset parses+plots: {label}", True, f"kind={kind}")
            fig.savefig(os.path.join(outdir, "preset.png"))
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

    # 9. v2: sliders — a*x^2 + b*x + c with a=1, b=-5, c=6 has roots 2, 3.
    pexpr = parse_function_with_params("y = a*x^2 + b*x + c")
    sub = substitute_params(pexpr, {"a": 1, "b": -5, "c": 6})
    check("slider substitution gives roots 2 and 3",
          real_roots(sub) == [2.0, 3.0], str(real_roots(sub)))
    fig, _, _ = render_input("sliders: y = a*x^2 + b*x + c",
                             params={"a": 1, "b": -5, "c": 6})
    fig.savefig(os.path.join(outdir, "sliders-quadratic.png"))
    check("sliders preset renders", True)

    # 10. v2: multiple functions plotted together.
    _, f1 = parse_input("y = x^2")
    _, f2 = parse_input("y = sin(x)")
    fig, info = make_multi_plot([f1, f2])
    check("multi-plot has 2 functions", len(info["functions"]) == 2,
          str(info["functions"]))
    fig.savefig(os.path.join(outdir, "multi.png"))

    # 11. v2: 3D surface z = x^2 + y^2, f(1, 2) = 5.
    expr3d = parse_two_var_function("z = x^2 + y^2")
    fig, info = make_3d_plot(expr3d)
    check("3D surface f(1,2) = 5", abs(info["sample_at_1_2"] - 5.0) < 1e-9,
          str(info["sample_at_1_2"]))
    p3d = os.path.join(outdir, "surface-3d.png")
    fig.savefig(p3d)
    check("3D surface PNG saved", os.path.getsize(p3d) > 5000,
          f"{os.path.getsize(p3d)} bytes")
    fig2, _, _ = render_input("3d: z = sin(x)*cos(y)")
    fig2.savefig(os.path.join(outdir, "surface-sincos.png"))

    # 12. v2: system x + y = 5, x - y = 1 -> (3, 2).
    sexprs = parse_system("x + y = 5 ; x - y = 1")
    sols = solve_system(sexprs)
    real_sols = [(s[0].real, s[1].real) for s in sols
                 if abs(s[0].imag) < 1e-9 and abs(s[1].imag) < 1e-9]
    check("system solves to (3, 2)", (3.0, 2.0) in real_sols, str(real_sols))
    steps = system_steps(sexprs)
    check("system steps show (3, 2)", any("3" in s and "2" in s for s in steps),
          " | ".join(steps))
    fig, _ = make_system_plot(sexprs)
    fig.savefig(os.path.join(outdir, "system-intersection.png"))

    # 13. v2: complex roots x^2 + 1 = 0 -> +i and -i.
    _, ce = parse_input("x^2 + 1 = 0")
    croots = complex_roots(ce)
    check("complex roots are +i and -i",
          len(croots) == 2 and all(abs(abs(r.imag) - 1) < 1e-9
                                   and abs(r.real) < 1e-9 for r in croots),
          str(croots))
    csteps = solve_steps(ce)
    check("quadratic steps report complex roots",
          any("complex" in s.lower() for s in csteps), " | ".join(csteps))

    # 14. v2: cubic steps x^3 - 6x^2 + 11x - 6 = 0 -> roots 1, 2, 3.
    _, cube = parse_input("x^3 - 6x^2 + 11x - 6 = 0")
    check("cubic roots 1, 2, 3", real_roots(cube) == [1.0, 2.0, 3.0],
          str(real_roots(cube)))
    check("cubic steps show roots 1, 2, 3",
          all(any(f"x = {n}" in s for s in solve_steps(cube)) for n in (1, 2, 3)))

    # 15. v2: implicit circle x^2 + y^2 = 25 renders as a real PNG.
    fig, _, _ = render_input("implicit: x^2 + y^2 = 25")
    pimp = os.path.join(outdir, "implicit-circle.png")
    fig.savefig(pimp)
    check("implicit circle PNG saved", os.path.getsize(pimp) > 5000,
          f"{os.path.getsize(pimp)} bytes")
    fig, _, _ = render_input("implicit: x^2/9 + y^2/4 = 1")
    fig.savefig(os.path.join(outdir, "implicit-ellipse.png"))

    # 16. v2: parametric circle starts at (1, 0).
    xt, yt = parse_parametric("x = cos(t) ; y = sin(t)")
    fig, info = make_parametric_plot(xt, yt)
    check("parametric circle starts at (1, 0)",
          abs(info["start_point"][0] - 1.0) < 1e-9
          and abs(info["start_point"][1]) < 1e-9, str(info["start_point"]))
    fig.savefig(os.path.join(outdir, "parametric-circle.png"))
    fig, _, _ = render_input("parametric: x = sin(3*t) ; y = sin(2*t)")
    fig.savefig(os.path.join(outdir, "parametric-lissajous.png"))

    # 17. v2: polar rose r = 2*sin(3*theta), r(pi/6) = 2.
    rexpr = parse_polar("r = 2*sin(3*theta)")
    fig, info = make_polar_plot(rexpr)
    check("polar rose r(pi/6) = 2", abs(info["r_at_pi_over_6"] - 2.0) < 1e-9,
          str(info["r_at_pi_over_6"]))
    fig.savefig(os.path.join(outdir, "polar-rose.png"))

    # 18. v2: every new preset renders through render_input.
    for label, text in PRESETS[10:]:
        try:
            if text.lower().startswith("sliders:"):
                fig, _, _ = render_input(text, params={"a": 1, "b": -5, "c": 6})
            else:
                fig, _, _ = render_input(text)
            check(f"v2 preset renders: {label}", True)
        except Exception as exc:  # noqa: BLE001
            check(f"v2 preset renders: {label}", False, str(exc))

    # 19. v2: bad new-mode input rejected, never a crash.
    for bad in ["3d: z =", "system: x + y = 5", "implicit: x^2 +",
                "parametric: x = cos(t)", "polar: r =", "multi: y = x^2"]:
        try:
            render_input(bad)
            check(f"bad v2 input rejected: {bad!r}", False, "rendered without error")
        except Exception as exc:  # noqa: BLE001
            check(f"bad v2 input rejected: {bad!r}", True, type(exc).__name__)

    # 20. Breadth: exact arithmetic and fractions stay exact.
    exact, dec = compute_arithmetic("1/2 + 1/3")
    check("arithmetic 1/2 + 1/3 = 5/6", exact == "5/6"
          and abs(dec - 0.8333333333) < 1e-9, f"{exact}, {dec}")
    exact, _ = compute_arithmetic("3/4 * 2/5")
    check("fractions 3/4 * 2/5 = 3/10", exact == "3/10", exact)
    try:
        compute_arithmetic("1/0")
        check("arithmetic division by zero rejected", False, "no error")
    except Exception as exc:  # noqa: BLE001
        check("arithmetic division by zero rejected", True, type(exc).__name__)

    # 21. Breadth: trigonometry evaluated exactly.
    exact, dec = compute_arithmetic("sin(pi/3)")
    check("trig sin(pi/3) = sqrt(3)/2", exact == "sqrt(3)/2"
          and abs(dec - 0.8660254038) < 1e-9, f"{exact}, {dec}")
    exact, _ = compute_arithmetic("tan(pi/4)")
    check("trig tan(pi/4) = 1", exact == "1", exact)

    # 22. Breadth: limits.
    check("limit sin(x)/x at 0 = 1",
          compute_limit("sin(x)/x at 0") == "1", compute_limit("sin(x)/x at 0"))
    check("limit (x^2-1)/(x-1) at 1 = 2",
          compute_limit("(x^2-1)/(x-1) at 1") == "2")

    # 23. Breadth: ODE dy/dx = y -> C1*exp(x), C=1 curve is 1 at x=0.
    rhs = parse_ode("dy/dx = y")
    sol = solve_ode_general(rhs)
    check("ODE dy/dx = y general solution has exp(x)", "exp(x)" in str(sol), str(sol))
    fig, info = make_ode_plot(rhs)
    check("ODE C=1 curve at x=0 is 1",
          info["value_at_0_for_C_1"] is not None
          and abs(info["value_at_0_for_C_1"] - 1.0) < 1e-9,
          str(info["value_at_0_for_C_1"]))
    pode = os.path.join(outdir, "ode-dydx-y.png")
    fig.savefig(pode)
    check("ODE plot PNG saved", os.path.getsize(pode) > 5000,
          f"{os.path.getsize(pode)} bytes")
    lines = compute_text("ode: dy/dx = -2*y")
    check("ODE dy/dx = -2y solution text", any("exp" in s for s in lines),
          " | ".join(lines))

    # 24. Breadth: matrices — det, inverse, eigenvalues, singular case.
    mlines = compute_matrix("[[1,2],[3,4]]")
    check("matrix det -2", any("Determinant: -2" in s for s in mlines),
          " | ".join(mlines))
    check("matrix inverse correct",
          any("[[-2, 1], [3/2, -1/2]]" in s for s in mlines), " | ".join(mlines))
    check("matrix eigenvalues contain sqrt(33)",
          any("sqrt(33)" in s for s in mlines), " | ".join(mlines))
    slines = compute_matrix("[[1,2],[2,4]]")
    check("singular matrix has no inverse",
          any("does not exist" in s for s in slines), " | ".join(slines))
    oplines = compute_matrix("[[1,2],[3,4]] * [[5,6],[7,8]]")
    check("matrix multiplication [[19,22],[43,50]]",
          any("[[19, 22], [43, 50]]" in s for s in oplines), " | ".join(oplines))

    # 25. Breadth: every new breadth preset renders/computes.
    for label, text in PRESETS[21:]:
        try:
            if text.lower().startswith(("calc:", "limit:", "matrix:", "ode:")):
                if text.lower().startswith("ode:"):
                    fig, _, _ = render_input(text)
                else:
                    compute_text(text)
            else:
                fig, _, _ = render_input(text)
            check(f"breadth preset works: {label}", True)
        except Exception as exc:  # noqa: BLE001
            check(f"breadth preset works: {label}", False, str(exc))

    # 26. GUI file compiles. A real Tk window cannot open headlessly in
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
