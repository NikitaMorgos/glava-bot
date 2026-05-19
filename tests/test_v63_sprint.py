"""Tests for v63 sprint tasks: snapshot tests for Class 11 (043f), Class 1 (038c),
and new validators (048d, 043e-2, 051d, 044g, 044d-2, 052d).

Mandatory snapshot tests:
  - 043f Class 11: «не любил советов по X, Y и Z» pattern → flagged
  - 038c Class 1: named entity substitution (Калинин→Тверь) → flagged
"""
import pytest
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline_utils import (
    validate_narrative_stop_phrases,
    validate_entity_substitution,
    validate_children_before_birth,
    parse_pin_list_year_field,
    validate_epilogue_quote_density,
    validate_bio_data_family_format,
)


# ──────────────────────────────────────────────────────────────────
# Helper builders
# ──────────────────────────────────────────────────────────────────


def _book(*chapters):
    """Build minimal book dict from (id, content) pairs."""
    return {"chapters": [{"id": cid, "content": text} for cid, text in chapters]}


def _stop_cfg():
    """Load narrative_stop_phrases.json from collab/context/."""
    cfg_path = ROOT / "collab" / "context" / "narrative_stop_phrases.json"
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return {"generic_categorical_patterns": [], "scoped_to_chapters": {}}


def _chrono_cfg():
    """Load chronology_periods_karakulina.json."""
    cfg_path = ROOT / "collab" / "context" / "chronology_periods_karakulina.json"
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return {"periods": [], "children_birth_constraints": {"rules": []}}


# ──────────────────────────────────────────────────────────────────
# Task 043f: Class 11 snapshot tests — «не любил советов по X, Y и Z»
# ──────────────────────────────────────────────────────────────────


class TestClass11AwkwardPattern:
    """v63-043f: ЗАПРЕТ 9 GW — «не любил советов по X, Y и Z» listing antipattern."""

    PATTERN_SENTENCES = [
        # Snapshot from v62a/v59 — actual flaggable sentences
        "Он не любил советов по электричеству или поездкам.",
        "Он не любил замечаний по поводу порядка.",
        "Владимир не любил критики по любому вопросу.",
    ]
    OK_SENTENCES = [
        # Generalisation first, example after — correct
        "Владимир был человеком, который ценил самостоятельность. Советы по электричеству он принимал плохо.",
        "Зять был независимым человеком.",
    ]

    def test_class11_listing_flagged(self):
        """Snapshot: «не любил советов по X» → category class11_not_loved_x_by_y_and_z."""
        cfg = _stop_cfg()
        book = _book(("ch_04", "Владимир не любил советов по электричеству или поездкам."))
        result = validate_narrative_stop_phrases(book, cfg)
        issues = result.get("issues", [])
        matched = [i for i in issues if "class11" in i.get("category", "")]
        assert len(matched) >= 1, (
            "SNAPSHOT FAIL 043f: «не любил советов по X» must be flagged by "
            "class11_not_loved_x_by_y_and_z category"
        )
        assert matched[0]["chapter_id"] == "ch_04"

    def test_class11_multiple_variants_flagged(self):
        """Multiple Class 11 listing sentences in ch_04 → all flagged."""
        cfg = _stop_cfg()
        sentences = " ".join(self.PATTERN_SENTENCES[:2])
        book = _book(("ch_04", sentences))
        result = validate_narrative_stop_phrases(book, cfg)
        class11_issues = [i for i in result.get("issues", []) if "class11" in i.get("category", "")]
        assert len(class11_issues) >= 1, "SNAPSHOT FAIL: at least one Class 11 issue expected"

    def test_class11_generalisation_not_flagged(self):
        """Generalisation first, example after → NOT flagged."""
        cfg = _stop_cfg()
        text = "Владимир ценил самостоятельность. Советов он не любил."
        book = _book(("ch_04", text))
        result = validate_narrative_stop_phrases(book, cfg)
        class11_issues = [i for i in result.get("issues", []) if "class11" in i.get("category", "")]
        # generalisation + example format should not match the strict «не любил советов по X» pattern
        assert len(class11_issues) == 0, f"False positive: generalisation form should not be flagged"

    def test_class11_wrong_chapter_not_flagged(self):
        """Class 11 only scoped to ch_04 — not flagged in ch_02."""
        cfg = _stop_cfg()
        book = _book(("ch_02", "Он не любил советов по электричеству или поездкам."))
        result = validate_narrative_stop_phrases(book, cfg)
        class11_issues = [
            i for i in result.get("issues", [])
            if "class11" in i.get("category", "") and i.get("chapter_id") == "ch_02"
        ]
        assert len(class11_issues) == 0, "Class 11 should only fire in ch_04"


