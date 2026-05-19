"""Tests for v65 tasks:
- 043f-3: Class 11 v64 snapshot
- 048e: chronology FP fix
- 048f: descendants in early context (Class 12 extend)
- 048g: cross-paragraph duplication (Class 19)
- 046f: historical notes distribution
- 044i: required episodes coverage
- 049e-2: rule13_revision_applied schema
- 049g: preserve_root_level_metadata
- 049f-2: orchestrator coverage
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import json


# ──────────────────────────────────────────────────────────────────
# 043f-3: Class 11 v64 snapshot
# ──────────────────────────────────────────────────────────────────

def test_class11_v64_especially_by_X_Y_other():
    """v64 snapshot — «— особенно по X, Y и другим Z»."""
    from pipeline_utils import validate_narrative_stop_phrases
    import json as _json
    cfg = _json.load(open("collab/context/narrative_stop_phrases.json", encoding="utf-8"))
    sentence = (
        "Владимир не любил советов — особенно по электричеству, поездкам "
        "и другим бытовым вопросам."
    )
    book = {"chapters": [{"id": "ch_02", "content": sentence}]}
    result = validate_narrative_stop_phrases(book, cfg)
    cats = [i.get("category") for i in result.get("issues", [])]
    assert any("class11_not_loved" in (c or "") for c in cats), (
        f"v64 Class 11 form not caught. Got: {cats}"
    )


def test_class11_v62a_still_caught():
    """v62a form still works with v7 config."""
    from pipeline_utils import validate_narrative_stop_phrases
    import json as _json
    cfg = _json.load(open("collab/context/narrative_stop_phrases.json", encoding="utf-8"))
    sentence = "Владимир не любил советов, особенно по электричеству и поездкам."
    book = {"chapters": [{"id": "ch_02", "content": sentence}]}
    result = validate_narrative_stop_phrases(book, cfg)
    cats = [i.get("category") for i in result.get("issues", [])]
    assert any("class11_not_loved" in (c or "") for c in cats)


def test_class11_v64_short_form():
    """v64 short form without 'в принципе'."""
    from pipeline_utils import validate_narrative_stop_phrases
    import json as _json
    cfg = _json.load(open("collab/context/narrative_stop_phrases.json", encoding="utf-8"))
    sentence = "Не выносил замечаний — особенно по работе, дому."
    book = {"chapters": [{"id": "ch_02", "content": sentence}]}
    result = validate_narrative_stop_phrases(book, cfg)
    cats = [i.get("category") for i in result.get("issues", [])]
    assert any("class11_not_loved" in (c or "") for c in cats)


# ──────────────────────────────────────────────────────────────────
# 048e: chronology FP fix
# ──────────────────────────────────────────────────────────────────

def test_ch01_paspart_skipped():
    """ch_01 паспортичка skipped по config — no false positives."""
    from pipeline_utils import validate_chronological_consistency
    book = {"chapters": [
        {"id": "ch_01", "content": "Родились дети: Валерий в 1948 году, Татьяна в 1956 году."}
    ]}
    fact_map = {"persons": [
        {"name": "Валерий", "birth_year": 1948},
        {"name": "Татьяна", "birth_year": 1956},
    ]}
    result = validate_chronological_consistency(book, fact_map)
    assert result["errors_count"] == 0, f"ch_01 should be skipped. Got: {result['issues']}"


def test_birth_declaration_sentence_skip():
    """Sentence самостоятельно объявляет birth_year — не FP."""
    from pipeline_utils import validate_chronological_consistency
    book = {"chapters": [
        {"id": "ch_02", "content": "В 1946 году сыграли свадьбу. Родились дети: Валерий в 1948 году, Татьяна в 1956 году."}
    ]}
    fact_map = {"persons": [
        {"name": "Валерий", "birth_year": 1948},
        {"name": "Татьяна", "birth_year": 1956},
    ]}
    result = validate_chronological_consistency(book, fact_map)
    # Sentence with Валерий contains 1948 = birth → skip
    ch02_errors = [i for i in result["issues"] if i["chapter_id"] == "ch_02" and i.get("type") == "person_mentioned_before_birth"]
    assert len(ch02_errors) == 0, f"Birth declaration should be skipped. Got: {ch02_errors}"


def test_epilogue_generic_family_skip():
    """Generic 'семья / создала семью' в epilogue — не flag child-before-birth."""
    from pipeline_utils import validate_chronological_consistency
    book = {"chapters": [
        {"id": "epilogue", "content": "Родившись в 1920 году, она потеряла семью рано. После войны создала семью."}
    ]}
    fact_map = {"persons": [
        {"name": "Валерий", "birth_year": 1948},
    ]}
    result = validate_chronological_consistency(book, fact_map)
    epilogue_errors = [i for i in result["issues"] if i["chapter_id"] == "epilogue"]
    assert len(epilogue_errors) == 0, f"Epilogue generic family should not be flagged. Got: {epilogue_errors}"


def test_real_chronology_error_still_caught():
    """Real error in ch_02 — should still be caught."""
    from pipeline_utils import validate_chronological_consistency
    # Use nominative form — validator uses substring match on fact_map name
    book = {"chapters": [
        {"id": "ch_02", "content": "В 1940 году Татьяна часто ходила с ними гулять."}
    ]}
    fact_map = {"persons": [
        {"name": "Татьяна", "birth_year": 1956},
    ]}
    result = validate_chronological_consistency(book, fact_map)
    assert result["errors_count"] >= 1, "Real error (1940 < 1956) should be caught"


# ──────────────────────────────────────────────────────────────────
# 048f: Class 12 extend — descendants in early context
# ──────────────────────────────────────────────────────────────────

def test_v64_polya_sons_in_childhood_context():
    """v64 snapshot — Коля-лётчик упомянут в context 1933 (profession=лётчик → min 1950)."""
    from pipeline_utils import validate_descendants_in_early_context
    book = {"chapters": [{"id": "ch_02", "content":
        "В 1933 году началась трагедия. Тётя Поля забрала Валентину из детдома. "
        "У тёти Поли была фамилия Амельченко и трое сыновей: Толя из Белгорода, Коля-лётчик и Витя."
    }]}
    fact_map = {
        "subject": {"birth_year": 1920},
        "persons": [
            {"name": "Полина", "relation_to_subject": "старшая сестра", "birth_year": 1908},
            {"name": "Коля", "relation_to_subject": "племянник", "parent": "Полина", "profession": "лётчик"},
        ]
    }
    result = validate_descendants_in_early_context(book, fact_map)
    flagged = [i["person_name"] for i in result["issues"]]
    assert "Коля" in flagged, f"Коля-лётчик should be flagged. Got: {flagged}"


def test_negative_grandchild_proper_context():
    """Внук в правильном контексте (после inferred birth) — не flag."""
    from pipeline_utils import validate_descendants_in_early_context
    book = {"chapters": [{"id": "ch_02", "content":
        "В 1985 году внук Никита учился в школе."
    }]}
    fact_map = {
        "subject": {"birth_year": 1920},
        "persons": [
            {"name": "Татьяна", "relation_to_subject": "дочь", "birth_year": 1956, "marriage_year": 1977},
            {"name": "Никита", "relation_to_subject": "внук", "parent": "Татьяна"},
        ]
    }
    result = validate_descendants_in_early_context(book, fact_map)
    # Никита inferred 1977+1=1978. 1985 > 1978 → OK
    assert not result["issues"], f"Nikita in 1985 should be OK. Got: {result['issues']}"


# ──────────────────────────────────────────────────────────────────
# 048g: Class 19 — cross-paragraph duplication
# ──────────────────────────────────────────────────────────────────

def test_v64_duplicate_vlasevo_paragraph():
    """v64 snapshot — дословный повтор абзаца про крещения/Власьево."""
    from pipeline_utils import validate_cross_paragraph_duplication
    para = (
        "Даже в 1990-е годы, когда в семье прошла волна крещений, сама не "
        "крестилась. Несколько раз ходила в Воскресенскую церковь во Власево, "
        "но в душе осталась атеисткой. В доме не было икон, Библии — "
        "«вообще ничего про Бога не было»."
    )
    book = {"chapters": [
        {"id": "ch_03", "content": f"Some intro paragraph.\n\n{para}\n\nSome ending."},
        {"id": "ch_04", "content": f"Other intro.\n\n{para}\n\nOther ending."},
    ]}
    result = validate_cross_paragraph_duplication(book)
    assert result["errors_count"] == 1, f"Duplicate should be caught. Got: {result['errors_count']}"
    assert result["issues"][0]["similarity"] > 0.9


def test_negative_short_phrases_no_flag():
    """Короткие фразы (< 100 chars) repeating — НЕ flag."""
    from pipeline_utils import validate_cross_paragraph_duplication
    book = {"chapters": [
        {"id": "ch_02", "content": "First full paragraph about something.\n\n«Такая она и есть»."},
        {"id": "ch_03", "content": "Another full paragraph.\n\n«Такая она и есть»."},
    ]}
    result = validate_cross_paragraph_duplication(book)
    assert result["errors_count"] == 0, "Short quoted phrase should not be flagged"


def test_negative_paraphrase_below_threshold():
    """Paraphrase с ~50% сходства — НЕ flag."""
    from pipeline_utils import validate_cross_paragraph_duplication
    para1 = "В послевоенные годы Валентина не работала и занималась домом, хозяйством и воспитанием детей."
    para2 = "В период жизни за рубежом она вела домашнее хозяйство и воспитывала ребёнка без работы."
    book = {"chapters": [
        {"id": "ch_02", "content": f"{para1}\n\nДругая тема."},
        {"id": "ch_03", "content": f"{para2}\n\nЕщё что-то."},
    ]}
    result = validate_cross_paragraph_duplication(book)
    assert result["errors_count"] == 0, f"Paraphrase should be below threshold. Got: {result}"


# ──────────────────────────────────────────────────────────────────
# 046f: historical notes distribution
# ──────────────────────────────────────────────────────────────────

def test_hist_notes_ch04_below_threshold():
    """ch_04 = 0 inline, threshold = 1 → warning."""
    from pipeline_utils import validate_historical_notes_distribution
    book = {
        "chapters": [
            {"id": "ch_02", "content": "***Контекст 1930-х.*** Далее текст. ***Ещё контекст.*** Текст."},
            {"id": "ch_03", "content": "***Портрет эпохи.*** Текст. ***Ещё исторический контекст.***"},
            {"id": "ch_04", "content": "Текст без исторических врезок."},
        ],
        "historical_notes": []
    }
    result = validate_historical_notes_distribution(book)
    ch04_issues = [i for i in result["issues"] if i["chapter_id"] == "ch_04"]
    assert len(ch04_issues) == 1, f"ch_04 below threshold should be warned. Got: {result['issues']}"
    assert ch04_issues[0]["found"] == 0
    assert ch04_issues[0]["expected"] == 1


def test_hist_notes_all_ok():
    """All chapters above threshold — no issues."""
    from pipeline_utils import validate_historical_notes_distribution
    book = {
        "chapters": [
            {"id": "ch_02", "content": "***A.*** ***B.*** ***C.*** Main text."},
            {"id": "ch_03", "content": "***D.*** ***E.*** Portrait text."},
            {"id": "ch_04", "content": "***F.*** Episodes text."},
        ],
        "historical_notes": []
    }
    result = validate_historical_notes_distribution(book)
    assert result["warnings_count"] == 0, f"All OK but got issues: {result['issues']}"


# ──────────────────────────────────────────────────────────────────
# 044i: required episodes coverage
# ──────────────────────────────────────────────────────────────────

def test_required_episode_missing_flag():
    """Required episode absent → error."""
    from pipeline_utils import validate_required_episodes_coverage
    pin_list = [
        {"episode_id": "ep_029", "title": "Продажа дачи", "markers": ["продал.*дач", "дач.*продал"], "required_in_narrative": True}
    ]
    book = {"chapters": [{"id": "ch_02", "content": "Текст без упоминания дачи."}]}
    result = validate_required_episodes_coverage(book, pin_list)
    assert result["covered_count"] == 0
    assert result["errors_count"] == 1
    assert any(i["category"] == "missing_required_episode" for i in result["issues"])


def test_required_episode_present():
    """Required episode присутствует → covered."""
    from pipeline_utils import validate_required_episodes_coverage
    pin_list = [
        {"episode_id": "ep_017", "title": "Дача в 60-х", "markers": ["дач"], "required_in_narrative": True}
    ]
    book = {"chapters": [{"id": "ch_02", "content": "В 60-х у них появилась дача за городом."}]}
    result = validate_required_episodes_coverage(book, pin_list)
    assert result["covered_count"] == 1
    assert result["errors_count"] == 0


def test_optional_episode_not_flagged():
    """Optional episode absent → no error."""
    from pipeline_utils import validate_required_episodes_coverage
    pin_list = [
        {"episode_id": "byt_012", "title": "Шляпки", "markers": ["шляпк"], "required_in_narrative": False}
    ]
    book = {"chapters": [{"id": "ch_02", "content": "Текст без шляпок."}]}
    result = validate_required_episodes_coverage(book, pin_list)
    assert not result["issues"]


# ──────────────────────────────────────────────────────────────────
# 049g: preserve_root_level_metadata
# ──────────────────────────────────────────────────────────────────

def test_preserve_writing_notes_restored():
    """writing_notes = {} after LE → restored from pre-LE."""
    from pipeline_utils import preserve_root_level_metadata
    pre_le = {
        "chapters": [{"id": "ch_02", "content": "text"}],
        "writing_notes": {"rule13_revision_applied": [{"hint_id": "h_001", "action": "rewritten"}]},
    }
    post_le = {
        "chapters": [{"id": "ch_02", "content": "text improved"}],
        "writing_notes": {},
    }
    result = preserve_root_level_metadata(post_le, pre_le)
    assert result["writing_notes"] == pre_le["writing_notes"]


def test_preserve_nonempty_not_overwritten():
    """Non-empty post-LE writing_notes → NOT overwritten."""
    from pipeline_utils import preserve_root_level_metadata
    pre_le = {"writing_notes": {"rule13_revision_applied": [{"hint_id": "h_001", "action": "rewritten"}]}}
    post_le = {"writing_notes": {"rule13_revision_applied": [{"hint_id": "h_002", "action": "deleted"}]}}
    result = preserve_root_level_metadata(post_le, pre_le)
    assert result["writing_notes"] == post_le["writing_notes"]  # post-LE not overwritten


def test_preserve_chapters_untouched():
    """Only root metadata preserved, not chapters."""
    from pipeline_utils import preserve_root_level_metadata
    pre_le = {"chapters": [{"id": "ch_02", "content": "old"}], "writing_notes": {"x": 1}}
    post_le = {"chapters": [{"id": "ch_02", "content": "new improved text"}], "writing_notes": {}}
    result = preserve_root_level_metadata(post_le, pre_le)
    assert result["chapters"][0]["content"] == "new improved text"  # chapters untouched


# ──────────────────────────────────────────────────────────────────
# 049f-2: collect_revision_hints — all validators coverage
# ──────────────────────────────────────────────────────────────────

def test_collect_revision_hints_warning_level_included():
    """Warning-level finding → hint with must_apply=False."""
    from pipeline_utils import collect_revision_hints
    book_draft = {"chapters": [{"id": "ch_02", "content": "Текст."}]}
    validator_outputs = {
        "discourse_markers": {
            "issues": [{
                "type": "below_threshold",
                "category": "below_threshold",
                "chapter_id": "ch_02",
                "severity": "warning",
                "expected": 8,
                "found": 2,
                "snippet": "Текст.",
            }]
        }
    }
    hints = collect_revision_hints(book_draft, validator_outputs)
    dms = [h for h in hints if h["validator"] == "discourse_markers"]
    assert len(dms) == 1
    assert dms[0]["must_apply"] is False  # warning → must_apply=False


def test_collect_revision_hints_error_level_must_apply():
    """Error-level finding → hint with must_apply=True."""
    from pipeline_utils import collect_revision_hints
    book_draft = {"chapters": [{"id": "ch_02", "content": "Дубль абзаца."}]}
    validator_outputs = {
        "cross_paragraph_duplication": {
            "issues": [{
                "type": "cross_paragraph_duplication",
                "category": "duplicate_paragraph",
                "chapter_id": "ch_02",
                "severity": "error",
                "snippet": "Дубль абзаца.",
            }]
        }
    }
    hints = collect_revision_hints(book_draft, validator_outputs)
    dups = [h for h in hints if h["validator"] == "cross_paragraph_duplication"]
    assert len(dups) == 1
    assert dups[0]["must_apply"] is True


def test_collect_revision_hints_missing_validator_no_crash():
    """Missing validator → warning logged, no crash."""
    from pipeline_utils import collect_revision_hints
    book_draft = {"chapters": [{"id": "ch_02", "content": "Text."}]}
    # Only some validators provided
    validator_outputs = {
        "narrative_truism": {"issues": []}
    }
    hints = collect_revision_hints(book_draft, validator_outputs)
    assert isinstance(hints, list)  # no crash
