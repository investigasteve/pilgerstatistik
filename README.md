# pilgerstatistik

Sammelt die Pilgerstatistik der Oficina del Peregrino (Santiago de Compostela) und archiviert sie mit Datum.

## Was hier läuft

| Was | Wie | Ergebnis |
|---|---|---|
| Tägliche Abfrage des öffentlichen Berichts (Power BI) | GitHub Actions, jede Nacht 03:17 UTC (`taeglich.yml`) | `data/powerbi/JJJJ-MM-TT/` mit Rohantworten, CSV, Screenshot, `diagnose.json` |
| Jahresberichte 2004 bis heute (PDF) | Einmal von Hand starten (`jahresberichte.yml`) | `data/jahre/JJJJ.json` und `data/jahre/alle-jahre.csv` (jahr, tabelle, name, wert, prozent) |

Tabellen der Jahresberichte: Sexos, Medios, Motivos, Edades, Países, Autonomías, Caminos, Procedencias, Profesiones.

## Quellen
- Aktuell: öffentlicher Bericht auf https://oficinadelperegrino.com/en/statistics-2/
- Bis 2019: PDF-Jahresberichte, z. B. https://oficinadelperegrino.com/wp-content/uploads/2016/02/peregrinaciones2019.pdf

## Erster Start
Reiter **Actions** → „Jahresberichte … einlesen“ → Run workflow. Danach „Täglich Pilgerdaten sammeln“ → Run workflow. Das Ergebnis jedes Laufs steht in der Kurzübersicht des Laufs und als Dateien im Ordner `data`.
