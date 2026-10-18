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
python3 scripts/images/import_local_recipe_images.py
python3 scripts/images/verify_recipe_images.py
```

Das Importskript prüft Rezept-ID, Bildnummer, Dateiformat und Dubletten. Es schreibt nur Referenzen auf tatsächlich vorhandene Dateien in beide JSON-Dateien, entfernt leere Bildplatzhalter und erzeugt den gemeinsamen Bildkatalog. Wiederholtes Ausführen ist möglich. Das Prüfsript prüft Dateiinhalte, alle Referenzen, die gemeinsame Reihenfolge und die Bildnachweise.

## Bilder im Admin-Bereich

Für neue oder bearbeitete Rezepte lassen sich bis zu drei Fotos über die Dateiauswahl mit Vorschau hinzufügen, austauschen oder entfernen. Die App zeigt den Rezeptnamen und die ausgewählte Herkunft neben den Bildplätzen. Bei neuen Rezepten fließt der Ländercode, sofern gewählt, in die Rezept-ID ein; Gerichte mit demselben Namen aus verschiedenen Ländern erhalten so getrennte Bildordner. Die App erkennt gleiche Bildinhalte bereits bei der Auswahl und der Backend-Service prüft sie erneut beim Speichern.

Diese Fotos werden unter dem konfigurierten Benutzerdatenordner in `recipe_images/<rezept-id>/image_0N-<kennung>.<format>` gespeichert. Der Dateiname erhält eine eindeutige Kennung, damit ein vorhandenes Foto beim Austauschen nicht überschrieben wird. Die Referenzen stehen im Rezept-Overlay `recipe-edits.json`. Beim Entfernen eines Fotos oder Rezepts löscht die App nur dessen importierte Benutzerdateien; der gebündelte Katalog bleibt unverändert. Für diese Benutzerfotos liegen noch keine Urheber- oder Lizenzangaben vor, daher zeigt die Galerie den Rechte-Status als offen an.

## Rechte und Urhebernachweise

Für lokal hinzugefügte Dateien legt der Import `data/recipe_images/LOCAL_IMAGE_CREDITS.json` an. Neue Bilder erhalten zunächst `rights_status: "pending"`; Urheber oder Lizenz werden nicht geraten. Trage für jede Datei `author`, `license` und bei externen Bildern `source_url` sowie gegebenenfalls `license_url` ein. Setze `rights_status` danach auf `approved` für eine ausdrücklich erteilte Projektnutzung oder `licensed` für eine überprüfte Lizenz und führe `python3 scripts/images/import_local_recipe_images.py` erneut aus. Ändert sich die Bilddatei, setzt der Import ihren Rechte-Status vorsichtshalber wieder auf `pending`.

`IMAGE_ATTRIBUTIONS.csv` und `.md` werden aus diesen Angaben erzeugt. Die App zeigt den Status oder den Urhebernachweis beim Bild an. `python3 scripts/images/verify_recipe_images.py` zählt offene Rechte; für eine Veröffentlichung müssen sie geklärt sein.

Alle 586 Rezepte haben bereits ein lokales Bild. Weitere Bilder können mit dem Importskript eingebunden werden; der frühere automatische Wikimedia-Downloader wird dafür nicht benötigt. Alle vorhandenen Bildnachweise stehen derzeit auf `pending` und müssen vor einer Veröffentlichung geprüft werden.

## Kompakte Desktop-Pakete

Der Windows- und Linux-Build ruft `scripts/build/common/stage_catalogs.py` auf. Das Skript erstellt in `build/catalogs` JPEG-Kopien mit maximal 960 Pixeln Kantenlänge und Qualitätswert 74. Es passt die Bildpfade in Kopien beider Sprachkataloge sowie in den Bildnachweisen an. Die 586 PNG-Quelldateien (255 MiB) ergeben dabei etwa 26 MiB JPEG-Dateien; Benutzerbilder werden nicht verändert. Für den Build wird Pillow aus `src/requirements-build.txt` benötigt. Der Pakettest lädt ein Bild mit Kivy, und der Windows-CI-Job prüft zusätzlich die installierte Anwendung. Die Originaldateien und ihre Prüfsummen bleiben Grundlage für Import und Rechteprüfung.
