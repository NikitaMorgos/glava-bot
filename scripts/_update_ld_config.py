import json, pathlib
p = pathlib.Path("/opt/glava/prompts/pipeline_config.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["layout_designer"]["prompt_file"] = "08_layout_designer_v3.md"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("updated: layout_designer -> 08_layout_designer_v3.md")
