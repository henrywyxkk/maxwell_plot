"""Matplotlib FigureCanvasTkAgg embedded in a tkinter Frame for plot preview."""
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class PlotCanvas(ttk.Frame):
    """Widget that displays a matplotlib Figure with navigation toolbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._figure: Figure | None = None
        self._canvas: FigureCanvasTkAgg | None = None
        self._toolbar: NavigationToolbar2Tk | None = None
        self._setup_ui()

    def _setup_ui(self):
        # Placeholder figure
        self._figure = Figure(figsize=(6, 4), dpi=100, facecolor="white")
        self._figure.subplots_adjust(left=0.13, right=0.95, top=0.93, bottom=0.15)
        ax = self._figure.add_subplot(111)
        ax.text(0.5, 0.5, "Select CSV files to preview",
                ha="center", va="center", fontsize=12, color="#888",
                transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])

        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._toolbar = NavigationToolbar2Tk(self._canvas, self)

        self._toolbar.pack(side=tk.TOP, fill=tk.X)
        self._canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def set_figure(self, fig: Figure):
        """Replace the current figure with a new one."""
        self._figure = fig
        self._canvas.figure = fig
        self._canvas.draw()

    @property
    def figure(self) -> Figure | None:
        return self._figure

    @property
    def canvas(self) -> FigureCanvasTkAgg:
        return self._canvas
