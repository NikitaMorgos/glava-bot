import json
c = json.load(open('/opt/glava/pipeline_config.json'))
gw = c.get('ghostwriter', {})
print('ghostwriter:', json.dumps(gw, indent=2, ensure_ascii=False))
print()
# also check phase_b section
pb = c.get('phase_b', c.get('ghostwriter_phase_b', {}))
print('phase_b:', json.dumps(pb, indent=2, ensure_ascii=False))
