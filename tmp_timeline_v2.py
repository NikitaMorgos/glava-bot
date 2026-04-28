from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

try:
    pdfmetrics.registerFont(TTFont('PTSerif', 'fonts/PTSerif-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('PTSerif-Bold', 'fonts/PTSerif-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('PTSans-Bold', 'fonts/PTSans-Bold.ttf'))
    has_fonts = True
except:
    has_fonts = False

fn = 'PTSerif' if has_fonts else 'Times-Roman'
fb = 'PTSerif-Bold' if has_fonts else 'Times-Bold'
fsb = 'PTSans-Bold' if has_fonts else 'Helvetica-Bold'

pw, ph = 148*mm, 210*mm
mt, mb, ml, mr = 18*mm, 14*mm, 16*mm, 14*mm
tw = pw - ml - mr

bg = HexColor('#faf6f0')
tc = HexColor('#3d2e1f')
acc = HexColor('#c4a070')
label_gray = HexColor('#8b7355')

# Timeline column layout
line_x = ml + 10*mm  # vertical line position
dot_r = 1.5*mm       # dot radius
text_x = line_x + 6*mm  # text starts after dot

out = r'C:\Users\user\Downloads\timeline_v2_preview.pdf'
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

def draw_text(c, t, x, y, w, f=fn, s=9, l=13, col=tc):
    c.setFont(f, s); c.setFillColor(col)
    for line in wrap(c, t, f, s, w):
        if y < mb: break
        c.drawString(x, y, line); y -= l
    return y

timeline = [
    ('1920–1938', 'Детство и сиротство',
     'Родилась в селе Мариевка. В 1933 году голод разрушил семью: мать умерла, отец ушёл на заработки. Тринадцатилетней попала в детдом, откуда её забрала старшая сестра Полина в Старобельск.'),
    ('1938–1941', 'Учёба и первая работа',
     'Поступила в Кировоградскую фельдшерско-акушерскую школу. В 1940 году получила специальность акушерки и была направлена в село Глинск.'),
    ('1941–1945', 'Война',
     'Призвана 23 июня 1941 года. Служила старшей медсестрой хирургического отделения на двух фронтах. Медаль «За боевые заслуги» (1943), орден «Красная Звезда» (1945).'),
    ('1946–1962', 'Семья и переезды',
     'Вышла замуж за Дмитрия Каракулина. Жили в Германии, Вышнем Волочке, Калинине, Венгрии. Родились сын Валерий (1948) и дочь Татьяна (1956).'),
    ('1962–1994', 'Оседание и карьера',
     'Квартира в посёлке Химинститут. Тридцать два года в поликлинике. «Ударник коммунистического труда» (1965). В 1978 году умер муж.'),
    ('1994–2005', 'Последние годы',
     'Вышла на пенсию. После замужества дочери осталась одна в квартире. В 2005 году переехала к дочери после перелома ноги.'),
]

c.setFillColor(bg)
c.rect(0, 0, pw, ph, fill=True, stroke=False)

y = ph - mt

# Section header "ХРОНОЛОГИЯ ЖИЗНИ"
c.setFont(fsb, 7)
c.setFillColor(acc)
c.drawString(ml, y, 'ХРОНОЛОГИЯ ЖИЗНИ')
y -= 8*mm

# Calculate total height of timeline
entries_y = []  # save dot positions
start_y = y

# First pass: measure heights and collect dot positions
temp_c = canvas.Canvas('/tmp/null.pdf', pagesize=(pw, ph))
try:
    pdfmetrics.registerFont(TTFont('PTSerif_m', 'fonts/PTSerif-Regular.ttf'))
except:
    pass
positions = []
cur_y = y
for period, title, text in timeline:
    dot_y = cur_y - 1*mm
    positions.append(dot_y)
    # Period + title on same line (or period above title)
    cur_y -= 5*mm  # period line
    cur_y -= 5*mm  # title line
    # Wrap text with content width
    content_w = tw - (text_x - ml) - 4*mm
    lines = wrap(temp_c, text, fn, 9, content_w)
    cur_y -= len(lines) * 13  # text
    cur_y -= 5*mm  # spacing

end_y = cur_y

# Draw vertical line from first dot to last dot
c.setStrokeColor(acc)
c.setLineWidth(1)
if positions:
    c.line(line_x, positions[0], line_x, positions[-1])

# Second pass: actually draw
for i, (period, title, text) in enumerate(timeline):
    dot_y = positions[i]

    # Dot
    c.setFillColor(acc)
    c.circle(line_x, dot_y, dot_r, fill=1, stroke=0)

    # Period
    c.setFont(fsb, 7)
    c.setFillColor(label_gray)
    c.drawString(text_x, dot_y - 1*mm, period)
    row_y = dot_y - 1*mm - 5*mm

    # Title
    c.setFont(fb, 10)
    c.setFillColor(tc)
    c.drawString(text_x, row_y, title)
    row_y -= 5*mm

    # Description
    content_w = tw - (text_x - ml) - 4*mm
    row_y = draw_text(c, text, text_x, row_y, content_w, fn, 9, 13)

# Page number
c.setFont(fsb, 7)
c.setFillColor(HexColor('#cccccc'))
c.drawCentredString(pw/2, 8*mm, '2')
c.showPage()

c.save()
print(f'Created: {out}')
