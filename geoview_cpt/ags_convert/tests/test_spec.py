"""Spec assets — A3.6 smoke."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


SPEC_DIR = Path(__file__).resolve().parents[1] / "spec"
DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"


class TestSpecPdf:
    def test_pdf_present(self):
        pdf = SPEC_DIR / "AGS4.1.pdf"
        assert pdf.exists(), f"missing spec PDF: {pdf}"

    def test_pdf_has_pdf_magic(self):
        pdf = SPEC_DIR / "AGS4.1.pdf"
        header = pdf.read_bytes()[:5]
        assert header == b"%PDF-"

    def test_pdf_size_reasonable(self):
        pdf = SPEC_DIR / "AGS4.1.pdf"
        assert pdf.stat().st_size > 1_000_000   # ~7 MB on download

    def test_pdf_sha256_matches_changelog(self):
        """
        CHANGELOG.md pins the SHA-256 — a refetch that produces a
        different hash should fail this test so we remember to
        bump the version history.
        """
        pdf = SPEC_DIR / "AGS4.1.pdf"
        expected = (
            "a91cf9d9ec5227130c736e2282eaff4f0944925d7a9a9ed8983e0762e5f80340"
        )
        actual = hashlib.sha256(pdf.read_bytes()).hexdigest()
        assert actual == expected, (
            f"PDF checksum drift — update CHANGELOG.md. expected={expected} "
            f"actual={actual}"
        )


class TestChangelog:
    def test_changelog_present(self):
        changelog = SPEC_DIR / "CHANGELOG.md"
        assert changelog.exists()

    def test_changelog_mentions_version(self):
        body = (SPEC_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "AGS4 v4.1" in body
        assert "a91cf9d9ec5227130c736e2282eaff4f0944925d7a9a9ed8983e0762e5f80340" in body


class TestRulesMatrix:
    def test_rules_matrix_present(self):
        rules = SPEC_DIR / "rules_1_20.md"
        assert rules.exists()

    def test_rules_has_20_entries(self):
        body = (SPEC_DIR / "rules_1_20.md").read_text(encoding="utf-8")
        # Count Rule 1..20 mentions in the table
        for n in range(1, 21):
            assert f"| {n} |" in body or f"| {n}a |" in body or f"| {n}b |" in body

    def test_rule_10_has_abcd_variants(self):
        body = (SPEC_DIR / "rules_1_20.md").read_text(encoding="utf-8")
        assert "10a" in body
        assert "10b" in body
        assert "10c" in body


class TestJakoMissingFieldsDoc:
    def test_document_present(self):
        doc = DOCS_DIR / "a3_jako_missing_fields.md"
        assert doc.exists(), f"missing JAKO audit doc: {doc}"

    def test_document_lists_core_groups(self):
        body = (DOCS_DIR / "a3_jako_missing_fields.md").read_text(encoding="utf-8")
        for g in ("PROJ", "LOCA", "SCPG", "SCPT", "SCPP"):
            assert f"## {g}" in body

    def test_document_calls_out_proj_id_gap(self):
        body = (DOCS_DIR / "a3_jako_missing_fields.md").read_text(encoding="utf-8")
        assert "PROJ_ID" in body
        assert "SCPG_CREW" in body
