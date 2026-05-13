"""Parse CSV files exported from Ansys Maxwell.

Handles real Maxwell export formats:
- Quoted headers: "Name [Unit]"
- Parameter columns (Irms, Nr/speed) within stacked condition blocks
- Time-domain data: Torque, Back EMF, CoreLoss
- Frequency-domain data: FFT with both Time + FFT Time columns
- Air gap flux density: Distance + BZ
"""
import re
import csv
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto

import pandas as pd
import numpy as np


class ColumnType(Enum):
    PARAMETER = auto()   # operating condition (repeated values)
    DATA = auto()        # regular numeric data (X or Y)
    FFT_X = auto()       # frequency-domain X axis
    FFT_Y = auto()       # frequency-domain amplitude
    UNKNOWN = auto()


@dataclass
class ColumnInfo:
    name: str
    unit: str
    index: int
    col_type: ColumnType = ColumnType.UNKNOWN


@dataclass
class ConditionGroup:
    """A subset of data for one specific operating condition."""
    label: str
    params: dict               # {param_name: value}
    dataframe: pd.DataFrame


@dataclass
class ParsedCSV:
    filepath: Path
    filename: str
    columns: list[ColumnInfo] = field(default_factory=list)
    dataframe: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata: dict = field(default_factory=dict)
    # Smart detection results
    param_cols: list[ColumnInfo] = field(default_factory=list)
    data_cols: list[ColumnInfo] = field(default_factory=list)
    fft_x_cols: list[ColumnInfo] = field(default_factory=list)
    fft_y_cols: list[ColumnInfo] = field(default_factory=list)
    conditions: list[ConditionGroup] = field(default_factory=list)
    is_fft_data: bool = False

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def suggested_x_col(self) -> str | None:
        """Suggest the best X-axis column. Excludes constant/parameter columns."""
        # For FFT data, prefer FFT-prefixed column
        if self.is_fft_data and self.fft_x_cols:
            return self.fft_x_cols[0].name
        # Prefer "Time" from data columns (must not be constant)
        for c in self.data_cols:
            if "time" in c.name.lower() and not _is_constant_column(c, self):
                return c.name
        # First non-constant data column
        for c in self.data_cols:
            if not _is_constant_column(c, self) and c.name not in [p.name for p in self.param_cols]:
                return c.name
        # Last fallback
        for c in self.columns:
            if not _is_constant_column(c, self) and c.name not in [p.name for p in self.param_cols]:
                return c.name
        if self.columns:
            return self.columns[0].name
        return None

    @property
    def suggested_y_cols(self) -> list[str]:
        """Suggest best Y-axis columns. Excludes constant columns and X column."""
        # For FFT: prefer FFT_Y columns, then FFT-named columns
        if self.is_fft_data:
            if self.fft_y_cols:
                return [c.name for c in self.fft_y_cols]
            x = self.suggested_x_col
            for c in self.columns:
                if c.name != x and "fft" in c.name.lower() and not _is_constant_column(c, self):
                    return [c.name]
        # Standard: non-constant data columns that aren't X
        x = self.suggested_x_col
        param_names = {p.name for p in self.param_cols}
        cols = []
        for c in self.data_cols:
            if c.name != x and not _is_constant_column(c, self) and c.name not in param_names:
                cols.append(c.name)
        if cols:
            return cols
        # Fallback: last non-constant column
        for c in reversed(self.columns):
            if c.name != x and not _is_constant_column(c, self):
                return [c.name]
        return [self.columns[-1].name]


# Patterns for identifying FFT columns
FFT_X_PATTERNS = ["fft time", "fft distance", "fft frequency", "fft freq",
                  "harmonic", "谐波次数", "fft_distance", "fft_time",
                  "fftdistance", "ffttime"]
FFT_Y_PATTERNS = ["fft ", "magnitude", "amplitude", "幅值", "fft_"]
FFT_FILE_PATTERNS = ["fft", "谐波", "harmonic", "frequency"]
# Regex to extract "Name [Unit]" pattern from header
# Handles: "Irms [A]", avg(Moving1.Torque) [NewtonMeter], "FFT BZ []", etc.
HEADER_PATTERN = re.compile(r'^"?\s*(.+?)\s*\[(.*?)\]\s*"?\s*$')


def parse_maxwell_csv(filepath: str | Path) -> ParsedCSV:
    """Parse a Maxwell-exported CSV file with smart column detection."""
    filepath = Path(filepath)
    result = ParsedCSV(filepath=filepath, filename=filepath.name)

    # Read CSV with pandas — handle both quoted and unquoted headers
    result.dataframe = pd.read_csv(filepath, encoding="utf-8-sig")

    # Parse header columns
    result.columns = _parse_header(list(result.dataframe.columns))

    # Rename DataFrame columns to clean names
    rename_map = {}
    for i, col_info in enumerate(result.columns):
        if i < len(result.dataframe.columns):
            rename_map[result.dataframe.columns[i]] = col_info.name
    result.dataframe = result.dataframe.rename(columns=rename_map)
    result.dataframe = result.dataframe.dropna(how="all")

    # Smart column classification
    _classify_columns(result)

    # Detect FFT data
    result.is_fft_data = (
        len(result.fft_x_cols) > 0 or
        len(result.fft_y_cols) > 0 or
        _is_fft_file(result)
    )

    # Check if columns with ONLY 1 unique value should be treated as parameters
    _refine_single_value_params(result)

    # Extract condition groups
    if result.param_cols:
        result.conditions = _group_by_conditions(result)

    return result