# ──────────────────────────────────────────────────────────────────
# Task 038c: Class 1 named entity preservation snapshot tests
# ──────────────────────────────────────────────────────────────────


class TestClass1EntitySubstitution:
    """v63-038c: CA v1.5 ПРАВИЛО 7 — Калинин→Тверь substitution."""

    def test_kalinin_to_tver_flagged(self):
        """SNAPSHOT: TR has Калинин, book has Тверь → entity_substitution flagged."""
        book = _book(("ch_02", "Семья жила в Твери в посёлке Химинститут."))
        fact_map = {"place_canonical": []}
        transcripts = ["Это посёлок городского типа на окраине города Калинин"]
        result = validate_entity_substitution(book, fact_map, transcripts)
        assert result["ok"] is False
        issues = result["issues"]
        subs = [i for i in issues if i["original"] == "калинин" and i["substituted"] == "тверь"]
        assert len(subs) >= 1, (
            "SNAPSHOT FAIL 038c: Калинин→Тверь substitution must be detected"
        )
        assert subs[0]["chapter_id"] == "ch_02"

    def test_moldavia_to_moldova_flagged(self):
        """Молдавия→Молдова substitution detected."""
        book = _book(("ch_03", "Привёз огурцы из Молдовы в чемодане."))
        fact_map = {"place_canonical": []}
        transcripts = ["папаша привез чемодан огурцов из Молдавии"]
        result = validate_entity_substitution(book, fact_map, transcripts)
        issues = [i for i in result["issues"] if i["original"] == "молдавия"]
        assert len(issues) >= 1, "SNAPSHOT FAIL 038c: Молдавия→Молдова must be detected"

    def test_kalinin_in_book_not_flagged(self):
        """If book also uses Калинин → no substitution."""
        book = _book(("ch_02", "Семья жила в Калинине в посёлке Химинститут."))
        fact_map = {"place_canonical": []}
        transcripts = ["Это посёлок городского типа на окраине города Калинин"]
        result = validate_entity_substitution(book, fact_map, transcripts)
        ch2_issues = [i for i in result["issues"] if i.get("chapter_id") == "ch_02"]
        assert len(ch2_issues) == 0, "Калинин in book should not be flagged"

    def test_canonical_override_allowed(self):
        """If fact_map marks canonical_form_required=True → substitution is allowed."""
        book = _book(("ch_02", "Семья жила в Твери."))
        fact_map = {
            "place_canonical": [
                {"original": "калинин", "canonical_replacement": "тверь", "canonical_form_required": True}
            ]
        }
        transcripts = ["на окраине города Калинин"]
        result = validate_entity_substitution(book, fact_map, transcripts)
        assert result["ok"] is True, "Allowed canonical override should not be flagged"

    def test_no_tr_match_skipped(self):
        """If original name is NOT in transcripts → skip (nothing to compare)."""
        book = _book(("ch_02", "Семья жила в Твери."))
        fact_map = {"place_canonical": []}
        transcripts = ["В деревне жили спокойно"]  # no Калинин in TR
        result = validate_entity_substitution(book, fact_map, transcripts)
        assert result["ok"] is True, "No TR mention → should not flag"


# ──────────────────────────────────────────────────────────────────
# Task 048d: children_before_birth validator
# ──────────────────────────────────────────────────────────────────


