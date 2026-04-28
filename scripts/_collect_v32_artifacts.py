import json, glob, shutil, os
from pathlib import Path

run_dir = Path(sorted(glob.glob('/opt/glava/exports/karakulina_v32_run_*'))[-1])
collab_dir = Path('/opt/glava/collab/runs/karakulina_v32_run_20260421')
collab_dir.mkdir(parents=True, exist_ok=True)

def cp(src_glob, dst_name=None):
    files = sorted(glob.glob(str(run_dir / src_glob)))
    if files:
        dst = collab_dir / (dst_name or Path(files[0]).name)
        shutil.copy2(files[0], dst)
        print(f"COPIED: {dst.name} ({dst.stat().st_size//1024}KB)")
    else:
        print(f"MISSING: {src_glob}")

# Stage 1
cp('karakulina_fact_map_full_*.json', 'fact_map_v32.json')
cp('karakulina_stage1_full_run_manifest_*.json', 'run_manifest_s1_v32.json')

# Stage 2
cp('karakulina_historian_*.json', 'historian_result_v32.json')
cp('karakulina_book_FINAL_*.json', 'book_FINAL_stage2_v32.json')
cp('karakulina_fc_report_iter1_*.json', 'fc_report_iter1_v32.json')
cp('karakulina_fc_report_iter2_*.json', 'fc_report_iter2_v32.json')
cp('karakulina_fc_report_iter3_*.json', 'fc_report_iter3_v32.json')
cp('karakulina_stage2_run_manifest_*.json', 'run_manifest_s2_v32.json')

# Stage 3 (in /opt/glava/exports, not run_dir)
exports = Path('/opt/glava/exports')
for src_g, dst_n in [
    ('karakulina_v32_book_FINAL_stage3_*.json', 'book_FINAL_stage3_v32.json'),
    ('karakulina_v32_FINAL_stage3_*.txt',       'FINAL_stage3_v32.txt'),
    ('karakulina_v32_liteditor_report_*.json',  'liteditor_report_v32.json'),
    ('karakulina_v32_proofreader_report_*.json','proofreader_report_v32.json'),
    ('karakulina_v32_stage3_run_manifest_*.json','run_manifest_s3_v32.json'),
]:
    files = sorted(glob.glob(str(exports / src_g)))
    if files:
        dst = collab_dir / dst_n
        shutil.copy2(files[0], dst)
        print(f"COPIED: {dst.name} ({dst.stat().st_size//1024}KB)")
    else:
        print(f"MISSING: {src_g}")

cp('run.log', 'run.log')
print(f"\nCollab dir: {collab_dir}")
print(f"Files: {len(list(collab_dir.iterdir()))}")
