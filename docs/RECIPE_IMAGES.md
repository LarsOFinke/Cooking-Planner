# Rezeptbilder

Die beiden Sprachkataloge verwenden dieselben 586 Rezept-IDs. Bilder liegen einmalig unter `data/recipe_images/<rezept-id>/image_01.webp` oder `.png`/`.jpg` und werden in `recipes_de.json` und `recipes_en.json` identisch referenziert. Pro Gericht sind ein bis drei Bilder möglich: `image_01`, `image_02`, `image_03`. WebP, PNG und JPEG werden unterstützt. Originaldateien bleiben beim Import unverändert.

## Eigene Bilddateien einbinden

Lege neue Dateien in den Ordner der passenden Rezept-ID und nummeriere sie fortlaufend. Beispiel:

```text
data/recipe_images/dz-algerischer-couscous/image_01.png
data/recipe_images/dz-algerischer-couscous/image_02.jpg
```

Die Schreibweise muss `image_01`, `image_02`, `image_03` verwenden; dieselbe Nummer darf nicht mit zwei Dateiendungen vorkommen. Anschließend:

```bash
python3 -m pip install -r scripts/images/requirements-images.txt
make images-sync
```

`make images-sync` prüft Rezept-ID, Bildnummer, Dateiformat und Dubletten. Es schreibt nur Referenzen auf tatsächlich vorhandene Dateien in beide JSON-Dateien, entfernt leere Bildplatzhalter und erzeugt den gemeinsamen Bildkatalog. Wiederholtes Ausführen ist möglich. `make images-verify` prüft Dateiinhalte, alle Referenzen, die gemeinsame Reihenfolge und die Bildnachweise.

## Rechte und Urhebernachweise

Für lokal hinzugefügte Dateien legt der Import `data/recipe_images/LOCAL_IMAGE_CREDITS.json` an. Neue Bilder erhalten zunächst `rights_status: "pending"`; Urheber oder Lizenz werden nicht geraten. Trage für jede Datei `author`, `license` und bei externen Bildern `source_url` sowie gegebenenfalls `license_url` ein. Setze `rights_status` danach auf `approved` für eine ausdrücklich erteilte Projektnutzung oder `licensed` für eine überprüfte Lizenz und führe `make images-sync` erneut aus. Ändert sich die Bilddatei, setzt der Import ihren Rechte-Status vorsichtshalber wieder auf `pending`.

`IMAGE_ATTRIBUTIONS.csv` und `.md` werden aus diesen Angaben erzeugt. Die App zeigt den Status oder den Urhebernachweis beim Bild an. `make images-verify` zählt offene Rechte; für eine Veröffentlichung müssen sie geklärt sein.

## Zusätzliche Commons-Bilder

`make images` übernimmt zuerst lokale Bilder und sucht danach höchstens zwei Bilder je Gericht auf Wikimedia Commons. Der Downloader kann per `--max-images 3` bis zu drei Bilder ergänzen. Er akzeptiert nur erkannte CC0-, CC-BY-, CC-BY-SA- oder Gemeinfrei-Metadaten und speichert Quellen und Lizenzlinks. Prüfe jeden automatischen Treffer vor Veröffentlichung anhand der verlinkten Originaldatei. Ohne Internetverbindung bleiben bereits eingebundene lokale Bilder erhalten.
