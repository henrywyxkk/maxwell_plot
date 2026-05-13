# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Desktop GUI application that batch-reads CSV files exported from Ansys Maxwell (electromagnetic simulation), auto-detects operating conditions and FFT data, and generates publication-quality plots with Chinese + English dual-language output. 3:2 aspect ratio, Origin-style aesthetics.

## Commands

```bash
# Run the app
python main.py

# Quick headless test (parse CSVs, export plots without GUI)
python -c "
from core.csv_parser import parse_maxwell_csv
from core.plot_engine import PlotEngine
from pathlib import Path
engine = PlotEngine()
for f in Path('test_data').glob('*.csv'):
    p = parse_maxwell_csv(f)
    fig = engine.create_fft_figure(p, p.suggested_x_col, p.suggested_y_cols[0], 'zh') if p.is_fft_data else engine.create_figure(p, p.suggested_x_col, p.suggested_y_cols, 'zh')
    engine.export_figure(fig, 'test_output', f.stem)
"
```

No test suite or linter is configured. Python 3.13 on Windows (Anaconda). Dependencies in `requirements.txt`.

## Architecture

```
main.py → gui/main_window.py (tkinter.Tk)
              ├── gui/file_list_panel.py      — CSV file list, add/remove
              ├── gui/plot_config_panel.py     — X/Y column selector, FFT toggle, export settings
              └── gui/plot_canvas.py           — matplotlib FigureCanvasTkAgg preview
         → core/batch_processor.py            — threading.Thread, processes N CSVs → N×2 plots
              └── core/plot_engine.py          — matplotlib figures (XY + FFT bar chart)
                   ├── config/origin_style.py  — rcParams, SimHei + Times New Roman fonts
                   └── core/label_mapper.py    — column name → (zh, en) label
         → core/csv_parser.py                  — ParsedCSV dataclass, column classification
```

**Data flow**: CSV files → `parse_maxwell_csv()` → `ParsedCSV` (columns typed as PARAMETER/DATA/FFT_X/FFT_Y, grouped into conditions) → `PlotEngine.create_figure()` or `create_fft_figure()` → export PNG+SVG via `export_figure()`.

## Key design details

### Why tkinter, not PySide6
PySide6 DLLs failed to load on Python 3.13 (error 127 "找不到指定的程序"). Switched to tkinter which ships with Python. `requirements.txt` still lists PySide6 but it is **not used** — do not re-add it.

### Column type detection (`csv_parser.py`)
- **PARAMETER**: few unique values (`nu ≤ 15` AND `unique_ratio < 0.1`) OR dominant value (`most_common ≥ 30%` AND `nu ≤ 15`). Single-unique-value columns (e.g. Nr=3000 everywhere) are moved to DATA by `_refine_single_value_params()`.
- **FFT_X / FFT_Y**: matched by substrings in `FFT_X_PATTERNS` / `FFT_Y_PATTERNS`. Also `_is_fft_file()` checks filename.
- Column classification is consulted by `suggested_x_col` / `suggested_y_cols` which exclude constant and parameter columns. The GUI pre-selects these suggestions.

### Maxwell CSV header format
Two variants exist in real exports:
- Unquoted: `Irms [A],Nr [],Time [ms],Moving1.Torque [NewtonMeter]`
- Quoted: `"Irms [A]","Nr []","Time [ms]","Moving1.Torque [NewtonMeter]"`

Empty-unit brackets `[]` appear frequently (e.g. `Nr []`, `FFT Time []`). The regex `r'^"?\s*(.+?)\s*\[(.*?)\]\s*"?\s*$'` handles both quoted/unquoted and empty units.

### Font setup (`config/origin_style.py`)
Loads SimHei and Times New Roman from `C:/Windows/Fonts/`. Font cache rebuild API changed between matplotlib 3.9 and 3.10: the code tries `fm.fontManager._load_fontmanager()` first, then falls back to `fm._load_fontmanager()`. Font fallback chain: SimHei → Times New Roman → DejaVu Sans.

### FFT normalization
- Find highest-amplitude bin → that's X=1 (fundamental/first harmonic)
- All other X values divided by the fundamental frequency
- Harmonics limited to 1–15
- Multi-condition: bars grouped left/right of each harmonic integer

### Dual-language output
`PlotEngine.create_figure()` and `create_fft_figure()` accept `language="zh"|"en"`. `BatchProcessor.run()` loops over both languages, appending `_zh` / `_en` suffixes to output filenames. Preview in GUI uses Chinese.

### Condition legend
No border (`edgecolor="none"`), positioned at upper right. Shows parameter values (e.g. `Irms=120`). Font: 12pt bold.

## Real Maxwell CSV patterns in `test_data/`

| Pattern | Files | Columns |
|---------|-------|---------|
| Avg Torque vs Current | `avgTorque.csv` | Irms (X), avg(Torque) (Y) |
| Torque over time, multi-current | `Nr_*_Torque.csv` | Irms (param), Nr (constant), Time (X), Torque (Y) |
| Back EMF over time | `Nr_*_eding_xianfandianshi.csv` | Irms (param), Time (X), PhaseA-PhaseB voltage (Y) |
| FFT of back EMF | `FFT Nr_*_xianfandianshi.csv` | Irms (param), FFT Time (FFT_X), FFT amplitude (Y) |
| Air gap flux density | `气隙磁密.csv` | Distance (X), BZ (Y) |
| FFT of flux density | `FFT_气隙磁密.csv` | FFT Distance (FFT_X), FFT BZ (Y) |
| Core loss | `Nr3000_Coreloss.csv` | Time (X), CoreLoss / CoreLoss(rotor) / CoreLoss(stator) (Y) |
