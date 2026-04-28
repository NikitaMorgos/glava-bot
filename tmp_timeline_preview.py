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

# Layout: left column = period, right column = content
col1_w = 30*mm  # period column
col_gap = 5*mm
col2_w = tw - col1_w - col_gap  # content column

out = r'C:\Users\user\Downloads\timeline_preview.pdf'
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
     'Родилась 17 декабря 1920 года в селе Мариевка. В 1933 году голод разрушил семью: мать умерла, отец ушёл на заработки. Тринадцатилетней попала в детдом, откуда её забрала старшая сестра Полина в Старобельск.'),
    ('1938–1941', 'Учёба и первая работа',
     'Поступила в Кировоградскую фельдшерско-акушерскую школу. После окончания в 1940 году получила специальность акушерки и была направлена в село Глинск.'),
    ('1941–1945', 'Война',
     'Призвана 23 июня 1941 года. Служила старшей медсестрой хирургического отделения на Юго-Западном и 4-м Украинском фронтах. Награждена медалью «За боевые заслуги» (1943) и орденом «Красная Звезда» (1945). Демобилизовалась в Германии 24 декабря 1945 года.'),
    ('1946–1962', 'Семья и переезды',
     'В 1946 году вышла замуж за Дмитрия Каракулина. Жили в Германии, Вышнем Волочке, Калинине. Родились сын Валерий (1948) и дочь Татьяна (1956). С 1958 по 1962 год жили в Венгрии.'),
    ('1962–1994', 'Оседание и карьера',
     'После демобилизации мужа семья получила квартиру в посёлке Химинститут. Тридцать два года проработала медсестрой в поликлинике. Звание «Ударник коммунистического труда» (1965), медаль за доблестный труд (1970). В 1978 году умер муж Дмитрий.'),
    ('1994–2005', 'Последние годы',
     'В августе 1994 года вышла на пенсию. После замужества дочери в 1996 году осталась одна в квартире. В 2005 году сломала ногу и переехала к дочери.'),
]

# === PAGE 1: Timeline ===
c.setFillColor(bg)
c.rect(0, 0, pw, ph, fill=True, stroke=False)

y = ph - mt

# Header "ХРОНОЛОГИЯ ЖИЗНИ"
c.setFont(fsb, 7)
c.setFillColor(acc)
c.drawString(ml, y, 'ХРОНОЛОГИЯ ЖИЗНИ')
y -= 6*mm

for period, title, text in timeline:
    # Period (left column)
    c.setFont(fsb, 7)
    c.setFillColor(label_gray)
    c.drawString(ml, y, period)

    # Title (right column, bold)
    c.setFont(fb, 10)
    c.setFillColor(tc)
    c.drawString(ml + col1_w + col_gap, y, title)
    y -= 5*mm

    # Description (right column, regular)
    y = draw_text(c, text, ml + col1_w + col_gap, y, col2_w, fn, 9, 13)
    y -= 4*mm

c.setFont(fsb, 7)
c.setFillColor(HexColor('#cccccc'))
c.drawCentredString(pw/2, 8*mm, '2')
c.showPage()

c.save()
print(f'Created: {out}')
