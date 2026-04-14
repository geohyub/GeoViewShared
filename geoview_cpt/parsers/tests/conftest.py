"""
Synthetic CPeT-IT .cpt fixture factory + real-JACO sample discovery.

The JACO samples (``H:/자코/...``) are ~6.5 MB each and live on an
external drive, so tests that need them are gated behind
:data:`JACO_AVAILABLE`. Everything else uses a tiny synthetic .cpt file
built from a hand-crafted XML template and zlib-compressed on the fly —
fast, deterministic, and small enough to run in CI containers that don't
have H: mounted.
"""
from __future__ import annotations

import os
import zlib
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Real JACO sample discovery (optional)
# ---------------------------------------------------------------------------


JACO_CANDIDATES = [
    Path(r"H:/자코/JAKO_Korea_area/CPet-iT_데이터입력/JACO_Korea_area_all.cpt"),
    Path(r"H:/자코/JAKO_Korea_area/분석결과_1st/JACO_Korea_area_all_1st.cpt"),
]


def _find_jaco_samples() -> list[Path]:
    return [p for p in JACO_CANDIDATES if p.exists()]


JACO_SAMPLES = _find_jaco_samples()
JACO_AVAILABLE = bool(JACO_SAMPLES)


jaco_required = pytest.mark.skipif(
    not JACO_AVAILABLE,
    reason="JACO samples not mounted (H: drive)",
)


@pytest.fixture(scope="session")
def jaco_all_path() -> Path:
    if not JACO_AVAILABLE:
        pytest.skip("JACO samples not mounted")
    return JACO_SAMPLES[0]


@pytest.fixture(scope="session")
def jaco_paths() -> list[Path]:
    if not JACO_AVAILABLE:
        pytest.skip("JACO samples not mounted")
    return list(JACO_SAMPLES)


# ---------------------------------------------------------------------------
# Synthetic sample
# ---------------------------------------------------------------------------


_SYNTH_XML = """\
<?xml version="1.0" encoding="UTF-8"?><CPT Version="30"><Various>\
<Handle>12345</Handle>\
<Project>Synth Project</Project>\
<ProjectID>PRJ-001</ProjectID>\
<Location>Test Bay</Location>\
<Comments>unit test</Comments>\
<First>Geoview</First>\
<Second>Marine Research Geotechnical Engineers</Second>\
<Third>Busan, South Korea</Third>\
<Forth>http://www.geoview.co.kr</Forth>\
<Path>D:\\fake\\geoview_logo.png</Path>\
<Unit_System>0</Unit_System>\
<Vertical_Plot>0</Vertical_Plot>\
<DisplayImage>true</DisplayImage>\
<FontName>Arial Narrow</FontName>\
<FontSize>7</FontSize>\
<CustomSBTnDesc>A;B;C;D;;;;;;</CustomSBTnDesc>\
</Various>\
<CPTFiles>\
<100>BLOB_BASE64_ONE\
<Handle>100</Handle>\
<CPTName>CPT-Alpha</CPTName>\
<CPTFileName>alpha.raw</CPTFileName>\
<InputCount>1000</InputCount>\
<OutputCount>1000</OutputCount>\
<MaxDepth>25.4</MaxDepth>\
<UnitSystem>0</UnitSystem>\
<ConeCorrected>true</ConeCorrected>\
<CPTProperties>\
<DepthInterval>2</DepthInterval>\
<Elevation>-30.5</Elevation>\
<GWT>0</GWT>\
<Alpha>.69</Alpha>\
<Nkt>16</Nkt>\
<Kocr>.33</Kocr>\
<WaterWeight>9.81</WaterWeight>\
<AutoGamma>true</AutoGamma>\
<DefaultGamma>19.5</DefaultGamma>\
</CPTProperties>\
<ChartPropertiesLeft><1><Auto>true</Auto><Min>0</Min><Max>50</Max></1></ChartPropertiesLeft>\
<ChartPropertiesBottom><1><Auto>true</Auto><Min>0</Min><Max>30</Max></1></ChartPropertiesBottom>\
<Samples/>\
<PileData>PILE_B64</PileData>\
</100>\
<200>BLOB_BASE64_TWO\
<Handle>200</Handle>\
<CPTName>CPT-Beta</CPTName>\
<CPTFileName></CPTFileName>\
<InputCount>2500</InputCount>\
<OutputCount>2500</OutputCount>\
<MaxDepth>40</MaxDepth>\
<UnitSystem>0</UnitSystem>\
<ConeCorrected>false</ConeCorrected>\
<CPTProperties>\
<Elevation>-55</Elevation>\
<GWT>0</GWT>\
<Nkt>14</Nkt>\
<Alpha>.72</Alpha>\
</CPTProperties>\
<ChartPropertiesLeft><1><Auto>false</Auto><Min>0</Min><Max>80</Max></1></ChartPropertiesLeft>\
<ChartPropertiesBottom><1><Auto>true</Auto></1></ChartPropertiesBottom>\
</200>\
</CPTFiles>\
<WebGMap><Zoom>13</Zoom></WebGMap>\
<OverlayProps/>\
</CPT>"""


def _build_synth_bytes() -> bytes:
    plain = _SYNTH_XML.encode("utf-8")
    return zlib.compress(plain, level=6)


@pytest.fixture
def synth_cpt_bytes() -> bytes:
    """Small valid CPeT-IT-shaped .cpt payload with 2 soundings."""
    return _build_synth_bytes()


@pytest.fixture
def synth_cpt_file(tmp_path, synth_cpt_bytes) -> Path:
    p = tmp_path / "synth.cpt"
    p.write_bytes(synth_cpt_bytes)
    return p


@pytest.fixture
def synth_xml_plain() -> bytes:
    return _SYNTH_XML.encode("utf-8")
