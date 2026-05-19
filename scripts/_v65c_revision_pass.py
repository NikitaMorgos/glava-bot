#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v65c: pointed revision pass — 4 targeted hints on v65 revised book.
Input: exports/stage2_v65/karakulina_book_FINAL_1779175986_revised.json
Output: exports/stage2_v65c/karakulina_book_FINAL_v65c_revised.json
"""
import json, sys, os, glob, re, time
from datetime import datetime
sys.path.insert(0, '/opt/glava')
sys.stdout.reconfigure(encoding='utf-8')

if not os.environ.get('ANTHROPIC_API_KEY'):
    try:
        with open('/opt/glava/.env', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
        print('Loaded .env')
    except FileNotFoundError:
        pass

from pipeline_utils import (
    load_config, load_prompt, parse_pin_list_from_markdown, audit_revision_diff
)
import anthropic

STAGE2_DIR = 'exports/stage2_v65'
V65C_DIR = 'exports/stage2_v65c'
FM_DIR = 'exports/karakulina_v65'
os.makedirs(V65C_DIR, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────
# v65c: 4 targeted hints
# ──────────────────────────────────────────────────────────────────────
V65C_HINTS = [
    {
        "hint_id": "c_001",
        "validator": "entity_substitution",
        "category": "named_entity_drift",
        "severity": "error",
        "must_apply": True,
        "chapter_id": None,
        "snippet": "на улицу Капошвара",
        "additional_snippets": ["улицу Капошвара", "улица Капошвара", "улице Капошвара"],
        "affected_chapters": ["ch_02", "ch_03", "ch_04", "epilogue"],
        "suggestion": (
            "Заменить ВСЕ вхождения 'улица Капошвара' → 'площадь Капошвара' (включая все падежные формы: "
            "'на улицу' → 'на площадь', 'на улице' → 'на площади'). "
            "TR2 и pin-list v6 ep_028 явно указывают: Капошвара — это площадь, не улица. "
            "Class 1 named entity drift повторяется 3 спринта подряд (v63/v64/v65)."
        )
    },
    {
        "hint_id": "c_002",
        "validator": "narrative_required_persons",
        "category": "missing_required_person",
        "severity": "error",
        "must_apply": True,
        "chapter_id": "ch_03",
        "snippet": None,
        "suggestion": (
            "В ch_03 добавить упоминание 'Баба Аня' как персонажа с контекстом. "
            "Баба Аня — свекровь рассказчика Татьяны (мать Владимира Маргося). "
            "Pin-list v6 relation_overrides помечает её narrative_required=true. "
            "Эпизод из TR2: Татьяна сравнивала отношения бабы Ани к детям со своими. "
            "Вставить кратко (1-2 sentence) в раздел 'Отношения в семье' или 'Традиции': "
            "например, 'В отличие от бабы Ани — матери первого мужа — Валентина не вмешивалась "
            "в воспитание внуков напрямую.' Не раскрывать подробно, только упомянуть."
        )
    },
    {
        "hint_id": "c_003",
        "validator": "pin_list_year_direction_drift",
        "category": "wrong_year_attribution",
        "severity": "error",
        "must_apply": True,
        "chapter_id": None,
        "snippet": "В 1990-е годы семья продала дачу",
        "additional_snippets": ["Когда в 1990-е годы семья продала дачу"],
        "affected_chapters": ["ch_02", "ch_03", "ch_04"],
        "suggestion": (
            "ep_029 'Продажа дачи' помечено в pin-list v6 как year_direction=before_1990s "
            "(Никитин уточнение: продали ДО 1990-х). "
            "Заменить 'В 1990-е годы семья продала дачу' → 'До 1990-х годов семья продала дачу' "
            "ИЛИ без attribution года: 'Семья продала дачу; Валентина очень жалела об этом'. "
            "Сохранить предложение про тётю Машу и сожаление Татьяны (они верны)."
        )
    },
    {
        "hint_id": "c_004",
        "validator": "pin_list_depth",
        "category": "insufficient_narrative_depth",
        "severity": "warning",
        "must_apply": False,
        "chapter_id": None,
        "snippet": None,
        "affected_chapters": ["ch_02", "ch_04"],
        "suggestion": (
            "Развернуть следующие pin-list events до ≥3 sentences с деталью из source или историческим контекстом "
            "(не дублировать существующий текст, ПРАВИЛО 0 scope lock): "
            "ep_003 — призыв на фронт 23 июня 1941 (добавить деталь о мобилизации медработников), "
            "ep_011 — операция на желудке 1960 (добавить последствия: перестала есть молочное), "
            "ep_016 — работа в поликлинике Химинститута (добавить деталь о приёме пациентов или уколах), "
            "ep_024 — чемодан огурцов из Молдавии (добавить реакцию Валентины на эпизод)."
        )
    },
]

# ──────────────────────────────────────────────────────────────────────
# Load input: v65 revised book
# ──────────────────────────────────────────────────────────────────────
INPUT_BOOK = os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_1779175986_revised.json')
if not os.path.exists(INPUT_BOOK):
    # Fallback: find any _revised book
    candidates = sorted([
        f for f in glob.glob(os.path.join(STAGE2_DIR, 'karakulina_book_FINAL_*.json'))
        if '_revised' in f
    ], reverse=True)
    if not candidates:
        print('ERROR: no v65 revised book found'); sys.exit(1)
    INPUT_BOOK = candidates[0]

print('Input book: %s' % INPUT_BOOK)
book_raw = json.load(open(INPUT_BOOK, encoding='utf-8'))
book_draft = book_raw.get('book_draft') or book_raw.get('book_final') or book_raw

fm_files = sorted(glob.glob(os.path.join(FM_DIR, 'karakulina_fact_map_full_*.json')), reverse=True)
if not fm_files:
    print('ERROR: no fact_map found'); sys.exit(1)
fm = json.load(open(fm_files[0], encoding='utf-8'))
print('Fact map: %s' % fm_files[0])

# ──────────────────────────────────────────────────────────────────────
# GW v2.24 call
# ──────────────────────────────────────────────────────────────────────
cfg = load_config()
gw_cfg = cfg['ghostwriter']
model = gw_cfg['model']
max_tokens = gw_cfg['max_tokens']
temperature = gw_cfg.get('temperature', 0.5)
system_prompt = load_prompt(gw_cfg['prompt_file'])
assert 'v2.24' in gw_cfg['prompt_file'], 'Expected GW v2.24, got: %s' % gw_cfg['prompt_file']
print('GW: %s | model=%s' % (gw_cfg['prompt_file'], model))

pin_list = parse_pin_list_from_markdown('collab/context/known_episodes_karakulina.md')
tr_files = sorted(glob.glob('collab/transcripts/*.txt'))
transcripts = [{'filename': os.path.basename(f), 'text': open(f, encoding='utf-8').read()} for f in tr_files[:2]]

# Only must_apply hints first (c_001/c_002/c_003 + optional c_004)
must_hints = [h for h in V65C_HINTS if h['must_apply']]
opt_hints = [h for h in V65C_HINTS if not h['must_apply']]
active_hints = must_hints + opt_hints
print('v65c hints: %d total (%d must_apply, %d optional)' % (
    len(active_hints), len(must_hints), len(opt_hints)))
for h in active_hints:
    print('  [%s] %s/%s ch=%s snippet=%.40s...' % (
        h['hint_id'], h['validator'], h['category'],
        h.get('chapter_id', 'multi'),
        str(h.get('snippet') or h['suggestion'][:40])
    ))

affected = list(set(
    ch for h in active_hints
    for ch in (h.get('affected_chapters') or ([h['chapter_id']] if h.get('chapter_id') else []))
))

user_message = {
    'phase': 'B',
    'call_type': 'revision',
    'sprint': 'v65c',
    'project_id': 'karakulina',
    'ghostwriter_version': 'v2.24',
    'subject': {'name': 'Каракулина Валентина Ивановна'},
    'fact_map': fm,
    'transcripts': transcripts,
    'current_book': book_draft,
    'revision_scope': {
        'type': 'rule13_revision_hints',
        'affected_chapters': affected,
        'instructions': (
            'Выполни revision по ПРАВИЛО 13. '
            'Исправь ТОЛЬКО указанные hints c_001–c_004. '
            'c_001: ОБЯЗАТЕЛЬНО заменить все формы "улица Капошвара" → "площадь Капошвара". '
            'c_002: ОБЯЗАТЕЛЬНО добавить упоминание Баба Аня в ch_03. '
            'c_003: ОБЯЗАТЕЛЬНО убрать "1990-е годы" из дачного эпизода. '
            'Все остальные главы и параграфы — НЕ МЕНЯТЬ (ПРАВИЛО 0 SCOPE LOCK). '
            'rule13_revision_applied ДОЛЖНО быть списком dict.'
        )
    },
    'revision_hints': active_hints,
    'pin_list': pin_list,
}

print('\n=== Running GW v2.24 v65c revision pass ===')
client = anthropic.Anthropic()
start = datetime.now()
raw_parts = []
with client.messages.stream(
    model=model,
    max_tokens=max_tokens,
    temperature=temperature,
    system=system_prompt,
    messages=[{'role': 'user', 'content': json.dumps(user_message, ensure_ascii=False)}]
) as stream:
    for text in stream.text_stream:
        raw_parts.append(text)
        print(text, end='', flush=True)

elapsed = (datetime.now() - start).total_seconds()
raw_response = ''.join(raw_parts)
print('\n\n[v65c GW] Done in %.1fs | %d chars' % (elapsed, len(raw_response)))

# Save raw
open(os.path.join(V65C_DIR, 'revision_raw_response_v65c.txt'), 'w', encoding='utf-8').write(raw_response)

json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
if not json_match:
    print('[v65c GW] No JSON found'); sys.exit(1)
try:
    book_revised = json.loads(json_match.group())
    print('[v65c GW] Parsed JSON OK')
except json.JSONDecodeError as e:
    print('[v65c GW] JSON parse error: %s' % e); sys.exit(1)

# Save
revised_path = os.path.join(V65C_DIR, 'karakulina_book_FINAL_v65c_revised.json')
json.dump(book_revised, open(revised_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: %s' % revised_path)

# writing_notes check
wn = book_revised.get('writing_notes', {})
r13 = wn.get('rule13_revision_applied')
print('\n=== writing_notes (rule13 proof) ===')
print('  type=%s' % type(r13).__name__)
if isinstance(r13, list):
    print('  OK: list count=%d' % len(r13))
    for i, d in enumerate(r13[:4]):
        print('  [%d]: %s' % (i, json.dumps(d, ensure_ascii=False)[:120]))

# Quick content checks
chapters = book_revised.get('chapters', [])
full_text = ' '.join((ch.get('content') or '') for ch in chapters)
print('\n=== v65c content checks ===')

# Kaposhvara check
kap_ulitsa = 'улица капошвара' in full_text.lower() or 'улице капошвара' in full_text.lower() or 'улицу капошвара' in full_text.lower()
kap_ploshad = 'площадь капошвара' in full_text.lower() or 'площади капошвара' in full_text.lower() or 'на площадь' in full_text.lower()
print('Капошвара: улица=%s площадь=%s → %s' % (
    kap_ulitsa, kap_ploshad,
    'OK ✅' if not kap_ulitsa and kap_ploshad else ('PARTIALLY FIXED ⚠️' if not kap_ulitsa else 'STILL WRONG ❌')
))

# Baba Anya
baba_anya = 'баба аня' in full_text.lower() or 'бабы ани' in full_text.lower() or 'бабе ане' in full_text.lower()
print('Баба Аня: %s' % ('PRESENT ✅' if baba_anya else 'MISSING ❌'))

# Dacha year
dacha_1990 = '1990-е годы семья продала' in full_text or 'в 1990-е годы семья' in full_text
dacha_fixed = 'до 1990-х' in full_text or ('продала дачу' in full_text and not dacha_1990)
print('Дача 1990-е: raw=%s fixed=%s → %s' % (
    dacha_1990, dacha_fixed,
    'OK ✅' if not dacha_1990 else '❌ STILL WRONG'
))

# Char counts
ch_chars = {ch['id']: len(ch.get('content') or '') for ch in chapters}
total_narrative = sum(ch_chars.get(k, 0) for k in ['ch_02', 'ch_03', 'ch_04', 'epilogue'])
print('\n=== Char counts ===')
for k, v in ch_chars.items():
    print('  %s: %d' % (k, v))
print('  Narrative total: %d' % total_narrative)

# Diff audit (threshold=30 for chapter-level hints)
print('\n=== Diff audit (threshold=30) ===')
diff = audit_revision_diff(book_draft, book_revised, active_hints)
n_unauthorized = len(diff.get('unauthorized_changes', []))
print('hints_count: %d' % diff.get('hints_count', 0))
print('applied: %d' % len(diff.get('applied', [])))
print('skipped: %d' % len(diff.get('skipped', [])))
print('unauthorized_changes: %d' % n_unauthorized)
json.dump(diff, open(os.path.join(V65C_DIR, 'revision_diff_audit_v65c.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Saved: revision_diff_audit_v65c.json')

# Checks
if wn.get('rule13_revision_failed'):
    print('\nFAIL: rule13_revision_failed=true'); sys.exit(1)
if n_unauthorized > 30:
    print('\nFAIL: unauthorized_changes=%d > threshold=30' % n_unauthorized); sys.exit(1)

print('\n=== v65c revision pass COMPLETE ===')
print('Output: %s' % revised_path)
