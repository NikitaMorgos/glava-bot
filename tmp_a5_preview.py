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
fi = 'PTSerif-Italic' if has_fonts else 'Times-Italic'
fb = 'PTSerif-Bold' if has_fonts else 'Times-Bold'
fs_sans = 'PTSans-Bold' if has_fonts else 'Helvetica-Bold'

pw, ph = 148*mm, 210*mm
mt, mb, ml, mr = 18*mm, 14*mm, 16*mm, 14*mm
tw = pw - ml - mr
sz, ld = 9.5, 14

bg = HexColor('#faf6f0')
acc = HexColor('#c4a070')
tc = HexColor('#3d2e1f')
hbg = HexColor('#f0ebe0')
htc = HexColor('#5a4a38')
cap = HexColor('#8b7355')
phc = HexColor('#e0d5c5')

out = r'C:\Users\user\Downloads\a5_photo_layout_preview.pdf'
c = canvas.Canvas(out, pagesize=(pw, ph))

def dbg(c): c.setFillColor(bg); c.rect(0,0,pw,ph,fill=True,stroke=False)
def dpn(c,n): c.setFont(fs_sans,7); c.setFillColor(HexColor('#ccc')); c.drawCentredString(pw/2,8*mm,str(n))

def wrap(c, t, f, s, w):
    words, lines, cur = t.split(), [], ''
    for word in words:
        test = cur+' '+word if cur else word
        if c.stringWidth(test,f,s)<=w: cur=test
        else:
            if cur: lines.append(cur)
            cur=word
    if cur: lines.append(cur)
    return lines

def dp(c, t, x, y, w, f=fn, s=sz, l=ld, col=tc):
    c.setFont(f,s); c.setFillColor(col)
    for line in wrap(c,t,f,s,w):
        if y<mb: break
        c.drawString(x,y,line); y-=l
    return y

p1='Валентина Ивановна Каракулина родилась 17 декабря 1920 года в селе Мариевка Новомиргородского района Кировоградской области. Отец Иван Андреевич работал плотником, мать Пелагея Алексеевна трудилась в колхозе.'
p2='В 1933 году голод разрушил семью. Отец ушёл на заработки, а мать умерла. Тринадцатилетняя Валентина попала в детдом, откуда её забрала старшая сестра Полина в Старобельск Луганской области.'
p3='В 1938 году Валентина поступила в Кировоградскую фельдшерско-акушерскую школу. Училась до 1940 года, получила специальность акушерки и была направлена в село Глинск.'
p4='23 июня 1941 года, на второй день войны, Валентину призвали в армию. Служила старшей медсестрой хирургического отделения в госпиталях на Юго-Западном и 4-м Украинском фронтах.'
p5='В 1946 году встретила Дмитрия Каракулина. Через две недели поженились в Старобельске и уехали в Германию.'
hist='К лету 1941 года нацистская Германия контролировала большую часть Европы. Нападение на СССР стало крупнейшей военной операцией в истории.'
callout='Пережив сиротство, она стала очень самостоятельной и привыкла полагаться только на себя.'

# === P1: Chapter start — title on top, PHOTO below, NO TEXT ===
dbg(c)
# Title block at top
c.setFont(fs_sans,7); c.setFillColor(acc)
c.drawString(ml, ph-mt, 'Глава 02')
c.setFont(fb,16); c.setFillColor(tc)
c.drawString(ml, ph-mt-14*mm, 'История жизни')
c.setStrokeColor(acc); c.setLineWidth(1.5)
c.line(ml, ph-mt-17*mm, ml+25*mm, ph-mt-17*mm)
# Photo below title
photo_top = ph - mt - 24*mm
photo_h = photo_top - mb
c.setFillColor(phc)
c.roundRect(ml, mb, tw, photo_h, 3, fill=True, stroke=False)
c.setFont(fi, 8); c.setFillColor(cap)
c.drawCentredString(pw/2, mb+photo_h/2, '[ФОТО — начало главы]')
dpn(c,3); c.showPage()

# === P2: Text only ===
dbg(c)
y = ph - mt
for p in [p1,p2,p3]: y = dp(c,p,ml,y,tw); y -= 6
dpn(c,4); c.showPage()

# === P3: Text + hist block ===
dbg(c)
y = ph - mt
y = dp(c,p4,ml,y,tw); y -= 10
bh = 28*mm; by = y-bh
c.setFillColor(hbg); c.rect(0,by,pw,bh,fill=True,stroke=False)
c.setFillColor(acc); c.rect(0,by,2,bh,fill=True,stroke=False)
c.setFont(fs_sans,6); c.setFillColor(acc)
c.drawString(10*mm, by+bh-9, 'ИСТОРИЧЕСКАЯ СПРАВКА')
dp(c,hist,10*mm,by+bh-20,tw-4*mm,fi,8.5,12,htc)
y = by-10
y = dp(c,p5,ml,y,tw)
dpn(c,5); c.showPage()

