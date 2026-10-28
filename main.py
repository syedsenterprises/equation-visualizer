"""Equation Visualizer — desktop math visualization app.

Type any equation (e.g. y = x^2, y = sin(x), 2x + 3 = 7) and see it
plotted, with roots marked, plus derivative/tangent and integral views
and real step-by-step solving for linear and quadratic equations.

Run:  python main.py
Requires: sympy, matplotlib (see requirements.txt). Tkinter ships with
most Python installs; on Debian/Ubuntu, `sudo apt install python3-tk`
if it is missing.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib

try:
    matplotlib.use("TkAgg")
except Exception:
    pass  # headless import (e.g. tests): keep whatever backend is set
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from equation_engine import (
    PRESETS, compute_text, make_plot, parse_input, parse_system,
    render_input, solve_steps, system_steps,
)

BODY_FONT = ("Segoe UI", 11)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Equation Visualizer")
        self.geometry("1100x700")
        self.current_fig = None

        # --- top input row ---
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Equation:", font=BODY_FONT).pack(side="left")
        self.entry = ttk.Entry(top, font=BODY_FONT, width=45)
        self.entry.pack(side="left", padx=8, fill="x", expand=True)
        self.entry.insert(0, "y = x^2 - 5x + 6")
        ttk.Button(top, text="Plot", command=lambda: self.plot("plot")).pack(side="left", padx=2)
        ttk.Button(top, text="Derivative", command=lambda: self.plot("derivative")).pack(side="left", padx=2)
        ttk.Button(top, text="Integral", command=lambda: self.plot("integral")).pack(side="left", padx=2)
        ttk.Button(top, text="Solve steps", command=self.show_steps).pack(side="left", padx=2)
        ttk.Button(top, text="Sliders", command=self.slider_plot).pack(side="left", padx=2)
        ttk.Button(top, text="Compute", command=self.compute).pack(side="left", padx=2)

        # --- v2 mode buttons: prepend the mode prefix, then plot ---
        modes = ttk.Frame(self, padding=(10, 0))
        modes.pack(fill="x")
        ttk.Label(modes, text="More:").pack(side="left")
        for label, prefix in [("Multi", "multi:"), ("3D", "3d:"),
                              ("System", "system:"), ("Implicit", "implicit:"),
                              ("Parametric", "parametric:"), ("Polar", "polar:")]:
            ttk.Button(modes, text=label,
                       command=lambda p=prefix: self.mode_plot(p)).pack(side="left", padx=2)

        # --- v2 sliders for a, b, c (live update while slider mode is on) ---
        self.slider_mode = False
        sliders = ttk.Frame(self, padding=(10, 0))
        sliders.pack(fill="x")
        ttk.Label(sliders, text="Parameters (sliders mode):").pack(side="left")
        self.slider_vars = {}
        for name, default in [("a", 1.0), ("b", -5.0), ("c", 6.0)]:
            ttk.Label(sliders, text=f"{name}:").pack(side="left", padx=(8, 0))
            var = tk.DoubleVar(value=default)
            self.slider_vars[name] = var
            tk.Scale(sliders, variable=var, from_=-10, to=10, resolution=0.1,
                     orient="horizontal", length=150,
                     command=lambda _v: self._on_slider()).pack(side="left")

        # --- options row ---
        opts = ttk.Frame(self, padding=(10, 0))
        opts.pack(fill="x")
        self.x_min = self._num_field(opts, "x min:", "-10")
        self.x_max = self._num_field(opts, "x max:", "10")
        self.tangent_x = self._num_field(opts, "tangent at x:", "1")
        self.int_a = self._num_field(opts, "integral from:", "-2")
        self.int_b = self._num_field(opts, "integral to:", "2")
        ttk.Button(opts, text="Save plot as PNG", command=self.save_png).pack(side="left", padx=8)

        # --- main split: presets + plot | results ---
        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(left, text="Try an example:", font=BODY_FONT).pack(anchor="w")
        self.preset_list = tk.Listbox(left, width=42, height=28, font=("Segoe UI", 10))
        for label, _ in PRESETS:
            self.preset_list.insert("end", label)
        self.preset_list.pack(fill="y", expand=True)
        self.preset_list.bind("<<ListboxSelect>>", self._preset_chosen)

        self.plot_frame = ttk.Frame(main)
        self.plot_frame.pack(side="left", fill="both", expand=True)
        self.canvas = None

        right = ttk.Frame(main, width=300)
        right.pack(side="right", fill="y", padx=(10, 0))
        ttk.Label(right, text="Results:", font=BODY_FONT).pack(anchor="w")
        self.results = tk.Text(right, width=42, height=30, wrap="word", font=("Segoe UI", 10))
        self.results.pack(fill="y", expand=True)

        self.status = ttk.Label(self, text="Ready — pick an example or type an equation.",
                                relief="sunken", anchor="w", padding=5)
        self.status.pack(fill="x", side="bottom")

        self.plot("plot")  # show the default equation immediately

    def _num_field(self, parent, label, default):
        ttk.Label(parent, text=label).pack(side="left")
        var = tk.StringVar(value=default)
        ttk.Entry(parent, textvariable=var, width=6).pack(side="left", padx=(2, 10))
        return var

    def _preset_chosen(self, _event):
        sel = self.preset_list.curselection()
        if not sel:
            return
        self.entry.delete(0, "end")
        self.entry.insert(0, PRESETS[sel[0]][1])
        self.slider_mode = PRESETS[sel[0]][1].lower().startswith("sliders:")
        self.plot("plot")

    def compute(self):
        """Text answer for calc:/limit:/matrix:/ode: inputs."""
        try:
            lines = compute_text(self.entry.get())
        except Exception as exc:  # noqa: BLE001 - user-facing error path
            messagebox.showerror("Could not compute that", str(exc))
            self.status.config(text=f"Error: {exc}")
            return
        self.results.delete("1.0", "end")
        self.results.insert("end", "\n".join(lines))
        self.status.config(text="Answer shown.")

    def _params(self):
        return {k: float(v.get()) for k, v in self.slider_vars.items()}

    def _on_slider(self):
        if self.slider_mode:
            self.plot("plot")

    def slider_plot(self):
        """Enter slider mode: entry must be a function using a, b, c."""
        text = self.entry.get()
        if not text.lower().startswith("sliders:"):
            self.entry.delete(0, "end")
            self.entry.insert(0, f"sliders: {text}")
        self.slider_mode = True
        self.plot("plot")

    def mode_plot(self, prefix):
        text = self.entry.get()
        known = ("multi:", "3d:", "system:", "implicit:", "parametric:",
                 "polar:", "sliders:")
        if not text.lower().startswith(known):
            self.entry.delete(0, "end")
            self.entry.insert(0, f"{prefix} {text}")
        self.slider_mode = False
        self.plot("plot")

    def _read_float(self, var, name, default):
        try:
            return float(var.get())
        except ValueError:
            raise ValueError(f"'{name}' must be a number (got '{var.get()}').")

    def plot(self, mode):
        """Parse, plot, and report. Errors are shown, never raised."""
        # v2 modes (preset prefixes, or slider mode) go through render_input.
        text = self.entry.get()
        v2_prefixes = ("multi:", "3d:", "system:", "implicit:",
                       "parametric:", "polar:", "sliders:", "ode:",
                       "calc:", "limit:", "matrix:")
        if text.strip().lower().startswith(v2_prefixes) or self.slider_mode:
            try:
                if self.slider_mode and not text.strip().lower().startswith("sliders:"):
                    text = f"sliders: {text}"
                fig, info, v2mode = render_input(text, params=self._params())
            except Exception as exc:  # noqa: BLE001 - user-facing error path
                messagebox.showerror("Could not plot that", str(exc))
                self.status.config(text=f"Error: {exc}")
                return
            if self.canvas is not None:
                self.canvas.get_tk_widget().destroy()
            plt.close("all")
            self.current_fig = fig
            self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self._show_info(info, v2mode)
            self.status.config(text=f"Plotted ({v2mode}): {info.get('expression', '')}")
            return
        try:
            kind, expr = parse_input(self.entry.get())
            x_min = self._read_float(self.x_min, "x min", -10)
            x_max = self._read_float(self.x_max, "x max", 10)
            if x_min >= x_max:
                raise ValueError("x min must be smaller than x max.")
            fig, info = make_plot(
                expr, kind, mode=mode, x_min=x_min, x_max=x_max,
                tangent_x=self._read_float(self.tangent_x, "tangent at x", 1),
                int_a=self._read_float(self.int_a, "integral from", -2),
                int_b=self._read_float(self.int_b, "integral to", 2),
            )
        except Exception as exc:  # noqa: BLE001 - user-facing error path
            messagebox.showerror("Could not plot that", str(exc))
            self.status.config(text=f"Error: {exc}")
            return
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        plt.close("all")
        self.current_fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._show_info(info, mode)
        self.status.config(text=f"Plotted: {info['expression']}")

    def _show_info(self, info, mode):
        if mode in ("multi", "3d", "system", "implicit", "parametric",
                    "polar", "sliders", "ode", "calc", "limit", "matrix"):
            lines = [f"Mode: {mode}"]
            if info.get("general_solution"):
                lines.append(f"General solution: {info['general_solution']}")
                if info.get("value_at_0_for_C_1") is not None:
                    lines.append(f"C = 1 curve at x = 0: "
                                 f"{info['value_at_0_for_C_1']:g}")
            if info.get("expression"):
                lines.append(f"Expression: {info['expression']}")
            if info.get("functions"):
                lines.append("Functions plotted:")
                lines.extend(f"  y = {f}" for f in info["functions"])
            if info.get("solutions") is not None:
                if info["solutions"]:
                    lines.append("Solutions (intersections):")
                    for sx, sy in info["solutions"]:
                        fmt = lambda z: f"{z.real:g}" if abs(z.imag) < 1e-9 else str(z)
                        lines.append(f"  x = {fmt(sx)}, y = {fmt(sy)}")
                else:
                    lines.append("No solution found.")
            if info.get("sample_at_1_2") is not None:
                lines.append(f"Value at (x=1, y=2): {info['sample_at_1_2']:g}")
            if info.get("start_point"):
                px, py = info["start_point"]
                lines.append(f"Curve starts at ({px:g}, {py:g})")
            if info.get("r_at_pi_over_6") is not None:
                lines.append(f"r at theta = pi/6: {info['r_at_pi_over_6']:g}")
            roots = info.get("roots", [])
            if roots:
                lines.append("Roots:")
                lines.extend(f"  x = {r:g}" for r in roots)
            self.results.delete("1.0", "end")
            self.results.insert("end", "\n".join(lines))
            return
        lines = [f"Equation: y = {info['expression']}"]
        roots = info.get("roots", [])
        if roots:
            lines.append("Roots (where the curve crosses y = 0):")
            lines.extend(f"  x = {r:g}" for r in roots)
        else:
            lines.append("No real roots in this view.")
        if mode == "derivative":
            lines.append(f"Derivative: f'(x) = {info['derivative']}")
            px, py = info["tangent_point"]
            lines.append(f"Tangent at x = {px:g}: point ({px:g}, {py:g}), "
                         f"slope = {info['tangent_slope']:g}")
        if mode == "integral":
            lo, hi = info["integral_bounds"]
            lines.append(f"Area under the curve from {lo:g} to {hi:g}: "
                         f"{info['integral_value']:g}")
        self.results.delete("1.0", "end")
        self.results.insert("end", "\n".join(lines))

    def show_steps(self):
        text = self.entry.get()
        if text.strip().lower().startswith("system:"):
            try:
                steps = system_steps(parse_system(text.split(":", 1)[1]))
            except Exception as exc:  # noqa: BLE001 - user-facing error path
                messagebox.showerror("Could not solve that", str(exc))
                return
            self.results.delete("1.0", "end")
            self.results.insert("end", "\n".join(steps))
            self.status.config(text="Step-by-step solution shown.")
            return
        try:
            kind, expr = parse_input(self.entry.get())
            if kind != "equation":
                # A function y = f(x) can still be solved as f(x) = 0.
                steps = ["Solving y = 0 for this function:"] + solve_steps(expr)
            else:
                steps = solve_steps(expr)
        except Exception as exc:  # noqa: BLE001 - user-facing error path
            messagebox.showerror("Could not solve that", str(exc))
            return
        self.results.delete("1.0", "end")
        self.results.insert("end", "\n".join(steps))
        self.status.config(text="Step-by-step solution shown.")

    def save_png(self):
        if self.current_fig is None:
            messagebox.showinfo("Nothing to save", "Plot something first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG image", "*.png")])
        if path:
            self.current_fig.savefig(path, dpi=150)
            self.status.config(text=f"Plot saved to {path}")


if __name__ == "__main__":
    App().mainloop()
