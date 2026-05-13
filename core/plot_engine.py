"""Generate publication-quality plots with Origin-like styling.

Supports:
- Standard XY line plots with operating-condition legend
- FFT bar charts (harmonics 1-15) with grouped multi-condition bars
- Smart axis label detection (Torque→转矩, Back EMF→线反电势, etc.)
- Dual-language output: Chinese + English versions
- 3:2 aspect ratio
"""
from pathlib import Path
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

from config.origin_style import (
    apply_origin_style, ORIGIN_COLORS,
    get_label_font_kwargs, get_condition_font_kwargs, get_tick_font_kwargs,
)
from core.csv_parser import ParsedCSV, ColumnInfo
from core.label_mapper import detect_label, detect_x_label


class PlotEngine:
    """Creates publication-quality matplotlib figures from parsed Maxwell CSV data."""

    def __init__(self):
        apply_origin_style()
        self.colors = ORIGIN_COLORS[:]
        self.label_font = get_label_font_kwargs()
        self.condition_font = get_condition_font_kwargs()

    # ── Standard XY line plot ───────────────────────────────

    def create_figure(
        self,
        parsed: ParsedCSV,
        x_col: str,
        y_cols: list[str],
        language: str = "zh",
    ) -> Figure:
        """Build an XY plot. language = 'zh' or 'en'."""
        fig, ax = plt.subplots(figsize=(6, 4))

        x_info = _find_col(parsed, x_col)

        if parsed.conditions:
            self._plot_with_conditions(ax, parsed, x_info, y_cols)
        else:
            self._plot_simple(ax, parsed, x_col, y_cols, language)

        # Smart axis labels
        y_info = _find_col(parsed, y_cols[0] if y_cols else "")
        self._set_axis_labels_smart(ax, parsed, x_info, y_info, language)

        fig.tight_layout()
        return fig

    def _plot_simple(self, ax, parsed, x_col, y_cols, language):
        """Simple plot: all Y curves against X."""
        df = parsed.dataframe
        for i, y_col in enumerate(y_cols):
            color = self.colors[i % len(self.colors)]
            x_data = pd.to_numeric(df[x_col], errors="coerce")
            y_data = pd.to_numeric(df[y_col], errors="coerce")
            mask = x_data.notna() & y_data.notna()
            y_info = _find_col(parsed, y_col)
            zh_label, en_label = detect_label(y_info, parsed)
            label = zh_label if language == "zh" else en_label
            ax.plot(x_data[mask], y_data[mask], color=color, label=label, linewidth=1.5)
        if len(y_cols) > 1:
            ax.legend(fontsize=12, edgecolor="#cccccc")

    def _plot_with_conditions(self, ax, parsed, x_info, y_cols):
        """Plot one curve per condition, with condition legend."""
        for i, cond in enumerate(parsed.conditions):
            color = self.colors[i % len(self.colors)]
            df = cond.dataframe
            x_name = x_info.name if x_info else parsed.columns[0].name
            x_data = pd.to_numeric(df[x_name], errors="coerce")

            for j, y_col in enumerate(y_cols):
                if y_col not in df.columns:
                    continue
                y_data = pd.to_numeric(df[y_col], errors="coerce")
                mask = x_data.notna() & y_data.notna()
                label = f"{cond.label}" if j == 0 else None
                ax.plot(x_data[mask], y_data[mask], color=color, label=label, linewidth=1.5)

        ax.legend(
            fontsize=12,
            edgecolor="none",
            loc="upper right",
            borderpad=0.2,
            borderaxespad=0.3,
        )

    # ── FFT Bar Chart (harmonics 1-15) ──────────────────────

    def create_fft_figure(
        self,
        parsed: ParsedCSV,
        x_col: str,
        y_col: str,
        language: str = "zh",
    ) -> Figure:
        """Create an FFT bar chart, harmonics 1-15, X normalized to fundamental."""
        fig, ax = plt.subplots(figsize=(6, 4))

        if parsed.conditions:
            self._plot_fft_grouped(ax, parsed, x_col, y_col)
        else:
            self._plot_fft_simple(ax, parsed, x_col, y_col)

        # Axis labels via smart detection
        x_info = _find_col(parsed, x_col)
        y_info = _find_col(parsed, y_col)

        zh_x, en_x = detect_x_label(x_info, parsed)
        zh_y, en_y = detect_label(y_info, parsed)

        if language == "zh":
            ax.set_xlabel(zh_x, **self.label_font)
            ax.set_ylabel(zh_y, **self.label_font)
        else:
            ax.set_xlabel(en_x, **self.label_font)
            ax.set_ylabel(en_y, **self.label_font)

        # Tick fonts
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        fig.tight_layout()
        return fig

    def _plot_fft_simple(self, ax, parsed, x_col, y_col):
        """Simple FFT bar chart — find fundamental, normalize, limit to harmonics 1-15."""
        df = parsed.dataframe
        x_raw = pd.to_numeric(df[x_col], errors="coerce")
        y_raw = pd.to_numeric(df[y_col], errors="coerce")
        mask = x_raw.notna() & y_raw.notna()
        x_vals = x_raw[mask].values
        y_vals = y_raw[mask].values

        if len(x_vals) == 0:
            return

        fund_idx = np.argmax(np.abs(y_vals))
        fund_x = x_vals[fund_idx]
        if fund_x != 0:
            x_norm = x_vals / fund_x
        else:
            x_norm = x_vals

        # Limit to harmonics 1-15
        mask_15 = (x_norm >= 0.5) & (x_norm <= 15.5)
        x_norm = x_norm[mask_15]
        y_vals = y_vals[mask_15]

        width = 0.4
        ax.bar(x_norm, y_vals, width=width, color=self.colors[0], edgecolor="black", linewidth=0.3)

        # Set integer ticks
        ax.set_xticks(range(1, min(16, int(max(x_norm)) + 1)))

    def _plot_fft_grouped(self, ax, parsed, x_col, y_col):
        """Grouped FFT bars: one group per condition, harmonics 1-15."""
        n_conds = len(parsed.conditions)
        if n_conds == 0:
            return

        global_fund = None
        all_harmonics = set()

        for cond in parsed.conditions:
            df = cond.dataframe
            x_raw = pd.to_numeric(df[x_col], errors="coerce")
            y_raw = pd.to_numeric(df[y_col], errors="coerce")
            mask = x_raw.notna() & y_raw.notna()
            if mask.sum() == 0:
                continue
            x = x_raw[mask].values
            y = y_raw[mask].values
            fund_x = x[np.argmax(np.abs(y))]
            if global_fund is None:
                global_fund = fund_x
            for v in x:
                ratio = v / global_fund if global_fund != 0 else v
                h = round(ratio)
                if 1 <= h <= 15:
                    all_harmonics.add(h)

        if global_fund is None or global_fund == 0:
            return

        harmonics = sorted(all_harmonics)
        bar_width = 0.35 / max(n_conds, 1)

        cond_handles = []
        for ci, cond in enumerate(parsed.conditions):
            df = cond.dataframe
            x_raw = pd.to_numeric(df[x_col], errors="coerce")
            y_raw = pd.to_numeric(df[y_col], errors="coerce")
            mask = x_raw.notna() & y_raw.notna()
            if mask.sum() == 0:
                continue
            x = x_raw[mask].values
            y = y_raw[mask].values

            harm_amp = {}
            for xv, yv in zip(x, y):
                h = round(xv / global_fund)
                if 1 <= h <= 15:
                    harm_amp[h] = harm_amp.get(h, 0) + yv

            offset = (ci - (n_conds - 1) / 2.0) * bar_width
            positions = np.array(harmonics) + offset
            heights = [harm_amp.get(h, 0) for h in harmonics]

            color = self.colors[ci % len(self.colors)]
            bars = ax.bar(positions, heights, width=bar_width, color=color,
                          edgecolor="black", linewidth=0.3)
            cond_handles.append((bars, cond.label))

        if cond_handles:
            ax.legend(
                [h[0] for h in cond_handles],
                [h[1] for h in cond_handles],
                fontsize=12,
                edgecolor="none",
                loc="upper right",
                borderpad=0.2,
            )

        ax.set_xticks(harmonics)
        ax.set_xticklabels([str(h) for h in harmonics])

    # ── Export ──────────────────────────────────────────────

    def export_figure(
        self,
        fig: Figure,
        output_dir: str | Path,
        base_name: str,
        formats: tuple[str, ...] = ("png", "svg"),
    ) -> list[Path]:
        """Save figure to disk. Returns paths of saved files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved = []
        for fmt in formats:
            fpath = output_dir / self._safe_filename(f"{base_name}.{fmt}")
            if fmt == "png":
                fig.savefig(fpath, dpi=300, format="png")
            else:
                fig.savefig(fpath, format=fmt)
            saved.append(fpath)
            plt.close(fig)

        return saved

    # ── Helpers ─────────────────────────────────────────────

    def _set_axis_labels_smart(self, ax, parsed, x_info, y_info, language):
        """Set axis labels using smart detection."""
        if x_info:
            zh_x, en_x = detect_x_label(x_info, parsed)
            ax.set_xlabel(zh_x if language == "zh" else en_x, **self.label_font)
        if y_info:
            zh_y, en_y = detect_label(y_info, parsed)
            ax.set_ylabel(zh_y if language == "zh" else en_y, **self.label_font)

    @staticmethod
    def _safe_filename(name: str) -> str:
        for ch in r'<>:"/\|?*':
            name = name.replace(ch, "_")
        return name


def _find_col(parsed: ParsedCSV, name: str) -> ColumnInfo | None:
    for c in parsed.columns:
        if c.name == name:
            return c
    return None
