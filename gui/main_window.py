"""Main application window — assembles all panels and coordinates actions."""
import os
import tkinter as tk
from tkinter import ttk, messagebox

from gui.file_list_panel import FileListPanel
from gui.plot_config_panel import PlotConfigPanel
from gui.plot_canvas import PlotCanvas
from core.csv_parser import parse_maxwell_csv, ColumnType
from core.plot_engine import PlotEngine
from core.batch_processor import BatchProcessor


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self._engine = PlotEngine()
        self._batch: BatchProcessor | None = None
        self._setup_ui()

    def _setup_ui(self):
        self.title("Ansys Maxwell CSV Plotter")
        self.geometry("1200x800")
        self.minsize(950, 600)

        # Theme
        style = ttk.Style()
        style.theme_use("clam")

        # Menu bar
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add CSV Files...", command=self._on_add_files)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._on_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

        # Main layout: PanedWindow
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left panel
        left = ttk.Frame(paned)
        self._file_list = FileListPanel(left, on_files_changed=self._on_files_changed)
        self._file_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self._config = PlotConfigPanel(
            left,
            on_preview=self._on_preview,
            on_export=self._on_export,
        )
        self._config.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        paned.add(left, minsize=360)

        # Right panel: plot canvas
        self._canvas = PlotCanvas(paned)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        paned.add(self._canvas, minsize=500)

        # Status bar
        self._status_var = tk.StringVar(value="Ready - Add CSV files to begin")
        status = ttk.Label(self, textvariable=self._status_var, relief=tk.SUNKEN,
                           anchor=tk.W, padding=(4, 2))
        status.pack(side=tk.BOTTOM, fill=tk.X)

    # ── Slots ──────────────────────────────────────────────

    def _on_files_changed(self):
        n = self._file_list.count
        self._status_var.set(f"{n} file(s) loaded - Configure axes and preview")
        if self._file_list.filepaths:
            self._update_column_selectors()
            self._on_preview()

    def _update_column_selectors(self):
        if not self._file_list.filepaths:
            return
        try:
            parsed = parse_maxwell_csv(self._file_list.filepaths[0])
            cols = []
            for c in parsed.columns:
                cols.append({
                    "name": c.name,
                    "unit": c.unit,
                    "col_type": c.col_type.name.lower(),
                })
            param_names = [c.name for c in parsed.param_cols]
            self._config.set_columns(
                cols,
                fft_detected=parsed.is_fft_data,
                param_names=param_names,
                suggested_x=parsed.suggested_x_col,
                suggested_y=parsed.suggested_y_cols,
            )
        except Exception as e:
            self._status_var.set(f"Error reading columns: {e}")

    def _on_preview(self):
        if not self._file_list.filepaths:
            return
        try:
            parsed = parse_maxwell_csv(self._file_list.filepaths[0])
        except Exception as e:
            messagebox.showwarning("Parse Error", str(e))
            return

        x_col = self._config.x_col
        y_cols = self._config.y_cols

        try:
            if self._config.fft_mode or parsed.is_fft_data:
                y_col = y_cols[0] if y_cols else parsed.suggested_y_cols[0]
                fig = self._engine.create_fft_figure(parsed, x_col, y_col, language="zh")
            else:
                valid_y = [y for y in y_cols if y in parsed.column_names]
                if not valid_y:
                    messagebox.showwarning("Error", "No valid Y columns selected.")
                    return
                fig = self._engine.create_figure(parsed, x_col, valid_y, language="zh")

            self._canvas.set_figure(fig)
            self._status_var.set(
                f"Preview: {parsed.filename}  (X={x_col}, Y={', '.join(y_cols)})"
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showwarning("Plot Error", str(e))

    def _on_export(self):
        if not self._file_list.filepaths:
            messagebox.showwarning("No Files", "Add CSV files first.")
            return
        output_dir = self._config.output_dir
        if not output_dir:
            messagebox.showwarning("No Output", "Select an output folder.")
            return
        if not os.path.isdir(output_dir):
            messagebox.showwarning("Invalid Folder", f"Folder not found:\n{output_dir}")
            return

        self._config._export_btn.config(state=tk.DISABLED)
        self._status_var.set("Exporting...")

        self._batch = BatchProcessor(
            filepaths=self._file_list.filepaths,
            x_col=self._config.x_col,
            y_cols=self._config.y_cols,
            output_dir=output_dir,
            formats=self._config.export_formats,
            title_template=self._config.title_template,
            force_fft=self._config.fft_mode,
            on_progress=self._on_progress,
            on_file_done=self._on_file_done,
            on_file_error=self._on_file_error,
            on_all_done=self._on_all_done,
        )
        self._batch.start()

    def _on_progress(self, current, total):
        self._status_var.set(f"Exporting... {current}/{total}")

    def _on_file_done(self, fp):
        self._status_var.set(f"Exported: {os.path.basename(fp)}")

    def _on_file_error(self, fp, msg):
        self.after(0, lambda m=msg, f=fp: messagebox.showwarning(
            "Export Error", f"{os.path.basename(f)}:\n{m}"))

    def _on_all_done(self, saved):
        self._config._export_btn.config(state=tk.NORMAL)
        n = len(saved)
        out = self._config.output_dir
        self._status_var.set(f"Done - {n} file(s) saved to {out}")
        self.after(0, lambda n=n, out=out: messagebox.showinfo(
            "Export Complete", f"{n} file(s) saved to:\n{out}"))

    def _on_add_files(self):
        self._file_list._on_add()

    def _on_about(self):
        messagebox.showinfo(
            "About",
            "Ansys Maxwell CSV Batch Plotter\n\n"
            "Reads CSV files exported from Ansys Maxwell and generates\n"
            "publication-quality plots with Origin-level styling.\n\n"
            "Features:\n"
            "- Auto-detect operating conditions & FFT data\n"
            "- Chinese (SimHei) + English (Times New Roman) fonts\n"
            "- 3:2 aspect ratio, 300 DPI export\n\n"
            "Built with tkinter + matplotlib."
        )

    def destroy(self):
        if self._batch and self._batch.is_alive():
            self._batch.cancel()
            self._batch.join(timeout=2)
        super().destroy()
