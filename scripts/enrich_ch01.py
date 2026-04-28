"""
enrich_ch01.py — собирает структурированный bio_data из fact_map
и обновляет content в ch_01 прооfreader-чекпойнта.

Формат ch_01 content: строки "Метка: Значение" + секции "**СЕКЦИЯ**"
— парсится _story_bio_data_block() в pdf_renderer.py
"""
import json
import pathlib
import sys
import shutil
import datetime

ROOT = pathlib.Path('/opt/glava')
EXPORTS = ROOT / 'exports'

# ── Входные файлы ────────────────────────────────────────────────────────────
PROOF_IN  = EXPORTS / 'karakulina_gate2b_v3_input_proofreader_checkpoint_20260417_080301.json'
FM_IN     = EXPORTS / 'karakulina_gate2b_v3_input_fact_map_checkpoint_20260417_080301.json'

ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
PROOF_OUT = EXPORTS / f'karakulina_enriched_ch01_{ts}.json'

# ── Загрузка ─────────────────────────────────────────────────────────────────
with open(PROOF_IN, encoding='utf-8') as f:
    book = json.load(f)

with open(FM_IN, encoding='utf-8') as f:
    fm_raw = json.load(f)

fm = fm_raw.get('content', fm_raw)

subj    = fm.get('subject', {})
persons = fm.get('persons', [])
tl      = fm.get('timeline', [])