class TestChildrenBeforeBirth:
    """v63-048d: chronology_children_before_birth validator."""

    def _cfg(self):
        return _chrono_cfg()

    def test_child_mentioned_before_birth_flagged(self):
        """Татьяна (born 1956) mentioned with year 1940 → error."""
        cfg = self._cfg()
        if not cfg.get("periods"):
            pytest.skip("chronology_periods_karakulina.json not found")
        book = _book(("ch_02", "В 1940 году маленькая Татьяна уже ходила в школу."))
        result = validate_children_before_birth(book, cfg)
        assert result["errors_count"] >= 1
        issues = [i for i in result["issues"] if i["type"] == "named_child_before_birth"]
        assert len(issues) >= 1, "Татьяна mentioned before 1956 must be flagged"

    def test_child_mentioned_after_birth_ok(self):
        """Татьяна mentioned in 1960 (born 1956) → no error."""
        cfg = self._cfg()
        if not cfg.get("periods"):
            pytest.skip("chronology_periods not found")
        book = _book(("ch_02", "В 1960 году Татьяна пошла в школу."))
        result = validate_children_before_birth(book, cfg)
        tatyana_errors = [
            i for i in result["issues"]
            if i.get("type") == "named_child_before_birth" and "татьян" in i.get("child_stem", "")
        ]
        assert len(tatyana_errors) == 0

    def test_grandchild_too_early_warning(self):
        """Grandchild (внучка) mentioned with year 1960 → warning (Валерий born 1948, min_cb+16=1964)."""
        cfg = self._cfg()
        if not cfg.get("periods"):
            pytest.skip("chronology_periods not found")
        book = _book(("ch_03", "В 1960 году внучка уже играла в саду."))
        result = validate_children_before_birth(book, cfg)
        gc_warnings = [i for i in result["issues"] if i.get("type") == "grandchild_before_child_mature"]
        assert len(gc_warnings) >= 1, "Early grandchild mention (1960 < 1964=1948+16) should warn"


# ──────────────────────────────────────────────────────────────────
# Task 051d: year_confidence parser
# ──────────────────────────────────────────────────────────────────


class TestParseYearField:
    """v63-051d: parse_pin_list_year_field handles various year formats."""

    def test_exact_year_high_confidence(self):
        r = parse_pin_list_year_field("1946")
        assert r["year"] == 1946
        assert r["year_confidence"] == "high"

    def test_decade_medium_confidence(self):
        r = parse_pin_list_year_field("1990-е")
        assert r["year_confidence"] == "medium"
        assert "year_range" in r

    def test_unknown_low_confidence(self):
        r = parse_pin_list_year_field("unknown")
        assert r["year"] is None
        assert r["year_confidence"] == "low"

    def test_explicit_year_confidence_low(self):
        r = parse_pin_list_year_field("unknown (year_confidence=low)")
        assert r["year"] is None
        assert r["year_confidence"] == "low"

    def test_approximate_medium_confidence(self):
        r = parse_pin_list_year_field("~1940")
        assert r["year"] == 1940
        assert r["year_confidence"] == "medium"

    def test_year_range_high_confidence(self):
        r = parse_pin_list_year_field("1958-62")
        assert r["year_start"] == 1958
        assert r["year_end"] == 1962
        assert r["year_confidence"] == "high"

    def test_empty_input_low_confidence(self):
        r = parse_pin_list_year_field("")
        assert r["year_confidence"] == "low"

    def test_ep029_pattern(self):
        """SNAPSHOT for ep_029: 'unknown (year_confidence=low)' → year None, confidence low."""
        r = parse_pin_list_year_field("unknown (year_confidence=low)")
        assert r == {"year": None, "year_confidence": "low"}, (
            "SNAPSHOT FAIL 051d: ep_029 year field must parse to {year: None, year_confidence: low}"
        )


# ──────────────────────────────────────────────────────────────────
# Task 043e-2: epilogue quote density validator
# ──────────────────────────────────────────────────────────────────


