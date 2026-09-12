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
