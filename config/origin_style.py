"""matplotlib rcParams tuned to match Origin aesthetics with Chinese/English hybrid fonts.

Requirements from user:
- Chinese: SimHei (黑体) 26pt bold for axis labels
- English/numbers: Times New Roman 26pt bold for axis labels
- Condition legend: same fonts but 24pt bold, no border
- Aspect ratio: 3:2
"""
import matplotlib as mpl
import matplotlib.font_manager as fm
from pathlib import Path


def apply_origin_style():
    """Apply Origin-style rcParams with SimHei + Times New Roman hybrid font."""
    _setup_fonts()

    mpl.rcParams.update({
        # Figure — 3:2 aspect ratio
        "figure.facecolor": "white",
        "figure.dpi": 300,
        "figure.figsize": (6, 4),         # 3:2 ratio
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.1,

        # Font defaults
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 14,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 12,

        # Axes
        "axes.facecolor": "white",
        "axes.edgecolor": "black",
        "axes.linewidth": 1.0,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,

        # Ticks — inward
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.size": 5,
        "ytick.major.size": 5,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.minor.size": 3,
        "ytick.minor.size": 3,
        "xtick.minor.width": 0.5,
        "ytick.minor.width": 0.5,
        "xtick.top": False,
        "ytick.right": False,

        # Lines
        "lines.linewidth": 1.5,
        "lines.markersize": 6,
        "lines.markeredgewidth": 0.5,

        # Legend
        "legend.frameon": True,
        "legend.framealpha": 1.0,
        "legend.edgecolor": "#cccccc",
        "legend.fancybox": False,
        "legend.loc": "best",
        "legend.borderpad": 0.4,
        "legend.borderaxespad": 0.6,

        # Padding
        "axes.xmargin": 0.02,
        "axes.ymargin": 0.05,
    })


def _setup_fonts():
    """Configure SimHei + Times New Roman font fallback chain."""
    font_dir = Path("C:/Windows/Fonts")

    # Add SimHei
    simhei_path = font_dir / "simhei.ttf"
    if simhei_path.exists():
        fm.fontManager.addfont(str(simhei_path))

    # Add Times New Roman
    times_path = font_dir / "times.ttf"
    if times_path.exists():
        fm.fontManager.addfont(str(times_path))

    # Rebuild font cache (API varies by matplotlib version)
    try:
        fm.fontManager._load_fontmanager(try_read_cache=False)
    except AttributeError:
        # matplotlib >= 3.10
        fm._load_fontmanager(try_read_cache=False)

    # Font fallback: SimHei (Chinese) -> Times New Roman (English/numbers) -> DejaVu Sans (math symbols)
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = ["SimHei", "Times New Roman", "DejaVu Sans", "Arial"]

    # Use ASCII hyphen-minus (not Unicode minus) — all fonts support it
    mpl.rcParams["axes.unicode_minus"] = False


def get_label_font_kwargs():
    """Font properties for axis labels: 14pt bold."""
    return {"fontsize": 14, "fontweight": "bold"}


def get_condition_font_kwargs():
    """Font properties for condition annotation: 12pt bold."""
    return {"fontsize": 12, "fontweight": "bold"}


def get_tick_font_kwargs():
    """Font properties for tick labels: 11pt."""
    return {"fontsize": 11}


# Color cycle: distinct, publication-safe colors
ORIGIN_COLORS = [
    "#E41A1C",  # red
    "#377EB8",  # blue
    "#4DAF4A",  # green
    "#984EA3",  # purple
    "#FF7F00",  # orange
    "#A65628",  # brown
    "#F781BF",  # pink
    "#000000",  # black
    "#66C2A5",  # teal
    "#8DA0CB",  # lavender
]
