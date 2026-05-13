"""Plot configuration panel: X/Y axis selection, FFT mode, title, export settings."""
import tkinter as tk
from tkinter import ttk, filedialog


class PlotConfigPanel(ttk.LabelFrame):
    """Panel for configuring plot axes and export settings."""

    def __init__(self, parent, on_preview=None, on_export=None):
        super().__init__(parent, text="Plot Configuration", padding=4)
        self._columns: list[dict] = []          # [{name, unit, col_type}]
        self._y_vars: list[tk.BooleanVar] = []   # checkbox vars for Y columns
        self._on_preview = on_preview
        self._on_export = on_export
        self._setup_ui()

    def _setup_ui(self):
        # ── Detection Info ──
        info_frame = ttk.LabelFrame(self, text="Detection", padding=2)
        info_frame.pack(fill=tk.X, pady=2)
        self._detect_label = ttk.Label(info_frame, text="Add files to auto-detect…", foreground="gray")
        self._detect_label.pack(anchor=tk.W, padx=2)

        # ── FFT Toggle ──
        self._fft_var = tk.BooleanVar(value=False)
        self._fft_check = ttk.Checkbutton(info_frame, text="FFT Mode (harmonic bar chart)",
                                           variable=self._fft_var)
        self._fft_check.pack(anchor=tk.W, padx=2)

        # ── Axes ──
        axes_frame = ttk.LabelFrame(self, text="Axes", padding=4)
        axes_frame.pack(fill=tk.X, pady=2)

        row0 = ttk.Frame(axes_frame)
        row0.pack(fill=tk.X, pady=1)
        ttk.Label(row0, text="X Axis:", width=8).pack(side=tk.LEFT)
        self._x_combo = ttk.Combobox(row0, state="readonly")
        self._x_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        row1 = ttk.Frame(axes_frame)
        row1.pack(fill=tk.X, pady=1)
        ttk.Label(row1, text="Y Axis:", width=8).pack(side=tk.LEFT, anchor=tk.N)
        self._y_frame = ttk.Frame(axes_frame)
        self._y_frame.pack(fill=tk.X, padx=(80, 0), pady=2)

        # ── Title ──
        title_frame = ttk.LabelFrame(self, text="Title", padding=4)
        title_frame.pack(fill=tk.X, pady=2)
        ttk.Label(title_frame, text="Template:").pack(side=tk.LEFT)
        self._title_var = tk.StringVar(value="{filename}")
        self._title_entry = ttk.Entry(title_frame, textvariable=self._title_var)
        self._title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # ── Export ──
        export_frame = ttk.LabelFrame(self, text="Export", padding=4)
        export_frame.pack(fill=tk.X, pady=2)

        self._png_var = tk.BooleanVar(value=True)
        self._svg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_frame, text="PNG (300 DPI)", variable=self._png_var).pack(anchor=tk.W)
        ttk.Checkbutton(export_frame, text="SVG", variable=self._svg_var).pack(anchor=tk.W)

        dir_row = ttk.Frame(export_frame)
        dir_row.pack(fill=tk.X, pady=2)
        ttk.Label(dir_row, text="Output:").pack(side=tk.LEFT)
        self._dir_var = tk.StringVar()
        ttk.Entry(dir_row, textvariable=self._dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(dir_row, text="…", width=2, command=self._on_browse).pack(side=tk.RIGHT)

        # ── Buttons ──
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_frame, text="Preview",
                   command=lambda: self._on_preview and self._on_preview()).pack(side=tk.LEFT, padx=2)
        self._export_btn = ttk.Button(btn_frame, text="Export All",
                                       command=lambda: self._on_export and self._on_export())
        self._export_btn.pack(side=tk.RIGHT, padx=2)

    def set_columns(self, columns: list[dict], fft_detected: bool = False,
                    param_names: list[str] | None = None,
                    suggested_x: str | None = None,
                    suggested_y: list[str] | None = None):
        """Populate selectors from [{name, unit, col_type}, …].

        col_type: 'param' | 'data' | 'fft_x' | 'fft_y' | 'unknown'
        """
        self._columns = columns

        # Update detection label
        parts = []
        if fft_detected:
            parts.append("FFT detected")
        if param_names:
            parts.append(f"Conditions: {', '.join(param_names)}")
        if parts:
            self._detect_label.config(text=" | ".join(parts), foreground="black")
        else:
            self._detect_label.config(text="Standard XY data", foreground="black")
        self._fft_var.set(fft_detected)

        # Populate X combo and Y checkboxes
        col_labels = []
        for c in columns:
            suffix = ""
            ct = c.get("col_type", "")
            if ct == "param":
                suffix = " [COND]"
            elif ct == "fft_x":
                suffix = " [FFT-X]"
            elif ct == "fft_y":
                suffix = " [FFT-Y]"
            display = f"{c['name']} [{c['unit']}]" if c.get('unit') else c['name']
            col_labels.append(display + suffix)

        self._x_combo["values"] = col_labels
        if col_labels:
            # Pre-select suggested X
            x_selected = False
            if suggested_x:
                for i, c in enumerate(columns):
                    if c["name"] == suggested_x:
                        self._x_combo.current(i)
                        x_selected = True
                        break
            if not x_selected:
                for i, c in enumerate(columns):
                    if c["name"].lower() in ("time", "fft time", "fft distance", "distance"):
                        self._x_combo.current(i)
                        x_selected = True
                        break
            if not x_selected:
                self._x_combo.current(min(1, len(col_labels) - 1))

        # Rebuild Y checkboxes
        for w in self._y_frame.winfo_children():
            w.destroy()
        self._y_vars.clear()
        for i, c in enumerate(columns):
            if suggested_y and c["name"] in suggested_y:
                checked = True
            elif c.get("col_type") in ("fft_y",):
                checked = True
            elif c.get("col_type") == "data" and c["name"] != suggested_x:
                checked = True
            else:
                checked = False
            var = tk.BooleanVar(value=checked)
            self._y_vars.append(var)
            cb = ttk.Checkbutton(self._y_frame, text=col_labels[i], variable=var)
            cb.pack(anchor=tk.W)

    def _on_browse(self):
        d = filedialog.askdirectory(title="Select Output Folder")
        if d:
            self._dir_var.set(d)

    @property
    def x_col(self) -> str:
        idx = self._x_combo.current()
        if 0 <= idx < len(self._columns):
            return self._columns[idx]["name"]
        return self._x_combo.get() or ""

    @property
    def y_cols(self) -> list[str]:
        cols = []
        for i, var in enumerate(self._y_vars):
            if i < len(self._columns) and var.get():
                cols.append(self._columns[i]["name"])
        return cols if cols else [self.x_col]

    @property
    def title_template(self) -> str:
        return self._title_var.get() or "{filename}"

    @property
    def output_dir(self) -> str:
        return self._dir_var.get()

    @property
    def export_formats(self) -> tuple[str, ...]:
        fmts = []
        if self._png_var.get():
            fmts.append("png")
        if self._svg_var.get():
            fmts.append("svg")
        return tuple(fmts) if fmts else ("png",)

    @property
    def fft_mode(self) -> bool:
        return self._fft_var.get()
