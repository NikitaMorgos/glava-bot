import json, pathlib
ROOT = pathlib.Path("/opt/glava")
src = ROOT / "exports/karakulina_stage4_cover_designer_call1_20260404_063526.json"
d = json.loads(src.read_text(encoding="utf-8"))
cc = d.get("cover_composition", d)
out = {"final_cover_composition": cc}
dst = ROOT / "exports/karakulina_cover_call2_synthetic.json"
dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("done:", dst.name, len(str(cc)), "chars")
