# StudyFlash Local

Een lokale Streamlit-studieapp geïnspireerd op de zichtbare functies van Studyflash.

## Wat zit erin?
- Decks/cursussen
- Import van ChatGPT-gegenereerde JSON
- Flashcards
- Spaced repetition met een eenvoudige SM-2-achtige scheduler
- Quiz/self-test
- Samenvatting + kernpunten
- Kaarten bewerken, toevoegen en verwijderen
- Voortgang en mastery
- Lokale SQLite-opslag van leerprogressie
- Export van het studiepakket

Studyflash zelf noemt momenteel o.a. bestanden uploaden, samenvattingen, uitleg, flashcards, quizzen/oefenexamens, spaced repetition, persoonlijke leerplannen en voortgang als functies. Deze app reproduceert de belangrijkste lokale leerfuncties, maar niet hun online account/cloud/backend of hun proprietary AI.

## Installeren

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open daarna de lokale URL die Streamlit toont.

## AI-workflow

1. Open ChatGPT.
2. Upload je PDF, Word-document, PowerPoint, notities enz.
3. Gebruik `CHATGPT_PROMPT.txt`.
4. Laat ChatGPT uitsluitend de JSON produceren.
5. Sla die tekst op als bijvoorbeeld `biologie.json`.
6. Open StudyFlash Local en importeer het JSON-bestand.
7. Leer de kaarten. De app slaat je herhalingsstatus lokaal op in `studyflash_local.db`.

## CSV
Een eenvoudige CSV kan ook worden geïmporteerd met kolommen:
`front,back,tags`
Tags worden gescheiden met `|`.

## Belangrijk
De app bevat bewust geen OpenAI API-koppeling. Daardoor blijft het AI-gedeelte in jouw normale ChatGPT-chat zitten en kun je de inhoud eerst controleren voordat die in de leerapp terechtkomt.

- Tijdens het leren direct een nieuwe kaart toevoegen
"# flashcard_local" 
"# flashcard_local" 

## Nieuw in v4: woordenlijsten

Ga naar **Woordjes** en open **Woordenlijst importeren of plakken**. Geef de lijst een unieke naam en stel de twee talen in (standaard NL en EN). Upload CSV/JSON of plak woordparen. Klik op **Woordenlijst toevoegen**; de bestaande decks blijven behouden.

CSV (komma, puntkomma of tab; UTF-8):

```csv
nl,en
huis,house
fiets,bicycle | bike
```

JSON:

```json
{"pairs":[{"nl":"huis","en":"house"},{"nl":"fiets","en":"bicycle | bike"}]}
```

Ook een JSON-lijst zonder het pairs-object werkt. In plaats van nl/en kun je source/target of front/back gebruiken. Een volledig StudyFlash-pakket importeer je via de bestaande import in de zijbalk.

Plakken:

```text
huis = house
fiets = bicycle | bike
```

Gebruik precies twee velden per regel. Bij komma's in een woord gebruik je geldige CSV-aanhalingstekens. Zet toegestane alternatieven aan beide kanten achter een |. Exact dubbele woordparen worden één keer geïmporteerd. Ongeldige invoer wordt afgewezen zonder gedeeltelijke import.

Kies **NL → EN** of **EN → NL** en daarna **Flashcards** of **Antwoord typen**. Bij flashcards draai je de kaart om en beoordeel je zelf of je het antwoord wist. Bij typen volgt automatische feedback, met alle toegestane antwoorden. Foute woorden komen opnieuw terug totdat de ronde klaar is.

Antwoordcontrole negeert hoofdletters, extra witruimte, afsluitende .!? en typografische apostroffen. Accenten tellen standaard mee, maar kunnen worden genegeerd via de checkbox. Geen automatische acceptatie van spelfouten of weggelaten lidwoorden. Elk alternatief telt afzonderlijk als goed antwoord.

Via **Kaarten** kun je woordparen handmatig toevoegen, aanpassen en verwijderen. Ook **Kaart toevoegen tijdens het leren** blijft beschikbaar. Een bestaand deck kun je in Woordjes omzetten naar een woordenlijst.

De woordjesvoortgang blijft lokaal bewaard per gebruiker, deck en richting. Beide oefenvormen delen deze telling binnen dezelfde richting. Woordjes oefent alle woorden en houdt zijn eigen telling bij; **Leren** behoudt de bestaande spaced-repetitionplanning in de oorspronkelijke front/back-richting. Stampen, samenvattingen, kernpunten en bestaande leerstatus blijven beschikbaar. Sneltoetsen in Leren zijn nu optioneel; laat ze uit tijdens typen of invoeren van kaarten.

## Bestaande installatie bijwerken

1. Stop de oude app.
2. Maak een kopie van de gehele bestaande appmap, vooral `studyflash_local.db` en `shared_decks.json`.
3. Kopieer `app.py`, `vocabulary.py`, `vocabulary_ui.py`, `requirements.txt` en eventueel deze README en het startbestand naar de bestaande map. Behoud je database en shared_decks.json.
4. Voer in die map uit:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Voor een nieuwe installatie met Python op je PATH:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Daarna kun je ook dubbelklikken op `start_studyflash.bat`. Open http://localhost:8501 als de browser niet vanzelf opent. De database wordt vanaf v4 altijd naast app.py opgeslagen, ook als je vanuit een andere map start.

**Back-up:** Exporteer studiepakket bewaart decks en kaarten, niet de leerstatus. Kopieer de SQLite-database terwijl de app gestopt is om alle voortgang te bewaren. De download-ZIP bevat geen persoonlijke database.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
```

Getest op 8 oktober 2026 met Python 3.12 en Streamlit 1.65.0: CSV/JSON/plakken, invoervalidatie, antwoordnormalisatie en alternatieven, beide richtingen, flashcards, fout-herhaling, eenmalig tellen van feedback, persistente opslag, kaarten toevoegen/bewerken/verwijderen en de bestaande spaced-repetitionbeoordeling. Vier tests geslaagd, waaronder een Streamlit AppTest die de gebruikersstappen doorloopt. Geen volledige handmatige browsertest.

## Snellere bediening (9 oktober 2026)

Kies het gewenste onderdeel via **Scherm** bovenaan. Alleen dat onderdeel wordt uitgevoerd. In **Kaarten** selecteer je één kaart om te bewerken. In **Woordjes** vernieuwen antwoordcontrole en de volgende vraag alleen het oefengedeelte. Leerstatus wordt per deck in één databasevraag opgehaald.

Vijf geautomatiseerde tests slagen, inclusief 288 kaarten: slechts één editor, geen verborgen kaartinvoer op het oefenscherm en geen herinitialisatie van de gewone leer-/stamptabellen bij woordantwoorden. De responstijd van de gehoste app is niet gemeten.
