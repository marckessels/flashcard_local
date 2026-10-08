"""Vocabulary import and explicit, conservative answer matching."""
import csv
import io
import json
import re
import unicodedata
import uuid
import hashlib


def normalize(value, ignore_accents=False):
    value = unicodedata.normalize('NFKC', value).casefold()
    value = value.translate(str.maketrans({'’': "'", '‘': "'", '–': '-', '—': '-'}))
    value = ' '.join(value.split()).strip(' .!?')
    if ignore_accents:
        value = ''.join(c for c in unicodedata.normalize('NFD', value)
                        if not unicodedata.combining(c))
    return value


def matches(answer, expected, ignore_accents=False):
    actual = normalize(answer, ignore_accents)
    return bool(actual) and any(actual == normalize(x, ignore_accents)
                               for x in expected.split('|') if x.strip())


def parse_pairs(text, kind='paste'):
    if kind == 'json':
        data = json.loads(text.lstrip('\ufeff'))
        rows = data.get('pairs') if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError('JSON: gebruik een lijst of een object met een pairs-lijst.')
    else:
        text = text.lstrip('\ufeff')
        if not text.strip():
            raise ValueError('De woordenlijst is leeg.')
        first = text.splitlines()[0]
        separator = '\t' if '\t' in first else ';' if ';' in first else ',' if ',' in first else '='
        raw = list(csv.reader(io.StringIO(text), delimiter=separator))
        raw = [r for r in raw if any(x.strip() for x in r)]
        header = [x.strip().casefold() for x in raw[0]]
        if header in (['nl', 'en'], ['front', 'back'], ['source', 'target']):
            raw = raw[1:]
        rows = raw
    result = []
    seen = set()
    for i, row in enumerate(rows, 1):
        if isinstance(row, dict):
            left = row.get('nl', row.get('front', row.get('source')))
            right = row.get('en', row.get('back', row.get('target')))
        elif isinstance(row, list) and len(row) == 2:
            left, right = row
        else:
            raise ValueError(f'Woordpaar {i}: verwacht precies twee velden.')
        if not isinstance(left, str) or not isinstance(right, str) or not left.strip() or not right.strip():
            raise ValueError(f'Woordpaar {i}: beide woorden moeten niet-lege tekst zijn.')
        left, right = left.strip(), right.strip()
        if any(not x.strip() for value in (left, right) for x in value.split('|')):
            raise ValueError(f'Woordpaar {i}: lege alternatieve vertaling.')
        pair = (left, right)
        if pair not in seen:
            result.append({'id': 'vocab-' + uuid.uuid4().hex, 'front': left,
                           'back': right, 'tags': [], 'source': 'user'})
            seen.add(pair)
    if not result:
        raise ValueError('De woordenlijst bevat geen woordparen.')
    return result


def make_deck(name, cards, source_language='NL', target_language='EN'):
    if not name.strip() or not source_language.strip() or not target_language.strip():
        raise ValueError('Vul naam en beide talen in.')
    return {'name': name.strip(), 'kind': 'vocabulary',
            'source_language': source_language.strip(), 'target_language': target_language.strip(),
            'cards': cards, 'description': 'Woordenlijst', 'summary': ''}


def load_example_csv(path):
    """Load the bundled English/Dutch list with stable progress identifiers."""
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not {'Engels', 'Nederlands'}.issubset(reader.fieldnames or []):
            raise ValueError('Voorbeeldwoordenlijst mist Engels/Nederlands-kolommen.')
        cards = []
        seen = set()
        for number, row in enumerate(reader, 2):
            en, nl = row['Engels'].strip(), row['Nederlands'].strip()
            if not en or not nl:
                raise ValueError(f'Voorbeeldwoordenlijst: leeg woord op regel {number}.')
            cid = 'example-en-nl-' + hashlib.sha256(json.dumps([en, nl], ensure_ascii=False).encode('utf-8')).hexdigest()[:24]
            if cid in seen:
                continue
            seen.add(cid)
            cards.append({'id': cid, 'front': en, 'back': nl,
                          'tags': [f"Foto {row['Foto']}"] if row.get('Foto') else [],
                          'source': path.name})
    deck = make_deck('Engels - Nederlands (voorbeeld)', cards, 'EN', 'NL')
    deck['description'] = 'Voorbeeldwoordenlijst uit engels_nederlands_woordjes.csv'
    return deck
