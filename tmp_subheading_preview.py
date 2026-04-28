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
    has_fonts = True
except:
    has_fonts = False

fn = 'PTSerif' if has_fonts else 'Times-Roman'
fb = 'PTSerif-Bold' if has_fonts else 'Times-Bold'
fi = 'PTSerif-Italic' if has_fonts else 'Times-Italic'
fs_sans = 'PTSans-Bold' if has_fonts else 'Helvetica-Bold'

pw, ph = 148*mm, 210*mm
mt, mb, ml, mr = 18*mm, 14*mm, 16*mm, 14*mm
tw = pw - ml - mr

bg = HexColor('#faf6f0')
tc = HexColor('#3d2e1f')
acc = HexColor('#c4a070')

out = r'C:\Users\user\Downloads\subheading_preview.pdf'
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

p1 = 'Валентина Ивановна родилась 17 декабря 1920 года в селе Мариевка Новомиргородского района Кировоградской области. Отец Иван Андреевич работал плотником, мать Пелагея Алексеевна трудилась в колхозе. Валентина была младшим ребёнком в семье, у неё были старшие сёстры и младший брат, который умер в детстве.'
p2 = 'В 1933 году голод разрушил семью. Отец ушёл на заработки, а мать умерла. Тринадцатилетняя Валентина попала в детдом, откуда её забрала старшая сестра Полина в Старобельск Луганской области.'
p3 = 'В Старобельске Валентина получила возможность продолжить образование. В 1938 году она поступила в Кировоградскую фельдшерско-акушерскую школу, где училась до 1940 года. Получив специальность акушерки, была направлена в Кировоградскую область, Светловодский район, село Глинск.'
p4 = '23 июня 1941 года, на второй день войны, Валентину призвали в Советскую армию. Она служила старшей медсестрой хирургического отделения в военных госпиталях, дослужившись до звания младшего лейтенанта медицинской службы.'
p5 = 'Военный путь пролёг через многие города и страны: Кировоград, Воронеж, Саратов, Фрунзе на Юго-Западном фронте, затем Киев, Западная Украина, Польша, Чехословакия и Германия в составе 4-го Украинского фронта.'

# === PAGE 1 ===
c.setFillColor(bg)
c.rect(0, 0, pw, ph, fill=True, stroke=False)

y = ph - mt

# Subheading: PT Serif Bold, 14pt
c.setFont(fb, 14)
c.setFillColor(tc)
c.drawString(ml, y, 'Детство и голод')
y -= 8*mm  # space after subheading

# Body text
y = dp(c, p1, ml, y, tw)
y -= 5
y = dp(c, p2, ml, y, tw)
y -= 8*mm  # space before next subheading

# Next subheading
c.setFont(fb, 14)
c.setFillColor(tc)
c.drawString(ml, y, 'Юность и учёба')
y -= 8*mm

y = dp(c, p3, ml, y, tw)

# Page number
c.setFont(fs_sans, 7)
c.setFillColor(HexColor('#cccccc'))
c.drawCentredString(pw/2, 8*mm, '5')
c.showPage()

# === PAGE 2 ===
c.setFillColor(bg)
c.rect(0, 0, pw, ph, fill=True, stroke=False)

y = ph - mt

# Subheading
c.setFont(fb, 14)
c.setFillColor(tc)
c.drawString(ml, y, 'Война')
y -= 8*mm

y = dp(c, p4, ml, y, tw)
y -= 5
y = dp(c, p5, ml, y, tw)

c.setFont(fs_sans, 7)
c.setFillColor(HexColor('#cccccc'))
c.drawCentredString(pw/2, 8*mm, '6')
c.showPage()

c.save()
print(f'Created: {out}')
