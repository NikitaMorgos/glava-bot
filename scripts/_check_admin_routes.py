import sys
sys.path.insert(0, '/opt/glava')
from admin.app import app
rules = [str(r) for r in app.url_map.iter_rules() if '/api' in str(r)]
print('\n'.join(sorted(rules)))
