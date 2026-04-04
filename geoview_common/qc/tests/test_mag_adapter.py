"""Regression tests for the shared MAG QC adapter."""

from __future__ import annotations

import sys
from pathlib import Path


_SHARED_ROOT = Path(__file__).resolve().parents[3]
_SOFTWARE_ROOT = _SHARED_ROOT.parent
_MAGQC_ROOT = _SOFTWARE_ROOT / "QC" / "MagQC"

for path in (_SHARED_ROOT, _MAGQC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from geoview_common.qc.mag import analyze_mag_data
import core as native_core


def _build_records(
    count: int = 120,
    field_fn=None,
    interval_ms: int = 100,
    gap_index: int | None = None,
) -> list[dict]:
    field_fn = field_fn or (lambda idx: 48500.0)
    records = []
    now = 0
    for idx in range(count):
        if gap_index is not None and idx == gap_index:
            now += interval_ms * 6
        records.append({
            "field": field_fn(idx),
            "epochMs": now,
        })
        now += interval_ms
    return records


def test_mag_adapter_uses_native_noise_keys():
    records = _build_records(field_fn=lambda idx: 48500.0 + (5.0 if idx % 2 else 0.0))
    parsed_result = {
        "data": records,
        "integrity": {
            "totalLines": len(records),
            "validRecords": len(records),
            "corruptCount": 0,
            "recoveredCount": 0,
            "timeReversals": 0,
            "timeGaps": 0,
            "timeDuplicates": 0,
        },
    }

    result = analyze_mag_data(records, file_name="noise.mag", parsed_result=parsed_result, detrend=False)

    noise_stage = result.stages[0]
    peak_to_peak = next(metric for metric in noise_stage.metrics if metric.name == "Peak-to-Peak")
    std_dev = next(metric for metric in noise_stage.metrics if metric.name == "Std Dev")

    assert peak_to_peak.value == 5.0
    assert std_dev.value > 0
    assert noise_stage.status.name == "FAIL"


def test_mag_adapter_respects_parsed_integrity_summary():
    records = _build_records()
    parsed_result = {
        "data": records,
        "integrity": {
            "totalLines": 100,
            "validRecords": 90,
            "corruptCount": 10,
            "recoveredCount": 0,
            "timeReversals": 0,
            "timeGaps": 0,
            "timeDuplicates": 0,
        },
    }

    result = analyze_mag_data(records, file_name="integrity.mag", parsed_result=parsed_result)

    integrity_stage = next(stage for stage in result.stages if stage.stage_name == "Data Integrity")
    valid_metric = next(metric for metric in integrity_stage.metrics if metric.name == "Valid Records")

    assert valid_metric.value == 90.0
    assert integrity_stage.status.name == "WARN"
    assert result.total_score == 80.0


def test_mag_adapter_computes_timestamp_stats_without_placeholder():
    records = _build_records(gap_index=30)

    result = analyze_mag_data(records, file_name="timing.mag")

    timestamp_stage = next(stage for stage in result.stages if stage.stage_name == "Timestamp Continuity")
    regularity_metric = next(metric for metric in timestamp_stage.metrics if metric.name == "Regularity")
    gap_metric = next(metric for metric in timestamp_stage.metrics if metric.name == "Gap Count")

    assert regularity_metric.value < 100.0
    assert gap_metric.value >= 1
    assert any(issue.category == "timing" for issue in result.issues)
    assert result.extra["timestamp"]["gap_count"] >= 1


def test_mag_adapter_matches_native_core_measurements():
    records = _build_records(field_fn=lambda idx: 48500.0 + (5.0 if idx % 2 else 0.0), gap_index=20)
    parsed_result = {
        "data": records,
        "integrity": {
            "totalLines": len(records),
            "validRecords": len(records),
            "corruptCount": 0,
            "recoveredCount": 0,
            "timeReversals": 0,
            "timeGaps": 0,
            "timeDuplicates": 0,
        },
    }

    native = native_core.run_full_analysis(records, detrend=False)
    native_timestamp = native_core.analyze_timestamp_continuity(records).get("stats", {})
    adapter = analyze_mag_data(records, file_name="native-match.mag", parsed_result=parsed_result, detrend=False)

    measurements = adapter.extra["measurements"]
    assert measurements["noise_pp"] == native["noise"]["pp"]
    assert measurements["fourth_diff_exceedance"] == native["fourth_diff"]["stats"]["exceedance_pct"]
    assert measurements["spike_pct"] == native["spikes"]["spike_pct"]
    assert measurements["integrity_pct"] == 100.0
    assert measurements["timestamp_regularity"] == native_timestamp["regularity_pct"]
    assert adapter.extra["integrity"]["validPct"] == 100.0
