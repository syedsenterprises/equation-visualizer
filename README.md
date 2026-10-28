# Equation Visualizer

A desktop app that shows you what a math equation *does*. Type any
equation or function and it plots it, marks its roots, draws its
derivative and tangent line, shades the area under the curve, and shows
real step-by-step solving for linear and quadratic equations. Works
fully offline on a PC — no account, no internet needed after install.

![Quadratic plot with roots marked](screenshots/quadratic.png)

## What it does

- **2D plots** of any function with labeled axes, grid, and the equation
  on the plot — e.g. `y = x^2`, `y = sin(x)`, `y = e^x`, `y = |x|`
- **Roots marked** on the plot: where the curve crosses y = 0, plus the
  solution values of equations like `2x + 3 = 7` and `x^2 - 5x + 6 = 0`
- **Derivative view**: plots f(x) and f'(x) together, plus the tangent
  line at any x you choose
- **Integral view**: shades the area under the curve between two bounds
  and shows the computed area value
- **Step-by-step solving** for linear and quadratic equations, computed
  from real coefficients (not canned text): discriminant, quadratic
  formula, factored form where it applies
- **10 one-click presets**: linear, quadratic, cubic, sine, cosine,
  exponential, logarithm, absolute value, and two equations — so a
  first-time user sees it work instantly
- **Plain-language errors**: invalid input shows a message, never a crash
- **Save plot as PNG** from the app

## How to run

### Windows

```bat
pip install -r requirements.txt
python main.py
```

### Linux / macOS

```bash
pip install -r requirements.txt
python3 main.py
```

Tkinter ships with most Python installs. On Debian/Ubuntu, if it is
missing: `sudo apt install python3-tk`.

## Try it

| Type this | You will see |
|---|---|
| `y = x^2 - 5x + 6` | Parabola with roots x = 2 and x = 3 marked |
| `y = sin(x)` | Sine wave |
| `2x + 3 = 7` | Line for 2x − 4, root x = 2 |
| `x^2 - 5x + 6 = 0` | Same parabola, roots marked, plus Solve steps |
| `y = e^x` | Exponential curve |

Then click **Derivative** (tangent at your chosen x) or **Integral**
(shaded area between your chosen bounds).

## How it works

- `main.py` — Tkinter GUI, the app entry point
- `equation_engine.py` — all math: parsing (sympy), roots, derivative,
  integral, step-by-step solving, and matplotlib plots
- `test_engine.py` — headless verification (see below)

Input accepts `^` for powers, implicit multiplication (`2x`), `ln(x)`,
and `|x|`. Only `x` is the variable; anything else is reported as an
unknown name instead of silently mis-parsing.

## Tests (verified)

```bash
python3 test_engine.py
```

All checks pass: all 10 presets parse and plot, quadratic roots 2 and 3,
linear root 2, derivative of x² is 2x with tangent slope 2 at x = 1,
integral of x² from 0 to 3 is 9, a real sine PNG is saved (27,137
bytes), and bad input (`""`, `y =`, `x^^2`, `hello world`) is rejected
with a plain error. Sample plots are in `screenshots/`.

## Known limitations (honest gaps)

- **The GUI window itself was not opened in this Linux VM** (no display
  available headlessly). The math/plotting engine is fully verified via
  `test_engine.py` and `main.py` compiles cleanly, but the Tk window
  has not been clicked through on a real desktop yet — please run
  `python main.py` on a PC with a display to confirm the window.
- Single variable only (`x`); no 3D plots, no systems of equations, no
  complex roots shown (a negative discriminant is reported as "no real
  roots").
- The default x-range is −10 to 10 (adjustable in the app); very large
  values can make the y-axis hard to read.

## License

MIT — see [LICENSE](LICENSE).
