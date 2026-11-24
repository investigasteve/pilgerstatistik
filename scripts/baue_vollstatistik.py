#!/usr/bin/env python3
"""Erzeugt data/statistik-voll.json für die Statistikseite: Jahres- und Monatswerte je Dimension
(Weg, Land, Region, Startort, Motiv, Geschlecht, Alter, Fortbewegung, Beruf), kompakt über Namenslisten."""
import sqlite3, json, os, collections
HIER = os.path.dirname(os.path.abspath(__file__))
DATEN = os.path.join(HIER, '..', 'data')
con = sqlite3.connect(os.path.join(DATEN, 'pilgerstatistik.sqlite'))

# Zusammenführung abweichender Schreibweisen derselben Angabe (verschiedene Jahre/Quellen). None = weglassen.
ALIAS = {
 'weg': {
  'Frances-Camino de': 'Camino Francés', 'Portugues-Camino': 'Camino Portugués', 'Portugués-Camino': 'Camino Portugués',
  'Norte-Camino de': 'Camino del Norte', 'Primitivo-Camino': 'Camino Primitivo', 'Ingles-Camino': 'Camino Inglés', 'Inglés-Camino': 'Camino Inglés',
  'Via de la Plata': 'Vía de la Plata', 'Muxia-Finisterre': 'Muxía-Finisterre', 'Muxía - Finisterre': 'Muxía-Finisterre',
  'Invierno de Camino': 'Camino de Invierno', 'Camino Portugués de la Costa': 'Camino Portugués por la Costa',
  'Camino Portugues de la costa': 'Camino Portugués por la Costa', 'Camino Portugues de la Costa': 'Camino Portugués por la Costa',
  'Costa Camino Portugués': 'Camino Portugués por la Costa', 'Otros caminos': 'Otros Caminos',
  'Desconocido': None, '(ohne Angabe)': None},
 'motiv': {'Religiosa': 'Religioso', 'Religiosa y otras': 'Religioso y otros', 'No Religioso': 'No religioso', 'No religiosa': 'No religioso', 'Desconocido': None},
 'geschlecht': {'Hombres': 'Hombre', 'Mujeres': 'Mujer'},
 'alter': {'Menores de 30': '<30', '< 30': '<30', 'De 30 a 60': '30-60', '30 - 60': '30-60', 'Mayores de 60': '>60', '> 60': '>60',
           'De 0 a 12': '0-12', 'De 13 a 18': '13-18', 'De 19 a 35': '19-35', 'De 36 a 65': '36-65', 'Más de 65': '>65'},
 'fortbewegung': {'Biciclet': 'Bicicleta'},
 'beruf': {'Tecnicos': 'Técnicos', 'Religiosas/os': 'Religiosas'},
 'region': {'Valencia': 'Comunidad Valenciana', 'Euskadi': 'País Vasco', 'Pais Vasco': 'País Vasco', 'Andalucia': 'Andalucía', 'Aragon': 'Aragón',
            'Castilla la Mancha': 'Castilla La Mancha', 'Españoles en el extranjero': 'Españoles residentes en el extranjero',
            'Residentes Extranjero': 'Residentes en el extranjero', 'Extranjeros residentes en España': 'Extranjeros', 'Seleccionar': None},
 'land': {'Desconocido': None, '(ohne Angabe)': None},
 'startort': {'Desconocido': None, '(ohne Angabe)': None},
}
def kanon(dim, name):
    a = ALIAS.get(dim, {})
    return a[name] if name in a else name

namen = collections.defaultdict(list)
index = {}
def idx(dim, name):
    k = (dim, name)
    if k not in index:
        index[k] = len(namen[dim]); namen[dim].append(name)
    return index[k]

jsum = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
for j, d, n, w in con.execute("SELECT jahr, dimension, name, wert FROM werte"):
    n = kanon(d, n)
    if n is not None: jsum[d][str(j)][n] += w
msum = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int))))
for j, m, d, n, w in con.execute("SELECT jahr, monat, dimension, name, wert FROM monate"):
    n = kanon(d, n)
    if n is not None: msum[d][str(j)][str(m)][n] += w
jahr = {d: {j: [[idx(d, n), w] for n, w in sorted(v.items(), key=lambda x: -x[1])] for j, v in ys.items()} for d, ys in jsum.items()}
monat = {d: {j: {m: [[idx(d, n), w] for n, w in sorted(v.items(), key=lambda x: -x[1])] for m, v in ms.items()} for j, ms in ys.items()} for d, ys in msum.items()}

gesamt = collections.defaultdict(dict)
for j, m, n, w in con.execute("SELECT jahr, monat, name, wert FROM monat_kennzahlen"):
    gesamt[str(j)].setdefault(str(m), {})[n] = w

sprache = {l: s for l, s, h in con.execute("SELECT land, sprache, hinweis FROM land_sprache") if s}
stand = con.execute("SELECT MAX(stand) FROM tagesstand").fetchone()[0]
kenn = collections.defaultdict(dict)
for j, n, w in con.execute("SELECT jahr, name, wert FROM kennzahlen"):
    kenn[str(j)][n] = w

out = {'stand': stand, 'namen': namen, 'jahr': jahr, 'monat': monat, 'gesamt': gesamt,
       'sprache_land': sprache, 'kennzahlen': kenn}
pfad = os.path.join(DATEN, 'statistik-voll.json')
with open(pfad, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
print('geschrieben', pfad, os.path.getsize(pfad) // 1024, 'KB')
