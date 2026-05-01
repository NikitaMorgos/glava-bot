import subprocess
result = subprocess.run(
    ['pdftotext', '/opt/glava/exports/karakulina_stage4_gate_2c_20260501_080607.pdf', '-'],
    capture_output=True, text=True
)
text = result.stdout
hashes = [l for l in text.split('\n') if '##' in l or l.strip().startswith('###')]
if hashes:
    print('FAIL: found ## symbols:', hashes[:5])
else:
    print('OK: no ## symbols in PDF')
subheadings_check = ['Строгость как проявление любви', 'Итог: человек своей эпохи']
found = [s for s in subheadings_check if s in text]
missing = [s for s in subheadings_check if s not in text]
print(f'Subheadings in PDF: {found}')
if missing:
    print(f'MISSING subheadings: {missing}')
