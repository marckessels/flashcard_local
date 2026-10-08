# Validatie v4

Vier geautomatiseerde tests geslaagd op 8 oktober 2026. De integratietest doorloopt bestaande flashcards, Good-beoordeling, import zonder verlies van bestaande decks, typvragen in beide richtingen, herhaling na fouten, flashcards omdraaien, voortgang per richting, bewaren na nieuwe sessie, handmatig toevoegen, bewerken en verwijderen.

Normalisatie en CSV/JSON/geplakte import zijn afzonderlijk getest, inclusief ongeldige invoer. De tests werken met een tijdelijke database; de oorspronkelijke database wordt niet gewijzigd.

Omgeving: Python 3.12, Streamlit 1.65.0, streamlit-hotkeys 0.6.0. Streamlit meldt de bestaande use_container_width-optie als verouderd; deze werkt in de geteste versie. Geen handmatige browsertest uitgevoerd.