def _parse_header(header: list[str]) -> list[ColumnInfo]:
    """Parse header row, extracting name and unit from 'Name [Unit]' format."""
    columns = []
    for i, col in enumerate(header):
        col = str(col).strip().strip('"').strip("'")
        m = HEADER_PATTERN.match(col)
        if m:
            name = m.group(1).strip()
            unit = m.group(2).strip()
        else:
            name = col
            unit = ""
        columns.append(ColumnInfo(name=name, unit=unit, index=i))
    return columns


def _classify_columns(parsed: ParsedCSV):
    """Auto-classify columns as parameter, data, or FFT."""
    df = parsed.dataframe

    for col_info in parsed.columns:
        if col_info.name not in df.columns:
            col_info.col_type = ColumnType.UNKNOWN
            continue

        series = pd.to_numeric(df[col_info.name], errors="coerce").dropna()
        if len(series) == 0:
            col_info.col_type = ColumnType.UNKNOWN
            continue

        name_lower = col_info.name.lower().replace(" ", "").replace("_", "")

        # Check FFT X-axis columns first
        if _matches_pattern(name_lower, FFT_X_PATTERNS):
            col_info.col_type = ColumnType.FFT_X
            parsed.fft_x_cols.append(col_info)
            continue

        # Check FFT Y-axis columns
        if _matches_pattern(name_lower, FFT_Y_PATTERNS) and "fft_" not in name_lower.replace("fft", ""):
            # Only classify as FFT_Y if the name starts with FFT or contains FFT specifically
            if name_lower.startswith("fft") or "fft" in name_lower:
                col_info.col_type = ColumnType.FFT_Y
                parsed.fft_y_cols.append(col_info)
                continue

        # Check if it's a parameter column
        if _is_parameter_column(series):
            col_info.col_type = ColumnType.PARAMETER
            parsed.param_cols.append(col_info)
        else:
            col_info.col_type = ColumnType.DATA
            parsed.data_cols.append(col_info)


def _refine_single_value_params(parsed: ParsedCSV):
    """Columns with only 1 unique value are truly constant (not useful params).
    Move constant columns from param_cols to data_cols."""
    df = parsed.dataframe
    new_params = []
    for col_info in parsed.param_cols:
        series = pd.to_numeric(df[col_info.name], errors="coerce").dropna()
        if series.nunique() > 1:
            new_params.append(col_info)
        else:
            # Only 1 value — not a useful parameter for grouping
            col_info.col_type = ColumnType.DATA
            parsed.data_cols.append(col_info)
    parsed.param_cols = new_params


def _matches_pattern(name_lower: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat in name_lower:
            return True
    return False


def _is_constant_column(col_info: ColumnInfo, parsed: ParsedCSV) -> bool:
    """True if this column has only 1 unique value (constant, not useful as Y)."""
    if col_info.name not in parsed.dataframe.columns:
        return False
    series = pd.to_numeric(parsed.dataframe[col_info.name], errors="coerce").dropna()
    return series.nunique() <= 1


def _is_fft_file(parsed: ParsedCSV) -> bool:
    """Check if the filename suggests FFT data."""
    name_lower = parsed.filename.lower().replace(" ", "").replace("_", "")
    for pat in FFT_FILE_PATTERNS:
        if pat in name_lower:
            return True
    return False


def _is_parameter_column(series: pd.Series) -> bool:
    """A column is a parameter if it has few unique values AND they repeat in blocks."""
    if len(series) < 5:
        return False
    nu = series.nunique()
    if nu <= 1:
        return False
    n = len(series)
    unique_ratio = nu / n
    most_common_ratio = series.value_counts().iloc[0] / n

    # Parameter columns: very few distinct values AND low unique ratio
    if nu <= 15 and unique_ratio < 0.1:
        return True
    # Also: dominant repeated value (>=30% of rows) AND few total unique values
    if most_common_ratio >= 0.3 and nu <= 15:
        return True
    return False


def _group_by_conditions(parsed: ParsedCSV) -> list[ConditionGroup]:
    """Group rows by unique combinations of parameter columns."""
    df = parsed.dataframe
    param_names = [c.name for c in parsed.param_cols]

    if not param_names:
        return []

    # Use all param columns for grouping
    groups = []
    for param_vals, sub in df.groupby(param_names):
        if len(sub) < 2:
            continue
        if not isinstance(param_vals, tuple):
            param_vals = (param_vals,)

        params = dict(zip(param_names, param_vals))
        # Build label
        label_parts = []
        for pn, pv in params.items():
            if isinstance(pv, (float, np.floating)):
                label_parts.append(f"{pn}={pv:.4g}")
            else:
                label_parts.append(f"{pn}={pv}")
        label = ", ".join(label_parts)
        groups.append(ConditionGroup(label=label, params=params, dataframe=sub.copy()))

    return groups


def _split_blocks(raw: str) -> list[str]:
    """Split CSV content into blocks separated by blank lines."""
    lines = raw.strip().split("\n")
    blocks = []
    current = []
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks
