#!/usr/bin/env python3
import subprocess, sys, glob, os

pdf = '/opt/glava/exports/karakulina_stage4_gate_2c_20260505_142001.pdf'
for pg in [1, 5, 11, 15, 20]:
    out_prefix = f'/opt/glava/exports/v43_page_{pg:02d}'
    r = subprocess.run(
        ['pdftocairo', '-png', '-r', '120', '-f', str(pg), '-l', str(pg), pdf, out_prefix],
        capture_output=True
    )
    files = sorted(glob.glob(out_prefix + '*.png'))
    if files:
        dest = f'/opt/glava/exports/v43_page_{pg:02d}.png'
        if files[0] != dest:
            os.rename(files[0], dest)
        print(f'OK page {pg}: {dest}')
    else:
        print(f'FAIL page {pg}: {r.stderr.decode()[:200]}')
