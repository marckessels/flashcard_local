---
name: woordjes-toevoegen
description: Voeg een woordenlijst (meestal foto's vanaf de telefoon) toe als nieuw vocabulary-deck in shared_decks.json, test en commit. Gebruik bij "/woordjes-toevoegen <decknaam>" of als de gebruiker foto's van woordjes stuurt om toe te voegen.
argument-hint: <decknaam, bv. "Duits - Lektion 7">
---

# Woordenlijst toevoegen

Doel: zo weinig mogelijk tokens. Lees `shared_decks.json`, `app.py` of andere
code NIET. Het script hieronder doet het werk en de validatie.

## Stappen

1. **Lees de foto('s)** die de gebruiker meestuurde. Neem elk woordpaar over
   precies zoals het er staat (spelling, lidwoorden, meervouden, accenten).
   - `front` = Nederlands, `back` = de vreemde taal (zoals in de bestaande decks),
     tenzij de gebruiker iets anders zegt.
   - Meerdere goede antwoorden/varianten: scheid met ` | `
     (bv. `"front": "tas | zak"`). Nooit een leeg deel rond `|`.
   - Duitse zelfstandige naamwoorden: `der Hund, die Hunde` (lidwoord +
     meervoud als dat op de lijst staat).
   - Onleesbaar of twijfelachtig woord? Niet gokken: zet het in je eindbericht.

2. **Decknaam**: gebruik de naam uit het argument. Zonder argument: kies een
   naam in de stijl `Taal - Hoofdstuk/Thema` (bv. `Duits - Lektion 7`,
   `Engels - Travel & Home`, `Latijn - Castor et Pollux 7`). Kies een korte,
   nieuwe `id_prefix` in kleine letters (bv. `duits-l7`, `engels-th2`, `cep7`).

3. **Schrijf** `work/new_deck.json` (de map `work/` is lokaal kladwerk):

   ```json
   {
     "name": "Duits - Lektion 7",
     "id_prefix": "duits-l7",
     "source_language": "NL",
     "target_language": "DE",
     "summary": "35 woordparen uit Lektion 7.",
     "cards": [
       {"front": "de hond", "back": "der Hund, die Hunde"}
     ]
   }
   ```
   Taalcodes: `EN`, `DE`, `FR`, `LA`, `ES`.

4. **Voeg toe** (valideert, maakt card-ids, laat de rest van het bestand intact):

   ```
   python .claude/skills/woordjes-toevoegen/add_deck.py work/new_deck.json
   ```
   Bij `FOUT:` de oorzaak in `work/new_deck.json` herstellen en opnieuw draaien.
   Het script weigert een bestaande decknaam: een bestaand deck aanvullen doe
   je NIET met deze skill (de database gaat voor op het JSON-bestand); meld
   dat aan de gebruiker.

5. **Test** met de projectomgeving:

   ```
   .venv/Scripts/python.exe -m unittest discover -s . -p "test_*.py"
   ```
   Bestaat `.venv` niet (bv. in een cloudsessie), gebruik dan `python` en
   installeer eerst `python -m pip install -r requirements.txt`. Falen er
   tests: stoppen en melden, niet committen.

6. **Commit** (alleen `shared_decks.json`, niet pushen):

   ```
   git add shared_decks.json
   git commit -m "Add vocabulary deck '<naam>' (<aantal> words)"
   ```

7. **Eindbericht** (kort, Nederlands): decknaam, aantal woorden, eventuele
   twijfelgevallen. Vermeld dat het deck verschijnt na het (her)starten of
   verversen van de app.
