"""Tests for geoview_cpt.derivation.sbt — Phase A-2 A2.5b."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.derivation.sbt import (
    ROBERTSON_1990_ZONES,
    classify_ic_to_robertson_1990_zone,
    classify_robertson_1990,
)
from geoview_cpt.model import CPTChannel


class TestSingleClassifier:
    @pytest.mark.parametrize(
        "ic, expected_zone",
        [
            (1.0,  7),  # gravelly sand
            (1.30, 7),
            (1.31, 6),  # clean sand
            (2.04, 6),
            (2.05, 5),  # silty sand
            (2.59, 5),
            (2.60, 4),  # clayey silt
            (2.94, 4),
            (2.95, 3),  # clay
            (3.59, 3),
            (3.60, 2),  # organic clay
            (5.00, 2),
        ],
    )
    def test_zone_boundaries(self, ic, expected_zone):
        assert classify_ic_to_robertson_1990_zone(ic) == expected_zone

    def test_nan_yields_zero(self):
        assert classify_ic_to_robertson_1990_zone(float("nan")) == 0

    def test_inf_yields_zero(self):
        assert classify_ic_to_robertson_1990_zone(float("inf")) == 0


class TestVectorClassifier:
    def test_array(self):
        ic = CPTChannel(name="Ic", unit="-", values=[1.0, 2.0, 2.5, 3.0, 3.8])
        zones = classify_robertson_1990(ic)
        assert zones.values.tolist() == [7.0, 6.0, 5.0, 3.0, 2.0]
        assert zones.name == "SBT"

    def test_handles_nan(self):
        ic = CPTChannel(name="Ic", unit="-", values=[2.0, float("nan"), 3.0])
        zones = classify_robertson_1990(ic)
        assert zones.values[0] == 6.0
        assert zones.values[1] == 0.0
        assert zones.values[2] == 3.0


class TestZoneLabels:
    def test_all_nine_present(self):
        assert set(ROBERTSON_1990_ZONES.keys()) == set(range(1, 10))

    def test_zone_strings_nonempty(self):
        for label in ROBERTSON_1990_ZONES.values():
            assert label
