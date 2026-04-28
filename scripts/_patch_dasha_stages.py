"""Добавляет маршруты /dasha/stages в dasha.py, если их ещё нет."""
from pathlib import Path

TARGET = Path("/opt/glava/admin/blueprints/dasha.py")

ROUTES = '''

# ── Описания этапов пайплайна ─────────────────────────────────────

_STAGES_DIR = _ROOT_DIR / "docs" / "stages"

STAGE_ORDER = [
    ("02_fact_extractor",      "02 · Фактолог"),
    ("03_ghostwriter",         "03 · Писатель"),
    ("04_fact_checker",        "04 · Фактчекер"),
    ("05_literary_editor",     "05 · Литредактор"),
    ("06_proofreader",         "06 · Корректор"),
    ("07_photo_editor",        "07 · Фоторедактор"),
    ("08_layout_designer",     "08 · Верстальщик"),
    ("09_qa_layout",           "09 · QA вёрстки"),
    ("11_interview_architect",  "11 · Интервьюер"),
    ("12_historian",           "12 · Историк-краевед"),
    ("13_cover_designer",      "13 · Дизайнер обложки"),
]


def _render_stage(path: "Path") -> str:
    import markdown as _md
    text = path.read_text(encoding="utf-8")
    return _md.markdown(text, extensions=["tables", "fenced_code"])


@bp.route("/stages")
@role_required("dev", "dasha")
def stages():
    cards = []
    existing = {p.stem: p for p in _STAGES_DIR.glob("*.md") if p.stem != "STAGE_TEMPLATE"}
    for key, name in STAGE_ORDER:
        if key in existing:
            html = _render_stage(existing[key])
            cards.append({"key": key, "name": name, "html": html, "exists": True})
        else:
            cards.append({"key": key, "name": name, "html": "", "exists": False})
    known_keys = {k for k, _ in STAGE_ORDER}
    for p in sorted(existing.values(), key=lambda x: x.stem):
        if p.stem not in known_keys:
            cards.append({"key": p.stem, "name": p.stem, "html": _render_stage(p), "exists": True})
    return render_template("dasha/stages.html", cards=cards)


@bp.route("/stages/<stage_key>/upload", methods=["POST"])
@role_required("dev", "dasha")
def stage_upload(stage_key: str):
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "Файл не выбран"}), 400
    if not f.filename.lower().endswith(".md"):
        return jsonify({"ok": False, "error": "Только .md файлы"}), 400
    _STAGES_DIR.mkdir(parents=True, exist_ok=True)
    target = _STAGES_DIR / f"{stage_key}.md"
    f.save(str(target))
    return jsonify({"ok": True, "key": stage_key})
'''

existing = TARGET.read_text(encoding="utf-8")
if "def stages(" in existing:
    print("Маршруты уже добавлены, пропускаю.")
else:
    TARGET.write_text(existing + ROUTES, encoding="utf-8")
    print("Маршруты добавлены успешно.")
