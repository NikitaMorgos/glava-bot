#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Форматирует interview_questions JSON в Markdown.
Поддерживает обе структуры: плоский список questions[] и groups[].
Записывает exports/karakulina_FINAL_questions_<ts>.md
"""
import json, pathlib, sys
from datetime import datetime

EXPORTS = pathlib.Path(__file__).resolve().parent.parent / "exports"

candidates = sorted(EXPORTS.glob("karakulina_stage4_interview_questions_*.json"))
if not candidates:
    sys.exit("[ERROR] karakulina_stage4_interview_questions_*.json не найден")

src = candidates[-1]
data = json.loads(src.read_text(encoding="utf-8"))
print(f"[SRC] {src.name}")

hero  = data.get("hero_name", "Каракулина Валентина Ивановна")
ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
out   = EXPORTS / f"karakulina_FINAL_questions_{ts}.md"

lines = []

# Build question index (id -> question object)
all_qs = data.get("questions", [])
q_index = {q["id"]: q for q in all_qs if "id" in q}
total   = len(all_qs)

# Groups with question_ids (GLAVA format) or embedded questions
groups = data.get("question_groups", data.get("groups", []))

lines += [
    f"# Уточняющие вопросы: {hero}",
    "",
    f"Сформировано: {datetime.now().strftime('%d.%m.%Y')}  ",
    f"Всего вопросов: **{total}**",
    "",
    "---",
    "",
]

# ── Case 1: groups reference questions by id ──────────────────────
if groups and all(g.get("question_ids") for g in groups if isinstance(g, dict)):
    for i, grp in enumerate(groups, 1):
        theme = grp.get("theme", grp.get("title", f"Группа {i}"))
        intro = grp.get("intro_for_client", grp.get("description", ""))
        ids   = grp.get("question_ids", [])
        lines.append(f"## {i}. {theme}")
        if intro:
            lines.append(f"*{intro}*")
        lines.append("")
        for j, qid in enumerate(ids, 1):
            q = q_index.get(qid)
            if not q:
                continue
            qtext = q.get("text", "")
            pri   = q.get("priority", "")
            gap   = q.get("related_gap", "")
            resp  = q.get("suggested_respondent", {})
            who   = resp.get("name", "") if isinstance(resp, dict) else ""
            badge = " `!`" if pri == "high" else ""
            lines.append(f"{j}. {qtext}{badge}")
            notes = []
            if gap:
                notes.append(f"период: {gap}")
            if who:
                notes.append(f"кому задать: {who}")
            unlock = q.get("what_it_unlocks", "")
            if unlock:
                notes.append(unlock)
            if notes:
                lines.append(f"   > *{'; '.join(notes)}*")
        lines.append("")

# ── Case 2: flat list grouped by category ────────────────────────
else:
    from collections import defaultdict
    by_cat = defaultdict(list)
    for q in all_qs:
        by_cat[q.get("category", "other")].append(q)

    CATEGORY_NAMES = {
        "inner_world":         "Внутренний мир и переживания",
        "family":              "Семья и отношения",
        "family_structure":    "Семейное дерево",
        "daily_life":          "Быт и повседневность",
        "historical":          "Исторический контекст",
        "values":              "Ценности и убеждения",
        "work":                "Работа и профессия",
        "memory":              "Воспоминания и рефлексия",
        "childhood":           "Детство",
        "war":                 "Война и испытания",
        "life_turning_point":  "Поворотные моменты",
        "faith":               "Вера и духовность",
        "other":               "Прочее",
    }

    for cat_key, qs in sorted(by_cat.items()):
        cat_name = CATEGORY_NAMES.get(cat_key, cat_key.replace("_", " ").title())
        lines.append(f"## {cat_name}")
        lines.append("")
        for j, q in enumerate(qs, 1):
            qtext  = q.get("text", "")
            gap    = q.get("related_gap", "")
            pri    = q.get("priority", "")
            resp   = q.get("suggested_respondent", {})
            who    = resp.get("name", "") if isinstance(resp, dict) else ""
            badge  = " `!`" if pri == "high" else ""
            lines.append(f"{j}. {qtext}{badge}")
            notes  = []
            if gap:
                notes.append(f"период: {gap}")
            if who:
                notes.append(f"кому задать: {who}")
            unlock = q.get("what_it_unlocks", "")
            if unlock:
                notes.append(unlock)
            if notes:
                lines.append(f"   > *{'; '.join(notes)}*")
        lines.append("")

lines += [
    "---",
    "",
    "*Документ сформирован автоматически системой Glava.*",
]

out.write_text("\n".join(lines), encoding="utf-8")
print(f"[OK] Questions: {out.name} ({out.stat().st_size} bytes, {total} questions)")
