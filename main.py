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

from equation_engine import PRESETS, make_plot, parse_input, solve_steps

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
        self.preset_list = tk.Listbox(left, width=42, height=14, font=("Segoe UI", 10))
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
        self.plot("plot")

    def _read_float(self, var, name, default):
        try:
            return float(var.get())
        except ValueError:
            raise ValueError(f"'{name}' must be a number (got '{var.get()}').")

    def plot(self, mode):
        """Parse, plot, and report. Errors are shown, never raised."""
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
