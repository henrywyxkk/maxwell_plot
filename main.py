"""Ansys Maxwell CSV Batch Plotter — entry point.

Usage:
    python main.py                           # Launch GUI
    python main.py --batch <files_or_dirs>   # Batch process without GUI
    python main.py --batch . --output out/   # Process all CSVs in current dir
    python main.py --batch file1.csv file2.csv --output out/
"""
import sys
import os
from pathlib import Path


def collect_csvs(paths: list[str]) -> list[str]:
    """Given files and/or directories, return unique list of all .csv file paths."""
    csvs = set()
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for f in pp.glob('*'):
                if f.suffix.lower() == '.csv':
                    csvs.add(str(f))
        elif pp.suffix.lower() == '.csv':
            csvs.add(str(pp))
    return sorted(csvs)


def batch_mode(raw_args: list[str]):
    """Headless batch processing."""
    # Parse args
    output_dir = None
    output_flag = False
    paths = []

    for a in raw_args:
        if output_flag:
            output_dir = a
            output_flag = False
        elif a in ('--output', '-o'):
            output_flag = True
        elif a in ('--batch', '-b'):
            continue
        else:
            paths.append(a)

    if not paths:
        print("Usage: python main.py --batch <files_or_dirs> [--output <dir>]")
        print("Example: python main.py --batch ./test_data --output ./plots")
        return

    csvs = collect_csvs(paths)
    if not csvs:
        print("No CSV files found.")
        return

    if output_dir is None:
        output_dir = "output"

    print(f"Processing {len(csvs)} CSV file(s) → {output_dir}/")

    from core.csv_parser import parse_maxwell_csv
    from core.plot_engine import PlotEngine

    engine = PlotEngine()
    total_saved = 0
    errors = 0

    for fp in csvs:
        try:
            parsed = parse_maxwell_csv(fp)
            x = parsed.suggested_x_col
            ys = parsed.suggested_y_cols
            base = Path(fp).stem

            if parsed.is_fft_data:
                fig_zh = engine.create_fft_figure(parsed, x, ys[0], language="zh")
                fig_en = engine.create_fft_figure(parsed, x, ys[0], language="en")
            else:
                fig_zh = engine.create_figure(parsed, x, ys, language="zh")
                fig_en = engine.create_figure(parsed, x, ys, language="en")

            saved = engine.export_figure(fig_zh, output_dir, f"{base}_zh", ("png", "svg"))
            saved += engine.export_figure(fig_en, output_dir, f"{base}_en", ("png", "svg"))
            total_saved += len(saved)

            cond_info = f" [{len(parsed.conditions)} conditions]" if parsed.conditions else ""
            print(f"  OK  {os.path.basename(fp)} → {base}_*.png/svg{cond_info}")

        except Exception as e:
            errors += 1
            print(f"  ERR {os.path.basename(fp)}: {e}")

    print(f"\nDone: {total_saved} files, {errors} error(s) → {os.path.abspath(output_dir)}")


def gui_mode():
    """Launch tkinter GUI."""
    from gui.main_window import MainWindow
    app = MainWindow()
    app.mainloop()


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--batch', '-b'):
        batch_mode(sys.argv[1:])
    else:
        gui_mode()


if __name__ == "__main__":
    main()
