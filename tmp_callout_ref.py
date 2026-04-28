from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

try:
    pdfmetrics.registerFont(TTFont('PTSerif', 'fonts/PTSerif-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('PTSerif-Italic', 'fonts/PTSerif-Italic.ttf'))
    pdfmetrics.registerFont(TTFont('PTSerif-Bold', 'fonts/PTSerif-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('PTSans-Bold', 'fonts/PTSans-Bold.ttf'))
except:
    pass

fn = 'PTSerif'
fi = 'PTSerif-Italic'
fb = 'PTSerif-Bold'
fsb = 'PTSans-Bold'

pw, ph = 148*mm, 210*mm
mt, mb, ml, mr = 18*mm, 14*mm, 16*mm, 14*mm
tw = pw - ml - mr

bg = HexColor('#faf6f0')
tc = HexColor('#3d2e1f')
acc = HexColor('#c4a070')
cap = HexColor('#8b7355')

out = r'C:\Users\user\Downloads\callout_reference.pdf'
c = canvas.Canvas(out, pagesize=(pw, ph))

def wrap(c, t, f, s, w):
    words, lines, cur = t.split(), [], ''
    for word in words:
        test = cur+' '+word if cur else word
        if c.stringWidth(test, f, s) <= w: cur = test
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines

def dp(c, t, x, y, w, f=fn, s=9.5, l=14, col=tc):
    c.setFont(f, s); c.setFillColor(col)
    for line in wrap(c, t, f, s, w):
        if y < mb: break
        c.drawString(x, y, line); y -= l
    return y

c.setFillColor(bg)
c.rect(0, 0, pw, ph, fill=True, stroke=False)

y = ph - mt

# Body text before
p_before = 'После смерти мужа в 1978 году характер изменился — появились сварливость, недовольство, особенно строгость по отношению к внукам. «От рук отбились», — говорила она о них, когда те не мыли посуду или шалили.'
y = dp(c, p_before, ml, y, tw)
y -= 10*mm

# === CALLOUT ===
callout_text = 'Пережив сиротство, она стала очень самостоятельной и привыкла полагаться только на себя.'

callout_inset = 10*mm
cl = ml + callout_inset
cr = pw - mr - callout_inset
cw = cr - cl

# Top line
c.setStrokeColor(acc)
c.setLineWidth(0.5)
c.line(cl, y, cr, y)
y -= 16  # padding top

# Callout text — PT Serif Italic 13pt, left align, leading 20pt
c.setFont(fi, 13)
c.setFillColor(tc)
lines = wrap(c, callout_text, fi, 13, cw)
for line in lines:
    c.drawString(cl, y, line)
    y -= 20

y -= 6  # space between text and attribution

# Attribution — PT Serif Italic 8pt, right align, color #8b7355
c.setFont(fi, 8)
c.setFillColor(cap)
c.drawRightString(cr, y, '\u2014 из воспоминаний семьи')
y -= 12  # padding bottom

# Bottom line
c.setStrokeColor(acc)
c.setLineWidth(0.5)
c.line(cl, y, cr, y)
y -= 10*mm

# Body text after
p_after = 'Валентина была «стойким оловянным солдатиком» — не показывала слёз, капризов или нытья, даже когда было очень тяжело. Нельзя сказать, что она была очень эмоциональной — скорее, сдержанной.'
y = dp(c, p_after, ml, y, tw)

# Page number
c.setFont(fsb, 7)
c.setFillColor(HexColor('#cccccc'))
c.drawCentredString(pw/2, 8*mm, '10')

# Specification note at bottom
c.setFont(fsb, 6)
c.setFillColor(HexColor('#999999'))
spec_y = 16*mm
c.drawString(ml, spec_y + 6, 'Спецификация callout:')
c.setFont(fn, 6)
specs = [
    'Текст: PT Serif Italic 13pt, цвет #3d2e1f, leading 20pt, align left',
    'Линии: #c4a070, 0.5pt, сверху и снизу, без фона',
    'Подпись: PT Serif Italic 8pt, цвет #8b7355, align right',
    'Отступы: 16pt сверху, 6pt между текстом и подписью, 12pt снизу',
    'Inset по бокам: 10mm от основных полей',
]
sy = spec_y - 2
for line in specs:
    c.drawString(ml, sy, line)
    sy -= 7

c.showPage()
c.save()
print(f'Created: {out}')
