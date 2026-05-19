#!/usr/bin/env python3
"""Push v65 artifacts via subprocess to avoid git hook issues."""
import subprocess, sys

cmds = [
    ['git', '-C', '/opt/glava', 'add', 'collab/runs/karakulina-v65-artifacts/'],
    ['git', '-C', '/opt/glava', 'commit', '-m', 'runs: karakulina v65 partial artifacts Stage1+Stage2+validators'],
    ['git', '-C', '/opt/glava', 'push', 'origin', 'runs/karakulina-v65-artifacts'],
]
for cmd in cmds:
    print('Running:', ' '.join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    print('stdout:', r.stdout)
    print('stderr:', r.stderr)
    if r.returncode != 0:
        print('FAILED:', r.returncode)
        sys.exit(1)
    print('OK')
print('PUSH_DONE')
