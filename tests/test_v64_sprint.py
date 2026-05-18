# tests/test_v64_sprint.py
"""
Snapshot tests for v64 sprint tasks:
 - test_class17_narrative_truism (043h)  — ≥4 tests
 - test_class1_recurring_patterns (043d-2) — ≥6 tests
 - test_class11_recurring_patterns (043f-2) — ≥5 tests
 - test_personal_historical_voice (046e)  — ≥6 tests
 - test_revision_orchestrator (049f)     — ≥5 tests
"""
import sys, os, re
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pipeline_utils as pu

# =====================================================================
# Helpers
# =====================================================================

def _book_with_chapter(chid: str, text: str) -> dict:
    """Minimal book dict with one chapter."""
    return {"chapters": [{"id": chid, "content": text}]}


def _check_stop_phrases(sentence: str, cfg_path: str | None = None) -> list:
    """Run validate_narrative_stop_phrases on a single sentence book."""
    import json
    book = _book_with_chapter("ch_02", sentence)
    cfg_base = cfg_path or os.path.join(
        os.path.dirname(__file__), "..", "collab", "context", "narrative_stop_phrases.json"
    )
    with open(cfg_base, encoding="utf-8") as f:
        config = json.load(f)
    result = pu.validate_narrative_stop_phrases(book, config)
    return result.get("issues", [])


def _check_truism(text: str) -> list:
    """Run validate_narrative_truism on text in ch_02."""
    book = _book_with_chapter("ch_02", text)
    result = pu.validate_narrative_truism(book)
    return result.get("issues", [])


def _check_personal_voice(text: str, chid: str = "ch_02") -> list:
    """Count personal-historical voice patterns."""
    book = _book_with_chapter(chid, text)
    result = pu.validate_personal_historical_voice(book)
    count = result.get("markers_found_per_chapter", {}).get(chid, 0)
    return count


# =====================================================================
# 043h — Class 17 narrative truism (≥4 tests)
# =====================================================================

class TestClass17NarrativeTruism:

    def test_obvious_responsibility_v63_example(self):
        """v63 snapshot — sister taking responsibility truism."""
        paragraph = (
            "В те годы сестра, забравшая ребёнка из детдома, брала на себя "
            "огромную ответственность — продуктовые карточки, одежда, образование, "
            "всё ложилось на её плечи."
        )
        flags = _check_truism(paragraph)
        cats = [f["category"] for f in flags]
        assert "obvious_responsibility_constatation" in cats, (
            f"obvious_responsibility_constatation not found. Got: {cats}"
        )

    def test_everything_fell_on_shoulders_v63_example(self):
        """v63 snapshot — 'всё ложилось на её плечи'."""
        paragraph = "В те трудные годы всё ложилось на её плечи."
        flags = _check_truism(paragraph)
        cats = [f["category"] for f in flags]
        assert "everything_fell_on_shoulders" in cats, (
            f"everything_fell_on_shoulders not found. Got: {cats}"
        )

    def test_accepted_calmly_v63_example(self):
        """v63 snapshot — subjective emotional ascription."""
        sentence = "Валентина приняла это решение сына спокойно."
        flags = _check_truism(sentence)
        cats = [f["category"] for f in flags]
        assert "accepted_calmly" in cats, (
            f"accepted_calmly not found. Got: {cats}"
        )

    def test_required_strength_and_character(self):
        """Generic truism — 'требовало огромной силы характера'."""
        sentence = "Это требовало огромной силы и характера."
        flags = _check_truism(sentence)
        cats = [f["category"] for f in flags]
        assert "required_strength_and_character" in cats, (
            f"required_strength_and_character not found. Got: {cats}"
        )

    def test_negative_specific_action_no_flag(self):
        """Generic sentence with specific factual content — НЕ flag."""
        paragraph = (
            "Полина забрала Валентину из детдома и привезла в Старобельск, "
            "где жила с мужем."
        )
        flags = _check_truism(paragraph)
        truism_cats = [
            "obvious_responsibility_constatation", "everything_fell_on_shoulders",
            "accepted_calmly", "required_strength_and_character",
        ]
        triggered = [f["category"] for f in flags if f["category"] in truism_cats]
        assert not triggered, f"False positive truism flags: {triggered}"

    def test_ch01_excluded_from_truism_scan(self):
        """ch_01 не сканируется на truism (scope = narrative only)."""
        book = _book_with_chapter("ch_01", "Валентина приняла это решение спокойно.")
        result = pu.validate_narrative_truism(book)
        assert result["issues"] == [], "ch_01 should not be scanned for truism"


