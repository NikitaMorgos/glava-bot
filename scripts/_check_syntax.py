import ast
for f in ['/opt/glava/scripts/test_stage2_pipeline.py', '/opt/glava/scripts/test_stage2_phase_b.py']:
    try:
        ast.parse(open(f).read())
        print(f'OK: {f.split("/")[-1]}')
    except SyntaxError as e:
        print(f'ERROR: {f.split("/")[-1]}: {e}')
