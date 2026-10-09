import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from vocabulary import parse_pairs, matches, make_deck


class VocabularyTests(unittest.TestCase):
    def test_import_formats(self):
        for text, kind in [('nl,en\nhuis,house\nfiets,bike', 'csv'),
                           ('huis = house\nfiets = bike', 'paste'),
                           ('nl;en\nhuis;house\nfiets;bike', 'csv'),
                           ('huis\thouse\nfiets\tbike', 'paste'),
                           (json.dumps({'pairs': [{'nl':'huis', 'en':'house'}, {'nl':'fiets','en':'bike'}]}), 'json')]:
            cards = parse_pairs(text, kind)
            self.assertEqual([c['back'] for c in cards], ['house', 'bike'])
            self.assertEqual(len({c['id'] for c in cards}), 2)

    def test_validation(self):
        for text in ['', 'nl,en', 'huis,', 'huis,house,extra', 'huis=house|']:
            with self.assertRaises(ValueError):
                parse_pairs(text)
        with self.assertRaises(ValueError):
            parse_pairs('{"pairs":[{"nl":3,"en":"three"}]}', 'json')
        self.assertEqual(len(parse_pairs('huis=house\nhuis=house')), 1)

    def test_answer_matching(self):
        self.assertTrue(matches('  BIKE! ', 'bicycle | bike'))
        self.assertTrue(matches('ice   cream', 'ice cream'))
        self.assertTrue(matches('don’t', "don't"))
        self.assertFalse(matches('cafe', 'café'))
        self.assertTrue(matches('cafe', 'café', True))
        self.assertFalse(matches('house', 'the house'))
        self.assertFalse(matches('bkie', 'bike'))
        self.assertFalse(matches('', 'bike'))

    def test_app_workflow_and_existing_study(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).parent
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            folder = Path(folder)
            for name in ('app.py', 'vocabulary.py', 'vocabulary_ui.py'):
                shutil.copy(root / name, folder / name)
            at = AppTest.from_file(str(folder / 'app.py'), default_timeout=20).run()
            self.assertFalse(at.exception)
            self.assertFalse(any(b.key == 'v_import' for b in at.button))
            at.radio(key='screen').set_value('🧠 Leren').run()
            # Existing flashcards and review scheduling still work.
            next(b for b in at.button if b.label == 'Toon antwoord').click().run()
            self.assertFalse(at.exception)
            next(b for b in at.button if b.label == 'Good').click().run()
            self.assertFalse(at.exception)
            # Create a vocabulary deck without replacing the study deck.
            at.radio(key='screen').set_value('🌍 Woordjes').run()
            at.text_input(key='v_name').set_value('Testwoorden')
            at.text_area(key='v_paste').set_value('fiets=bicycle | bike')
            at.button(key='v_import').click().run()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.session_state.data['decks']), 2)
            at.radio(key='v_mode').set_value('Antwoord typen').run()
            next(x for x in at.text_input if x.label == 'Jouw vertaling').set_value('wrong')
            next(b for b in at.button if b.label == 'Controleer antwoord').click().run()
            self.assertTrue(any('Nog oefenen' in e.value for e in at.error))
            self.assertEqual(len(at.session_state.v_queue), 1)
            self.assertEqual(next(x for x in at.text_input if x.label == 'Jouw vertaling').value, '')
            self.assertFalse(any(b.label == 'Volgend woord' for b in at.button))
            # Rerunning feedback must not count twice.
            at.run()
            next(x for x in at.text_input if x.label == 'Jouw vertaling').set_value(' BIKE! ')
            next(b for b in at.button if b.label == 'Controleer antwoord').click().run()
            self.assertTrue(any('Goed!' in e.value for e in at.success))
            self.assertEqual(at.session_state.v_queue, [])
            at.radio(key='v_direction').set_value(1).run()
            self.assertEqual(len(at.session_state.v_queue), 1)
            next(x for x in at.text_input if x.label == 'Jouw vertaling').set_value('fiets')
            next(b for b in at.button if b.label == 'Controleer antwoord').click().run()
            self.assertFalse(at.exception)
            at.radio(key='v_mode').set_value('Flashcards').run()
            next(b for b in at.button if b.label == 'Draai woordkaart om').click().run()
            self.assertTrue(any(e.value == 'fiets' for e in at.info))
            next(b for b in at.button if b.label == 'Juist onthouden').click().run()
            self.assertFalse(at.exception)
            conn = sqlite3.connect(folder / 'studyflash_local.db')
            self.assertEqual(conn.execute('SELECT attempts,correct FROM vocabulary_progress WHERE direction=0').fetchone(), (2,1))
            self.assertEqual(conn.execute('SELECT attempts,correct FROM vocabulary_progress WHERE direction=1').fetchone(), (2,2))
            self.assertEqual(conn.execute('SELECT MAX(reps) FROM progress WHERE deck="Demo"').fetchone()[0], 1)
            conn.close()
            # Data persists after a new session.
            fresh = AppTest.from_file(str(folder / 'app.py'), default_timeout=20).run()
            self.assertFalse(fresh.exception)
            self.assertEqual(len(fresh.session_state.data['decks']), 2)
            fresh.selectbox[0].set_value('Testwoorden').run()
            fresh.radio(key='screen').set_value('✏️ Kaarten').run()
            fresh.text_input(key='new_front').set_value('huis')
            fresh.text_area(key='new_back').set_value('house')
            next(b for b in fresh.button if b.label == 'Kaart toevoegen').click().run()
            self.assertFalse(fresh.exception)
            self.assertEqual(len(fresh.session_state.data['decks'][1]['cards']), 2)
            cid = fresh.session_state.data['decks'][1]['cards'][1]['id']
            fresh.selectbox(key='edit_card_Testwoorden').set_value(cid).run()
            fresh.text_input(key=f'fTestwoorden{cid}').set_value('het huis')
            fresh.button(key=f'sTestwoorden{cid}').click().run()
            self.assertEqual(fresh.session_state.data['decks'][1]['cards'][1]['front'], 'het huis')
            fresh.button(key=f'dTestwoorden{cid}').click().run()
            self.assertFalse(fresh.exception)
            self.assertEqual(len(fresh.session_state.data['decks'][1]['cards']), 1)

    def test_large_deck_only_renders_active_screen(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).parent
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            folder = Path(folder)
            for name in ('app.py', 'vocabulary.py', 'vocabulary_ui.py'):
                shutil.copy(root / name, folder / name)
            cards = parse_pairs('\n'.join(f'woord{i}=word{i}' for i in range(288)))
            (folder / 'shared_decks.json').write_text(json.dumps({'decks': [make_deck('Groot', cards)]}), encoding='utf-8')
            at = AppTest.from_file(str(folder / 'app.py'), default_timeout=20).run()
            self.assertFalse(at.exception)
            self.assertFalse(any(x.key == 'new_front' for x in at.text_input))
            at.radio(key='screen').set_value('🌍 Woordjes').run()
            at.radio(key='v_mode').set_value('Antwoord typen').run()
            self.assertFalse(at.exception)
            self.assertLess(len(at.text_input) + len(at.text_area) + len(at.button), 15)
            # A vocabulary answer must not touch the regular study tables.
            statements = []
            at.session_state.db_connection.set_trace_callback(statements.append)
            next(x for x in at.text_input if x.label == 'Jouw vertaling').set_value('wrong')
            next(b for b in at.button if b.label == 'Controleer antwoord').click().run()
            self.assertFalse(at.exception)
            self.assertFalse(any('INSERT OR IGNORE INTO progress' in x or 'stamp_progress' in x for x in statements))
            at.session_state.db_connection.set_trace_callback(None)
            at.radio(key='screen').set_value('✏️ Kaarten').run()
            self.assertFalse(at.exception)
            self.assertEqual(sum(x.label == 'Voorkant' for x in at.text_input), 1)
            self.assertLess(len(at.text_input) + len(at.text_area) + len(at.button), 15)


if __name__ == '__main__':
    unittest.main()

