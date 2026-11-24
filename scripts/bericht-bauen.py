#!/usr/bin/env python3
"""Baut den mehrseitigen Pilgerbericht als PDF (je Sprache) aus data/statistik-voll.json.
Aufruf:  python3 scripts/bericht-bauen.py            (alle sechs Sprachen)
Ergebnis: data/berichte/pilgerbericht-<sprache>.pdf
Benötigt: reportlab (pip install reportlab), Schrift DejaVu Sans."""
import json, os, sys, datetime, math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
D = json.load(open(os.path.join(WURZEL, 'data', 'statistik-voll.json'), encoding='utf-8'))
N = json.load(open(os.path.join(WURZEL, 'data', 'bericht', 'bericht-namen.json'), encoding='utf-8'))
ALIAS = json.load(open(os.path.join(WURZEL, 'data', 'bericht', 'startort-kanon.json'), encoding='utf-8'))['alias']
for _r, _k in ALIAS.get('land', {}).items():
    if _k not in D['sprache_land'] and _r in D['sprache_land']: D['sprache_land'][_k] = D['sprache_land'][_r]

for pfad in ('/usr/share/fonts/truetype/dejavu', os.path.join(HIER, 'fonts'), 'C:/Windows/Fonts'):
    if os.path.exists(os.path.join(pfad, 'DejaVuSans.ttf')):
        pdfmetrics.registerFont(TTFont('F', os.path.join(pfad, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('FB', os.path.join(pfad, 'DejaVuSans-Bold.ttf')))
        break
else:
    sys.exit('DejaVuSans.ttf nicht gefunden (Ordner tools/fonts anlegen und Dateien dort ablegen).')

DUNKEL, GOLD, GRAU, LINIE, TEXT = HIER and HexColor('#1d3b3d'), HexColor('#c2882b'), HexColor('#6b655b'), HexColor('#d9d2c3'), HexColor('#1f1f1f')
LANGS = ['de', 'en', 'es', 'gl', 'fr', 'hu']

TX = {
 'de': dict(titel='Pilgerbericht %s', unter='Pilger in Santiago de Compostela · Stand der Daten: %s', blick='Auf einen Blick', gesamt='Pilger gesamt', spanier='davon Spanier', ausl='davon Ausländer', vj='gegenüber %s', s_jahre='Pilger pro Jahr seit 2004', s_monate='Monat für Monat: %s im Vergleich zu %s', s_weg='Auf welchem Weg?', s_land='Woher kommen sie?', s_region='Aus welcher Region Spaniens?', s_startort='Wo starten sie?', s_motiv='Warum gehen sie?', s_sprache='Welche Sprachen? (nach Herkunftsland)', s_geschlecht='Männer oder Frauen?', s_alter='Wie alt sind sie?', s_fortbewegung='Zu Fuß, Rad oder Pferd?', s_beruf='Welcher Beruf?', jahr_bez='Jahr %s', stand19='Jahr 2019 – die letzten veröffentlichten Jahreswerte zu dieser Frage', basis_sp='Anteile an den spanischen Pilgern', quelle='Quelle: Oficina del Peregrino, Santiago de Compostela. Aufbereitet von steffenpfeiffer.es.', hinweis_sprache='Die Sprache ist aus dem Herkunftsland abgeleitet.', ohne='nicht zugeordnet', seite='Seite %s', mon=['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'], datum='%d.%m.%Y'),
 'en': dict(titel='Pilgrim report %s', unter='Pilgrims in Santiago de Compostela · Data as of: %s', blick='At a glance', gesamt='Total pilgrims', spanier='of them Spanish', ausl='of them foreign', vj='compared with %s', s_jahre='Pilgrims per year since 2004', s_monate='Month by month: %s compared with %s', s_weg='Which route?', s_land='Where do they come from?', s_region='Which region of Spain?', s_startort='Where do they start?', s_motiv='Why do they walk?', s_sprache='Which languages? (by country of origin)', s_geschlecht='Men or women?', s_alter='How old are they?', s_fortbewegung='On foot, by bike or on horse?', s_beruf='What jobs do they have?', jahr_bez='Year %s', stand19='Year 2019 – the latest published annual figures for this question', basis_sp='Shares of the Spanish pilgrims', quelle='Source: Oficina del Peregrino, Santiago de Compostela. Prepared by steffenpfeiffer.es.', hinweis_sprache='The language is derived from the country of origin.', ohne='not assigned', seite='Page %s', mon=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], datum='%d/%m/%Y'),
 'es': dict(titel='Informe del peregrino %s', unter='Peregrinos en Santiago de Compostela · Datos a fecha de: %s', blick='De un vistazo', gesamt='Total de peregrinos', spanier='de ellos españoles', ausl='de ellos extranjeros', vj='frente a %s', s_jahre='Peregrinos por año desde 2004', s_monate='Mes a mes: %s frente a %s', s_weg='¿Qué camino?', s_land='¿De dónde vienen?', s_region='¿De qué región de España?', s_startort='¿Dónde empiezan?', s_motiv='¿Por qué caminan?', s_sprache='¿Qué idiomas? (según el país de origen)', s_geschlecht='¿Hombres o mujeres?', s_alter='¿Qué edad tienen?', s_fortbewegung='¿A pie, en bici o a caballo?', s_beruf='¿Qué profesión tienen?', jahr_bez='Año %s', stand19='Año 2019: las últimas cifras anuales publicadas sobre esta pregunta', basis_sp='Porcentajes sobre los peregrinos españoles', quelle='Fuente: Oficina del Peregrino, Santiago de Compostela. Elaborado por steffenpfeiffer.es.', hinweis_sprache='El idioma se deduce del país de origen.', ohne='sin asignar', seite='Página %s', mon=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'], datum='%d/%m/%Y'),
 'gl': dict(titel='Informe do peregrino %s', unter='Peregrinos en Santiago de Compostela · Datos a data de: %s', blick='Dunha ollada', gesamt='Total de peregrinos', spanier='deles españois', ausl='deles estranxeiros', vj='fronte a %s', s_jahre='Peregrinos por ano desde 2004', s_monate='Mes a mes: %s fronte a %s', s_weg='Que camiño?', s_land='De onde veñen?', s_region='De que rexión de España?', s_startort='Onde comezan?', s_motiv='Por que camiñan?', s_sprache='Que idiomas? (segundo o país de orixe)', s_geschlecht='Homes ou mulleres?', s_alter='Que idade teñen?', s_fortbewegung='A pé, en bici ou a cabalo?', s_beruf='Que profesión teñen?', jahr_bez='Ano %s', stand19='Ano 2019: as últimas cifras anuais publicadas sobre esta pregunta', basis_sp='Porcentaxes sobre os peregrinos españois', quelle='Fonte: Oficina del Peregrino, Santiago de Compostela. Elaborado por steffenpfeiffer.es.', hinweis_sprache='O idioma dedúcese do país de orixe.', ohne='sen asignar', seite='Páxina %s', mon=['xan','feb','mar','abr','mai','xuñ','xul','ago','set','out','nov','dec'], datum='%d/%m/%Y'),
 'fr': dict(titel='Rapport des pèlerins %s', unter='Pèlerins à Saint-Jacques-de-Compostelle · Données au : %s', blick='En un coup d’œil', gesamt='Total des pèlerins', spanier='dont Espagnols', ausl='dont étrangers', vj='par rapport à %s', s_jahre='Pèlerins par an depuis 2004', s_monate='Mois par mois : %s par rapport à %s', s_weg='Quel chemin ?', s_land='D’où viennent-ils ?', s_region='De quelle région d’Espagne ?', s_startort='Où commencent-ils ?', s_motiv='Pourquoi marchent-ils ?', s_sprache='Quelles langues ? (selon le pays d’origine)', s_geschlecht='Hommes ou femmes ?', s_alter='Quel âge ont-ils ?', s_fortbewegung='À pied, à vélo ou à cheval ?', s_beruf='Quelle profession ?', jahr_bez='Année %s', stand19='Année 2019 : les derniers chiffres annuels publiés sur cette question', basis_sp='Parts des pèlerins espagnols', quelle='Source : Oficina del Peregrino, Santiago de Compostela. Mis en forme par steffenpfeiffer.es.', hinweis_sprache='La langue est déduite du pays d’origine.', ohne='non attribué', seite='Page %s', mon=['janv.','févr.','mars','avr.','mai','juin','juil.','août','sept.','oct.','nov.','déc.'], datum='%d/%m/%Y'),
 'hu': dict(titel='Zarándokjelentés %s', unter='Zarándokok Santiago de Compostelában · Az adatok állapota: %s', blick='Egy pillantásra', gesamt='Zarándokok összesen', spanier='ebből spanyol', ausl='ebből külföldi', vj='előző év: %s', s_jahre='Zarándokok évente 2004 óta', s_monate='Hónapról hónapra: %s és %s összehasonlítása', s_weg='Melyik út?', s_land='Honnan jönnek?', s_region='Spanyolország melyik régiójából?', s_startort='Hol indulnak?', s_motiv='Miért zarándokolnak?', s_sprache='Milyen nyelveken beszélnek? (származási ország szerint)', s_geschlecht='Férfiak vagy nők?', s_alter='Hány évesek?', s_fortbewegung='Gyalog, biciklivel vagy lóháton?', s_beruf='Milyen foglalkozásúak?', jahr_bez='%s. év', stand19='2019 – az erre a kérdésre utoljára közzétett éves adatok', basis_sp='A spanyol zarándokok arányában', quelle='Forrás: Oficina del Peregrino, Santiago de Compostela. Feldolgozta: steffenpfeiffer.es.', hinweis_sprache='A nyelv a származási országból következik.', ohne='nem besorolt', seite='%s. oldal', mon=['jan','feb','már','ápr','máj','jún','júl','aug','szep','okt','nov','dec'], datum='%Y.%m.%d.'),
}

def zahl(n, l):
    s = '{:,}'.format(int(round(n)))
    return s.replace(',', '.' if l in ('de', 'es', 'gl') else ('\u202f' if l in ('fr', 'hu') else ','))
def prozent(p, l):
    if p < 0.1 and p > 0: t = '<0,1' if l != 'en' else '<0.1'
    else: t = ('%.1f' % p) if l == 'en' else ('%.1f' % p).replace('.', ',')
    return t + (' %' if l != 'en' else '%')

def jahressumme(j):
    k = D['kennzahlen'].get(str(j))
    if k and k.get('Pilger gesamt'): return k['Pilger gesamt']
    for dim in ('geschlecht', 'land'):
        r = D['jahr'].get(dim, {}).get(str(j))
        if r: return sum(p[1] for p in r)
    return None

def liste(dim, j, monat=0):
    q = 'land' if dim == 'sprache' else dim
    roh = (D['monat'][q][str(j)][str(monat)] if monat else D['jahr'][q][str(j)])
    namen = D['namen'][q]
    m = {}
    al = ALIAS.get(q, {})
    for k, v in roh:
        n = al.get(namen[k], namen[k]); m[n] = m.get(n, 0) + v
    if dim == 'sprache':
        s = {}
        for land, v in m.items():
            sp = D['sprache_land'].get(land, '__ohne'); s[sp] = s.get(sp, 0) + v
        return s
    return m

ALTER_REIHE = ['0-12', '13-18', '19-35', '36-65', '>65', '<30', '30-60', '>60']

def bauen(l):
    t, nm = TX[l], N['namen'][l]
    voll = [int(j) for j, mo in D['gesamt'].items() if len(mo) >= 12]
    bj = max(voll); vj = bj - 1
    st = datetime.date.fromisoformat(D['stand'])
    stand = st.strftime(t['datum'])
    pfad = os.path.join(WURZEL, 'data', 'berichte', 'pilgerbericht-%s.pdf' % l)
    c = canvas.Canvas(pfad, pagesize=A4)
    c.setTitle(t['titel'] % bj); c.setAuthor('steffenpfeiffer.es')
    W, H = A4; RL, RR, RO, RU = 52, 52, 60, 56
    S = {'y': H - RO, 'seite': 0}

    def marke():
        c.saveState(); c.setFillColor(HexColor('#1d3b3d')); c.setFillAlpha(0.06); c.setFont('FB', 58)
        c.translate(W / 2, H / 2); c.rotate(32); c.drawCentredString(0, 0, 'steffenpfeiffer.es'); c.restoreState()
    def seitenkopf():
        S['seite'] += 1; marke()
        c.setStrokeColor(DUNKEL); c.setLineWidth(1.2); c.line(RL, H - 36, W - RR, H - 36)
        c.setFont('FB', 8); c.setFillColor(DUNKEL); c.drawString(RL, H - 30, 'STEFFENPFEIFFER.ES')
        c.setFont('F', 8); c.setFillColor(GRAU); c.drawRightString(W - RR, H - 30, t['titel'] % bj)
        c.setFont('F', 8); c.drawString(RL, 30, t['quelle']); c.drawRightString(W - RR, 30, t['seite'] % S['seite'])
        S['y'] = H - RO
    def neu():
        if S['seite']: c.showPage()
        seitenkopf()
    def platz(h):
        if S['y'] - h < RU: neu()
    def ueberschrift(text, sub=None):
        platz(70)
        S['y'] -= 14; c.setFont('FB', 14); c.setFillColor(DUNKEL); c.drawString(RL, S['y'], text)
        S['y'] -= 6
        if sub:
            S['y'] -= 10; c.setFont('F', 8.5); c.setFillColor(GRAU); c.drawString(RL, S['y'], sub)
        S['y'] -= 8

    def balken(dim, j, basis, top=None, sub=None, reihenfolge=None, monat=0):
        m = liste(dim, j, monat)
        ks = reihenfolge(list(m)) if reihenfolge else sorted(m, key=lambda k: -m[k])
        if top: ks = ks[:top]
        mx = max(m[k] for k in ks) or 1
        zh = 15.5
        if len(ks) * zh + 60 < H - RO - RU: platz(len(ks) * zh + 60)
        ueberschrift(t['s_' + dim], sub)
        bx = RL + 176; bb = W - RR - bx - 108
        for k in ks:
            platz(zh + 2)
            S['y'] -= zh
            name = t['ohne'] if k == '__ohne' else nm.get(dim, {}).get(k, k)
            c.setFont('F', 9); c.setFillColor(TEXT)
            if pdfmetrics.stringWidth(name, 'F', 9) > 168:
                while pdfmetrics.stringWidth(name + '…', 'F', 9) > 168 and len(name) > 4: name = name[:-1]
                name = name.rstrip() + '…'
            c.drawString(RL, S['y'] + 3, name)
            c.setFillColor(HexColor('#efe9e1')); c.rect(bx, S['y'] + 2, bb, 8, stroke=0, fill=1)
            c.setFillColor(GOLD if k == ks[0] else DUNKEL); c.rect(bx, S['y'] + 2, max(1.2, bb * m[k] / mx), 8, stroke=0, fill=1)
            c.setFont('FB', 8.5); c.setFillColor(TEXT)
            c.drawRightString(W - RR, S['y'] + 3, zahl(m[k], l) + ' · ' + prozent(100.0 * m[k] / basis, l) if basis else zahl(m[k], l))
        S['y'] -= 6

    # ---- Seite 1: Kennzahlen ----
    neu()
    S['y'] -= 40; c.setFont('FB', 26); c.setFillColor(DUNKEL); c.drawString(RL, S['y'], t['titel'] % bj)
    S['y'] -= 20; c.setFont('F', 10); c.setFillColor(GRAU); c.drawString(RL, S['y'], t['unter'] % stand)
    S['y'] -= 12; c.setStrokeColor(GOLD); c.setLineWidth(2.5); c.line(RL, S['y'], RL + 60, S['y'])
    kz, kzv = D['kennzahlen'][str(bj)], D['kennzahlen'][str(vj)]
    ueberschrift(t['blick'])
    bw = (W - RL - RR - 24) / 3
    for i, (lab, key) in enumerate([(t['gesamt'], 'Pilger gesamt'), (t['spanier'], 'Spanier'), (t['ausl'], 'Ausländer')]):
        x = RL + i * (bw + 12); y0 = S['y'] - 82
        c.setStrokeColor(LINIE); c.setLineWidth(0.8); c.setFillColor(HexColor('#ffffff')); c.rect(x, y0, bw, 82, stroke=1, fill=1)
        c.setFillColor(DUNKEL); c.setFont('FB', 19); c.drawString(x + 12, y0 + 52, zahl(kz[key], l))
        c.setFillColor(GRAU); c.setFont('F', 8.5); c.drawString(x + 12, y0 + 36, lab)
        d = 100.0 * (kz[key] - kzv[key]) / kzv[key]
        c.setFont('FB', 9); c.setFillColor(HexColor('#2f6b3a') if d >= 0 else HexColor('#9b2f2f'))
        txt = ('+' if d >= 0 else '−') + ('%.1f' % abs(d)).replace('.', ',' if l != 'en' else '.') + (' %' if l != 'en' else '%')
        c.drawString(x + 12, y0 + 18, txt); c.setFont('F', 8); c.setFillColor(GRAU); c.drawString(x + 12 + pdfmetrics.stringWidth(txt, 'FB', 9) + 6, y0 + 18, t['vj'] % vj)
    S['y'] -= 100

    # ---- Pilger pro Jahr ----
    jahre = sorted(int(j) for j in D['jahr']['land'])
    ueberschrift(t['s_jahre'])
    gh = 130; platz(gh + 30); y0 = S['y'] - gh - 14
    ws = [(j, jahressumme(j)) for j in jahre if jahressumme(j)]
    mx = max(v for _, v in ws); skala = 100000 * math.ceil(mx / 100000.0)
    gw = W - RL - RR - 34; slot = gw / len(ws); bwid = slot * 0.66
    c.setStrokeColor(LINIE); c.setLineWidth(0.5)
    for f in (0, .5, 1):
        yy = y0 + gh * f; c.line(RL + 34, yy, W - RR, yy); c.setFont('F', 7); c.setFillColor(GRAU); c.drawRightString(RL + 28, yy - 2, zahl(skala * f / 1000, l) + 'k')
    for i, (j, v) in enumerate(ws):
        x = RL + 34 + i * slot + (slot - bwid) / 2
        c.setFillColor(GOLD if j == bj else DUNKEL); c.rect(x, y0, bwid, gh * v / skala, stroke=0, fill=1)
        if j % 2 == 0 or j == ws[-1][0]:
            c.setFont('F', 7); c.setFillColor(GRAU); c.drawCentredString(x + bwid / 2, y0 - 10, str(j)[2:])
    S['y'] = y0 - 24

    # ---- Monatsverlauf ----
    def monat_summen(j): return [D['gesamt'][str(j)].get(str(m), {}).get('Pilger gesamt', 0) for m in range(1, 13)]
    a, v = monat_summen(bj), monat_summen(vj)
    ueberschrift(t['s_monate'] % (bj, vj)); gh = 120; platz(gh + 40); y0 = S['y'] - gh - 14
    mx = max(max(a), max(v)); skala = 10000 * math.ceil(mx / 10000.0); gw = W - RL - RR - 34
    c.setStrokeColor(LINIE); c.setLineWidth(0.5)
    for f in (0, .5, 1):
        yy = y0 + gh * f; c.line(RL + 34, yy, W - RR, yy); c.setFont('F', 7); c.setFillColor(GRAU); c.drawRightString(RL + 28, yy - 2, zahl(skala * f / 1000, l) + 'k')
    def pt(i, val): return RL + 34 + gw * (i + 0.5) / 12, y0 + gh * val / skala
    for serie, farbe, breite, strich in ((v, GRAU, 1, True), (a, GOLD, 2.2, False)):
        c.setStrokeColor(farbe); c.setLineWidth(breite); c.setDash(3, 2) if strich else c.setDash()
        p = c.beginPath()
        for i, val in enumerate(serie):
            x, y = pt(i, val); (p.moveTo if i == 0 else p.lineTo)(x, y)
        c.drawPath(p, stroke=1, fill=0); c.setDash()
    for i in range(12):
        x, _ = pt(i, 0); c.setFont('F', 7); c.setFillColor(GRAU); c.drawCentredString(x, y0 - 10, t['mon'][i])
    S['y'] = y0 - 22
    c.setFillColor(GOLD); c.rect(RL, S['y'], 14, 3, stroke=0, fill=1); c.setFont('F', 8); c.setFillColor(TEXT); c.drawString(RL + 19, S['y'] - 2, str(bj))
    c.setStrokeColor(GRAU); c.setDash(3, 2); c.line(RL + 60, S['y'] + 1.5, RL + 74, S['y'] + 1.5); c.setDash(); c.drawString(RL + 79, S['y'] - 2, str(vj))
    S['y'] -= 16

    # ---- Aufschlüsselungen des Berichtsjahres ----
    ges, sp = kz['Pilger gesamt'], kz['Spanier']
    sub = t['jahr_bez'] % bj
    balken('weg', bj, ges, sub=sub)
    balken('land', bj, ges, top=25, sub=sub)
    balken('region', bj, sp, sub=sub + ' · ' + t['basis_sp'])
    balken('startort', bj, ges, top=25, sub=sub)
    balken('motiv', bj, ges, sub=sub)
    balken('sprache', bj, ges, top=15, sub=sub + ' · ' + t['hinweis_sprache'])
    # ---- Nur bis 2019 ----
    g19 = D['kennzahlen']['2019']['Pilger gesamt']
    sub19 = t['stand19']
    balken('geschlecht', 2019, g19, sub=sub19)
    balken('alter', 2019, g19, sub=sub19, reihenfolge=lambda ks: sorted(ks, key=lambda k: ALTER_REIHE.index(k) if k in ALTER_REIHE else 99))
    balken('fortbewegung', 2019, g19, sub=sub19)
    balken('beruf', 2019, g19, top=18, sub=sub19)
    c.showPage(); c.save()
    print('OK', pfad, S['seite'], 'Seiten')

if __name__ == '__main__':
    for l in (sys.argv[1:] or LANGS): bauen(l)
