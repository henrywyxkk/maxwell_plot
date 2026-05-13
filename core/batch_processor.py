"""Batch process multiple CSV files — one plot per file, dual-language output.

Auto-detects plot type (FFT vs standard XY) and exports both Chinese and English versions.
Runs on a daemon thread so the GUI stays responsive.
"""
import threading
from pathlib import Path
from collections.abc import Callable

from core.csv_parser import parse_maxwell_csv
from core.plot_engine import PlotEngine


class BatchProcessor(threading.Thread):
    """Process a list of CSV files and export Chinese + English plots per file."""

    def __init__(
        self,
        filepaths: list[str],
        x_col: str,
        y_cols: list[str],
        output_dir: str,
        formats: tuple[str, ...] = ("png", "svg"),
        title_template: str = "{filename}",
        force_fft: bool = False,
        on_progress: Callable[[int, int], None] | None = None,
        on_file_done: Callable[[str], None] | None = None,
        on_file_error: Callable[[str, str], None] | None = None,
        on_all_done: Callable[[list[str]], None] | None = None,
    ):
        super().__init__(daemon=True)
        self._filepaths = filepaths
        self._x_col = x_col
        self._y_cols = y_cols
        self._output_dir = output_dir
        self._formats = formats
        self._title_template = title_template
        self._force_fft = force_fft
        self._on_progress = on_progress
        self._on_file_done = on_file_done
        self._on_file_error = on_file_error
        self._on_all_done = on_all_done
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def run(self):
        engine = PlotEngine()
        total = len(self._filepaths)
        saved_all = []

        for i, fp in enumerate(self._filepaths):
            if self._cancelled.is_set():
                break

            try:
                parsed = parse_maxwell_csv(fp)
                base_name = Path(fp).stem
                use_fft = self._force_fft or parsed.is_fft_data
                y_col = self._y_cols[0] if self._y_cols else parsed.suggested_y_cols[0]

                # Generate both Chinese and English versions
                for lang, lang_suffix in [("zh", "_zh"), ("en", "_en")]:
                    if use_fft:
                        fig = engine.create_fft_figure(parsed, self._x_col, y_col, language=lang)
                    else:
                        fig = engine.create_figure(parsed, self._x_col, self._y_cols, language=lang)

                    base = f"{base_name}{lang_suffix}"
                    saved = engine.export_figure(fig, self._output_dir, base, self._formats)
                    saved_all.extend([str(p) for p in saved])

                if self._on_file_done:
                    self._on_file_done(fp)
            except Exception as e:
                if self._on_file_error:
                    self._on_file_error(fp, str(e))

            if self._on_progress:
                self._on_progress(i + 1, total)

        if self._on_all_done:
            self._on_all_done(saved_all)
