"""Smart axis label detection — maps Maxwell column names to Chinese + English labels.

Recognizes common motor/electromagnetic simulation quantities exported by Ansys Maxwell.
"""
import re
from core.csv_parser import ParsedCSV, ColumnInfo


# Per-keyword mapping: keyword -> (Chinese, English)
# Order matters: more specific patterns first
KEYWORD_MAP: list[tuple[list[str], tuple[str, str]]] = [
    # Back EMF / induced voltage
    (["inducedvoltage", "backemf", "induced emf"], ("线反电势", "Line Back EMF")),
    # Cogging torque
    (["coggingtorque", "cogging torque"], ("齿槽转矩", "Cogging Torque")),
    # Torque
    (["torque", "转矩"], ("转矩", "Torque")),
    # Flux density / BZ
    (["fluxdensity", "bz", "磁密", "flux density"], ("气隙磁密", "Air Gap Flux Density")),
    # Flux linkage
    (["fluxlinkage", "flux linkage", "磁链"], ("磁链", "Flux Linkage")),
    # Core loss
    (["coreloss", "铁耗", "core loss"], ("铁耗", "Core Loss")),
    # Loss (generic)
    (["loss", "损耗"], ("损耗", "Loss")),
    # Current
    (["irms", "current", "电流"], ("电流", "Current")),
    # Voltage
    (["voltage", "电压"], ("电压", "Voltage")),
    # Power
    (["power", "功率"], ("功率", "Power")),
    # Speed / Nr
    (["speed", "nr ", "转速"], ("转速", "Speed")),
    # Force
    (["force", "力"], ("力", "Force")),
    # Inductance
    (["inductance", "电感"], ("电感", "Inductance")),
    # Time
    (["time", "时间"], ("时间", "Time")),
    # Position / Distance
    (["distance", "position", "位置", "距离"], ("位置", "Position")),
    # FFT axis
    (["fft time", "fft distance", "harmonicorder", "谐波次数", "ffttime", "fftdistance"], ("谐波次数", "Harmonic Order")),
    # Harmonic amplitude
    (["amplitude", "magnitude", "幅值", "fft "], ("幅值", "Amplitude")),
]


def detect_label(col_info: ColumnInfo | None, parsed: ParsedCSV | None = None) -> tuple[str, str]:
    """Detect Chinese and English label for a column.

    Returns (zh_label, en_label) with units appended.
    """
    if col_info is None:
        return ("", "")

    name_lower = col_info.name.lower().replace(" ", "").replace("_", "")

    # Try detecting PhaseA-PhaseB pattern for line voltage
    name_original = col_info.name.lower()
    if "phasea" in name_original and "phaseb" in name_original:
        zh = "线反电势"
        en = "Line Back EMF"
    else:
        zh, en = _match_keyword(name_lower)

    # Append unit
    if col_info.unit:
        zh = f"{zh} [{col_info.unit}]"
        en = f"{en} [{col_info.unit}]"

    return zh, en


def detect_x_label(col_info: ColumnInfo, parsed: ParsedCSV) -> tuple[str, str]:
    """Detect X-axis label. For FFT data, always use '谐波次数'."""
    if parsed.is_fft_data:
        return ("谐波次数", "Harmonic Order")
    return detect_label(col_info, parsed)


def _match_keyword(name_lower: str) -> tuple[str, str]:
    """Match column name against keyword patterns."""
    for keywords, (zh, en) in KEYWORD_MAP:
        for kw in keywords:
            if kw in name_lower:
                return (zh, en)
    # Fallback: use original name
    return (name_lower, name_lower)


def sanitize_name(name: str) -> str:
    """Clean up a column name for display — remove common Maxwell artifacts."""
    # Remove parenthetical prefixes like "avg()" but keep content
    name = re.sub(r'^avg\((.*?)\)$', r'Avg \1', name)
    # Remove Moving1. prefix
    name = name.replace("Moving1.", "")
    return name
