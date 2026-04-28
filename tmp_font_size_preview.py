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

# Sizes: current → -30%
# Chapter title: 24pt → 17pt
# Subheading: 16pt → 11pt
# Body: 9.5pt (unchanged)

ch_title_size = 17
sub_size = 11
body_size = 9.5
body_lead = 14

out = r'C:\Users\user\Downloads\font_size_preview.pdf'
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

def dp(c, t, x, y, w, f=fn, s=body_size, l=body_lead, col=tc):
    c.setFont(f, s); c.setFillColor(col)
    for line in wrap(c, t, f, s, w):
        if y < mb: break
        c.drawString(x, y, line); y -= l
    return y

p1 = 'Валентина Ивановна родилась 17 декабря 1920 года в селе Мариевка Новомиргородского района Кировоградской области. Отец Иван Андреевич работал плотником, мать Пелагея Алексеевна — в колхозе. Валентина была младшим ребёнком в семье, у неё были старшие сёстры и младший брат, который умер в детстве.'
p2 = 'В 1933 году семью настигло страшное бедствие — голод. Отец ушёл на заработки, мать умерла. Тринадцатилетняя Валентина попала в детдом, но её оттуда забрала старшая сестра Полина и увезла в Старобельск Луганской области.'
p3 = 'В Старобельске Валентина училась в школе. В 1938 году поступила в Кировоградскую фельдшерско-акушерскую школу, которую окончила в 1940 году, получив специальность акушерки.'
p4 = 'Валентина была преданной коммунисткой. Вступила в партию в июле 1943 года на фронте и пронесла эти убеждения через всю жизнь. «Победа благодаря Сталину была» — это было её глубокое убеждение.'
p5 = 'Валентина не говорила «я тебя люблю». Она кормила, стирала, гладила, шила. Бисквиты с кремом, который взбивала «каким-то чудным образом», выглаженные рубашки, авоська из зонтика — это был её язык любви.'

# === PAGE 1: Chapter start ===
c.setFillColor(bg)
c.rect(0, 0, pw, ph, fill=True, stroke=False)

y = ph - mt

# Chapter label "Глава 02"
c.setFont(fsb, 8)
c.setFillColor(acc)
c.drawString(ml, y, 'Глава 02')
y -= 6*mm

# Chapter title (17pt = 24 * 0.7)
c.setFont(fsb, ch_title_size)
c.setFillColor(tc)
c.drawString(ml, y, 'История жизни')
y -= 3*mm

# Accent line
c.setStrokeColor(acc)
c.setLineWidth(1.5)
c.line(ml, y, ml + 20*mm, y)
y -= 8*mm

# Subheading (11pt = 16 * 0.7)
c.setFont(fsb, sub_size)
c.setFillColor(tc)
c.drawString(ml, y, 'Детство и голод')
y -= 6*mm

# Body text
y = dp(c, p1, ml, y, tw)
y -= 4
y = dp(c, p2, ml, y, tw)
y -= 6*mm

# Next subheading
c.setFont(fsb, sub_size)
c.setFillColor(tc)
c.drawString(ml, y, 'Юность и учёба')
y -= 6*mm

y = dp(c, p3, ml, y, tw)

c.setFont(fsb, 7)
c.setFillColor(HexColor('#cccccc'))
c.drawCentredString(pw/2, 8*mm, '3')
c.showPage()

# === PAGE 2: Chapter 03 start ===
c.setFillColor(bg)
c.rect(0, 0, pw, ph, fill=True, stroke=False)

y = ph - mt

c.setFont(fsb, 8)
c.setFillColor(acc)
c.drawString(ml, y, 'Глава 03')
y -= 6*mm

c.setFont(fsb, ch_title_size)
c.setFillColor(tc)
c.drawString(ml, y, 'Портрет человека')
y -= 3*mm

c.setStrokeColor(acc)
c.setLineWidth(1.5)
c.line(ml, y, ml + 20*mm, y)
y -= 8*mm

# Flat subheadings — NO "Ценности и установки"
c.setFont(fsb, sub_size)
c.setFillColor(tc)
c.drawString(ml, y, 'Советская идеология как основа мировоззрения')
y -= 6*mm

y = dp(c, p4, ml, y, tw)
y -= 6*mm

c.setFont(fsb, sub_size)
c.setFillColor(tc)
c.drawString(ml, y, 'Труд как форма любви')
y -= 6*mm

y = dp(c, p5, ml, y, tw)

c.setFont(fsb, 7)
c.setFillColor(HexColor('#cccccc'))
c.drawCentredString(pw/2, 8*mm, '8')
c.showPage()

c.save()
print(f'Created: {out}')
print(f'Chapter title: PT Sans Bold {ch_title_size}pt (was 24pt, -30%)')
print(f'Subheading: PT Sans Bold {sub_size}pt (was 16pt, -30%)')
print(f'Body: PT Serif {body_size}pt (unchanged)')
