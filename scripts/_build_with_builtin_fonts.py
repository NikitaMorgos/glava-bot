"""
Заменяет все кастомные шрифты на встроенные ReportLab и запускает сборку PDF.
"""
import os, subprocess
from pathlib import Path

os.chdir('/opt/glava')
src = Path('exports/karakulina_layout_ready.py')
code = src.read_text(encoding='utf-8')

# Замена кастомных шрифтов на встроенные ReportLab
replacements = {
    'PlayfairDisplay-Regular': 'Times-Roman',
    'PlayfairDisplay-Bold':    'Times-Bold',
    'PlayfairDisplay-Italic':  'Times-Italic',
    'Merriweather-Regular':    'Times-Roman',
    'Merriweather-Bold':       'Times-Bold',
    'Merriweather-Italic':     'Times-Italic',
    'Raleway-Regular':         'Helvetica',
    'Raleway-Light':           'Helvetica',
    'Raleway-Bold':            'Helvetica-Bold',
}
for custom, builtin in replacements.items():
    code = code.replace(f"'{custom}'", f"'{builtin}'")
    code = code.replace(f'"{custom}"', f'"{builtin}"')

# Убираем весь блок регистрации шрифтов — он теперь не нужен
import re
# Удаляем try/except блок с pdfmetrics.registerFont
code = re.sub(
    r'# Регистрация шрифтов.*?pass  # уже обработано выше\n',
    '# Используются встроенные шрифты ReportLab\n',
    code, flags=re.DOTALL
)
# Убираем импорт TTFont если остался
code = code.replace('from reportlab.pdfbase.ttfonts import TTFont\n', '')

dst = Path('/tmp/karakulina_builtin_fonts.py')
dst.write_text(code, encoding='utf-8')
print(f'Скрипт готов: {dst}')

# Проверяем синтаксис
import py_compile, sys
try:
    py_compile.compile(str(dst), doraise=True)
    print('Синтаксис OK')
except py_compile.PyCompileError as e:
    print(f'Синтаксическая ошибка: {e}')
    sys.exit(1)

# Запускаем
print('Запускаю сборку PDF...')
result = subprocess.run(
    ['/opt/glava/.venv/bin/python', str(dst)],
    capture_output=True, text=True, cwd='/opt/glava'
)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr[-1500:])
print("Exit code:", result.returncode)
