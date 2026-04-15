"""Tests for geoview_cpt.scpt.first_break_picking — Phase A-2 A2.14."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.scpt import (
    DEFAULT_STA_WINDOW_MS,
    DEFAULT_THRESHOLD,
    FirstBreakPick,
    pick_first_breaks,
    pseudo_interval_velocity,
    true_interval_velocity,
)


# ---------------------------------------------------------------------------
# Synthetic seismogram factory
# ---------------------------------------------------------------------------


def _synthetic_traces(
    n_traces: int = 5,
    n_samples: int = 4000,
    sample_rate_hz: float = 2000.0,
    velocities_m_s: float = 200.0,
    depths_m: list[float] | None = None,
) -> tuple[np.ndarray, list[float]]:
    """
    Build a synthetic ``(n_traces, n_samples)`` seismogram whose first
    arrival walks monotonically with depth.

    Each trace has a flat noise floor of 0.01 amplitude and an
    impulsive spike at the expected first-arrival sample, followed
    by a short oscillation.
    """
    rng = np.random.default_rng(seed=42)
    if depths_m is None:
        # Keep first arrival well past the LTA window (≥ sample 40
        # at 2 kHz + 20 ms LTA → 50 ms = 10 m at V=200)
        depths_m = [15.0 + 5.0 * i for i in range(n_traces)]
    dt_s = 1.0 / sample_rate_hz
    data = rng.normal(scale=0.01, size=(n_traces, n_samples))
    for i, z in enumerate(depths_m):
        # straight-ray one-way time from surface source at (0, 0)
        t_arr_s = z / velocities_m_s
        idx = int(round(t_arr_s / dt_s))
        if idx + 10 >= n_samples:
            continue
        # Impulse + ringing
        data[i, idx] += 1.0
        data[i, idx + 1] -= 0.7
        data[i, idx + 2] += 0.4
        data[i, idx + 3] -= 0.2
    return data, depths_m


# ---------------------------------------------------------------------------
# Picker
# ---------------------------------------------------------------------------


class TestPickFirstBreaks:
    def test_picks_every_trace(self):
        data, depths = _synthetic_traces()
        picks = pick_first_breaks(data, depths, sample_rate_hz=2000.0)
        assert len(picks) == len(depths)
        for i, p in enumerate(picks):
            assert isinstance(p, FirstBreakPick)
            assert p.trace_index == i
            assert p.depth_m == depths[i]

    def test_times_increase_with_depth(self):
        data, depths = _synthetic_traces(n_traces=5)
        picks = pick_first_breaks(data, depths, sample_rate_hz=2000.0)
        times = [p.time_ms for p in picks]
        assert all(times[i] <= times[i + 1] for i in range(len(times) - 1))

    def test_picked_times_match_ground_truth(self):
        """First arrival at V=200 m/s → depth / 200 seconds."""
        data, depths = _synthetic_traces(
            n_traces=5,
            depths_m=[10.0, 20.0, 30.0, 40.0, 50.0],
            velocities_m_s=200.0,
            n_samples=4000,
            sample_rate_hz=2000.0,
        )
        picks = pick_first_breaks(data, depths, sample_rate_hz=2000.0)
        for p in picks:
            expected_ms = p.depth_m / 200.0 * 1000.0
            assert abs(p.time_ms - expected_ms) < 2.0   # 2 ms tolerance

    def test_confidence_in_unit_range(self):
        data, depths = _synthetic_traces()
        picks = pick_first_breaks(data, depths, sample_rate_hz=2000.0)
        for p in picks:
            assert 0.0 <= p.confidence <= 1.0

    def test_noise_only_trace_not_picked(self):
        rng = np.random.default_rng(seed=0)
        noise = rng.normal(scale=0.02, size=(1, 2000))
        picks = pick_first_breaks(noise, [5.0], sample_rate_hz=2000.0)
        assert len(picks) == 0

    def test_shape_validation(self):
        with pytest.raises(ValueError, match="2-D"):
            pick_first_breaks(np.zeros(10), [1.0], sample_rate_hz=2000.0)

    def test_depth_count_mismatch(self):
        with pytest.raises(ValueError, match="length"):
            pick_first_breaks(np.zeros((3, 10)), [1.0], sample_rate_hz=2000.0)

    def test_zero_sample_rate(self):
        with pytest.raises(ValueError):
            pick_first_breaks(np.zeros((1, 10)), [1.0], sample_rate_hz=0.0)

    def test_custom_windows(self):
        data, depths = _synthetic_traces()
        picks = pick_first_breaks(
            data, depths, sample_rate_hz=2000.0,
            sta_window_ms=1.0, lta_window_ms=10.0, threshold=5.0,
        )
        assert len(picks) == len(depths)


# ---------------------------------------------------------------------------
# Interval velocity helpers
# ---------------------------------------------------------------------------


class TestIntervalVelocity:
    def _pair(self, z_a: float, t_a: float, z_b: float, t_b: float):
        return (
            FirstBreakPick(
                trace_index=0, depth_m=z_a, time_ms=t_a, sample_index=0,
                confidence=1.0,
            ),
            FirstBreakPick(
                trace_index=1, depth_m=z_b, time_ms=t_b, sample_index=1,
                confidence=1.0,
            ),
        )

    def test_true_interval_200(self):
        # 2 m separation, 10 ms apart → 200 m/s
        a, b = self._pair(2.0, 10.0, 4.0, 20.0)
        assert true_interval_velocity(a, b) == pytest.approx(200.0)

    def test_true_interval_zero_when_degenerate(self):
        a, b = self._pair(4.0, 20.0, 4.0, 20.0)
        assert true_interval_velocity(a, b) == 0.0

    def test_pseudo_interval_vertical_source(self):
        # Vertical source (offset 0) collapses pseudo to true V
        a, b = self._pair(2.0, 10.0, 4.0, 20.0)
        v = pseudo_interval_velocity(a, b, source_offset_x_m=0.0)
        assert v == pytest.approx(200.0)

    def test_pseudo_interval_slant_source_small_correction(self):
        a, b = self._pair(10.0, 50.0, 20.0, 100.0)
        v_slant = pseudo_interval_velocity(a, b, source_offset_x_m=2.0)
        v_vertical = pseudo_interval_velocity(a, b, source_offset_x_m=0.0)
        # Slant path ΔR between adjacent receivers is marginally less
        # than vertical Δz (Pythagoras), so apparent V is slightly lower
        assert v_slant < v_vertical
        assert abs(v_slant - v_vertical) / v_vertical < 0.02

    def test_pseudo_degenerate_returns_zero(self):
        a, b = self._pair(5.0, 50.0, 5.0, 50.0)
        assert pseudo_interval_velocity(a, b) == 0.0

    def test_pseudo_rejects_reversed_pair(self):
        a, b = self._pair(4.0, 20.0, 2.0, 10.0)
        assert pseudo_interval_velocity(a, b) == 0.0