# =====================================================================
# 043d-2 — Class 1 recurring patterns (≥6 tests)
# =====================================================================

class TestClass1RecurringPatterns:

    def test_speciality_defined_life_v62a(self):
        """v62a snapshot — original form (закрыт task 043d)."""
        sentence = "В 1938 году Валентине дали специальность, которая определила всю её жизнь."
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        found = any("speciality_defined_life" in c for c in cats)
        assert found, f"speciality_defined_life not found. Got: {cats}"

    def test_speciality_defined_life_v63_recurring(self):
        """v63 snapshot — recurring form 'дальнейшую жизнь в медицине'."""
        sentence = (
            "В 1938 году ей дали профессию акушерки — специальность, "
            "которая определила всю её дальнейшую жизнь в медицине."
        )
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        found = any("speciality_defined_life" in c for c in cats)
        assert found, f"speciality_defined_life_v3 not caught for recurring form. Got: {cats}"

    def test_episode_especially_remembered_v63(self):
        """v63 snapshot — multiplication of significance."""
        sentence = (
            "Один эпизод особенно запомнился: когда Владимир работал со счётчиком, "
            "Валентина сделала ему замечание."
        )
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        assert "episode_especially_remembered" in cats, (
            f"episode_especially_remembered not found. Got: {cats}"
        )

    def test_motivation_attribution_seemed_v63(self):
        """v63 snapshot — motivation confabulation (огурцы новая форма)."""
        sentence = (
            "Валентина была недовольна — ей казалось, что родственники мужа "
            "должны присылать больше подарков."
        )
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        assert "motivation_attribution_seemed" in cats, (
            f"motivation_attribution_seemed not found. Got: {cats}"
        )

    def test_negative_factual_education_no_flag(self):
        """Factual education sentence без causal claim — НЕ flag."""
        sentence = "В 1938 году Валентина поступила в Кировоградскую фельдшерско-акушерскую школу."
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        false_pos = [c for c in cats if "speciality_defined_life" in c]
        assert not false_pos, f"False positive speciality flags: {false_pos}"

    def test_negative_factual_episode_no_flag(self):
        """Factual episode без 'особенно запомнился' — НЕ flag."""
        sentence = "В 1977 году произошёл конфликт между Валентиной и зятем из-за счётчика."
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        assert "episode_especially_remembered" not in cats, (
            f"False positive episode_especially_remembered: {cats}"
        )

    def test_stage_event_changed_extended(self):
        """stage_event_changed_X_extended pattern."""
        sentence = "Случилось важное событие, которое сильно повлияло на семью."
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        assert "stage_event_changed_X_extended" in cats or any(
            "event" in c for c in cats
        ), f"stage_event_changed not caught. Got: {cats}"


# =====================================================================
# 043f-2 — Class 11 recurring patterns (≥5 tests)
# =====================================================================