# === P4: Text + callout ===
dbg(c)
y = ph - mt
y = dp(c,p1,ml,y,tw); y -= 12
cl,cr = ml+6*mm, pw-mr-6*mm; cw = cr-cl
c.setStrokeColor(acc); c.setLineWidth(0.5)
c.line(cl,y,cr,y); y -= 14
y = dp(c,callout,cl+2*mm,y,cw-4*mm,fi,11,16)
y -= 5
c.setFont(fi,7); c.setFillColor(cap)
c.drawRightString(cr, y, '\u2014 из воспоминаний семьи')
y -= 6; c.line(cl,y,cr,y); y -= 12
y = dp(c,p3,ml,y,tw)
dpn(c,6); c.showPage()

# === P5: Next chapter — title on top, PHOTO below ===
dbg(c)
c.setFont(fs_sans,7); c.setFillColor(acc)
c.drawString(ml, ph-mt, 'Глава 03')
c.setFont(fb,16); c.setFillColor(tc)
c.drawString(ml, ph-mt-14*mm, 'Портрет человека')
c.setStrokeColor(acc); c.setLineWidth(1.5)
c.line(ml, ph-mt-17*mm, ml+25*mm, ph-mt-17*mm)
photo_top2 = ph - mt - 24*mm
photo_h2 = photo_top2 - mb
c.setFillColor(phc)
c.roundRect(ml, mb, tw, photo_h2, 3, fill=True, stroke=False)
c.setFont(fi,8); c.setFillColor(cap)
c.drawCentredString(pw/2, mb+photo_h2/2, '[ФОТО — начало главы]')
dpn(c,7); c.showPage()

# === P6: Text (portrait chapter) ===
dbg(c)
y = ph - mt
y = dp(c,'Валентина Ивановна была человеком, которого сформировали самые тяжёлые испытания XX века. Голод 1933 года, потеря родителей и детдом сформировали в ней железную внутреннюю опору.',ml,y,tw)
y -= 6
y = dp(c,'Она была как муравей, а не стрекоза из известной басни. К искусству тяги не было, зато трудолюбие стало второй натурой.',ml,y,tw)
y -= 6
y = dp(c,'Характер у неё был добрый, но вспыльчивый — могла зарубиться на пустом месте и устроить скандал. Но отходчивая. После смерти мужа появилось больше недовольства.',ml,y,tw)
dpn(c,8); c.showPage()

# === P7: Photo section — 1 vertical ===
dbg(c)
c.setFont(fs_sans,7); c.setFillColor(acc)
c.drawString(ml, ph-mt+3*mm, 'ФОТОГРАФИИ')
c.setFillColor(phc)
c.roundRect(ml, ph/2+5*mm, tw, ph/2-mt-8*mm, 3, fill=True, stroke=False)
c.setFont(fi,8); c.setFillColor(cap)
c.drawCentredString(pw/2, ph*3/4, '[Фото 1 — вертикальное]')
c.setFont(fi,7.5); c.setFillColor(cap)
c.drawCentredString(pw/2, ph/2-2*mm, 'Валентина, 1944')
dpn(c,15); c.showPage()

# === P8: Photo section — 2 horizontal ===
dbg(c)
half = (ph-mt-mb-10*mm)/2
c.setFillColor(phc)
c.roundRect(ml, ph-mt-half, tw, half-5*mm, 3, fill=True, stroke=False)
c.setFont(fi,8); c.setFillColor(cap)
c.drawCentredString(pw/2, ph-mt-half/2, '[Фото 2 — горизонтальное]')
c.setFont(fi,7.5); c.setFillColor(cap)
c.drawCentredString(pw/2, ph-mt-half-1*mm, 'Семья, 1958')
c.setFillColor(phc)
c.roundRect(ml, mb+15*mm, tw, half-5*mm, 3, fill=True, stroke=False)
c.setFont(fi,8); c.setFillColor(cap)
c.drawCentredString(pw/2, mb+15*mm+(half-5*mm)/2, '[Фото 3 — горизонтальное]')
c.setFont(fi,7.5); c.setFillColor(cap)
c.drawCentredString(pw/2, mb+8*mm, 'На даче, 1965')
dpn(c,16); c.showPage()

c.save()
print(f'Created: {out}')
print('8 pages A5 (148x210mm):')
print('  p1: Ch.02 start — photo + title (NO text)')
print('  p2-4: Text pages')
print('  p5: Ch.03 start — photo + title (NO text)')
print('  p6: Text page')
print('  p7-8: Photo section at end')