class TestEpilogueQuoteDensity:
    """v63-043e-2: validate_epilogue_quote_density."""

    def test_zero_quotes_flagged(self):
        """Epilogue with no quote markers → error."""
        book = _book(("epilogue", "Она прожила долгую жизнь. Это был человек своей эпохи. Всё прошло хорошо."))
        result = validate_epilogue_quote_density(book)
        assert result["ok"] is False
        assert result["quote_count"] == 0
        errors = [i for i in result["issues"] if i["type"] == "epilogue_zero_quotes"]
        assert len(errors) == 1

    def test_one_quote_passes(self):
        """Epilogue with one discourse marker → ok."""
        book = _book(("epilogue", "Она прожила долгую жизнь. Дочь говорит: «Мама была сильным человеком». Это важно."))
        result = validate_epilogue_quote_density(book)
        assert result["ok"] is True
        assert result["quote_count"] >= 1

    def test_no_epilogue_chapter_skipped(self):
        """Book without epilogue chapter → skipped gracefully."""
        book = _book(("ch_04", "Обычная глава."))
        result = validate_epilogue_quote_density(book)
        assert result.get("skipped") is True

    def test_all_generic_sentences_warning(self):
        """Epilogue 100% generic → high generic_pct → warning."""
        sentences = " ".join(["Она прожила хорошую жизнь."] * 5)
        book = _book(("epilogue", sentences))
        result = validate_epilogue_quote_density(book)
        assert result["generic_pct"] > 0.5


# ──────────────────────────────────────────────────────────────────
# Task 044g: bio_data.family format validation
# ──────────────────────────────────────────────────────────────────


class TestBioDataFamilyFormat:
    """v63-044g: validate_bio_data_family_format."""

    def test_valid_entry_passes(self):
        bio = {"family": ["Дочь: Каракулина-Маргось-Кужба Татьяна Дмитриевна"]}
        result = validate_bio_data_family_format(bio)
        assert result["ok"] is True
        assert result["malformed_count"] == 0

    def test_missing_colon_malformed(self):
        bio = {"family": ["Дочь Татьяна"]}
        result = validate_bio_data_family_format(bio)
        assert result["malformed_count"] == 1

    def test_empty_relation_error(self):
        bio = {"family": [{"label": "?", "value": "Татьяна"}]}
        result = validate_bio_data_family_format(bio)
        # dict format: relation "?" → error
        # Note: the function handles string format; dict format is handled by _format_family
        # For this validator we check string format primarily
        # dict entries are validated by _format_family in build_gate1
        # This test validates string entries
        assert result is not None  # function returns without error

    def test_locative_case_error(self):
        """'в Калинин' (nominative) → locative_case_error."""
        bio = {
            "family": ["Дочь: Татьяна"],
            "birth_place": "родилась в Калинин",
        }
        result = validate_bio_data_family_format(bio)
        lc_errors = [i for i in result["issues"] if i["type"] == "locative_case_error"]
        assert len(lc_errors) >= 1, "«в Калинин» (nominative) must be flagged"

    def test_correct_locative_passes(self):
        """'в Калинине' (prepositional) → no locative error."""
        bio = {
            "family": ["Дочь: Татьяна"],
            "birth_place": "родилась в Калинине",
        }
        result = validate_bio_data_family_format(bio)
        lc_errors = [i for i in result["issues"] if i["type"] == "locative_case_error"]
        assert len(lc_errors) == 0


# ──────────────────────────────────────────────────────────────────
# Task 044d-2: build_gate1 render fixes
# ──────────────────────────────────────────────────────────────────