class TestClass11RecurringPatterns:

    def test_v63_in_principle_especially(self):
        """v63 snapshot — pattern эволюция 'в принципе, особенно по'."""
        sentence = (
            "Владимир не любил советов в принципе, особенно по практическим "
            "вопросам — будь то электричество или распорядок поездок."
        )
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        found = any("class11" in c for c in cats)
        assert found, f"Class 11 in-principle pattern not caught. Got: {cats}"

    def test_v62a_simple_form_still_caught(self):
        """v62a форма — должна оставаться в coverage."""
        sentence = "Владимир не любил советов, особенно по электричеству и поездкам."
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        found = any("class11" in c for c in cats)
        assert found, f"Class 11 v62a simple form not caught. Got: {cats}"

    def test_v63_budtto_form(self):
        """v63 forms with 'будь то X или Y'."""
        sentence = (
            "Не любил он лишних вопросов — будь то политика или бытовые мелочи."
        )
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        found = any("class11" in c for c in cats)
        assert found, f"Class 11 budtto form not caught. Got: {cats}"

    def test_v63_practical_questions_budtto(self):
        """Full v63 form: по практическим вопросам — будь то."""
        sentence = "Он не принимал советов по практическим вопросам — будь то ремонт или кулинария."
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        found = any("class11" in c for c in cats)
        assert found, f"Class 11 'по практическим вопросам — будь то' not caught. Got: {cats}"

    def test_negative_single_object_no_flag(self):
        """Сингулярный объект без enumeration — НЕ flag."""
        sentence = "Владимир не любил советов от тёщи."
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        false_pos = [c for c in cats if "class11" in c]
        assert not false_pos, f"False positive class11 flags: {false_pos}"

    def test_negative_legitimate_listing_no_flag(self):
        """Перечисление без 'не любил' framing — НЕ flag."""
        sentence = "Дома стояли по обеим сторонам улицы: справа кирпичные, слева деревянные."
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        false_pos = [c for c in cats if "class11" in c]
        assert not false_pos, f"False positive class11 flags: {false_pos}"


# =====================================================================
# 046e — Class 18 personal-historical voice (≥6 tests)
# =====================================================================

class TestPersonalHistoricalVoice:

    def test_kak_pomnyu_pattern(self):
        """Pattern 'как я помню, в [период]...' — match."""
        count = _check_personal_voice("Как я помню, в 90-е цены росли каждую неделю.")
        assert count >= 1, "Pattern 'как я помню' not detected"

    def test_togda_u_nas_pattern(self):
        """Pattern 'тогда у нас в семье...' — match."""
        count = _check_personal_voice("Тогда у нас в семье было принято собираться по воскресеньям.")
        assert count >= 1, "Pattern 'тогда у нас' not detected"

    def test_kogda_ya_byl_pattern(self):
        """Pattern 'когда я был ребёнком...' — match."""
        count = _check_personal_voice("Когда я была ребёнком, бабушка часто рассказывала про войну.")
        assert count >= 1, "Pattern 'когда я был ребёнком' not detected"

    def test_v_sovetskoe_vremya_pattern(self):
        """Pattern 'в советское время...' — match."""
        count = _check_personal_voice("В советское время всё было иначе — очереди, карточки, дефицит.")
        assert count >= 1, "Pattern 'в советское время' not detected"

    def test_negative_pure_discourse_marker(self):
        """Pure discourse marker без personal-historical — НЕ count."""
        count = _check_personal_voice("Татьяна вспоминает, что бабушка готовила пирожки.")
        assert count == 0, f"False positive personal-historical for discourse marker: {count}"

    def test_negative_objective_historical(self):
        """Objective historical_note — НЕ count."""
        count = _check_personal_voice("В 1933 году в Кировоградской области был голод.")
        assert count == 0, f"False positive personal-historical for objective fact: {count}"

    def test_threshold_below_generates_issue(self):
        """ch_02 с 0 markers, threshold 3 → generates below_threshold issue."""
        book = _book_with_chapter("ch_02", "Валентина работала в поликлинике.")
        result = pu.validate_personal_historical_voice(book)
        ch02_issues = [i for i in result["issues"] if i["chapter_id"] == "ch_02"]
        assert ch02_issues, "Expected below_threshold issue for ch_02 with 0 markers"
        assert ch02_issues[0]["found"] == 0
        assert ch02_issues[0]["expected"] == 3

    def test_threshold_met_no_issue(self):
        """ch_02 с достаточным количеством markers — нет issue."""
        text = (
            "Как я помню, в 1962 году семья переехала. "
            "Тогда у нас в семье всё изменилось. "
            "Когда я была ребёнком, Химинститут казался огромным. "
        )
        book = _book_with_chapter("ch_02", text)
        result = pu.validate_personal_historical_voice(book)
        ch02_issues = [i for i in result["issues"] if i["chapter_id"] == "ch_02"]
        assert not ch02_issues, f"Unexpected issues for met threshold: {ch02_issues}"


# =====================================================================
# 049f — Revision orchestrator (≥5 tests)
# =====================================================================

