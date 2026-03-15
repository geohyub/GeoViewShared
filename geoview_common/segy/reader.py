"""
GeoView SEG-Y Reader
====================
Common segyio wrapper shared by 6+ projects.

Usage:
    from geoview_common.segy.reader import read_segy_info

    info = read_segy_info("file.sgy")
    print(info["n_traces"], info["sample_rate_ms"])
"""

from pathlib import Path
from typing import Union, Optional

try:
    import segyio
    HAS_SEGYIO = True
except ImportError:
    HAS_SEGYIO = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def read_segy_info(filepath: Union[str, Path],
                   strict: bool = False) -> dict:
    """
    Read basic SEG-Y file information.

    Returns dict with keys:
        n_traces, n_samples, sample_rate_us, sample_rate_ms,
        format_code, ebcdic_header, binary_header
    """
    if not HAS_SEGYIO:
        raise ImportError("segyio is required: pip install segyio")

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"SEG-Y file not found: {filepath}")

    with segyio.open(str(filepath), "r",
                     strict=strict, ignore_geometry=True) as f:
        n_traces = f.tracecount
        n_samples = len(f.samples)
        sample_rate_us = segyio.tools.dt(f)
        sample_rate_ms = sample_rate_us / 1000.0

        # Binary header info
        format_code = f.bin[segyio.BinField.Format]

        # EBCDIC header (first 3200 bytes)
        try:
            ebcdic = f.text[0] if f.text else ""
        except Exception:
            ebcdic = ""

        return {
            "filepath": str(filepath),
            "filename": filepath.name,
            "n_traces": n_traces,
            "n_samples": n_samples,
            "sample_rate_us": sample_rate_us,
            "sample_rate_ms": sample_rate_ms,
            "record_length_ms": n_samples * sample_rate_ms,
            "format_code": format_code,
            "ebcdic_header": ebcdic,
            "file_size_mb": filepath.stat().st_size / (1024 * 1024),
        }


def read_trace_headers(filepath: Union[str, Path],
                       fields: Optional[list] = None,
                       max_traces: int = 0) -> list:
    """
    Read trace header values.

    Parameters:
        filepath: SEG-Y file path
        fields: List of segyio.TraceField to read (default: common fields)
        max_traces: Max traces to read (0 = all)

    Returns:
        List of dicts, one per trace
    """
    if not HAS_SEGYIO:
        raise ImportError("segyio is required: pip install segyio")

    if fields is None:
        fields = [
            segyio.TraceField.TRACE_SEQUENCE_LINE,
            segyio.TraceField.FieldRecord,
            segyio.TraceField.TraceNumber,
            segyio.TraceField.CDP,
            segyio.TraceField.SourceX,
            segyio.TraceField.SourceY,
            segyio.TraceField.GroupX,
            segyio.TraceField.GroupY,
            segyio.TraceField.INLINE_3D,
            segyio.TraceField.CROSSLINE_3D,
        ]

    with segyio.open(str(filepath), "r",
                     strict=False, ignore_geometry=True) as f:
        n = f.tracecount
        if max_traces > 0:
            n = min(n, max_traces)

        headers = []
        for i in range(n):
            row = {}
            for field in fields:
                row[str(field)] = f.header[i][field]
            headers.append(row)

    return headers


def read_traces(filepath: Union[str, Path],
                trace_indices: Optional[list] = None) -> "np.ndarray":
    """
    Read trace data as numpy array.

    Parameters:
        filepath: SEG-Y file path
        trace_indices: Specific trace indices to read (None = all)

    Returns:
        2D numpy array (n_traces, n_samples)
    """
    if not HAS_SEGYIO or not HAS_NUMPY:
        raise ImportError("segyio and numpy required")

    with segyio.open(str(filepath), "r",
                     strict=False, ignore_geometry=True) as f:
        if trace_indices is None:
            return segyio.tools.collect(f.trace[:])
        return np.array([f.trace[i] for i in trace_indices])
