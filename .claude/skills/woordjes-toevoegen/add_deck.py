"""Append a vocabulary deck to shared_decks.json without reformatting the file.

Usage: python .claude/skills/woordjes-toevoegen/add_deck.py work/new_deck.json

The input file holds ONE deck object:
  {"name": ..., "summary": ..., "source_language": "NL", "target_language": "DE",
   "id_prefix": "duits-l7", "cards": [{"front": ..., "back": ...}, ...]}
Card ids are generated as <id_prefix>-001, -002, ... Validation mirrors
load_package() in app.py. Refuses to touch an existing deck name.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "shared_decks.json"
CLOSING = "\n    }\n  ]\n}"


def fail(msg):
    sys.exit(f"FOUT: {msg}")


def main():
    if len(sys.argv) != 2:
        fail("geef het pad naar het deck-JSON-bestand mee")
    deck = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    name = str(deck.get("name", "")).strip()
    prefix = str(deck.get("id_prefix", "")).strip()
    if not name:
        fail("deck heeft geen naam")
    if not prefix:
        fail("id_prefix ontbreekt")
    cards = deck.get("cards")
    if not isinstance(cards, list) or not cards:
        fail("cards-lijst is leeg")
    for i, card in enumerate(cards, 1):
        for key in ("front", "back"):
            value = card.get(key)
            if not isinstance(value, str) or not value.strip():
                fail(f"kaart {i}: lege {key}")
            if any(not part.strip() for part in value.split("|")):
                fail(f"kaart {i}: leeg alternatief rond '|' in {key}")

    text = TARGET.read_text(encoding="utf-8")
    existing = json.loads(text)
    if name in {d.get("name") for d in existing["decks"]}:
        fail(f"deck '{name}' bestaat al; kies een andere naam")
    used_prefixes = {str(c.get("id", "")).rsplit("-", 1)[0]
                     for d in existing["decks"] for c in d.get("cards", [])}
    if prefix in used_prefixes:
        fail(f"id_prefix '{prefix}' is al in gebruik")

    width = max(3, len(str(len(cards))))
    header = {
        "name": name,
        "kind": "vocabulary",
        "source_language": deck.get("source_language", "NL"),
        "target_language": deck.get("target_language", ""),
        "description": deck.get("description", "Woordenlijst"),
        "summary": deck.get("summary") or f"{len(cards)} woordparen.",
    }
    lines = ["    },", "    {"]
    lines += [f"      {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},"
              for k, v in header.items()]
    lines.append('      "cards": [')
    card_lines = []
    for i, card in enumerate(cards, 1):
        obj = {"id": f"{prefix}-{i:0{width}d}", "front": card["front"].strip(),
               "back": card["back"].strip(), "tags": card.get("tags", []), "source": "user"}
        card_lines.append("        " + json.dumps(obj, ensure_ascii=False))
    lines.append(",\n".join(card_lines))
    lines.append("      ]")

    stripped = text.rstrip()
    idx = stripped.rfind(CLOSING)
    if idx == -1 or stripped[idx:] != CLOSING:
        fail("onverwacht einde van shared_decks.json; voeg handmatig toe")
    new_text = stripped[:idx] + "\n" + "\n".join(lines) + CLOSING + "\n"

    parsed = json.loads(new_text)  # must still be valid JSON
    assert parsed["decks"][-1]["name"] == name
    TARGET.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"OK: '{name}' toegevoegd met {len(cards)} kaarten "
          f"({prefix}-{1:0{width}d} t/m {prefix}-{len(cards):0{width}d}).")


if __name__ == "__main__":
    main()
