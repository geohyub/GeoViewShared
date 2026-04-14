"""End-to-end read test — synthetic + real JACO (optional) — A2.0 Step 2."""
from __future__ import annotations

import pytest

from geoview_cpt.parsers.cpet_it_v30 import read_cpt_v30, read_cpt_v30_bytes
from geoview_cpt.model import CPTProject, CPTSounding

from .conftest import jaco_required


# ---------------------------------------------------------------------------
# Synthetic sample — always runs
# ---------------------------------------------------------------------------


class TestSyntheticRead:
    def test_returns_cpt_project(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert isinstance(proj, CPTProject)

    def test_two_soundings_in_synth(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert len(proj) == 2
        assert all(isinstance(s, CPTSounding) for s in proj)

    def test_sounding_headers(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        alpha, beta = proj.soundings
        assert alpha.name == "CPT-Alpha"
        assert alpha.handle == 100
        assert alpha.element_tag == "100"
        assert alpha.file_name == "alpha.raw"
        assert alpha.input_count == 1000
        assert alpha.output_count == 1000
        assert alpha.max_depth_m == pytest.approx(25.4)
        assert alpha.unit_system == 0
        assert alpha.cone_corrected is True

        assert beta.name == "CPT-Beta"
        assert beta.handle == 200
        assert beta.cone_corrected is False

    def test_sounding_properties(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        alpha = proj.get_sounding("CPT-Alpha")
        assert alpha.properties["Nkt"] == "16"
        assert alpha.properties["Alpha"] == ".69"
        assert alpha.nkt == 16.0
        assert alpha.alpha == pytest.approx(0.69)
        assert alpha.elevation_m == pytest.approx(-30.5)
        assert alpha.gwt_m == 0.0
        assert alpha.depth_interval_m == 2.0

    def test_get_sounding_by_handle(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.get_sounding(100).name == "CPT-Alpha"
        assert proj.get_sounding(200).name == "CPT-Beta"

    def test_get_sounding_missing_raises(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        with pytest.raises(KeyError):
            proj.get_sounding("nope")

    def test_cptfiles_raw_decoded(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        # Both element tags should be present; text wasn't valid base64 but
        # the reader uses validate=False so we at least get a key entry.
        assert set(proj.cptfiles_raw.keys()) == {"100", "200"}


# ---------------------------------------------------------------------------
# Real JACO sample — only runs when H: is mounted
# ---------------------------------------------------------------------------


@jaco_required
class TestJacoSample:
    def test_reads_13_soundings(self, jaco_all_path):
        proj = read_cpt_v30(jaco_all_path)
        assert len(proj) == 13

    def test_jaco_branding(self, jaco_all_path):
        proj = read_cpt_v30(jaco_all_path)
        assert proj.partner_brand == "Geoview"
        assert proj.partner_description == "Marine Research Geotechnical Engineers"
        assert proj.partner_address == "Busan, South Korea"
        assert proj.partner_url == "http://www.geoview.co.kr"

    def test_jaco_project_name(self, jaco_all_path):
        proj = read_cpt_v30(jaco_all_path)
        assert "Jako" in proj.name

    def test_jaco_sounding_names(self, jaco_all_path):
        proj = read_cpt_v30(jaco_all_path)
        names = sorted(s.name for s in proj)
        # 13 JACO soundings include CPT-01 .. CPT-09 with extras
        assert len(names) == 13
        assert "CPT-01" in names
        assert any("CPT-09" in n for n in names)

    def test_jaco_nkt_values_extracted(self, jaco_all_path):
        proj = read_cpt_v30(jaco_all_path)
        nkts = [s.nkt for s in proj if s.nkt is not None]
        assert len(nkts) == 13
        # Typical JACO Nkt range
        for v in nkts:
            assert 5 <= v <= 30

    def test_jaco_chart_config_preserved(self, jaco_all_path):
        proj = read_cpt_v30(jaco_all_path)
        s = proj.soundings[0]
        assert "left" in s.chart_config_raw
        assert "bottom" in s.chart_config_raw
        assert len(s.chart_config_raw["left"]) > 100

    def test_jaco_blob_bytes_nonempty(self, jaco_all_path):
        proj = read_cpt_v30(jaco_all_path)
        # Every sounding carries a nonempty base64 blob
        for s in proj:
            assert len(s.blob_b64) > 100

    def test_jaco_both_variants_readable(self, jaco_paths):
        for p in jaco_paths:
            proj = read_cpt_v30(p)
            assert len(proj) == 13
            assert proj.partner_brand == "Geoview"