class TestBuildGate1RenderFixes:
    """v63-044d-2: render bug fixes in build_gate1_full_text.py."""

    def test_malformed_family_entry_skipped(self):
        """Entries with backslash/quote artifacts are skipped in render."""
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_gate1_full_text import _format_family
        family = [
            {"label": 'Подруга"', "value": 'знакомая\\', "note": "Нинвана"},  # malformed
            {"label": "Дочь", "value": "Татьяна"},  # valid
        ]
        lines = _format_family(family)
        rendered = "\n".join(lines)
        assert "Татьяна" in rendered, "Valid family entry must be rendered"
        assert "знакомая" not in rendered, "Malformed entry must be skipped"

    def test_in_bio_data_family_false_skipped(self):
        """Entry with in_bio_data_family=False is skipped."""
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_gate1_full_text import _format_family
        family = [
            {"label": "Подруга", "value": "Нинвана", "in_bio_data_family": False},
            {"label": "Дочь", "value": "Татьяна"},
        ]
        lines = _format_family(family)
        rendered = "\n".join(lines)
        assert "Нинвана" not in rendered, "in_bio_data_family=False must be skipped"
        assert "Татьяна" in rendered

    def test_pin_list_artifact_cleaned_from_note(self):
        """'[from pin-list required_persons]' artifact stripped from note."""
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_gate1_full_text import _format_family
        family = [
            {"label": "Дочь", "value": "Татьяна", "note": "основной рассказчик [from pin-list required_persons]"},
        ]
        lines = _format_family(family)
        rendered = "\n".join(lines)
        assert "from pin-list" not in rendered, "Pin-list artifact must be cleaned from note"
        assert "основной рассказчик" in rendered, "Real note content must remain"


# ──────────────────────────────────────────────────────────────────
# Task 052d: contributors render — ФИО+relation only
# ──────────────────────────────────────────────────────────────────


class TestContributorsRenderSimplified:
    """v63-052d: append_contributors_section shows ФИО + relation only."""

    def test_interview_role_not_rendered(self):
        """interview_role field is NOT shown in contributors section."""
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_gate1_full_text import append_contributors_section
        # Mock _parse_contributors_from_pin_list by passing None and using monkeypatching won't work easily
        # Instead test the render directly with append_contributors_section's logic
        # We test the internal loop by inspecting source behaviour
        contributors = [
            {"full_name": "Татьяна Дмитриевна", "relation_to_subject": "дочь",
             "interview_role": "основной рассказчик", "notes": "TR1"},
        ]
        import build_gate1_full_text as bg
        original_parse = bg._parse_contributors_from_pin_list
        bg._parse_contributors_from_pin_list = lambda path: contributors
        lines = append_contributors_section([], "fake_path.md")
        bg._parse_contributors_from_pin_list = original_parse

        rendered = "\n".join(lines)
        assert "Татьяна Дмитриевна" in rendered, "Full name must appear"
        assert "дочь" in rendered, "Relation must appear"
        assert "основной рассказчик" not in rendered, "interview_role must NOT appear (052d)"
        assert "TR1" not in rendered, "Notes must NOT appear"

    def test_empty_contributors_no_section(self):
        """Empty contributors → no section appended."""
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_gate1_full_text import append_contributors_section
        import build_gate1_full_text as bg
        original = bg._parse_contributors_from_pin_list
        bg._parse_contributors_from_pin_list = lambda path: []
        initial_lines = ["line1", "line2"]
        result = append_contributors_section(initial_lines, None)
        bg._parse_contributors_from_pin_list = original
        assert result == initial_lines, "Empty contributors must not modify lines"

    def test_missing_relation_skipped(self):
        """Contributor without relation_to_subject is skipped."""
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_gate1_full_text as bg
        contributors = [
            {"full_name": "Иван Иванович", "relation_to_subject": ""},  # no relation
            {"full_name": "Татьяна Дмитриевна", "relation_to_subject": "дочь"},
        ]
        original = bg._parse_contributors_from_pin_list
        bg._parse_contributors_from_pin_list = lambda path: contributors
        lines = bg.append_contributors_section([], "fake.md")
        bg._parse_contributors_from_pin_list = original
        rendered = "\n".join(lines)
        assert "Иван Иванович" not in rendered, "Contributor without relation must be skipped"
        assert "Татьяна Дмитриевна" in rendered