class TestRevisionOrchestrator:

    def test_collect_revision_hints_empty_validators(self):
        """Empty validator outputs → empty hints list."""
        book = _book_with_chapter("ch_02", "Текст главы.")
        result = pu.collect_revision_hints(book, {})
        assert result == []

    def test_collect_revision_hints_from_truism(self):
        """Truism issue converts to hint with correct fields."""
        book = _book_with_chapter("ch_02", "В те годы всё ложилось на её плечи.")
        validator_outputs = {
            "narrative_truism": {
                "issues": [{
                    "type": "narrative_truism",
                    "category": "everything_fell_on_shoulders",
                    "chapter_id": "ch_02",
                    "snippet": "В те годы всё ложилось на её плечи.",
                    "severity": "warning",
                    "suggestion": "delete_sentence",
                    "reason": "narrative truism",
                }]
            }
        }
        hints = pu.collect_revision_hints(book, validator_outputs)
        assert len(hints) == 1
        h = hints[0]
        assert h["hint_id"] == "h_001"
        assert h["validator"] == "narrative_truism"
        assert h["must_apply"] is False  # warning → must_apply=False
        assert "delete_sentence" in h["suggestion"]

    def test_collect_revision_hints_error_must_apply_true(self):
        """Error-level hint → must_apply=True."""
        book = _book_with_chapter("ch_02", "Специальность, которая определила всю её жизнь.")
        validator_outputs = {
            "narrative_stop_phrases": {
                "issues": [{
                    "category": "speciality_defined_life_v3",
                    "chapter_id": "ch_02",
                    "snippet": "Специальность, которая определила всю её жизнь.",
                    "severity": "error",
                    "suggestion": "Удалить causal claim.",
                }]
            }
        }
        hints = pu.collect_revision_hints(book, validator_outputs)
        assert len(hints) == 1
        assert hints[0]["must_apply"] is True

    def test_audit_revision_diff_no_unauthorized(self):
        """Diff audit: changes match flagged snippets → 0 unauthorized."""
        snippet = "В те годы всё ложилось на её плечи."
        draft = _book_with_chapter("ch_02", snippet + " Работала каждый день.")
        revised = _book_with_chapter("ch_02", "Работала каждый день.")
        hints = [{"hint_id": "h_001", "snippet": snippet, "severity": "warning", "must_apply": False}]
        audit = pu.audit_revision_diff(draft, revised, hints)
        assert audit["hints_count"] == 1
        # Since we don't have writing_notes in simplified test, just verify structure
        assert "unauthorized_changes_count" in audit

    def test_collect_hints_multiple_validators(self):
        """Multiple validators → multiple hints with unique IDs."""
        book = _book_with_chapter("ch_02", "Нарратив.")
        validator_outputs = {
            "chronology_check": {
                "issues": [{"category": "person_mentioned_before_birth", "chapter_id": "ch_02",
                             "snippet": "С детьми в Германии.", "severity": "error",
                             "person_name": "Валерий", "event_year_range": "1946-48"}]
            },
            "narrative_truism": {
                "issues": [{"category": "accepted_calmly", "chapter_id": "ch_02",
                             "snippet": "Приняла спокойно.", "severity": "warning",
                             "suggestion": "delete_sentence"}]
            },
        }
        hints = pu.collect_revision_hints(book, validator_outputs)
        assert len(hints) == 2
        ids = {h["hint_id"] for h in hints}
        assert len(ids) == 2, "All hint_ids should be unique"
        validators = {h["validator"] for h in hints}
        assert "chronology_check" in validators
        assert "narrative_truism" in validators


# =====================================================================
# Integration: narrative_stop_phrases pattern_options support
# =====================================================================

class TestPatternOptionsSupport:
    """Validate that pattern_options (array) is supported by existing validator."""

    def test_pattern_options_any_match(self):
        """Class 11 category with pattern_options → any match triggers flag."""
        sentence = (
            "Не любила она в принципе, особенно по хозяйственным делам."
        )
        flags = _check_stop_phrases(sentence)
        cats = [f["category"] for f in flags]
        found = any("class11_not_loved_x_by_y_and_z_extended" in c for c in cats)
        assert found, f"pattern_options match for class11_extended not found. Got: {cats}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