# ── Вспомогательные функции ───────────────────────────────────────────────────
def year_str(ev):
    d = ev.get('date', {})
    y = d.get('year')
    m = d.get('month')
    day = d.get('day')
    if not y:
        return ''
    if m and day:
        months = ['', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        return f'{day} {months[m]} {y}'
    if m:
        months = ['', 'янв.', 'февр.', 'март', 'апр.', 'май', 'июнь',
                  'июль', 'авг.', 'сент.', 'окт.', 'нояб.', 'дек.']
        return f'{months[m]} {y}'
    return str(y)

def find_event(keyword):
    kw = keyword.lower()
    for ev in tl:
        if kw in ev.get('title', '').lower() or kw in ev.get('description', '').lower():
            return ev
    return None

def find_person(relation):
    rel = relation.lower()
    for p in persons:
        if rel in p.get('relation_to_subject', '').lower():
            return p
    return None

# ── Строим content ch_01 ─────────────────────────────────────────────────────
# Сначала находим ch_01 (нужна для извлечения даты смерти из оригинала)
chapters = book.get('chapters', [])
ch01 = next((c for c in chapters if c.get('id') == 'ch_01'), None)
if ch01 is None:
    print('ERROR: ch_01 не найдена в книге')
    sys.exit(1)

lines = []

# — Личные данные —
lines.append('**ЛИЧНЫЕ ДАННЫЕ**')
lines.append(f'Имя: {subj.get("name", "Каракулина Валентина Ивановна")}')

birth_ev = find_event('рождени')
if birth_ev:
    birth_desc = birth_ev.get('description', '')
    # Берём место из subject или из description
    birth_place = subj.get('birth_place', '') or birth_desc
    lines.append(f'Дата рождения: {year_str(birth_ev)}, {birth_place}')
else:
    by = subj.get('birth_year', '')
    bp = subj.get('birth_place', '')
    lines.append(f'Дата рождения: {by}, {bp}')

# Дата смерти — ищем из subject или из оригинального ch_01 content
death_year = subj.get('death_year')
if not death_year:
    # Пробуем вытащить из оригинального text ("Умерла 2022 год")
    import re as _re
    orig = ch01.get('content', '')  # ch01 ещё не обновлён
    m = _re.search(r'[Уу]мер[а]?\D{0,10}(\d{4})', orig)
    if m:
        death_year = int(m.group(1))
if death_year:
    death_place_ev = next((ev for ev in tl if str(death_year) in str(ev.get('date',{}).get('year',''))
                           and 'смерт' in ev.get('title','').lower()
                           and 'матер' not in ev.get('title','').lower()), None)
    death_place = death_place_ev.get('location', '') if death_place_ev else 'Харьков'
    lines.append(f'Дата смерти: {death_year}, {death_place}')
else:
    # Дата смерти не найдена в subject и не в исходном content — используем известное значение
    lines.append('Дата смерти: 2022, Харьков')

# — Образование —
lines.append('')
lines.append('**ОБРАЗОВАНИЕ**')
edu_enter = find_event('поступлени')
edu_finish = find_event('окончани')
if edu_enter:
    lines.append(f'Поступление: {year_str(edu_enter)}, {edu_enter["title"]}')
if edu_finish:
    lines.append(f'Окончание: {year_str(edu_finish)}, {edu_finish.get("description","")[:80]}')

# — Военная служба —
lines.append('')
lines.append('**ВОЕННАЯ СЛУЖБА**')
призыв = find_event('призыв')
демоб  = find_event('демобилиза')
if призыв:
    lines.append(f'Призыв: {year_str(призыв)}')
if демоб:
    lines.append(f'Демобилизация: {year_str(демоб)}, {демоб.get("location","")}')

mil_ev = find_event('военная служба')
if mil_ev:
    lines.append(f'Должность: {mil_ev.get("description","")[:100]}')

партия = find_event('партию')
if партия:
    lines.append(f'Вступление в партию: {year_str(партия)}')

# — Награды —
lines.append('')
lines.append('**НАГРАДЫ**')
for ev in tl:
    t = ev.get('title', '').lower()
    if any(k in t for k in ['медал', 'орден', 'звани', 'ударник']):
        lines.append(f'{year_str(ev)}: {ev["title"]}')

# — Трудовая деятельность (послевоенная, НЕ военная) —
lines.append('')
lines.append('**ТРУДОВАЯ ДЕЯТЕЛЬНОСТЬ**')
for ev in tl:
    t = ev.get('title', '').lower()
    d = ev.get('description', '').lower()
    ev_year = ev.get('date', {}).get('year', 0) or 0
    # Только послевоенная + только гражданская
    if ev_year < 1946:
        continue
    if any(k in t or k in d for k in ['санэпид', 'поликлиник', 'медсестр', 'пенси', 'начало работы']):
        lines.append(f'{year_str(ev)}: {ev["title"]}')

# — Семья —
lines.append('')
lines.append('**СЕМЬЯ**')
муж = find_person('муж')
сын = find_person('сын')
дочь = find_person('дочь')

if муж:
    death_note = f' (умер {муж.get("death_year")})' if муж.get('death_year') else ''
    lines.append(f'Муж: {муж["name"]}{death_note} — {муж.get("description","")}')
if сын:
    born = f' (р. {сын["birth_year"]})' if сын.get('birth_year') else ''
    lines.append(f'Сын: {сын["name"]}{born}')
if дочь:
    born = f' (р. {дочь["birth_year"]})' if дочь.get('birth_year') else ''
    lines.append(f'Дочь: {дочь["name"]}{born}')

внук = find_person('внук')
внучка = find_person('внучка')
if внук:
    lines.append(f'Внук: {внук["name"]} — {внук.get("description","")}')
if внучка:
    lines.append(f'Внучка: {внучка["name"]}')

# — Ключевые даты хронологии —
lines.append('')
lines.append('**ХРОНОЛОГИЯ**')
key_ids = ['event_002', 'event_003', 'event_009', 'event_012', 'event_014',
           'event_015', 'event_019', 'event_020', 'event_023', 'event_026',
           'event_032', 'event_033', 'event_035']
for ev in tl:
    if ev.get('id') in key_ids:
        y = ev.get('date', {}).get('year', '')
        lines.append(f'{y}: {ev["title"]}')

# ── Обновляем ch_01 в книге ───────────────────────────────────────────────────

old_content = ch01.get('content', '')
new_content = '\n'.join(lines)

print(f'Старый content ch_01 ({len(old_content)} симв.):')
print(f'  {old_content[:120]}...')
print(f'\nНовый content ch_01 ({len(new_content)} симв.):')
print(new_content[:800])

ch01['content'] = new_content
# Сбрасываем paragraphs[], чтобы prepare_book_for_layout пересобрал их из content
ch01.pop('paragraphs', None)

# ── Сохраняем ────────────────────────────────────────────────────────────────
with open(PROOF_OUT, 'w', encoding='utf-8') as f:
    json.dump(book, f, ensure_ascii=False, indent=2)

print(f'\n✅ Сохранено: {PROOF_OUT.name}')
print(f'Используй в рендере: --book {PROOF_OUT}')
